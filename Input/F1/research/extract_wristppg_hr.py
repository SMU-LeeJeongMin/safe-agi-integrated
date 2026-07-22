"""
Wrist PPG During Exercise → 손목 HR 아웃라이어 보간 + ECG 정답 검증
=====================================================================
교수님 피드백 반영: "손목(워치) 데이터는 아웃라이어가 많을 것 → 보간법으로
노이즈 처리 잘 해보기". 이 데이터는 손목 PPG(노이즈)와 흉부 ECG(정답)를 동시
측정하므로, 보간이 실제로 노이즈를 개선하는지 ECG 정답과 대조해 검증할 수 있다.

작업 흐름:
  1) ECG R-peak(.atr 수작업 주석) → HR 정답 시계열 (초당 1값)
  2) PPG 파형 → 피크 검출로 HR 추정 (모션 아티팩트로 아웃라이어 발생)
  3) PPG HR 아웃라이어 탐지 (생리 범위 이탈 + 급격한 변화율)
  4) 보간(선형)으로 아웃라이어 구간 복원
  5) 보간 전/후 PPG HR 을 ECG 정답과 오차(MAE) 비교 → 개선 정량 입증
  6) 보간된 HR 을 활동별(walk/run) 분포로 추출 (국건영·PAMAP2·Non-EEG 동일 규격)

입력: wrist-ppg 데이터 폴더 (sN_walk / sN_run 등의 .dat/.hea/.atr)
      15채널, 256Hz. ch0=chest_ecg, ch1=wrist_ppg.
출력:
      dist_summary_wristppg.csv    보간 후 HR 분포 (활동별)
      dist_samples_wristppg.csv    샘플 보존
      interp_validation_wristppg.csv  보간 전/후 정답 대비 오차 (검증 근거)

사용:
  pip install wfdb scipy pandas numpy
  python extract_wristppg_hr.py "<wrist-ppg 데이터 폴더>"
  # 걷기·달리기만: 기본값. 자전거 포함하려면 --with-bike
"""
import sys, os, glob
import numpy as np
import pandas as pd

try:
    import wfdb
    from scipy.signal import find_peaks
except ImportError:
    print("필요 패키지: pip install wfdb scipy pandas numpy")
    raise

FS = 256                    # 샘플링레이트(Hz)
HR_MIN, HR_MAX = 40, 210    # 생리적 유효 심박 범위(bpm)
MAX_JUMP_BPM = 25           # 1초 사이 허용 최대 변화(아웃라이어 판정)
MAX_SAMPLES_PER_CELL = 5000

# 활동 라벨 매핑 (파일명 → 활동)
def activity_of(fname):
    n = fname.lower()
    if "walk" in n:
        return "walking"
    if "run" in n:
        return "running"
    if "bike" in n:
        return "cycling"
    return "other"


def hr_from_ecg_rpeaks(record_path):
    """.atr 의 ECG R-peak 주석 → 초 단위 HR 정답 시계열 반환."""
    try:
        ann = wfdb.rdann(record_path, "atr")
    except Exception:
        return None
    rpeaks = np.array(ann.sample)          # 샘플 인덱스
    if len(rpeaks) < 3:
        return None
    t = rpeaks / FS                        # 초
    rr = np.diff(t)                        # R-R 간격(초)
    inst_hr = 60.0 / rr                    # 순간 심박
    t_mid = (t[:-1] + t[1:]) / 2
    # 생리 범위만
    ok = (inst_hr >= HR_MIN) & (inst_hr <= HR_MAX)
    return t_mid[ok], inst_hr[ok]


def hr_from_ppg(sig, fs=FS):
    """PPG 파형 → 피크 검출로 초 단위 HR 추정 (노이즈 포함)."""
    x = np.asarray(sig, dtype=float)
    x = x - np.nanmean(x)
    # 최소 피크 간격 = 최고심박 기준 (210bpm → 약 0.286s)
    min_dist = int(fs * 60.0 / HR_MAX)
    peaks, _ = find_peaks(x, distance=min_dist)
    if len(peaks) < 3:
        return None
    t = peaks / fs
    rr = np.diff(t)
    inst_hr = 60.0 / rr
    t_mid = (t[:-1] + t[1:]) / 2
    return t_mid, inst_hr


def resample_to_seconds(t, hr, duration):
    """불규칙 (t,hr) 를 1초 격자로 재배치 (없는 초는 NaN)."""
    grid = np.arange(0, int(duration) + 1)
    out = np.full(len(grid), np.nan)
    if t is None or len(t) == 0:
        return grid, out
    idx = np.clip(np.round(t).astype(int), 0, len(grid) - 1)
    for i, h in zip(idx, hr):
        out[i] = h
    return grid, out


def detect_and_interpolate(hr_grid):
    """아웃라이어 탐지 후 선형 보간. (보간된 시계열, 아웃라이어 마스크) 반환."""
    hr = hr_grid.copy()
    n = len(hr)
    outlier = np.zeros(n, dtype=bool)

    # 1) 생리 범위 이탈
    outlier |= (hr < HR_MIN) | (hr > HR_MAX)
    # 2) 급격한 변화율 (앞값 대비 점프)
    for i in range(1, n):
        if not np.isnan(hr[i]) and not np.isnan(hr[i - 1]):
            if abs(hr[i] - hr[i - 1]) > MAX_JUMP_BPM:
                outlier[i] = True

    cleaned = hr.copy()
    cleaned[outlier] = np.nan
    # 선형 보간 (양끝 NaN 은 최근값으로 채움)
    s = pd.Series(cleaned).interpolate(method="linear", limit_direction="both")
    return s.to_numpy(), outlier


