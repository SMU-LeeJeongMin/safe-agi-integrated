# -*- coding: utf-8 -*-
"""window 학습셋 저장 (단일 CSV, X/y 컬럼 구분)."""
import csv, json, os, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from window_features import build_windows, DYNAMIC_SIGNALS, CONTEXT_SIGNALS, WINDOW_SIZES

_HERE = os.path.dirname(os.path.abspath(__file__))
_SYNTH = os.path.dirname(_HERE)

# 입력: 이웃한 sessions/ 의 합성 세션, 출력: 이 windows/ 폴더
SESSIONS_CSV = os.path.join(_SYNTH, "sessions", "synth_sessions.csv")
OUT = _HERE

rows = build_windows(SESSIONS_CSV)

# 컬럼 순서: 메타 → X(피처) → y(정답)
meta_cols = ["window_id","session_id","persona_name","age","situation","window_size","start_min"]
x_cols = [k for k in rows[0] if "__" in k]
y_cols = ["y_e1","y_e2","y_risk_level","y_fatigue_state","y_outcome","label_disagreement_flag"]
header = meta_cols + x_cols + y_cols

csv_path = os.path.join(OUT, "window_dataset.csv")
with open(csv_path,"w",newline="",encoding="utf-8") as fp:
    w=csv.DictWriter(fp, fieldnames=header)
    w.writeheader()
    for r in rows: w.writerow({k:r.get(k,"") for k in header})

summary = {
    "total_windows": len(rows),
    "window_sizes": WINDOW_SIZES,
    "windows_per_size": dict(Counter(r["window_size"] for r in rows)),
    "stride": 1,
    "window_rep_rule": "max",
    "x_feature_count": len(x_cols),
    "x_features": x_cols,
    "y_columns": y_cols,
    "y_used_for_training": ["y_e1","y_e2"],
    "y_reserved": ["y_outcome","label_disagreement_flag"],
    "risk_level_distribution": dict(Counter(r["y_risk_level"] for r in rows)),
    "risk_ratio_by_size": {w: round(sum(1 for r in rows if r["window_size"]==w and r["y_risk_level"]=="위험")/
                                    sum(1 for r in rows if r["window_size"]==w),4) for w in WINDOW_SIZES},
    "source": "synth_sessions.csv (40세션 가상)",
    "layer": "가상 (규격 조건 정박)",
    "note_1min": "1분 window는 std=slope=0 (단일 시점). OPTUNA가 선택 시 순간값 모델이 됨",
    "teacher_note": "정답은 teacher_labels 단일 함수에서 규칙-오라클로 생성. 실데이터/결과라벨 오면 이 함수만 교체",
}
json_path = os.path.join(OUT,"window_summary.json")
with open(json_path,"w",encoding="utf-8") as fp:
    json.dump(summary,fp,ensure_ascii=False,indent=2)

print("저장:", csv_path)
print("행:", len(rows), "| X:", len(x_cols), "| y:", len(y_cols))
print("컬럼 총:", len(header))
