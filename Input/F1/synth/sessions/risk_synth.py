# -*- coding: utf-8 -*-
"""
risk_synth.py — 위험군 주입 세션 합성기 (F1 정답 레이블 설계 §5 구현)
=====================================================================
효준 tasks.py 의 페르소나 합성은 '사람의 다양성'(나이·체력)만 만들고
'상황의 다양성'(정상↔위험)은 못 만든다(강도 곡선을 원본과 공유하므로).
이 모듈은 그 위에, 규격 위험조건(SpO2<90, 과부하+SpO2경고 등)에 정박해
목표 등급이 나오도록 '상황 프로파일'을 세션에 주입한다.

- 계층: 전부 '가상' (규격 조건 정박, 근거 없는 위험 생성 금지)
- 목표 분포(§5): 정상50 / 주의20 / 경고20 / 위험10  (window 기준)
- 정답 생성은 여기서 하지 않는다 — teacher_labels(규칙-오라클)가 별도로 붙인다.
  이 모듈은 '위험이 나올 신호'를 설계할 뿐, 정답은 규칙이 판정한다.
"""
import numpy as np
from dataclasses import dataclass

# ── 규격 상수 (f1_model 과 동일 근거) ──
MAXHR_BASE = 220.0
SPO2_WARN = 94        # 90~94 경고
SPO2_DANGER = 90      # <90 위험

# ── 등급별 상황 프로파일 ──
# 각 값은 '분 단위 신호를 어느 강도로 밀지'를 정하는 목표치.
# 규격 조건에 정박: 경고=SpO2 경고구간+과부하, 위험=SpO2 위험구간.
@dataclass
class SituationProfile:
    name: str                 # 등급명
    hr_ratio_peak: float      # 과부하 구간 최대 심박비율 (MaxHR 대비)
    spo2_floor: float         # 세션 내 SpO2 최저치
    overload_minutes: int     # 과부하(ratio>0.6) 지속 분
    move_drop: float          # 이동량 저하율 0~1 (탈진 표현)
    weight: float             # 목표 분포 비율
    hr_cap: float = 1.0       # 세션 전체 심박비율 상한 (정상 순수화용)
    hr_z_peak: float = 0.0    # 후반 개인편차 목표 (위험 강화용, 0=미주입)


PROFILES = [
    # 등급별 후반 peak 신호를 목표 e1(윈도우 max 기준)에 역산 정합:
    #   정상 e1<0.5, 주의~0.59, 경고~0.79, 위험~0.94 (rule_ref e1 공식 기준)
    # 정상: ratio<0.6(규칙 과부하 경계) 미만 유지 — 3차결과물 "정상 과부하비 0.6 미만".
    SituationProfile("정상", hr_ratio_peak=0.56, spo2_floor=97,
                     overload_minutes=0,  move_drop=0.0, weight=0.50,
                     hr_cap=0.58, hr_z_peak=0.0),
    # 주의: ratio~0.70, spo2 95, hr_z 5 → e1~0.59
    SituationProfile("주의", hr_ratio_peak=0.70, spo2_floor=95,
                     overload_minutes=6,  move_drop=0.2, weight=0.30,
                     hr_cap=0.72, hr_z_peak=5.0),
    # 경고: ratio~0.80, spo2 93, hr_z 9 → e1~0.79
    SituationProfile("경고", hr_ratio_peak=0.80, spo2_floor=93,
                     overload_minutes=8,  move_drop=0.4, weight=0.13,
                     hr_cap=0.82, hr_z_peak=9.0),
    # 위험: ratio~0.92, spo2 88↓, hr_z 14 → e1~0.90+
    SituationProfile("위험", hr_ratio_peak=0.92, spo2_floor=88,
                     overload_minutes=12, move_drop=0.75, weight=0.12,
                     hr_cap=0.96, hr_z_peak=14.0),
]


def apply_situation(sess: dict, prof: SituationProfile, rng, max_hr: float):
    """
    페르소나 세션(sess)에, 등급 상황을 주입한 새 세션 반환.
    세션 후반부에 위험 구간을 배치(산행이 진행될수록 악화하는 자연스러운 서사).
    sess 는 tasks.synth_session 출력과 동일 키 구조를 기대.
    """
    n = len(sess["hr_mean_bpm"])
    out = {k: np.array(v, dtype=float) for k, v in sess.items()}

    # 전체 심박 상한 (정상 순수화 / 등급별 캡)
    cap_hr = prof.hr_cap * max_hr
    out["hr_mean_bpm"] = np.minimum(out["hr_mean_bpm"], cap_hr)
    if "hr_ratio_maxhr" in out:
        out["hr_ratio_maxhr"] = out["hr_mean_bpm"] / max_hr

    if prof.name == "정상":
        return out  # 상한만 적용, 위험 구간 미주입

    # 위험 구간 위치: 세션 후반 overload_minutes 분
    k = min(prof.overload_minutes, n)
    start = n - k

    # 심박: 후반 구간을 hr_ratio_peak 목표로 끌어올림
    target_hr = prof.hr_ratio_peak * max_hr
    ramp = np.linspace(0.0, 1.0, k)
    out["hr_mean_bpm"][start:] = (
        out["hr_mean_bpm"][start:] * (1 - ramp) + target_hr * ramp
        + rng.normal(0, 1.0, k)
    )
    if "hr_ratio_maxhr" in out:
        out["hr_ratio_maxhr"][start:] = out["hr_mean_bpm"][start:] / max_hr

    # 개인편차(hr_z_personal): 후반으로 갈수록 목표까지 상승 (위험 강화 축)
    if "hr_z_personal" in out and prof.hr_z_peak > 0:
        out["hr_z_personal"][start:] = (
            out["hr_z_personal"][start:] * (1 - ramp) + prof.hr_z_peak * ramp
        )

    # SpO2: 후반으로 갈수록 spo2_floor 까지 하강
    out["spo2_min_pct"][start:] = (
        out["spo2_min_pct"][start:] * (1 - ramp) + prof.spo2_floor * ramp
        + rng.normal(0, 0.1, k)
    )
    out["spo2_min_pct"] = np.clip(out["spo2_min_pct"], 85, 99)

    # 이동량: 탈진 표현 — 후반 걸음·속도 저하
    out["steps_1min"][start:] *= (1 - prof.move_drop)
    out["speed_mean_mpm"][start:] *= (1 - prof.move_drop)

    return out


def choose_profile(rng) -> SituationProfile:
    """목표 분포(weight)대로 등급 하나 샘플."""
    r = rng.random()
    cum = 0.0
    for p in PROFILES:
        cum += p.weight
        if r <= cum:
            return p
    return PROFILES[-1]
