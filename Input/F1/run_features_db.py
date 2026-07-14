"""
실 DB 기반 feature 러너 (Phase 2)
==================================
run_features.py(삼성헬스 zip 데모)를 실 DB read 기반으로 교체.

경로: safe_db read → db_adapter(표준 중간형식) → build_from_series(20컬럼) → CSV

라이브 무변경: read-only 엔진만 사용, DB에 아무것도 쓰지 않음.
services/result.py 교체(Phase 3)는 이 러너가 아니라 서버 측에서 build_from_series를
동일 경로로 호출하는 방식 — 여기서는 검증·CSV 재생성까지만.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd

from features.schema import COLUMNS, PERSONA, validate_columns
from features.build_features import build_from_series
from data_adapters.db_adapter import (make_engine, load_session,
                                       resolve_baseline, resolve_profile)
from data_adapters.weather import OpenMeteoArchiveProvider, StatVirtualWeatherProvider
from data_adapters.accident import accident_prior_summer

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")
os.makedirs(OUT, exist_ok=True)


def run(engine, session_id, *, heatwave_date="2023-08-04", weather_hour=14):
    hr, spo2, step, gps, meta = load_session(engine, session_id)

    # 환경 보정: 폭염일 실측 API → 실패 시 통계가상 폴백 (기존과 동일)
    anchor_lat = gps[0][1] if gps else 37.4212
    anchor_lon = gps[0][2] if gps else 127.0421
    acc = accident_prior_summer()
    try:
        wx = OpenMeteoArchiveProvider(date=heatwave_date, hour=weather_hour)\
            .get_weather(anchor_lat, anchor_lon)
        if wx.get("temperature") is None or wx["temperature"] < 26:
            raise RuntimeError("고온 아님, 폴백")
    except Exception:
        from datetime import datetime
        wx = StatVirtualWeatherProvider().get_weather(
            anchor_lat, anchor_lon, meta["start_time"])

    bl = resolve_baseline(meta)
    age_group, gender = resolve_profile(meta)

    rows = build_from_series(
        session_id, hr, spo2, step, gps,
        hr_rest=bl["resting_hr"], hr_std=bl["hr_std"], max_hr=bl["max_hr"],
        is_fallback=bl["is_fallback"],
        heat_index=wx["heat_index"], accident_prior=acc["prior"],
        age_group=age_group, gender=gender)

    report = {
        "session_id": session_id,
        "signal_counts": {"hr": len(hr), "spo2": len(spo2),
                          "step": len(step), "gps": len(gps)},
        "session_start": str(meta["start_time"]),
        "session_end_resolved": str(meta.get("end_time")),
        "baseline_source": bl["source"],
        "baseline": {"hr_rest": bl["resting_hr"], "hr_std": bl["hr_std"],
                     "max_hr": bl["max_hr"], "is_fallback": bl["is_fallback"]},
        "profile": {"age_group": age_group, "gender": gender},
        "weather": wx,
        "accident_prior": acc["prior"],
        "n_feature_rows": len(rows),
    }
    return rows, report


if __name__ == "__main__":
    from data_adapters.db_adapter import make_engine
    import json
    eng = make_engine()
    SESSION_ID = "97d67527cd4562da24c276c5e571cfc1"
    rows, report = run(eng, SESSION_ID)
    df = pd.DataFrame(rows, columns=COLUMNS)
    validate_columns(df)
    path = os.path.join(OUT, "fatigue_minute_features_db.csv")
    df.to_csv(path, index=False)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    print(f"\n생성: {len(df)}행 × {len(df.columns)}컬럼 → {path}")
