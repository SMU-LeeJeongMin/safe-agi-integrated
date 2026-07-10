"""
생체 데이터 어댑터
==================
심박 / SpO2 / 걸음 / 피부온도를 1분 단위로 정렬.
실측 시간 분포 제약(SpO2·체온은 2024-09 이후)을 그대로 반영.
"""
from datetime import datetime, timedelta
import statistics
from .common import get_zip, load_csv, col_index, parse_dt


def load_heart_rate(z):
    """[(datetime, hr, hr_min, hr_max)] 반환."""
    hdr, rows = load_csv(z, "tracker.heart_rate")
    i_st = col_index(hdr, "heart_rate.start_time", "start_time")
    i_hr = col_index(hdr, "heart_rate.heart_rate", "heart_rate")
    i_mn = col_index(hdr, "heart_rate_min")
    i_mx = col_index(hdr, "heart_rate_max")
    out = []
    if i_st is None or i_hr is None:      # 필수 컬럼 누락 시 방어
        return out
    for r in rows:
        if len(r) <= max(i_st, i_hr):
            continue
        dt = parse_dt(r[i_st])
        if not dt:
            continue
        try:
            hr = float(r[i_hr])
        except (ValueError, IndexError):
            continue
        if hr <= 0:
            continue
        def ff(i):
            try:
                return float(r[i])
            except (ValueError, IndexError, TypeError):
                return None
        out.append((dt, hr, ff(i_mn), ff(i_mx)))
    out.sort()
    return out


def estimate_baseline(hr_data):
    """개인 baseline: 실측 안정시 심박(하위10%)과 표준편차."""
    hrs = [h for _, h, _, _ in hr_data]
    if not hrs:                                          # 심박 데이터 없음 방어
        return {"resting_hr": None, "mean_hr": None, "std_hr": None, "n": 0}
    hrs_sorted = sorted(hrs)
    resting = hrs_sorted[len(hrs_sorted) // 10]          # 하위 10퍼센타일
    mean = statistics.mean(hrs)
    std = statistics.pstdev(hrs)
    return {"resting_hr": round(resting, 1),
            "mean_hr": round(mean, 1),
            "std_hr": round(std, 1),
            "n": len(hrs)}


def load_spo2(z):
    """[(datetime, spo2_min, spo2_max)] 반환."""
    hdr, rows = load_csv(z, "tracker.oxygen_saturation")
    i_st = col_index(hdr, "oxygen_saturation.start_time", "start_time")
    i_mn = col_index(hdr, "min")
    i_mx = col_index(hdr, "max")
    out = []
    for r in rows:
        if len(r) <= i_st:
            continue
        dt = parse_dt(r[i_st])
        if not dt:
            continue
        def ff(i):
            try:
                return float(r[i])
            except (ValueError, IndexError, TypeError):
                return None
        out.append((dt, ff(i_mn), ff(i_mx)))
    out.sort()
    return out


def load_skin_temp(z):
    """[(datetime, temp, tmax, tmin)] 반환."""
    hdr, rows = load_csv(z, "skin_temperature")
    i_st = col_index(hdr, "start_time")
    i_t = col_index(hdr, "temperature")
    i_mx = col_index(hdr, "max")
    i_mn = col_index(hdr, "min")
    out = []
    for r in rows:
        if len(r) <= i_st:
            continue
        dt = parse_dt(r[i_st])
        if not dt:
            continue
        def ff(i):
            try:
                return float(r[i])
            except (ValueError, IndexError, TypeError):
                return None
        out.append((dt, ff(i_t), ff(i_mx), ff(i_mn)))
    out.sort()
    return out


if __name__ == "__main__":
    z = get_zip()
    hr = load_heart_rate(z)
    print(f"심박 {len(hr)}행, 기간 {hr[0][0].date()}~{hr[-1][0].date()}")
    print("baseline:", estimate_baseline(hr))
    sp = load_spo2(z)
    print(f"SpO2 {len(sp)}행, 기간 {sp[0][0].date()}~{sp[-1][0].date()}")
    sk = load_skin_temp(z)
    print(f"피부온도 {len(sk)}행, 기간 {sk[0][0].date()}~{sk[-1][0].date()}")
