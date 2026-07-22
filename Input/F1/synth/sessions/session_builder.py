# -*- coding: utf-8 -*-
"""
session_builder.py — 사람×상황 세션 집합 생성 (Phase 2 통합 결합기)
====================================================================
Phase 2 모듈을 결합해 국건영 정박 + 신호 정박 + 상황축 + 급성이상 + 메타를
갖춘 세션 집합을 생성한다.

처리 순서 (한 세션이 만들어지는 흐름):
  1. sample_personas       국건영 정박 페르소나 (사람 축 재료)
  2. synth_session         페르소나 기반 116분 강도곡선 (모듈 A, 효준)
  3. apply_hr_variability  심박 강도비례 변동 + PAMAP2 안전범위   ┐ 사람 축 후처리
  4. apply_spo2_baseline   SpO2 정상 기저·변동 Non-EEG 정박       ┘ (상황 루프 밖, 1회)
  5. apply_situation       상황(정상/주의/경고/위험) 주입 (모듈 B) ┐ 상황 축
  6. maybe_inject_spike    급성 고심박 이상 5% 주입                ┘ (상황 루프 안, 세션별)
  7. person_id/session_id + label_origin 메타 부착

설계 주의:
  - 3·4(사람 축 후처리)는 상황 루프 '밖'에서 1회만. 같은 페르소나의 4개 상황
    세션이 동일한 몸(심박 변동·SpO2 기저)을 공유해야 하기 때문.
  - 6(급성 이상)은 상황 루프 '안'. 세션마다 독립적으로 5% 주입.

정답(y)은 여기서 붙이지 않는다 — window 단계에서 규칙-오라클(teacher)이 부착.

⚠️ 의존성: Model.maml.tasks (효준 모듈). 병합된 브랜치·환경에서 실행.
   저장소 루트는 SAFE_AGI_REPO 로 덮어쓸 수 있다.
"""
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
_DEFAULT_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", "..", ".."))
_REPO = os.environ.get("SAFE_AGI_REPO", _DEFAULT_REPO)
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from Model.maml.tasks import synth_session, load_base_session          # 모듈 A
from risk_synth import PROFILES, apply_situation                       # 모듈 B
from persona_sampler import sample_personas                            # 사람 축(국건영)
from hr_variability import apply_hr_variability                        # 심박 변동+PAMAP2
from spo2_baseline import apply_spo2_baseline                          # SpO2 Non-EEG
from acute_anomaly import maybe_inject_spike                           # 급성 이상 5%
from identity_origin import make_person_id, make_session_id, COLUMN_ORIGIN

MAX_HR_BASE = 220.0


def build_sessions(personas=None, n_personas=20, seed0=2000,
                   situations=None, inject_rate=0.05,
                   by_weight=False, sessions_per_persona=4):
    """
    페르소나 × 상황 = 세션 집합 생성 (Phase 2 통합).

    personas    : None 이면 sample_personas(n_personas) 로 국건영 정박 생성.
    n_personas  : 생성할 페르소나 수 (personas=None 일 때).
    situations  : None 이면 PROFILES(정상/주의/경고/위험).
    inject_rate : 급성 이상 주입률 (기본 5%).
    by_weight   : False 면 페르소나마다 전 상황 1개씩(균등). True 면 각 세션의
                  상황을 프로파일 weight 확률로 샘플(정상>주의>경고>위험 비율 반영).
    sessions_per_persona : by_weight=True 일 때 페르소나당 세션 수.
    반환: 리스트[dict] — {session_id, person_id, persona_name, age, age_band,
                          gender, situation, acute_anomaly_flag, minutes}
    """
    base = load_base_session()
    if personas is None:
        personas = sample_personas(n=n_personas, seed=seed0)
    situations = situations if situations is not None else PROFILES

    # weight 샘플링 준비
    weights = np.array([getattr(s, "weight", 1.0) for s in situations], dtype=float)
    weights = weights / weights.sum()

    sessions = []
    sid = 0
    for pi, p in enumerate(personas):
        # tasks.Persona 로 변환 (synth_session 호환)
        tp = p.to_task_persona() if hasattr(p, "to_task_persona") else p
        max_hr = MAX_HR_BASE - tp.age
        person_id = make_person_id(p)

        # ── 사람 축: 상황 루프 밖에서 1회 (모든 상황이 같은 몸 공유) ──
        rng_body = np.random.default_rng(seed0 + pi)
        sess = synth_session(base, tp, rng_body)
        sess = apply_hr_variability(
            sess, getattr(tp, "hr_std", 12.0),
            np.random.default_rng(seed0 + pi + 100000),
            rest_hr=getattr(tp, "rest_hr", 58.0))
        sess = apply_spo2_baseline(
            sess, getattr(p, "spo2_base", None),
            np.random.default_rng(seed0 + pi + 200000))

        # ── 상황 축: 균등(전 상황 1개씩) 또는 weight 샘플 ──
        if by_weight:
            pick_rng = np.random.default_rng(seed0 * 7 + pi)
            idxs = pick_rng.choice(len(situations), size=sessions_per_persona,
                                   p=weights)
            profs = [situations[i] for i in idxs]
        else:
            profs = situations

        rep_count = {}
        for prof in profs:
            sit_rng = np.random.default_rng(seed0 * 10 + sid)
            minutes = apply_situation(sess, prof, sit_rng, max_hr)

            # ── 급성 이상: 세션별 독립 5% 주입 ──
            minutes, injected = maybe_inject_spike(
                minutes, np.random.default_rng(seed0 * 100 + sid),
                max_hr, rate=inject_rate)

            rep = rep_count.get(prof.name, 0)
            rep_count[prof.name] = rep + 1
            sessions.append({
                "session_id": make_session_id(person_id, prof.name, rep),
                "person_id": person_id,
                "persona_name": getattr(p, "name", f"p{pi}"),
                "age": tp.age,
                "age_band": getattr(p, "age_band", ""),
                "gender": getattr(p, "gender", ""),
                "situation": prof.name,
                "acute_anomaly_flag": int(injected),
                "minutes": minutes,
            })
            sid += 1
    return sessions


def column_origin_map():
    """세션 컬럼 → label_origin (identity_origin 재노출)."""
    return dict(COLUMN_ORIGIN)


if __name__ == "__main__":
    from collections import Counter
    sessions = build_sessions(n_personas=20, seed0=2000)
    print(f"생성 세션 수: {len(sessions)} (페르소나 20 × 상황 4)")
    print("상황별:", dict(Counter(s["situation"] for s in sessions)))
    print("급성이상 주입:", sum(s["acute_anomaly_flag"] for s in sessions),
          f"({sum(s['acute_anomaly_flag'] for s in sessions)/len(sessions)*100:.1f}%)")
    print("고유 person_id:", len(set(s["person_id"] for s in sessions)),
          "(20명 기대, 충돌 시 미만)")
    print()
    s0 = sessions[0]
    print(f"예시 세션: {s0['session_id']}")
    print(f"  {s0['age_band']}{s0['gender']} age{s0['age']} 상황={s0['situation']} "
          f"분수={len(s0['minutes']['hr_mean_bpm'])}")
    hr = s0["minutes"]["hr_mean_bpm"]
    sp = s0["minutes"]["spo2_min_pct"]
    print(f"  심박 {hr.min():.0f}~{hr.max():.0f}, SpO2 {sp.min():.0f}~{sp.max():.0f}")
