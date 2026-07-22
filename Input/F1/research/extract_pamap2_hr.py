"""
PAMAP2 → 활동별 심박(HR) 분포 추출
=====================================================================
목적: 등산에 가까운 활동(걷기·노르딕워킹·계단)의 정상 HR 분포를 실측 근거로 확보.
      가상 세션이 "정상 심박 패턴"을 정박할 때 사용.

입력: PAMAP2_Dataset/Protocol/subject101.dat ~ subject109.dat
      (헤더 없는 공백구분, 54개 컬럼)
출력 (국건영과 동일한 Phase 1 분포표 규격):
      dist_summary_pamap2.csv   요약표 (변수×조건 한 행)
      dist_samples_pamap2.csv   샘플 보존 (부트스트랩·커널밀도용)

컬럼 구조 (PAMAP2 표준):
      0: timestamp(s)
      1: activityID
      2: heart_rate(bpm)   ← 목표
      3~53: IMU(손목/흉부/발목) — 이번 추출에서는 미사용

주의:
  - HR 컬럼은 결측이 NaN 으로 들어있음(센서 샘플링 주기 차이). dropna 필수.
  - activityID 0 은 "활동 없음(transient)" → 제외.
  - HR 유효범위 30~220 으로 클리핑(이상치 제거).

사용:
  python extract_pamap2_hr.py <Protocol_디렉토리>
  예) python extract_pamap2_hr.py "C:\\...\\PAMAP2_Dataset\\Protocol"
"""
import sys, os, glob
import pandas as pd

# 등산 근사 + 대조용 활동만 추출 (PAMAP2 activityID)
ACTIVITY_NAMES = {
    3:  "standing",           # 대조(정지)
    4:  "walking",            # 평지 걷기
    5:  "running",            # 대조(고강도)
    7:  "nordic_walking",     # 노르딕 워킹 — 등산 근사 최상
    12: "ascending_stairs",   # 계단 오르기
    13: "descending_stairs",  # 계단 내리기
}

HR_MIN, HR_MAX = 30, 220
MAX_SAMPLES_PER_CELL = 5000


def load_subject(path):
    """subjectNNN.dat 한 개를 읽어 [activityID, heart_rate] 만 반환."""
    # 공백구분, 헤더 없음. 필요한 2개 컬럼(1,2)만 읽어 메모리 절약.
    df = pd.read_csv(path, sep=r"\s+", header=None,
                     usecols=[1, 2], names=["activityID", "heart_rate"],
                     na_values=["NaN"])
    df["subject"] = os.path.basename(path).replace(".dat", "")
    return df


def main(protocol_dir):
    files = sorted(glob.glob(os.path.join(protocol_dir, "subject*.dat")))
    if not files:
        raise SystemExit(f"subject*.dat 파일을 찾지 못함: {protocol_dir}")
    print(f"참가자 파일 {len(files)}개 발견")

    frames = []
    for f in files:
        d = load_subject(f)
        n_raw = len(d)
        d = d.dropna(subset=["heart_rate"])
        print(f"  {os.path.basename(f)}: {n_raw}행 → HR 있는 {len(d)}행")
        frames.append(d)

    d = pd.concat(frames, ignore_index=True)

    # 대상 활동만, HR 유효범위만
    d = d[d["activityID"].isin(ACTIVITY_NAMES.keys())]
    d = d[(d["heart_rate"] >= HR_MIN) & (d["heart_rate"] <= HR_MAX)]
    d["activity"] = d["activityID"].map(ACTIVITY_NAMES)

    summary_rows, sample_rows = [], []
    for act, grp in d.groupby("activity"):
        v = grp["heart_rate"]
        summary_rows.append({
            "dataset": "PAMAP2", "variable": "heart_rate",
            "condition_key": "activity", "condition_value": act,
            "n": len(v),
            "mean": round(v.mean(), 2), "std": round(v.std(), 2),
            "min": round(v.min(), 2),
            "p05": round(v.quantile(.05), 2), "p25": round(v.quantile(.25), 2),
            "p50": round(v.quantile(.50), 2), "p75": round(v.quantile(.75), 2),
            "p95": round(v.quantile(.95), 2),
            "max": round(v.max(), 2),
            "missing_rate": None,
            "unit": "bpm", "layer": "MEASURED_SENSOR",
            "license": "PAMAP2(CC BY 4.0)",
        })
        keep = v.sample(min(len(v), MAX_SAMPLES_PER_CELL), random_state=42)
        for x in keep:
            sample_rows.append({
                "dataset": "PAMAP2", "variable": "heart_rate",
                "condition_key": "activity", "condition_value": act,
                "value": x,
            })

    summ = pd.DataFrame(summary_rows)
    samp = pd.DataFrame(sample_rows)
    out_summ = os.path.join(protocol_dir, "dist_summary_pamap2.csv")
    out_samp = os.path.join(protocol_dir, "dist_samples_pamap2.csv")
    summ.to_csv(out_summ, index=False, encoding="utf-8-sig")
    samp.to_csv(out_samp, index=False, encoding="utf-8-sig")

    print(f"\n요약표 저장: {out_summ}  ({len(summ)}행)")
    print(f"샘플 저장 : {out_samp}  ({len(samp)}행)")
    print("\n[활동별 HR 분포]")
    cols = ["activity" if False else "condition_value",
            "n", "mean", "std", "p05", "p50", "p95"]
    print(summ[["condition_value", "n", "mean", "std",
                "p05", "p50", "p95"]].to_string(index=False))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('사용: python extract_pamap2_hr.py "<Protocol 폴더 경로>"')
        sys.exit(1)
    main(sys.argv[1])
