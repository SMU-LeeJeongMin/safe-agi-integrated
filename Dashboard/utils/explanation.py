# 판단 근거 설명 생성 유틸리티 (구 xAI.py)
# 규칙 기반 중요도와 판단 근거 문장
# 위험 등급 임계값, 개인 baseline 상수 등 화면 설명에 쓰는 공용 상수도 여기서 관리

from typing import Any

import pandas as pd

# 표시 및 What-if용 상수 — 출처를 model/ 모듈로 일원화 (drift 방지)
#   - HR_BASELINE / HR_STD: model/personal_baseline.py의 국건영 60대 실측 prior를 import
#   - RISK_* 컷오프: 규격 DTO_v1.2 주3 = model/dto5.py risk_level()과 동일
#     (등급 판정 자체는 risk_label_from_score()가 model.dto5.risk_level에 위임)
#   - MAX_HR_60S: 페르소나 공식 220 − 65 (7/2 회의록)
from Model.personal_baseline import PRIOR_MEAN as HR_BASELINE  # 58.0
from Model.personal_baseline import PRIOR_STD as HR_STD        # 13.6
from Model.f1_model import K_PERSONAL_STD

MAX_HR_60S = 155.0        # 220 - 65
HR_OVERLOAD_RATIO = 0.85  # 심박 과부하 임계 비율
SPO2_WARN = 95.0          # 미만이면 경고
SPO2_DANGER = 90.0        # 미만이면 위험
LOW_STEPS = 10.0          # 이동량 저하 기준 (보/분)
LOW_SPEED = 10.0          # 이동량 저하 기준 (m/min)
REST_CYCLE_MIN = 90       # 휴식 주기 (분)
HEAT_WARN = 28.0          # 고온 가중 기준

RISK_CAUTION = 0.50       # 이상이면 주의 (level 1)
RISK_WARNING = 0.65       # 이상이면 경고 (level 2)
RISK_DANGER = 0.85        # 이상이면 위험 (level 3)


def get_nested(data: dict[str, Any], keys: list[str], default: Any = None) -> Any:
    current = data

    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
        if current is None:
            return default

    return current


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        return value != 0

    if isinstance(value, str):
        return value.strip().lower() in ["true", "1", "yes", "y"]

    return False


def format_id(value: Any, head: int = 8, tail: int = 4, max_len: int = 16) -> tuple[str, str | None]:
    """긴 식별자(세션 uuid 등)를 카드 표시용으로 축약한다.

    반환: (표시 문자열, 전체값 툴팁 문구 또는 None).
    max_len 이하면 원본 그대로 반환하고 툴팁은 생략한다.
    """
    text = "" if value is None else str(value)
    if len(text) <= max_len:
        return text, None
    return f"{text[:head]}…{text[-tail:]}", f"전체 세션 ID: {text}"


def format_value(value: Any, digits: int = 2) -> str:
    try:
        if pd.isna(value):
            return "-"
        if isinstance(value, float):
            return f"{value:.{digits}f}"
        return str(value)
    except Exception:
        return "-"


def risk_label_from_score(score: float) -> tuple[int, str]:
    """대표 위험도 -> (level, label). model/dto5.py의 규격 판정 함수에 위임."""
    from Model.dto5 import risk_level
    return risk_level(score)


