"""
Feature Table 생성 엔진 v4 (실측 파이프라인, 우회 없음)
======================================================
v3 문제: 스토리라인 값을 feature에 직접 주입 (집계 엔진 우회).
v4 해결: 원천 시계열 → resample 엔진(계층1) → feature. 데모도 동일 경로.
"""
from datetime import datetime, timedelta, timezone
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from features.schema import (COLUMNS, PERSONA, validate_columns, spo2_grade)
from features.resample import (resample_1min, interpolate_minute, gps_speed_1min,
                               sustained_overload, to_utc, KST)
from data_adapters.biometric import estimate_baseline, load_heart_rate
from data_adapters.weather import (OpenMeteoArchiveProvider,
                                   OpenMeteoProvider, StatVirtualWeatherProvider)
from data_adapters.accident import accident_prior_summer

UUID = "sess_demo_f1"
# 청계산 데모 앵커 (GIS+POI 둘 다 보유, est_min FLINK 계산 가능)
DEMO_LAT, DEMO_LON = 37.4212, 127.0421   # 청계산 GIS 노드 부근


def build_from_series(uuid, hr_series, spo2_series, step_series, gps_series,
                      *, hr_rest, hr_std, max_hr, heat_index, accident_prior,
                      age_group, gender):
    """원천 시계열 → 실제 1분 집계 → feature rows."""
    all_dts = [dt for dt, _ in hr_series] + [g[0] for g in gps_series]
    if not all_dts:
        return []
    t_start = min(all_dts).replace(second=0, microsecond=0)
    t_end = max(all_dts).replace(second=0, microsecond=0)
    n_min = int((t_end - t_start).total_seconds() / 60) + 1
    minute_keys = [t_start + timedelta(minutes=i) for i in range(n_min)]

    hr_bucket = resample_1min(hr_series, "mean")
    hr_max_bucket = resample_1min(hr_series, "max")
    hr_filled, hr_interp = interpolate_minute(hr_bucket, minute_keys)
    hr_max_filled, _ = interpolate_minute(hr_max_bucket, minute_keys)
    spo2_bucket = resample_1min(spo2_series, "min")
    spo2_filled, spo2_interp = interpolate_minute(spo2_bucket, minute_keys)
    step_bucket = resample_1min(step_series, "sum")
    step_filled, _ = interpolate_minute(step_bucket, minute_keys)
    gps_1min = gps_speed_1min(gps_series, minute_keys)

    ratio_rows = []
    for m in minute_keys:
        hr_v = hr_filled.get(m)
        ratio = (hr_v / max_hr) if hr_v is not None else 0.0
        ratio_rows.append((m, {"r": round(ratio, 4)}))
    overload_flags = sustained_overload(ratio_rows, "r", 0.60, 0.80, 5)

    rows = []
    for i, m in enumerate(minute_keys):
        hr_v = hr_filled.get(m)
        if hr_v is None:
            continue
        hr_mx = hr_max_filled.get(m, hr_v)
        gps_m = gps_1min.get(m)
        if gps_m:
            lat, lon, _, speed = gps_m
        else:
            lat, lon, speed = DEMO_LAT, DEMO_LON, 0.0
        spo2_v = spo2_filled.get(m)
        cumulative = i
        flags = []
        if m in hr_interp: flags.append("hr_interp")
        if spo2_v is None: flags.append("spo2")
        elif m in spo2_interp: flags.append("spo2_interp")
        if gps_m is None: flags.append("gps")
        rows.append({
            "uuid": uuid, "ts": to_utc(m),
            "user_lat": round(lat, 6), "user_lon": round(lon, 6),
            "hr_mean_bpm": round(hr_v, 1), "hr_max_bpm": round(hr_mx, 1),
            "hr_ratio_maxhr": round(hr_v / max_hr, 4),
            "hr_overload_5min": overload_flags[i],
            "hr_z_personal": round((hr_v - hr_rest) / hr_std, 4),
            "spo2_min_pct": round(spo2_v, 1) if spo2_v is not None else None,
            "spo2_grade": spo2_grade(spo2_v),
            "steps_1min": int(step_filled.get(m, 0)),
            "speed_mean_mpm": round(speed, 1),
            "cumulative_min": cumulative,
            "rest_due_90min": (cumulative > 0 and cumulative % 90 == 0),
            "heat_index": heat_index, "accident_prior": accident_prior,
            "age_group": age_group, "gender": gender,
            "missing_flags": ",".join(flags),
        })
    return rows


