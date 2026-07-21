# -*- coding: utf-8 -*-
"""
window_features.py — 슬라이딩 window 학습셋 구성
=================================================
합성 세션(../sessions/synth_sessions.csv)을 입력으로:
  1) 세션별 슬라이딩 window(1·3·5·10·13분, 1칸씩 겹침) 생성
  2) window 통계 피처(X) — 신호별 평균·최대·최소·표준편차·기울기
  3) 규칙-오라클로 정답(y) 부착 — window 대표는 max
  4) X / y 별도 컬럼 분리

정답 생성은 teacher_labels() 단일 함수에 격리 (교체 지점).
→ 이후 실데이터/결과라벨(y_outcome) 오면 이 함수만 교체.
"""
import csv
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_SYNTH = os.path.dirname(_HERE)          # 상위 synth/ (공용 rule_ref.py 위치)
for _p in (_HERE, _SYNTH):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from rule_ref import compute_e1_e2, risk_level

# 통계를 뽑을 관측 신호 (환경 상수 heat/accident는 window 내 불변이라 평균만)
DYNAMIC_SIGNALS = ["hr_mean_bpm", "hr_ratio_maxhr", "hr_z_personal",
                   "spo2_min_pct", "steps_1min", "speed_mean_mpm"]
CONTEXT_SIGNALS = ["cumulative_min", "heat_index", "accident_prior"]

WINDOW_SIZES = [1, 3, 5, 10, 13]


# ── 통계 피처 (X) ──────────────────────────────────────────
def _slope(arr):
    """구간 선형 추세 기울기 (분당 변화량)."""
    n = len(arr)
    if n < 2:
        return 0.0
    x = np.arange(n)
    return float(np.polyfit(x, arr, 1)[0])


def window_features(win_rows):
    """window 내 분별 행 리스트 → 통계 피처 dict (X)."""
    feat = {}
    for sig in DYNAMIC_SIGNALS:
        v = np.array([r[sig] for r in win_rows], dtype=float)
        feat[f"{sig}__mean"] = round(float(v.mean()), 4)
        feat[f"{sig}__max"] = round(float(v.max()), 4)
        feat[f"{sig}__min"] = round(float(v.min()), 4)
        feat[f"{sig}__std"] = round(float(v.std()), 4)
        feat[f"{sig}__slope"] = round(_slope(v), 4)
    for sig in CONTEXT_SIGNALS:
        v = np.array([r[sig] for r in win_rows], dtype=float)
        feat[f"{sig}__last"] = round(float(v[-1]), 4)  # 누적/환경은 마지막값
    return feat


# ── 정답 (y) — 규칙 오라클, 단일 격리 지점 ──────────────────
def teacher_labels(win_rows):
    """
    window 내 분별 신호로 규칙 e1/e2 산출 → max 대표(설계 §2).
    반환: y dict (y_e1, y_e2, y_risk_level, y_fatigue_state,
                  y_outcome/label_disagreement_flag 예약)
    ⚠️ 정답 교체 지점: 실데이터/결과라벨 오면 이 함수만 교체.
    """
    e1s, e2s = [], []
    for r in win_rows:
        f = {k: float(r[k]) for k in DYNAMIC_SIGNALS + CONTEXT_SIGNALS}
        e1, e2 = compute_e1_e2(f)
        e1s.append(e1); e2s.append(e2)
    y_e1, y_e2 = max(e1s), max(e2s)            # max 대표
    rep = max(y_e1, y_e2)
    _, risk_lab = risk_level(rep)

    # fatigue_state 파생 (규격 근사): rep 기반 3값
    if rep >= 0.85:
        fatigue = "즉시 중단"
    elif rep >= 0.65:
        fatigue = "휴식 권고"
    else:
        fatigue = "정상"

    return {
        "y_e1": y_e1,
        "y_e2": y_e2,
        "y_risk_level": risk_lab,
        "y_fatigue_state": fatigue,
        "y_outcome": "",                 # 예약 (설계 §3-A)
        "label_disagreement_flag": "",   # 예약 (설계 §3-C)
    }


# ── 슬라이딩 window 생성 ────────────────────────────────────
def load_sessions(csv_path):
    """세션별로 그룹화한 dict[session_id] = 행 리스트."""
    sessions = {}
    with open(csv_path, encoding="utf-8") as fp:
        for r in csv.DictReader(fp):
            sid = int(r["session_id"])
            sessions.setdefault(sid, []).append(r)
    # minute_idx 순 정렬
    for sid in sessions:
        sessions[sid].sort(key=lambda x: int(x["minute_idx"]))
    return sessions


def build_windows(csv_path):
    sessions = load_sessions(csv_path)
    rows = []
    wid = 0
    for sid, srows in sessions.items():
        meta = srows[0]
        n = len(srows)
        for wsize in WINDOW_SIZES:
            for start in range(n - wsize + 1):
                win = srows[start:start + wsize]
                X = window_features(win)
                y = teacher_labels(win)
                rec = {
                    "window_id": wid,
                    "session_id": sid,
                    "persona_name": meta["persona_name"],
                    "age": meta["age"],
                    "situation": meta["situation"],
                    "window_size": wsize,
                    "start_min": start,
                    **X,   # 피처
                    **y,   # 정답
                }
                rows.append(rec)
                wid += 1
    return rows


if __name__ == "__main__":
    import json
    from collections import Counter

    # 기본 입력: 이웃한 sessions/ 폴더의 합성 세션 CSV
    csv_in = os.path.join(_SYNTH, "sessions", "synth_sessions.csv")

    rows = build_windows(csv_in)
    print("총 window:", len(rows))
    print("window 크기별:", dict(Counter(r["window_size"] for r in rows)))
    print("정답 등급 분포:", dict(Counter(r["y_risk_level"] for r in rows)))
    # 피처/정답 컬럼 수
    sample = rows[0]
    x_cols = [k for k in sample if "__" in k]
    y_cols = [k for k in sample if k.startswith("y_") or k == "label_disagreement_flag"]
    print(f"X 피처 {len(x_cols)}개, y 컬럼 {len(y_cols)}개")