def build_feature_calculations(row: pd.Series) -> list[dict[str, str]]:
    """
    [2] Feature Engineering Panel용.
    선택 시점의 raw 값이 실제로 대입된 계산 과정을 행 단위로 반환.
    (원본 입력 -> 계산식 -> feature 값 -> 해석)
    """
    hr = to_float(row.get("hr_mean_bpm"))
    ratio = to_float(row.get("hr_ratio_maxhr"))
    z = to_float(row.get("hr_z_personal"))
    spo2 = to_float(row.get("spo2_min_pct"))
    grade = row.get("spo2_grade", "-")
    steps = to_float(row.get("steps_1min"))
    speed = to_float(row.get("speed_mean_mpm"))
    cum = to_float(row.get("cumulative_min"))
    rest_due = to_bool(row.get("rest_due_90min"))
    overload = to_bool(row.get("hr_overload_5min"))
    heat = to_float(row.get("heat_index"))
    prior = to_float(row.get("accident_prior"))
    missing = row.get("missing_flags")

    low_move = steps < LOW_STEPS or speed < LOW_SPEED

    return [
        {
            "feature": "hr_ratio_maxhr",
            "원본 입력": f"hr_mean_bpm {hr:.1f}",
            "계산 과정": f"{hr:.1f} ÷ {MAX_HR_60S:.0f} (60대 최대심박)",
            "값": f"{ratio:.3f}",
            "해석": (
                f"임계 {HR_OVERLOAD_RATIO:.2f} 초과 → 심박 과부하"
                if ratio >= HR_OVERLOAD_RATIO
                else f"임계 {HR_OVERLOAD_RATIO:.2f} 미만 → 여유"
            ),
        },
        {
            "feature": "hr_z_personal",
            "원본 입력": f"hr_mean_bpm {hr:.1f}",
            "계산 과정": f"({hr:.1f} − {HR_BASELINE:.0f}) ÷ {HR_STD}",
            "값": f"{z:.2f}",
            "해석": "개인 안정시 대비 표준화 점수 (클수록 평소보다 높음)",
        },
        {
            "feature": "hr_overload_5min",
            "원본 입력": "hr_ratio_maxhr 시퀀스",
            "계산 과정": f"ratio ≥ {HR_OVERLOAD_RATIO:.2f} 상태 5분 이상 지속 여부",
            "값": str(overload),
            "해석": "과부하 지속" if overload else "지속 없음",
        },
        {
            "feature": "spo2_grade",
            "원본 입력": f"spo2_min_pct {spo2:.1f}%",
            "계산 과정": f"≥{SPO2_WARN:.0f} 정상 / {SPO2_DANGER:.0f}~{SPO2_WARN:.0f} 경고 / <{SPO2_DANGER:.0f} 위험",
            "값": str(grade),
            "해석": f"SpO2 {spo2:.1f}% → {grade}",
        },
        {
            "feature": "이동량 (steps/speed)",
            "원본 입력": f"steps_1min {steps:.0f}보, speed {speed:.1f} m/min",
            "계산 과정": f"걸음 <{LOW_STEPS:.0f}보 또는 속도 <{LOW_SPEED:.0f} m/min",
            "값": f"{steps:.0f}보 / {speed:.1f} m/min",
            "해석": "이동량 저하" if low_move else "정상 이동",
        },
        {
            "feature": "rest_due_90min",
            "원본 입력": f"cumulative_min {cum:.0f}분",
            "계산 과정": f"누적 산행 {REST_CYCLE_MIN}분 주기 도래 여부",
            "값": str(rest_due),
            "해석": "휴식 주기 도래" if rest_due else "주기 미도래",
        },
        {
            "feature": "heat_index",
            "원본 입력": "기상 데이터 (기온 및 습도)",
            "계산 과정": "체감 위험 보정값 산출",
            "값": f"{heat:.1f}",
            "해석": f"{HEAT_WARN:.0f} 이상 고온 가중" if heat >= HEAT_WARN else "고온 가중 없음",
        },
        {
            "feature": "accident_prior",
            "원본 입력": "산악사고 통계 (여름 및 탈진 비율)",
            "계산 과정": "사고 prior 보정값",
            "값": f"{prior:.2f}",
            "해석": "환경 위험 보정에 반영",
        },
        {
            "feature": "missing_flags",
            "원본 입력": "결측 보간 이력",
            "계산 과정": "-",
            "값": "-" if pd.isna(missing) else str(missing),
            "해석": "결측 없음" if pd.isna(missing) else "보간된 값 포함",
        },
    ]


def build_threshold_checks(row: pd.Series, dto5: dict[str, Any]) -> list[dict[str, str]]:
    """
    [3] Model Explanation Panel용 판정 기준표 (규격 정의서 v0.3, judge_fatigue와 동일 규칙).
    각 feature의 현재값을 임계값과 나란히 놓고 충족 여부를 표시.
    """
    ratio = to_float(row.get("hr_ratio_maxhr"))
    spo2 = to_float(row.get("spo2_min_pct"))
    steps = to_float(row.get("steps_1min"))
    speed = to_float(row.get("speed_mean_mpm"))
    heat = to_float(row.get("heat_index"))
    overload = to_bool(row.get("hr_overload_5min"))
    rest_due = to_bool(row.get("rest_due_90min"))

    def mark(hit: bool) -> str:
        return "충족" if hit else "미충족"

    return [
        {
            "판정 항목": "심박 비율 과부하",
            "현재값": f"{ratio:.3f}",
            "기준": f"≥ {HR_OVERLOAD_RATIO:.2f}",
            "충족 여부": mark(ratio >= HR_OVERLOAD_RATIO),
        },
        {
            "판정 항목": "심박 과부하 5분 지속",
            "현재값": str(overload),
            "기준": "True",
            "충족 여부": mark(overload),
        },
        {
            "판정 항목": "SpO2 경고 구간",
            "현재값": f"{spo2:.1f}%",
            "기준": f"< {SPO2_WARN:.0f}%",
            "충족 여부": mark(spo2 < SPO2_WARN),
        },
        {
            "판정 항목": "이동량 저하",
            "현재값": f"{steps:.0f}보 / {speed:.1f} m/min",
            "기준": f"걸음 < {LOW_STEPS:.0f} 또는 속도 < {LOW_SPEED:.0f}",
            "충족 여부": mark(steps < LOW_STEPS or speed < LOW_SPEED),
        },
        {
            "판정 항목": "휴식 주기 도래",
            "현재값": f"누적 {to_float(row.get('cumulative_min')):.0f}분",
            "기준": f"{REST_CYCLE_MIN}분 주기",
            "충족 여부": mark(rest_due),
        },
        {
            "판정 항목": "고온 가중",
            "현재값": f"{heat:.1f}",
            "기준": f"≥ {HEAT_WARN:.0f}",
            "충족 여부": mark(heat >= HEAT_WARN),
        },
    ]


