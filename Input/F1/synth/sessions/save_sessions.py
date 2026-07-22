# -*- coding: utf-8 -*-
"""
save_sessions.py — 합성 세션 산출물 저장 (Phase 2 통합)
========================================================
build_sessions() 세션 집합을 단일 CSV로 저장한다.

- 세션 길이 = 116행/세션 (실측 뼈대 세션 길이).
- 메타: session_id · person_id · persona_name · age · age_band · gender ·
        situation · acute_anomaly_flag · minute_idx
- 신호 9종. 정답(y)은 미포함 — window 단계에서 규칙-오라클이 부착.

⚠️ 의존성: session_builder 가 Model.maml.tasks (효준 모듈)를 import.
   SAFE_AGI_REPO 로 저장소 루트 지정.
"""
import csv
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
_DEFAULT_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", "..", ".."))
_REPO = os.environ.get("SAFE_AGI_REPO", _DEFAULT_REPO)
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from session_builder import build_sessions

SIGNAL_COLS = ["hr_mean_bpm", "hr_ratio_maxhr", "hr_z_personal", "spo2_min_pct",
               "steps_1min", "speed_mean_mpm", "cumulative_min",
               "heat_index", "accident_prior"]
META_COLS = ["session_id", "person_id", "persona_name", "age", "age_band",
             "gender", "situation", "acute_anomaly_flag", "minute_idx"]

OUT_DIR = os.environ.get("SESSIONS_OUT", os.path.join(_HERE, "out"))
SESSION_LEN = 116


def save(sessions, out_dir=OUT_DIR):
    os.makedirs(out_dir, exist_ok=True)
    csv_path = os.path.join(out_dir, "synth_sessions.csv")

    total_rows = 0
    len_check = {}
    with open(csv_path, "w", newline="", encoding="utf-8") as fp:
        w = csv.writer(fp)
        w.writerow(META_COLS + SIGNAL_COLS)
        for idx, s in enumerate(sessions):
            m = s["minutes"]
            n = len(m["hr_mean_bpm"])
            len_check[idx] = n
            for i in range(n):
                row = [idx, s["person_id"], s["persona_name"], s["age"],
                       s.get("age_band", ""), s.get("gender", ""),
                       s["situation"], s.get("acute_anomaly_flag", 0), i]
                row += [round(float(m[c][i]), 4) for c in SIGNAL_COLS]
                w.writerow(row)
                total_rows += 1

    from collections import Counter
    summary = {
        "session_count": len(sessions),
        "session_length_rows": SESSION_LEN,
        "total_rows": total_rows,
        "situation_distribution": dict(Counter(s["situation"] for s in sessions)),
        "person_count": len(set(s["person_id"] for s in sessions)),
        "acute_anomaly_count": sum(s.get("acute_anomaly_flag", 0) for s in sessions),
        "signal_columns": SIGNAL_COLS,
        "label_included": False,
        "label_note": "정답(y)은 window 단계에서 규칙-오라클 부착",
        "all_sessions_116_rows": all(v == SESSION_LEN for v in len_check.values()),
    }
    with open(os.path.join(out_dir, "sessions_summary.json"), "w",
              encoding="utf-8") as fp:
        json.dump(summary, fp, ensure_ascii=False, indent=2)
    return csv_path, summary


if __name__ == "__main__":
    # 기본: 국건영 정박 페르소나, weight 기반 샘플
    sessions = build_sessions(n_personas=500, seed0=2000,
                              by_weight=True, sessions_per_persona=8)
    csv_path, summary = save(sessions)
    print("저장:", csv_path)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