def mae_vs_truth(hr_series, t_grid, ecg_t, ecg_hr):
    """PPG HR(초격자) 과 ECG 정답의 평균절대오차. 공통 시점만."""
    if ecg_t is None:
        return None
    _, ecg_grid = resample_to_seconds(ecg_t, ecg_hr, t_grid[-1])
    both = ~np.isnan(hr_series) & ~np.isnan(ecg_grid)
    if both.sum() == 0:
        return None
    return float(np.mean(np.abs(hr_series[both] - ecg_grid[both])))


def main(data_dir, with_bike=False):
    heas = sorted(glob.glob(os.path.join(data_dir, "*.hea")))
    records = [h[:-4] for h in heas]
    if not records:
        raise SystemExit(f".hea 파일을 찾지 못함: {data_dir}")

    summary_rows, sample_rows, valid_rows = [], [], []
    per_activity_hr = {}

    for rec in records:
        fname = os.path.basename(rec)
        act = activity_of(fname)
        if act == "other":
            continue
        if act == "cycling" and not with_bike:
            continue

        try:
            record = wfdb.rdrecord(rec)
        except Exception as e:
            print(f"  [skip] {fname}: {e}")
            continue
        names = [s.strip() for s in record.sig_name]
        if "wrist_ppg" not in names:
            continue
        ppg = record.p_signal[:, names.index("wrist_ppg")]
        duration = len(ppg) / FS

        # PPG → HR (노이즈)
        ppg_hr = hr_from_ppg(ppg)
        t_grid, ppg_grid = resample_to_seconds(*(ppg_hr if ppg_hr else (None, None)),
                                               duration=duration)
        # 보간 처리
        cleaned, outlier_mask = detect_and_interpolate(ppg_grid)

        # ECG 정답
        ecg = hr_from_ecg_rpeaks(rec)
        ecg_t, ecg_hr = ecg if ecg else (None, None)

        # 검증: 보간 전/후 정답 대비 오차
        mae_before = mae_vs_truth(ppg_grid, t_grid, ecg_t, ecg_hr)
        mae_after = mae_vs_truth(cleaned, t_grid, ecg_t, ecg_hr)
        n_out = int(outlier_mask.sum())
        valid_rows.append({
            "record": fname, "activity": act,
            "n_seconds": len(t_grid),
            "n_outliers": n_out,
            "outlier_rate": round(n_out / len(t_grid), 3) if len(t_grid) else None,
            "mae_before_interp": round(mae_before, 2) if mae_before else None,
            "mae_after_interp": round(mae_after, 2) if mae_after else None,
        })
        print(f"  {fname} [{act}]: 아웃라이어 {n_out}/{len(t_grid)} "
              f"({n_out/len(t_grid)*100:.1f}%), "
              f"MAE 보간전 {mae_before} → 보간후 {mae_after}")

        per_activity_hr.setdefault(act, []).extend(
            cleaned[~np.isnan(cleaned)].tolist())

    # 활동별 보간 HR 분포
    for act, vals in per_activity_hr.items():
        v = pd.Series(vals)
        v = v[(v >= HR_MIN) & (v <= HR_MAX)]
        summary_rows.append({
            "dataset": "WristPPG", "variable": "heart_rate_interp",
            "condition_key": "activity", "condition_value": act,
            "n": len(v),
            "mean": round(v.mean(), 2), "std": round(v.std(), 2),
            "min": round(v.min(), 2),
            "p05": round(v.quantile(.05), 2), "p25": round(v.quantile(.25), 2),
            "p50": round(v.quantile(.50), 2), "p75": round(v.quantile(.75), 2),
            "p95": round(v.quantile(.95), 2), "max": round(v.max(), 2),
            "missing_rate": None, "unit": "bpm",
            "layer": "MEASURED_SENSOR", "license": "WristPPG(ODC-By 1.0)",
        })
        keep = v.sample(min(len(v), MAX_SAMPLES_PER_CELL), random_state=42)
        for x in keep:
            sample_rows.append({
                "dataset": "WristPPG", "variable": "heart_rate_interp",
                "condition_key": "activity", "condition_value": act, "value": x})

    pd.DataFrame(summary_rows).to_csv(
        os.path.join(data_dir, "dist_summary_wristppg.csv"),
        index=False, encoding="utf-8-sig")
    pd.DataFrame(sample_rows).to_csv(
        os.path.join(data_dir, "dist_samples_wristppg.csv"),
        index=False, encoding="utf-8-sig")
    vdf = pd.DataFrame(valid_rows)
    vdf.to_csv(os.path.join(data_dir, "interp_validation_wristppg.csv"),
               index=False, encoding="utf-8-sig")

    print("\n[활동별 보간 HR 분포]")
    print(pd.DataFrame(summary_rows)[
        ["condition_value", "n", "mean", "std", "p05", "p50", "p95"]
    ].to_string(index=False))
    print("\n[보간 검증 요약]")
    ok = vdf.dropna(subset=["mae_before_interp", "mae_after_interp"])
    if len(ok):
        print(f"  레코드 {len(ok)}개 평균 아웃라이어율: "
              f"{ok['outlier_rate'].mean()*100:.1f}%")
        print(f"  평균 MAE: 보간 전 {ok['mae_before_interp'].mean():.2f} "
              f"→ 보간 후 {ok['mae_after_interp'].mean():.2f} bpm")
        improved = (ok['mae_after_interp'] < ok['mae_before_interp']).sum()
        print(f"  보간으로 정답 오차가 준 레코드: {improved}/{len(ok)}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('사용: python extract_wristppg_hr.py "<데이터 폴더>" [--with-bike]')
        sys.exit(1)
    main(sys.argv[1], with_bike=("--with-bike" in sys.argv))
