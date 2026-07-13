"""
최종 배포 (실 DB 기반) — 대시보드 전달용 산출물 생성
=====================================================
export.py(가상 시계열)와 동일한 산출물을 실 safe_db 데이터로 생성한다.

경로: safe_db read → 20컬럼 피처 → F1 모델(infer_f1) → DTO-5 → 대시보드용 파일
생성물(outputs/):
  1) fatigue_minute_features.csv   (A→B 접점, 규격 20컬럼)
  2) dto5_sequence.json            (규격 5블록, 모델 판정 결과)
  3) validation_report.json        (판정 검증 리포트)

라이브 무변경: read-only 엔진만 사용, DB에 아무것도 쓰지 않음.

사용:
  python export_db.py                       # 대표 세션
  python export_db.py <session_id>          # 특정 세션
"""
import os, sys, json
import pandas as pd
from collections import Counter

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(ROOT, "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, REPO_ROOT)

from features.schema import COLUMNS, validate_columns
from Model.f1_model import infer_f1
from data_adapters.location import load_cheonggye_rest
from data_adapters.db_adapter import make_engine
from run_features_db import run

OUT = os.path.join(ROOT, "outputs")
os.makedirs(OUT, exist_ok=True)

# 대표 세션 (검증 완료: 정상 산행, ~123분)
DEFAULT_SESSION = "97d67527cd4562da24c276c5e571cfc1"


def main(session_id=DEFAULT_SESSION, *, heatwave_date="2023-08-04", weather_hour=14):
    # 1) 실 DB → 20컬럼 피처 (검증된 run() 파이프라인 그대로)
    engine = make_engine()  # read-only
    rows, run_report = run(engine, session_id,
                           heatwave_date=heatwave_date, weather_hour=weather_hour)
    if not rows:
        raise RuntimeError(
            f"세션 {session_id}: 생성된 피처 행이 0개입니다. "
            "session_id·시간대(UTC/KST) 매칭을 확인하세요.")

    df = pd.DataFrame(rows, columns=COLUMNS)
    validate_columns(df)
    csv_path = os.path.join(OUT, "fatigue_minute_features.csv")
    df.to_csv(csv_path, index=False)

    # 2) 청계산 휴식지점(POI) → nearest_shelter 호환 형식
    cg = load_cheonggye_rest(os.path.join(ROOT, "data_raw", "poi_1961.shp"))
    shelters = [(n, kw, lon, lat, "청계산") for n, kw, lon, lat, pri in cg]

    # 3) 피처 → 모델 → DTO-5 (export.py와 동일 로직)
    dto5_seq = [infer_f1(r, shelters) for r in rows]
    json.dump(dto5_seq, open(os.path.join(OUT, "dto5_sequence.json"), "w",
                             encoding="utf-8"), ensure_ascii=False, indent=2)

    # 4) 검증 리포트
    states = Counter(d["fatigue"]["state"] for d in dto5_seq)
    report = {
        "source": "safe_db (real)",
        "session_id": session_id,
        "rows": len(df), "columns": len(df.columns),
        "signal_counts": run_report.get("signal_counts"),
        "session_start": run_report.get("session_start"),
        "session_end_resolved": run_report.get("session_end_resolved"),
        "baseline_source": run_report.get("baseline_source"),
        "state_distribution": dict(states),
        "segments": {},
    }
    for label, mask in [("정상", df.cumulative_min <= 30),
                        ("이상", (df.cumulative_min >= 60) & (df.cumulative_min <= 90)),
                        ("회복", df.cumulative_min >= 100)]:
        seg_idx = df[mask].index
        seg_states = [dto5_seq[i]["fatigue"]["state"] for i in seg_idx]
        report["segments"][label] = {
            "hr_range": ([round(float(df.loc[seg_idx].hr_mean_bpm.min()), 1),
                          round(float(df.loc[seg_idx].hr_mean_bpm.max()), 1)]
                         if len(seg_idx) else [None, None]),
            "states": list(dict.fromkeys(seg_states)),
        }
    report["F1_검증"] = {
        "이상구간_기대": "휴식 권고 발동",
        "이상구간_실제": report["segments"]["이상"]["states"],
        "휴식권고_포함": "휴식 권고" in report["segments"]["이상"]["states"],
    }
    fired = [d for d in dto5_seq if d["alerts"]]
    report["alert_발동수"] = len(fired)
    report["nearest_shelter_예시"] = next(
        (d["fatigue"]["nearest_shelter"] for d in dto5_seq
         if d["fatigue"]["nearest_shelter"]), None)
    json.dump(report, open(os.path.join(OUT, "validation_report.json"), "w",
                           encoding="utf-8"), ensure_ascii=False, indent=2)

    return csv_path, report


if __name__ == "__main__":
    sid = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SESSION
    csv_path, report = main(sid)
    print("=== 배포 (실 DB 기반) ===")
    print(f"세션: {report['session_id']}  (source: {report['source']})")
    print("outputs/: fatigue_minute_features.csv, dto5_sequence.json,")
    print("          validation_report.json")
    print(f"\n신호수: {report['signal_counts']}")
    print(f"세션시작: {report['session_start']}  baseline: {report['baseline_source']}")
    print(f"상태분포: {report['state_distribution']}")
    print(f"F1 검증: {json.dumps(report['F1_검증'], ensure_ascii=False)}")
    print(f"alert 발동: {report['alert_발동수']}개")
