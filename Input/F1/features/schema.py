"""
fatigue_minute_features 스키마 v3 (규격 정합) — Phase 2 실 DB 기준 주석
========================================================================
파이프라인 위치:
  실 safe_db (heart_rate_intervals / spo2_intervals / step_intervals /
              activity_samples.gps_lat·lon)
    → (db_adapter) 표준 중간형식
    → [이 feature table] 1분 집계 (A 담당: 성현)
    → F1 모델 e1/e2 산출 (B 담당)
    → DTO-5 (규격 5블록)

접점(불변): DTO-1 입력 개념 / 20컬럼 feature / DTO-5 5블록.
Phase 2에서 입력원만 삼성헬스 zip → 실 DB read로 교체(접점·컬럼 스키마 유지).

실 DB 매핑 (Phase 1 확정 · 기존 DTO-1 원문 컬럼명과 다름):
- heart_rates.value      → heart_rate_intervals.value_bpm (start_time==end_time, 시점)
- blood_oxygens.value    → spo2_intervals.value_pct       (0건 세션 정상 → 미측정)
- steps.value            → step_intervals.value_steps     (시점)
- samples.gps.lat/lon    → activity_samples.gps_lat/gps_lon (속도 컬럼 없음, 파생 계산)
- x_profile.age/gender   → users.age_group/gender          (null이면 PERSONA fallback)
- 개인 baseline           → session_biometric_summary.hr_rest(실측 우선), 없으면 PERSONA
- 세션 시간               → hiking_sessions.start_time/end_time(end null이면 activity 마지막 ts)

규격 반영:
- 체온 제거 (DTO-1 v1.1에서 워치 미지원으로 제외됨)
- age_group 문자열 ("60s"), age int 제거
- SpO2 3단계 판정 재료 (95/90~94/90미만), 미측정(null) 분기 포함
- 심박 과부하: MaxHR×0.6~0.8, 5분 지속 판정용 이력 필요
- ts 시간대: 실 DB는 timestamp without time zone(UTC/KST 미확정).
  현재 엔진은 naive→KST 가정 후 UTC 변환. raw_payload 원본 표기 확인 후 확정 필요
  (Phase 2 open item — 구조 검증엔 무영향, heat_index·일몰 판정에만 영향).
"""

# (컬럼명, dtype, nullable, 출처/비고) — 출처는 실 DB 기준(Phase 2)
FEATURE_SCHEMA = [
    ("uuid",              "str",      False, "hiking_sessions.session_id"),
    ("ts",                "datetime", False, "1분 윈도우 시작(현재 UTC 변환, tz 확정 필요)"),
    ("user_lat",          "float",    False, "activity_samples.gps_lat 1분 대표"),
    ("user_lon",          "float",    False, "activity_samples.gps_lon 1분 대표"),
    ("hr_mean_bpm",       "float",    False, "heart_rate_intervals.value_bpm 1분 평균(시점값)"),
    ("hr_max_bpm",        "float",    False, "1분 최대 심박"),
    ("hr_ratio_maxhr",    "float",    False, "hr_mean/max_hr(155). 과부하 판정(0.6~0.8)"),
    ("hr_overload_5min",  "bool",     False, "MaxHR×0.6~0.8가 5분 이상 지속 여부"),
    ("hr_z_personal",     "float",    False, "(hr-hr_rest)/std. summary.hr_rest 우선, 없으면 PERSONA"),
    ("spo2_min_pct",      "float",    True,  "spo2_intervals.value_pct 1분최소(0건이면 null)"),
    ("spo2_grade",        "str",      False, "정상(95+)/경고(90~94)/위험(<90)/미측정(null)"),
    ("steps_1min",        "int",      False, "step_intervals.value_steps 1분합(시점값)"),
    ("speed_mean_mpm",    "float",    False, "gps_lat/lon haversine 이동거리/분(m/min)"),
    ("cumulative_min",    "int",      False, "세션 경과분(end_time null이면 activity 마지막 ts)"),
    ("rest_due_90min",    "bool",     False, "90분 주기 휴식 도래 여부"),
    ("heat_index",        "float",    True,  "기상 API/통계가상 주입 체감온도"),
    ("accident_prior",    "float",    False, "accident_history 계절·유형 0~1"),
    ("age_group",         "str",      False, "users.age_group(null이면 PERSONA '60s')"),
    ("gender",            "str",      False, "users.gender(null이면 PERSONA 'M')"),
    ("missing_flags",     "str",      False, "결측/보간 컬럼명 콤마구분"),
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
