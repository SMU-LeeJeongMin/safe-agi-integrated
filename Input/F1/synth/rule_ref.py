# -*- coding: utf-8 -*-
"""
rule_ref.py — 규칙 공식 참조 사본 (검산 전용)
=============================================
Model/f1_model.py 의 compute_e1_e2 를 상대import 없이 재현한다.
⚠️ 정답 생성용이 아니라 '합성 신호가 목표 등급을 내는지' 검산하는 용도.
상수·공식은 f1_model 과 1:1 동일. 원본이 바뀌면 여기도 동기화 필요(단일 출처는 f1_model).
"""

def _clip(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))

W = {"bio": 0.55, "move": 0.20, "accu": 0.15, "env": 0.10}
K_PERSONAL_STD = 8
STEP_BASELINE = 90
SPEED_BASELINE = 52
SPO2_REF = 98
SPO2_FLOOR_RANGE = 8
ACCU_REF_MIN = 120
HEAT_BASE = 28
HEAT_RANGE = 10


def compute_e1_e2(f):
    hr_overload = _clip(f["hr_ratio_maxhr"])
    spo2 = f.get("spo2_min_pct")
    spo2_drop = _clip((SPO2_REF - spo2) / SPO2_FLOOR_RANGE) if spo2 is not None else 0.0
    hr_z = _clip(f["hr_z_personal"] / K_PERSONAL_STD)
    step_drop = _clip((STEP_BASELINE - f["steps_1min"]) / STEP_BASELINE)
    speed_drop = _clip((SPEED_BASELINE - f["speed_mean_mpm"]) / SPEED_BASELINE)
    accu = _clip(f["cumulative_min"] / ACCU_REF_MIN)
    hi = f.get("heat_index")
    heat = _clip((hi - HEAT_BASE) / HEAT_RANGE) if hi is not None else 0.0
    e1 = _clip(0.5 * hr_overload + 0.3 * spo2_drop + 0.2 * hr_z)
    move = _clip(0.5 * step_drop + 0.5 * speed_drop)
    env = _clip(0.6 * heat + 0.4 * f["accident_prior"])
    e2 = _clip(W["bio"] * e1 + W["move"] * move + W["accu"] * accu + W["env"] * env)
    return round(e1, 4), round(e2, 4)


def risk_level(rep):
    if rep >= 0.85:
        return 3, "위험"
    if rep >= 0.65:
        return 2, "경고"
    if rep >= 0.50:
        return 1, "주의"
    return 0, "정상"
