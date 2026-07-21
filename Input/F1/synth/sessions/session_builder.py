# -*- coding: utf-8 -*-
"""
session_builder.py — 사람×상황 세션 집합 생성 (결합기)
======================================================
두 축을 곱해 '정상/이상 다수 세션'을 만든다.

- 모듈 A (사람 축): Model.maml.tasks.synth_session — 페르소나별 116분 시계열.
    ※ 재사용(import). 실데이터 도착 시 이 A만 실데이터 로더로 교체.
- 모듈 B (상황 축): risk_synth.apply_situation — 세션에 정상/주의/경고/위험 주입.
- 결합기(여기): A × B. 페르소나 P명 × 상황 4종 = 세션 집합.

산출물: 세션 리스트. 각 세션 = {persona, situation, minutes(dict of arrays)}.
이 세션들이 window 단계(슬라이딩 window)의 입력이 된다.

정답(y)은 여기서 붙이지 않는다 — window 단계에서 규칙-오라클(teacher)이 부착.
이 단계는 '신호(X)를 담은 세션'까지만 만든다.

⚠️ 의존성: Model.maml.tasks (효준 모듈)가 필요하다. 해당 패키지가 병합된
   브랜치·환경에서 실행할 것. 저장소 루트는 SAFE_AGI_REPO 로 덮어쓸 수 있다.
"""
import os
import sys

import numpy as np

# 저장소 루트(Model 패키지 위치)를 경로에 추가. 기본값은 이 파일 기준 상대 추정.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
_DEFAULT_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", "..", ".."))
_REPO = os.environ.get("SAFE_AGI_REPO", _DEFAULT_REPO)
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from Model.maml.tasks import synth_session, load_base_session, demo_personas  # 모듈 A
from risk_synth import PROFILES, apply_situation                              # 모듈 B

MAX_HR_BASE = 220.0


def build_sessions(personas=None, seed0=2000, situations=None):
    """
    페르소나 × 상황 = 세션 집합 생성.
    반환: 리스트[dict] — {persona_name, age, situation, minutes}
    """
    base = load_base_session()
    personas = personas if personas is not None else demo_personas()
    situations = situations if situations is not None else PROFILES

    sessions = []
    sid = 0
    for pi, p in enumerate(personas):
        rng = np.random.default_rng(seed0 + pi)
        # 모듈 A: 이 페르소나의 정상 강도 세션
        sess = synth_session(base, p, rng)
        max_hr = MAX_HR_BASE - p.age
        for prof in situations:
            # 모듈 B: 상황 주입 (정상은 원본 강도, 나머지는 후반 위험구간)
            sit_rng = np.random.default_rng(seed0 * 10 + sid)
            minutes = apply_situation(sess, prof, sit_rng, max_hr)
            sessions.append({
                "session_id": sid,
                "persona_name": p.name,
                "age": p.age,
                "situation": prof.name,
                "minutes": minutes,     # dict[str, np.ndarray], 116분
            })
            sid += 1
    return sessions


if __name__ == "__main__":
    sessions = build_sessions()
    print(f"생성 세션 수: {len(sessions)}")
    from collections import Counter
    by_sit = Counter(s["situation"] for s in sessions)
    print("상황별:", dict(by_sit))
    s0 = sessions[0]
    print(f"예시 세션[0]: {s0['persona_name']} age={s0['age']} "
          f"상황={s0['situation']} 분수={len(s0['minutes']['hr_mean_bpm'])}")
