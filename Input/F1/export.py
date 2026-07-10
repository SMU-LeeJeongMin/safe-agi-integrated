"""
최종 배포 v3 (규격서 정합)
==========================
1) feature CSV (A→B 접점, 규격 컬럼)
2) DTO-5 시퀀스 (규격 5블록 JSON)
3) 검증 리포트 (규격 판정)
4) 근거 메모
"""
import os, sys, json
import pandas as pd
ROOT = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(ROOT, "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, REPO_ROOT)

from features.schema import COLUMNS, validate_columns
from features.build_features import build_feature_table
from Model.f1_model import infer_f1
from data_adapters.location import load_shelters

OUT = os.path.join(ROOT, "outputs")
os.makedirs(OUT, exist_ok=True)


def main():
    rows, meta = build_feature_table()
    df = pd.DataFrame(rows, columns=COLUMNS)
    validate_columns(df)
    csv_path = os.path.join(OUT, "fatigue_minute_features.csv")
    df.to_csv(csv_path, index=False)

    # 청계산 휴식지점 (업로드 POI, 이름기반). nearest_shelter 호환 형식으로 변환
    from data_adapters.location import load_cheonggye_rest
    cg = load_cheonggye_rest(os.path.join(ROOT, "data_raw", "poi_1961.shp"))
    # (name, cate_cd대용 kw, lon, lat, mntn) 형식
    shelters = [(n, kw, lon, lat, "청계산") for n, kw, lon, lat, pri in cg]
    dto5_seq = [infer_f1(r, shelters) for r in rows]
    json.dump(dto5_seq, open(os.path.join(OUT, "dto5_sequence.json"), "w",
                             encoding="utf-8"), ensure_ascii=False, indent=2)

    # 검증
    from collections import Counter
    states = Counter(d["fatigue"]["state"] for d in dto5_seq)
    report = {
        "rows": len(df), "columns": len(df.columns),
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
    csv_path, report = main()
    print("=== 배포 v3 (규격 정합) ===")
    print("outputs/: fatigue_minute_features.csv, dto5_sequence.json,")
    print("          validation_report.json")
    print(f"\n상태분포: {report['state_distribution']}")
    print(f"F1 검증: {json.dumps(report['F1_검증'], ensure_ascii=False)}")
    print(f"alert 발동: {report['alert_발동수']}개")
