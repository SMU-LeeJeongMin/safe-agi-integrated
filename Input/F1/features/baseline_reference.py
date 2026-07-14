"""
연령대·성별 심박 baseline 참조표
=================================
- 안정심박(resting_hr): 국민건강영양조사(KNHANES) 2020~2024 통합, HE_mPLS(60초 맥박수) 실측
    · 유효범위 30~200bpm, 결측 제외
    · 데이터 계층: 모집단 측정 통계 (1계층)
- 최대심박(max_hr): Fox 공식 220 - 대표나이(연령대 중간값)
    · 데이터 계층: 공식 유도값 (2계층)
    · 주의: Fox 공식은 청소년/초고령에서 정확도가 낮음

프로필(연령대·성별)이 null인 경우: 성인(20+) 전체 통계값으로 fallback.
표시(대시보드)용 프로필은 null 유지하되, 판정용 baseline은 본 참조표로 산출한다.

사용:
    from baseline_reference import get_baseline
    b = get_baseline(age_band="60s", gender="M")
    # → {'resting_hr': 58.4, 'resting_std': 13.5, 'max_hr': 155, 'source': ...}
"""

# 연령대×성별: (resting_hr_mean, resting_hr_std, n)  — KNHANES 2020-2024 HE_mPLS
RESTING_HR = {
    ("10s", "M"): (94.1, 23.9, 177), ("10s", "F"): (105.0, 14.1, 179),
    ("20s", "M"): (59.6, 16.2,  99), ("20s", "F"): ( 68.8, 22.8,  63),
    ("30s", "M"): (57.2, 11.8, 117), ("30s", "F"): ( 60.1, 16.1,  68),
    ("40s", "M"): (57.4, 12.2, 155), ("40s", "F"): ( 63.7, 19.2, 126),
    ("50s", "M"): (57.1, 11.3, 268), ("50s", "F"): ( 57.2, 11.2, 247),
    ("60s", "M"): (58.4, 13.5, 396), ("60s", "F"): ( 58.4, 12.7, 376),
    ("70s", "M"): (59.3, 13.5, 394), ("70s", "F"): ( 60.7, 14.7, 295),
    ("80s", "M"): (60.7, 15.1, 157), ("80s", "F"): ( 69.6, 18.9, 124),
}

# 연령대별 최대심박 (Fox 220 - 대표나이)
REP_AGE = {"10s": 15, "20s": 25, "30s": 35, "40s": 45,
           "50s": 55, "60s": 65, "70s": 75, "80s": 85}
MAX_HR = {band: 220 - age for band, age in REP_AGE.items()}

# 프로필 null fallback (성인 20+ 전체, KNHANES 2020-2024)
FALLBACK = {
    None:  (59.6, 14.4, 2885),   # 성별도 모름
    "M":   (58.5, 13.3, 1586),
    "F":   (60.9, 15.6, 1299),
}
FALLBACK_MAX_HR = 155  # 프로젝트 타겟 연령대(60대) 기준. 가정값.

RESTING_SOURCE = "KNHANES 2020-2024 HE_mPLS (60s male: mean58.4 std13.5 n396)"
MAX_HR_SOURCE = "Fox 220 - representative age"


def get_baseline(age_band=None, gender=None):
    """
    연령대·성별로 심박 baseline 반환.
    age_band: '20s'~'80s' 또는 None
    gender: 'M'/'F' 또는 None
    반환: dict(resting_hr, resting_std, max_hr, n, source, is_fallback)
    """
    key = (age_band, gender)
    if key in RESTING_HR:
        rest, std, n = RESTING_HR[key]
        return {
            "resting_hr": rest, "resting_std": std, "n": n,
            "max_hr": MAX_HR[age_band],
            "resting_source": RESTING_SOURCE, "max_hr_source": MAX_HR_SOURCE,
            "is_fallback": False,
        }
    # 연령대 없음 → 성별만으로 fallback
    g = gender if gender in ("M", "F") else None
    rest, std, n = FALLBACK[g]
    return {
        "resting_hr": rest, "resting_std": std, "n": n,
        "max_hr": FALLBACK_MAX_HR,
        "resting_source": RESTING_SOURCE + " (adult 20+ fallback)",
        "max_hr_source": "assumed 60s (profile null)",
        "is_fallback": True,
    }


if __name__ == "__main__":
    for ab, g in [("60s", "M"), ("30s", "F"), (None, "M"), (None, None)]:
        print(f"{ab},{g} → {get_baseline(ab, g)}")