def build_pipeline_summary(row: pd.Series, dto5: dict[str, Any]) -> list[dict[str, str]]:
    """상단 파이프라인 요약 스트립용 단계별 핵심 값."""
    hr = to_float(row.get("hr_mean_bpm"))
    spo2 = to_float(row.get("spo2_min_pct"))
    ratio = to_float(row.get("hr_ratio_maxhr"))
    z = to_float(row.get("hr_z_personal"))

    e2 = get_nested(dto5, ["risk", "e2_combined"], "-")
    rep = get_nested(dto5, ["risk", "representative"], "-")
    level = get_nested(dto5, ["risk", "level"], "-")
    label = get_nested(dto5, ["risk", "label"], "-")
    state = get_nested(dto5, ["fatigue", "state"], "-")

    shelter = get_nested(dto5, ["fatigue", "nearest_shelter"], None)
    if isinstance(shelter, dict):
        shelter_text = f"{shelter.get('name')}, {shelter.get('distance_m')}m, {shelter.get('est_min')}분"
    else:
        shelter_text = "없음"

    alerts = dto5.get("alerts") or []
    alert_text = alerts[0].get("title") if alerts else "알림 없음"

    return [
        {"stage": "Input", "main": f"HR {hr:.1f} bpm", "sub": f"SpO2 {spo2:.1f}%"},
        {"stage": "Feature", "main": f"ratio {ratio:.3f}", "sub": f"z {z:.2f}"},
        {"stage": "Model", "main": f"e2 {e2}", "sub": f"대표 {rep}"},
        {"stage": "Decision", "main": f"{label} (level {level})", "sub": f"{state}"},
        {"stage": "Output", "main": alert_text, "sub": shelter_text},
    ]


def build_feature_importance(row: pd.Series, dto5: dict[str, Any]) -> list[dict[str, Any]]:
    """
    현재 F1 모델 계산식 기준의 판단 근거 Top 5입니다.
    추후 Azure ML 또는 SHAP 기반 explanation이 연결되면 이 함수만 교체하면 됩니다.
    """
    candidates = []

    hr_ratio = to_float(row.get("hr_ratio_maxhr"))
    if hr_ratio > 0:
        candidates.append({
            "feature": "hr_ratio_maxhr",
            "importance": min(hr_ratio, 1.0),
            "reason": f"60대 기준 최대심박수 대비 심박 비율이 {hr_ratio:.2f}입니다."
        })

    hr_z = to_float(row.get("hr_z_personal"))
    if hr_z > 0:
        candidates.append({
            "feature": "hr_z_personal",
            "importance": min(hr_z / K_PERSONAL_STD, 1.0),
            "reason": f"개인 기준 대비 심박 상승 정도가 {hr_z:.2f}입니다."
        })

    if to_bool(row.get("hr_overload_5min")):
        candidates.append({
            "feature": "hr_overload_5min",
            "importance": 0.95,
            "reason": "심박 과부하가 5분 이상 지속되었습니다."
        })

    spo2_grade = row.get("spo2_grade")
    if spo2_grade == "위험":
        candidates.append({
            "feature": "spo2_grade",
            "importance": 0.90,
            "reason": "SpO2가 위험 구간으로 분류되었습니다."
        })
    elif spo2_grade == "경고":
        candidates.append({
            "feature": "spo2_grade",
            "importance": 0.75,
            "reason": "SpO2가 경고 구간으로 분류되었습니다."
        })

    if to_bool(row.get("rest_due_90min")):
        candidates.append({
            "feature": "rest_due_90min",
            "importance": 0.65,
            "reason": "누적 산행 90분 휴식 주기가 도래했습니다."
        })

    steps = to_float(row.get("steps_1min"), default=999.0)
    if steps < LOW_STEPS:
        candidates.append({
            "feature": "steps_1min",
            "importance": 0.62,
            "reason": f"최근 1분 걸음 수가 {steps:.0f}보로 낮습니다."
        })

    speed = to_float(row.get("speed_mean_mpm"), default=999.0)
    if speed < LOW_SPEED:
        candidates.append({
            "feature": "speed_mean_mpm",
            "importance": 0.58,
            "reason": f"GPS 기반 평균 속도가 {speed:.1f}m/min으로 낮습니다."
        })

    heat_index = to_float(row.get("heat_index"))
    if heat_index >= HEAT_WARN:
        candidates.append({
            "feature": "heat_index",
            "importance": min((heat_index - 20) / 15, 1.0),
            "reason": f"체감 위험 보정값 heat_index가 {heat_index:.1f}입니다."
        })

    accident_prior = to_float(row.get("accident_prior"))
    if accident_prior > 0:
        candidates.append({
            "feature": "accident_prior",
            "importance": min(accident_prior, 1.0),
            "reason": f"산악사고 기반 탈진 및 탈수 prior가 {accident_prior:.2f}입니다."
        })

    if not candidates:
        candidates.append({
            "feature": "normal_range",
            "importance": 0.10,
            "reason": "현재 선택 시점은 주요 위험 feature가 크게 활성화되지 않았습니다."
        })

    candidates = sorted(candidates, key=lambda x: x["importance"], reverse=True)
    return candidates[:5]


