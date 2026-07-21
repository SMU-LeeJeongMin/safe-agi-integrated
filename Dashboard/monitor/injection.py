# 이벤트 주입 (워치 유입값 인위 변동)
# 주입 상수와 F1 확정 공식 기반 재계산 피처 구성을 담당한다.

from __future__ import annotations

from typing import Any

import pandas as pd

from utils.explanation import ref_hr_baseline, to_bool, to_float


# 이벤트 주입 스텝 (버튼 1회당 변동량, 누를 때마다 누적)
INJECT_HR_STEP = 25.0      # 심박 ±bpm (기본 심박 대비 z점수 약 ±1.7 이동)
INJECT_SPO2_STEP = 6.0     # SpO2 ∓%p (실세션 98% 기준 1회에 경고 임계 95% 통과)
INJECT_HR_RANGE = (-75.0, 75.0)    # 누적 상하한
INJECT_SPO2_RANGE = (-6.0, 24.0)   # 누적 상하한 (음수 = SpO2 상승)
INJECT_STEPS_STEP = 10.0   # 걸음 수 ±보 (이동량 저하/재개 유도)
INJECT_STEPS_RANGE = (-100.0, 100.0)  # 누적 상하한

# F1 이벤트 주입 재계산 (Model/f1_model.py 확정 공식 재사용)
def _spo2_grade(value: float) -> str:
    if value >= 95:
        return "정상"
    if value >= 90:
        return "경고"
    return "위험"


def _injected_feature_dict(row: pd.Series, hr_boost: float, spo2_drop: float, steps_delta: float) -> dict[str, Any]:
    baseline = ref_hr_baseline(row)
    hr_new = to_float(row.get("hr_mean_bpm")) + hr_boost
    spo2_new = min(100.0, max(0.0, to_float(row.get("spo2_min_pct")) - spo2_drop))
    ratio_new = hr_new / baseline["max_hr"] if baseline["max_hr"] else 0.0

    # 주의: hr_overload_5min은 원래 "5분 지속" 조건이지만, 주입 데모에서는
    # 지속 이력이 없어 비율 도달 여부로 근사한다 (화면에 근사임을 명시)
    overload_new = to_bool(row.get("hr_overload_5min")) or (hr_boost > 0 and ratio_new >= 0.6)

    return {
        "hr_mean_bpm": hr_new,
        "hr_ratio_maxhr": ratio_new,
        "hr_z_personal": (hr_new - baseline["rest_hr"]) / baseline["rest_std"] if baseline["rest_std"] else 0.0,
        "hr_overload_5min": overload_new,
        "spo2_min_pct": spo2_new,
        "spo2_grade": _spo2_grade(spo2_new),
        # 걸음 주입 시 속도는 What-if와 동일 비율(52 m/min ÷ 90 보/분)로 재계산
        "steps_1min": max(0.0, to_float(row.get("steps_1min")) + steps_delta),
        "speed_mean_mpm": (
            max(0.0, to_float(row.get("steps_1min")) + steps_delta) * (52.0 / 90.0)
            if steps_delta != 0
            else to_float(row.get("speed_mean_mpm"))
        ),
        "cumulative_min": to_float(row.get("cumulative_min")),
        "rest_due_90min": to_bool(row.get("rest_due_90min")),
        "heat_index": to_float(row.get("heat_index")),
        "accident_prior": to_float(row.get("accident_prior")),
    }
