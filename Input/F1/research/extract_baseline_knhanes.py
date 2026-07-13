"""
국민건강영양조사(KNHANES) 원자료 → 연령대·성별 안정심박 baseline 추출
=====================================================================
입력: HN20~HN24 *_all.sav (SPSS 원시자료, HE_mPLS=60초 맥박수 포함)
출력: baseline_hr_reference.csv (연령대×성별 안정심박·최대심박 표)

변수:
  age      나이
  sex      성별 (1=남, 2=여)
  HE_mPLS  60초 맥박수 (안정심박)

처리:
  - HE_mPLS 유효범위 30~200bpm, 결측 제외
  - 연령대: 10s(~19), 20s~70s, 80s(80+)
  - 안정심박: 연령대×성별 평균/표준편차/표본수
  - 최대심박: Fox 220 - 대표나이(연령대 중간값)

사용: python extract_baseline_knhanes.py <sav파일들이_있는_디렉토리>
"""
import sys, os
import pyreadstat, pandas as pd, warnings
warnings.filterwarnings("ignore")

FILES = {
    "2020": "HN20_all.sav", "2021": "HN21_all.sav", "2022": "HN22_all.sav",
    "2023": "HN23_all.sav", "2024": "HN24_ALL.sav",
}
REP_AGE = {"10s": 15, "20s": 25, "30s": 35, "40s": 45,
           "50s": 55, "60s": 65, "70s": 75, "80s": 85}


def age_band(a):
    if a < 20: return "10s"
    if a >= 80: return "80s"
    return f"{int(a // 10 * 10)}s"


def main(base_dir):
    frames = []
    for yr, fname in FILES.items():
        path = _find(base_dir, fname)
        if not path:
            print(f"[skip] {fname} 없음")
            continue
        df, _ = pyreadstat.read_sav(path, usecols=["age", "sex", "HE_mPLS"])
        frames.append(df)
    if not frames:
        raise SystemExit("sav 파일을 찾지 못했습니다.")

    d = pd.concat(frames, ignore_index=True).dropna(subset=["age", "sex", "HE_mPLS"])
    d = d[(d.HE_mPLS >= 30) & (d.HE_mPLS <= 200)]
    d["age_band"] = d["age"].apply(age_band)
    d["gender"] = d["sex"].map({1.0: "M", 2.0: "F"})

    g = d.groupby(["age_band", "gender"])["HE_mPLS"].agg(
        resting_hr_mean="mean", resting_hr_std="std", n="count").reset_index()
    g["resting_hr_mean"] = g["resting_hr_mean"].round(1)
    g["resting_hr_std"] = g["resting_hr_std"].round(1)
    g["max_hr_fox"] = g["age_band"].map(lambda b: 220 - REP_AGE[b])
    g["resting_source"] = "KNHANES 2020-2024 HE_mPLS"
    g["max_hr_source"] = "Fox 220-rep_age"

    out = os.path.join(base_dir, "baseline_hr_reference.csv")
    g.to_csv(out, index=False, encoding="utf-8-sig")
    print(g.to_string(index=False))
    print(f"\n저장: {out}")

    adult = d[d.age >= 20]
    print(f"\n[fallback] 성인 20+ 전체: mean {adult.HE_mPLS.mean():.1f}, "
          f"std {adult.HE_mPLS.std():.1f}, n {len(adult)}")


def _find(base_dir, fname):
    for root, _, files in os.walk(base_dir):
        for f in files:
            if f.lower() == fname.lower():
                return os.path.join(root, f)
    return None


if __name__ == "__main__":
    base = sys.argv[1] if len(sys.argv) > 1 else "."
    main(base)
