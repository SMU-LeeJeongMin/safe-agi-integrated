"""
국민건강영양조사 60대 남성 안정시 심박 분석 (Phase 3 산출물)
=============================================================
외부 데이터로 60대 페르소나 기준값 확보.
5개년(2020~2024) 통합, HE_mPLS(60초 맥박수, 훈련된 간호사 측정).

▶ 분석 결과는 아래 RESULTS에 포함 — 파일 없이 확인 가능.
▶ 재현하려면 국건영 .sav 5개를 준비해 reproduce() 실행.
"""

# ── 분석 결과 (2020~2024 국건영, 60대 남성, HE_mPLS 실측) ──
RESULTS = {
    "2020": {"mean": 59.9, "std": 17.7, "n": 68},
    "2021": {"mean": 54.1, "std": 10.4, "n": 76},
    "2022": {"mean": 59.0, "std": 13.9, "n": 84},
    "2023": {"mean": 58.8, "std": 12.1, "n": 95},
    "2024": {"mean": 59.6, "std": 13.4, "n": 75},
}
INTEGRATED = {"mean": 58.3, "std": 13.6, "n": 398}   # 5개년 통합
PERSONA_CONFIRMED = {"resting_hr": 58, "std": 13.6}   # 페르소나 확정값


def show_results():
    """분석 결과 출력 (파일 불필요)."""
    print("=" * 55)
    print("국민건강영양조사 60대 남성 안정시 심박 (HE_mPLS)")
    print("=" * 55)
    for yr, r in RESULTS.items():
        print(f"  {yr}년: 평균 {r['mean']:.1f}bpm  std {r['std']:.1f}  (n={r['n']})")
    print("-" * 55)
    print(f"  5개년 통합: 평균 {INTEGRATED['mean']:.1f}bpm  "
          f"std {INTEGRATED['std']:.1f}  (n={INTEGRATED['n']})")
    print(f"  → 페르소나 확정: 안정시 {PERSONA_CONFIRMED['resting_hr']}bpm, "
          f"표준편차 {PERSONA_CONFIRMED['std']}")


def reproduce(data_dir="."):
    """
    국건영 원자료로 재현 (검증용). .sav 5개 필요.
    Colab: !pip install pyreadstat 후 파일 업로드하여 실행.
    """
    import os, pyreadstat, pandas as pd
    files = {"2020": "HN20_all.sav", "2021": "HN21_all.sav",
             "2022": "HN22_all.sav", "2023": "HN23_all.sav",
             "2024": "HN24_ALL.sav"}
    alld = []
    for yr, f in files.items():
        df, _ = pyreadstat.read_sav(os.path.join(data_dir, f),
                                    usecols=["age", "sex", "HE_mPLS"])
        d = df[(df.age >= 60) & (df.age < 70) & (df.sex == 1) & (df.HE_mPLS.notna())]
        alld.append(d)
        print(f"  {yr}: 평균 {d.HE_mPLS.mean():.1f}  std {d.HE_mPLS.std():.1f}  n={len(d)}")
    full = pd.concat(alld)
    print(f"  통합: 평균 {full.HE_mPLS.mean():.1f}  std {full.HE_mPLS.std():.1f}  n={len(full)}")
    return full


if __name__ == "__main__":
    show_results()   # 파일 없이 결과 확인
