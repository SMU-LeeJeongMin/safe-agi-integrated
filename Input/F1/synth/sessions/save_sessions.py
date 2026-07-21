# -*- coding: utf-8 -*-
"""
save_sessions.py — 합성 세션 산출물 저장 (통합 CSV)
===================================================
build_sessions() 세션 집합을 단일 CSV로 저장한다.

- 세션 길이 = 116행/세션. 근거: 실측 뼈대 세션(116분)을 원본 길이로 따름.
- 구조: session_id · persona_name · age · situation · minute_idx + 신호 9종
- 정답(y)은 미포함 — window 단계에서 규칙-오라클이 부착.

⚠️ 의존성: session_builder 가 Model.maml.tasks (효준 모듈)를 import 한다.
   해당 모듈이 병합된 브랜치에서 실행할 것. 저장소 루트를 SAFE_AGI_REPO 로 지정.
"""
import csv
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# 저장소 루트(Model 패키지 위치)를 경로에 추가. 기본값은 이 파일 기준 상대 추정.
_DEFAULT_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", "..", ".."))
_REPO = os.environ.get("SAFE_AGI_REPO", _DEFAULT_REPO)
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from session_builder import build_sessions

SIGNAL_COLS = ["hr_mean_bpm", "hr_ratio_maxhr", "hr_z_personal", "spo2_min_pct",
               "steps_1min", "speed_mean_mpm", "cumulative_min",
               "heat_index", "accident_prior"]

OUT_DIR = os.environ.get("SESSIONS_OUT", _HERE)   # 기본: 이 폴더에 저장
SESSION_LEN = 116   # 실측 뼈대 세션 길이 (고정 근거)


def save(sessions, out_dir=OUT_DIR):
    os.makedirs(out_dir, exist_ok=True)
    csv_path = os.path.join(out_dir, "synth_sessions.csv")

    header = ["session_id", "persona_name", "age", "situation", "minute_idx"] + SIGNAL_COLS
    total_rows = 0
    len_check = {}
    with open(csv_path, "w", newline="", encoding="utf-8") as fp:
        w = csv.writer(fp)
        w.writerow(header)
        for s in sessions:
            m = s["minutes"]
            n = len(m["hr_mean_bpm"])
            len_check[s["session_id"]] = n
            for i in range(n):
                row = [s["session_id"], s["persona_name"], s["age"], s["situation"], i]
                row += [round(float(m[c][i]), 4) for c in SIGNAL_COLS]
                w.writerow(row)
                total_rows += 1

    # 요약 리포트
    from collections import Counter
    summary = {
        "session_count": len(sessions),
        "session_length_rows": SESSION_LEN,
        "session_length_basis": "실측 뼈대 세션(116분) 길이를 따름",
        "total_rows": total_rows,
        "situation_distribution": dict(Counter(s["situation"] for s in sessions)),
        "persona_count": len(set(s["persona_name"] for s in sessions)),
        "signal_columns": SIGNAL_COLS,
        "label_included": False,
        "label_note": "정답(y)은 window 단계에서 규칙-오라클 부착",
        "all_sessions_116_rows": all(v == SESSION_LEN for v in len_check.values()),
    }
    json_path = os.path.join(out_dir, "sessions_summary.json")
    with open(json_path, "w", encoding="utf-8") as fp:
        json.dump(summary, fp, ensure_ascii=False, indent=2)

    return csv_path, json_path, summary


if __name__ == "__main__":
    sessions = build_sessions()
    csv_path, json_path, summary = save(sessions)
    print("저장 완료")
    print("  CSV :", csv_path)
    print("  요약:", json_path)
    print()
    print(json.dumps(summary, ensure_ascii=False, indent=2))
