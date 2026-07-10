"""
fatigue_minute_features 스키마 v3 (규격서 정합)
================================================
파이프라인 위치:
  DTO-1 heart_rates/blood_oxygens/steps (구간배열 {start,end,value})
    → [이 feature table] 1분 집계 (A 담당: 지둘)
    → F1 모델 e1/e2 산출 (B 담당)
    → DTO-5 (규격 5블록)

규격 반영:
- 체온 제거 (DTO-1 v1.1에서 워치 미지원으로 제외됨)
- age_group 문자열 ("60s"), age int 제거
- SpO2 3단계 판정 재료 (95/90~94/90미만)
- 심박 과부하: MaxHR×0.6~0.8, 5분 지속 판정용 이력 필요
"""

# (컬럼명, dtype, nullable, 출처/비고)
FEATURE_SCHEMA = [
    ("uuid",              "str",      False, "세션 UUID (DTO-1 uuid)"),
    ("ts",                "datetime", False, "1분 윈도우 시작(ISO8601 UTC)"),
    ("user_lat",          "float",    False, "samples.gps.lat 1분 대표"),
    ("user_lon",          "float",    False, "samples.gps.lon 1분 대표"),
    ("hr_mean_bpm",       "float",    False, "heart_rates.value 1분 가중평균"),
    ("hr_max_bpm",        "float",    False, "1분 최대 심박"),
    ("hr_ratio_maxhr",    "float",    False, "hr_mean/(220-age). 과부하 판정(0.6~0.8)"),
    ("hr_overload_5min",  "bool",     False, "MaxHR×0.6~0.8가 5분 이상 지속 여부"),
    ("hr_z_personal",     "float",    False, "(hr-hr_rest)/std. 개인 baseline"),
    ("spo2_min_pct",      "float",    True,  "blood_oxygens.value 1분최소(가상)"),
    ("spo2_grade",        "str",      False, "정상(95+)/경고(90~94)/위험(<90)"),
    ("steps_1min",        "int",      False, "steps.value 1분합"),
    ("speed_mean_mpm",    "float",    False, "gps 이동거리/분(m/min)"),
    ("cumulative_min",    "int",      False, "세션 경과분(90분마다 휴식 판정)"),
    ("rest_due_90min",    "bool",     False, "90분 주기 휴식 도래 여부"),
    ("heat_index",        "float",    True,  "기상청 API/가상 주입 체감온도"),
    ("accident_prior",    "float",    False, "accident_history 계절·유형 0~1"),
    ("age_group",         "str",      False, "연령대 '60s' (x_profile)"),
    ("gender",            "str",      False, "M/F/U"),
    ("missing_flags",     "str",      False, "결측 컬럼명 콤마구분"),
]

COLUMNS = [c[0] for c in FEATURE_SCHEMA]
NULLABLE = {c[0] for c in FEATURE_SCHEMA if c[2]}

# 가상 페르소나 (60대 남성). 질병청 국민건강영양조사 2020~2024 5개년 통합 실측 기반.
PERSONA = {
    "age": 65,
    "age_group": "60s",
    "gender": "M",
    "max_hr": 155,             # 220-65 (Fox). 국건영에 최대심박 측정 없어 공식 사용
    "resting_hr": 58,          # 국건영 5개년 통합 60대 남성 안정시 실측 평균 58.3 (n=398)
    "resting_hr_std": 13.6,    # 국건영 5개년 통합 실측 표준편차
}

# 규격 F1 임계 (정의서 v0.3)
HR_OVERLOAD_LOW = 0.60          # MaxHR×0.6~0.8
HR_OVERLOAD_HIGH = 0.80
SPO2_NORMAL = 95
SPO2_WARN = 90                 # 90~94 경고, <90 위험
REST_CYCLE_MIN = 90


def spo2_grade(spo2):
    if spo2 is None:
        return "미측정"
    if spo2 >= SPO2_NORMAL:
        return "정상"
    if spo2 >= SPO2_WARN:
        return "경고"
    return "위험"


def validate_columns(df):
    cols = list(df.columns)
    if cols != COLUMNS:
        raise ValueError(f"컬럼 불일치.\n기대: {COLUMNS}\n실제: {cols}")
    return True


if __name__ == "__main__":
    print(f"총 {len(COLUMNS)}개 컬럼 (규격 정합 v3, 체온 제거)")
    for name, dtype, nullable, note in FEATURE_SCHEMA:
        print(f"  {name:18s} {dtype:9s} {'NULL' if nullable else '필수':5s} {note}")