def _demo_series():
    """
    데모 시나리오를 '원천 시계열'로 생성 (실측 간격 모사).
    심박 앵커(F1 서사)에 느어아웅 실측 변동성을 노이즈로 적용.
    """
    from features.hr_pattern import apply_realistic_noise
    t0 = datetime(2023, 8, 4, 14, 0, tzinfo=KST)

    # 심박 앵커: 8분 간격, 0~115분 연속 서사 (정상→상승→이상→회복)
    hr_anchors = [
        (0, 78), (8, 82), (16, 85), (24, 88), (32, 90), (40, 92),
        (48, 105), (56, 120),
        (64, 132), (72, 140), (80, 146), (88, 148),
        (96, 138), (104, 124), (112, 112), (115, 108),
    ]
    # 느어아웅 실측 변동성 노이즈 적용 (앵커 형태 유지 + 실측 요동)
    hr_series = [(t0 + timedelta(minutes=mm), apply_realistic_noise(v, mm))
                 for mm, v in hr_anchors]

    spo2_anchors = [(0, 98), (30, 98), (55, 97), (75, 96), (88, 95), (105, 97)]
    spo2_series = [(t0 + timedelta(minutes=mm), v) for mm, v in spo2_anchors]

    # 걸음: 정상 활발 → 이상 급감 → 회복 저조
    step_series = ([(t0 + timedelta(minutes=m), 95) for m in range(0, 45)]
                   + [(t0 + timedelta(minutes=m), max(90 - (m-45)*4, 10)) for m in range(45, 91)]
                   + [(t0 + timedelta(minutes=m), 25) for m in range(91, 116)])

    # GPS: 5초 간격. 이상구간(60~90분)은 이동속도 저하(간격당 이동 축소)
    gps_series = []
    lat, lon = DEMO_LAT, DEMO_LON
    for m in range(0, 116):
        # 분당 이동량: 정상 빠름, 이상 느림, 회복 매우 느림
        if m < 45:
            step_m = 0.00018        # 정상 (약 20m/5s → 240m/min 수준 축소 스케일)
        elif m < 90:
            step_m = 0.00006        # 이상 (이동 저하)
        else:
            step_m = 0.00003        # 회복 (거의 정지)
        for s in range(0, 60, 5):
            dt = t0 + timedelta(minutes=m, seconds=s)
            lat += step_m / 12       # 5초당(=분당/12)
            lon += step_m / 12 * 0.8
            gps_series.append((dt, round(lat, 6), round(lon, 6), None))
    return hr_series, spo2_series, step_series, gps_series


def build_feature_table():
    """데모: 시나리오 시계열을 실측 파이프라인에 통과."""
    acc = accident_prior_summer()
    # 기상 (절충안): 과거 폭염일 실측 API(실연동+고온) → 실패 시 통계가상 폴백
    # 시연 폭염일: 2023-08-04 (Colab 확인: 청계산 오후2시 29.2℃, 흐림, 습도57%)
    #   ※ 비/뇌우 없는 순수 고온일로 선정 (다른 후보일은 이슬비·비)
    HEATWAVE_DATE = "2023-08-04"
    try:
        wx = OpenMeteoArchiveProvider(date=HEATWAVE_DATE, hour=14).get_weather(DEMO_LAT, DEMO_LON)
        if wx.get("temperature") is None or wx["temperature"] < 26:
            raise RuntimeError("고온 아님, 폴백")
    except Exception:
        wx = StatVirtualWeatherProvider().get_weather(DEMO_LAT, DEMO_LON, datetime(2023, 8, 4, 14, 0))
    hr_s, spo2_s, step_s, gps_s = _demo_series()
    # 안정시 심박·표준편차: 질병청 2024 60대 남성 실측 (느어아웅 30대 아님)
    rows = build_from_series(
        UUID, hr_s, spo2_s, step_s, gps_s,
        hr_rest=PERSONA["resting_hr"], hr_std=PERSONA["resting_hr_std"],
        max_hr=PERSONA["max_hr"], heat_index=wx["heat_index"],
        accident_prior=acc["prior"],
        age_group=PERSONA["age_group"], gender=PERSONA["gender"])
    meta = {
        "hr_pattern_source": "느어아웅 실측 변동성(연속변화 std 12.1, n=47,336)을 앵커곡선에 노이즈 적용",
        "resting_hr_source": "국건영 2020~2024 5개년 통합 60대 남성 실측 (평균58.3, std13.6, n=398)",
        "resting_hr": PERSONA["resting_hr"], "hr_std": PERSONA["resting_hr_std"],
        "max_hr_source": "Fox 공식 220-65 (질병청 최대심박 미측정)",
        "accident_prior_measured": acc,
        "weather_injected": wx, "max_hr": PERSONA["max_hr"],
        "demo_location": "청계산 (GIS+POI 보유, est_min FLINK 계산 가능)",
        "pipeline": "원천시계열 → resample(1분집계·보간) → GPS속도실계산 → 과부하5분(시간기반) → UTC변환",
        "demo_note": "데모 시나리오도 실측 파이프라인 전 과정 통과 (값 주입 우회 없음)",
    }
    return rows, meta


if __name__ == "__main__":
    import pandas as pd
    rows, meta = build_feature_table()
    df = pd.DataFrame(rows, columns=COLUMNS)
    validate_columns(df)
    print(f"생성 {len(df)}행 × {len(df.columns)}컬럼 (실측 파이프라인 v4)")
    print(f"파이프라인: {meta['pipeline']}")
    print(f"\n실제 계산 검증:")
    print(f"  speed: {df.speed_mean_mpm.min():.1f}~{df.speed_mean_mpm.max():.1f} m/min (GPS 실계산)")
    print(f"  보간행: {(df.missing_flags.str.contains('interp')).sum()}개")
    print(f"  UTC ts 예시: {df.ts.iloc[0]}")
    print(f"\n구간별:")
    for label, mask in [("정상", df.cumulative_min <= 30),
                        ("이상", (df.cumulative_min >= 60) & (df.cumulative_min <= 90)),
                        ("회복", df.cumulative_min >= 100)]:
        seg = df[mask]
        if len(seg):
            print(f"  {label}: 심박{seg.hr_mean_bpm.min():.0f}~{seg.hr_mean_bpm.max():.0f} "
                  f"과부하5분={seg.hr_overload_5min.any()} "
                  f"speed{seg.speed_mean_mpm.min():.0f}~{seg.speed_mean_mpm.max():.0f}")