def make_reason_text(row: pd.Series, dto5: dict[str, Any]) -> str:
    risk_label = get_nested(dto5, ["risk", "label"], "알 수 없음")
    fatigue_state = get_nested(dto5, ["fatigue", "state"], "알 수 없음")
    top_features = build_feature_importance(row, dto5)

    header = f"위험 등급은 '{risk_label}', 피로 상태는 '{fatigue_state}'입니다."

    reason_lines = []
    for idx, item in enumerate(top_features, start=1):
        reason_lines.append(f"{idx}. {item['reason']}")

    return header + "\n\n" + "\n".join(reason_lines)


def build_whatif_features(
    row: pd.Series,
    changed_hr: float,
    changed_spo2: float,
    changed_steps: float,
    changed_heat_index: float,
) -> dict[str, Any]:
    """
    What-if 슬라이더 값 4개 → infer_f1용 feature dict 변환.
    슬라이더 입력에 딸린 파생 컬럼(hr_ratio_maxhr, hr_z_personal,
    hr_overload_5min, spo2_grade, speed_mean_mpm)을 함께 재계산한다.
    """
    hr_ratio = changed_hr / MAX_HR_60S
    hr_z = (changed_hr - HR_BASELINE) / HR_STD

    if changed_spo2 >= SPO2_WARN:
        spo2_grade = "정상"
    elif changed_spo2 >= SPO2_DANGER:
        spo2_grade = "경고"
    else:
        spo2_grade = "위험"

    return {
        "uuid": row.get("uuid"),
        "ts": row.get("ts"),
        "user_lat": to_float(row.get("user_lat")),
        "user_lon": to_float(row.get("user_lon")),
        # 슬라이더 입력 4개
        "hr_mean_bpm": changed_hr,
        "spo2_min_pct": changed_spo2,
        "steps_1min": changed_steps,
        "heat_index": changed_heat_index,
        # 재계산 파생 컬럼
        "hr_ratio_maxhr": hr_ratio,
        "hr_z_personal": hr_z,
        # 5분 지속 플래그는 단일 시점이라 근사: 임계 비율 초과 여부로 대체
        "hr_overload_5min": hr_ratio >= HR_OVERLOAD_RATIO,
        "spo2_grade": spo2_grade,
        # 걸음 수에 연동해 재계산 (모델 baseline 비율: 52 m/min ÷ 90 보/분)
        "speed_mean_mpm": changed_steps * (52.0 / 90.0),
        # 슬라이더와 무관 → row 값 유지
        "cumulative_min": to_float(row.get("cumulative_min")),
        "rest_due_90min": to_bool(row.get("rest_due_90min")),
        "accident_prior": to_float(row.get("accident_prior")),
        "hr_max_bpm": changed_hr,
        "age_group": row.get("age_group"),
        "gender": row.get("gender"),
        "missing_flags": row.get("missing_flags"),
    }
