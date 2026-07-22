"""
Non-EEG Dataset → SpO2 / HR 정상 분포 추출
=====================================================================
목적: 정상 상태의 SpO2(산소포화도) 분포를 실측 근거로 확보.
      SpO2는 공개/실측 어디서도 확보 못 한 값이라 그동안 가상 보정 대상이었음.
      이 데이터로 "정상 SpO2가 어느 범위인지"를 실측으로 정박한다.
      HR도 함께 담겨 있어 보조로 추출.

입력: Non-EEG 데이터 폴더 (SubjectN_SpO2HR.dat/.hea, subjectinfo.csv)
      WFDB 형식 — .hea 헤더 + .dat 신호. wfdb 라이브러리로 읽어야
      ADC 게인/오프셋이 실제 물리값(%, bpm)으로 자동 변환됨.
출력 (국건영·PAMAP2와 동일한 Phase 1 분포표 규격):
      dist_summary_noneeg.csv
      dist_samples_noneeg.csv

신호: SpO2(%), hr(bpm). 참가자 20명(19~33세 성인), subjectinfo.csv로 성별 결합.

주의:
  - SpO2 유효범위 70~100%, HR 유효범위 30~220bpm 으로 이상치 클리핑.
  - 참가자 전원 젊은 성인이라 연령대 분포는 좁음 → SpO2 '정상 범위' 확보용.
  - 상태(안정/스트레스 등) 구분은 이번 추출에서 하지 않고 전체 정상 분포로 봄.
    (필요 시 .atr 주석으로 상태별 분리 가능하나, 여기서는 SpO2 범위 확보가 목표)

사용:
  pip install wfdb pandas
  python extract_noneeg_spo2hr.py "<Non-EEG 데이터 폴더>"
"""
import sys, os, glob
import pandas as pd

try:
    import wfdb
except ImportError:
    print("필요 패키지: pip install wfdb")
    raise

SPO2_MIN, SPO2_MAX = 70, 100
HR_MIN, HR_MAX = 30, 220
MAX_SAMPLES_PER_CELL = 5000


def load_subjectinfo(data_dir):
    p = os.path.join(data_dir, "subjectinfo.csv")
    if not os.path.exists(p):
        print("[주의] subjectinfo.csv 없음 → 성별 결합 생략")
        return None
    info = pd.read_csv(p)
    info.columns = [c.strip() for c in info.columns]
    return info.set_index("subject")


def read_record(path_no_ext):
    """SubjectN_SpO2HR (확장자 제외 경로) 를 읽어 SpO2, hr 시리즈 반환."""
    rec = wfdb.rdrecord(path_no_ext)  # .hea/.dat 자동 인식, 물리값 변환
    sig_names = [s.strip() for s in rec.sig_name]
    df = pd.DataFrame(rec.p_signal, columns=sig_names)
    return df


def main(data_dir):
    info = load_subjectinfo(data_dir)
    files = sorted(glob.glob(os.path.join(data_dir, "*_SpO2HR.hea")))
    if not files:
        raise SystemExit(f"*_SpO2HR.hea 파일을 찾지 못함: {data_dir}")
    print(f"SpO2HR 레코드 {len(files)}개 발견")

    frames = []
    for hea in files:
        base = hea[:-4]  # .hea 제거 → wfdb 가 쓰는 경로
        fname = os.path.basename(base)  # SubjectN_SpO2HR
        subj = int(fname.replace("Subject", "").replace("_SpO2HR", ""))
        try:
            df = read_record(base)
        except Exception as e:
            print(f"  [skip] {fname}: {e}")
            continue
        df["subject"] = subj
        if info is not None and subj in info.index:
            df["gender"] = info.loc[subj, "gender"]
        else:
            df["gender"] = None
        frames.append(df)
        print(f"  {fname}: {len(df)}샘플")

    d = pd.concat(frames, ignore_index=True)
    # 컬럼명 정규화 (SpO2 / hr)
    cols = {c.lower(): c for c in d.columns}
    spo2_col = cols.get("spo2")
    hr_col = cols.get("hr")

    summary_rows, sample_rows = [], []

    def add_var(series, condition_key, condition_value, varname, unit, lo, hi):
        v = pd.to_numeric(series, errors="coerce")
        v = v[(v >= lo) & (v <= hi)].dropna()
        if len(v) == 0:
            return
        summary_rows.append({
            "dataset": "Non-EEG", "variable": varname,
            "condition_key": condition_key, "condition_value": condition_value,
            "n": len(v),
            "mean": round(v.mean(), 2), "std": round(v.std(), 2),
            "min": round(v.min(), 2),
            "p05": round(v.quantile(.05), 2), "p25": round(v.quantile(.25), 2),
            "p50": round(v.quantile(.50), 2), "p75": round(v.quantile(.75), 2),
            "p95": round(v.quantile(.95), 2),
            "max": round(v.max(), 2),
            "missing_rate": None,
            "unit": unit, "layer": "MEASURED_SENSOR",
            "license": "Non-EEG(ODC-By 1.0)",
        })
        keep = v.sample(min(len(v), MAX_SAMPLES_PER_CELL), random_state=42)
        for x in keep:
            sample_rows.append({
                "dataset": "Non-EEG", "variable": varname,
                "condition_key": condition_key,
                "condition_value": condition_value, "value": x,
            })

    # 전체(all) 분포 + 성별 분포
    if spo2_col:
        add_var(d[spo2_col], "all", "all", "SpO2", "%", SPO2_MIN, SPO2_MAX)
        for g, grp in d.groupby("gender"):
            if g:
                add_var(grp[spo2_col], "gender", g, "SpO2", "%", SPO2_MIN, SPO2_MAX)
    if hr_col:
        add_var(d[hr_col], "all", "all", "heart_rate", "bpm", HR_MIN, HR_MAX)
        for g, grp in d.groupby("gender"):
            if g:
                add_var(grp[hr_col], "gender", g, "heart_rate", "bpm", HR_MIN, HR_MAX)

    summ = pd.DataFrame(summary_rows)
    samp = pd.DataFrame(sample_rows)
    out_summ = os.path.join(data_dir, "dist_summary_noneeg.csv")
    out_samp = os.path.join(data_dir, "dist_samples_noneeg.csv")
    summ.to_csv(out_summ, index=False, encoding="utf-8-sig")
    samp.to_csv(out_samp, index=False, encoding="utf-8-sig")

    print(f"\n요약표 저장: {out_summ}  ({len(summ)}행)")
    print(f"샘플 저장 : {out_samp}  ({len(samp)}행)")
    print("\n[분포 요약]")
    print(summ[["variable", "condition_value", "n", "mean", "std",
                "p05", "p50", "p95"]].to_string(index=False))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('사용: python extract_noneeg_spo2hr.py "<Non-EEG 데이터 폴더>"')
        sys.exit(1)
    main(sys.argv[1])
