# -*- coding: utf-8 -*-
"""
window_features_fast.py — 벡터화 슬라이딩 window 학습셋 구성 (Phase 2 벌크)
============================================================================
window_features.py 와 결과가 100% 동일하되, numpy 벡터화로 수십 배 빠르다.
벌크(수백만 window) 생성용. 기존 파이썬 루프판은 소규모·검산용으로 유지.

동일성 보장 포인트:
  - 통계(mean/max/min/std/slope)·round(4) 규칙 동일.
  - 정답: 분당 e1/e2 를 rule_ref.compute_e1_e2 로 계산 후, window 내 max 대표.
    (기존과 동일. 규칙 함수 자체는 재사용.)
  - 컬럼 순서·이름 동일.

정답 교체 지점: teacher 계산부(분당 e1/e2 산출)는 rule_ref 를 그대로 호출하므로,
실데이터 y_outcome 도착 시 기존과 같은 위치를 교체하면 된다.
"""
import csv
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_SYNTH = os.path.dirname(_HERE)
for _p in (_HERE, _SYNTH):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from rule_ref import compute_e1_e2, risk_level

DYNAMIC_SIGNALS = ["hr_mean_bpm", "hr_ratio_maxhr", "hr_z_personal",
                   "spo2_min_pct", "steps_1min", "speed_mean_mpm"]
CONTEXT_SIGNALS = ["cumulative_min", "heat_index", "accident_prior"]
WINDOW_SIZES = [1, 3, 5, 10, 13]


def _sliding_stats(arr, w):
    """
    1D arr 에 대해 창 크기 w 슬라이딩 통계 (n-w+1, ) 반환:
    mean, max, min, std, slope. 벡터화.
    """
    n = len(arr)
    m = n - w + 1
    # 슬라이딩 뷰 (m, w)
    idx = np.arange(m)[:, None] + np.arange(w)[None, :]
    win = arr[idx]                      # (m, w)
    mean = win.mean(axis=1)
    mx = win.max(axis=1)
    mn = win.min(axis=1)
    std = win.std(axis=1)
    if w < 2:
        slope = np.zeros(m)
    else:
        # 선형회귀 기울기 = cov(x,y)/var(x). x=0..w-1 고정.
        x = np.arange(w)
        xm = x.mean()
        xc = x - xm
        varx = (xc ** 2).sum()
        yc = win - mean[:, None]
        slope = (yc * xc[None, :]).sum(axis=1) / varx
    return mean, mx, mn, std, slope


def _teacher_e1e2_perminute(sig):
    """
    분당 e1/e2 를 계산 (n,). rule_ref.compute_e1_e2 를 분마다 호출.
    (규칙 함수 재사용 — 기존과 동일 결과. 여기가 정답 교체 지점.)
    """
    n = len(sig["hr_mean_bpm"])
    e1 = np.empty(n)
    e2 = np.empty(n)
    for i in range(n):
        f = {k: float(sig[k][i]) for k in DYNAMIC_SIGNALS + CONTEXT_SIGNALS}
        a, b = compute_e1_e2(f)
        e1[i] = a
        e2[i] = b
    return e1, e2


def build_windows_to_csv(csv_path, out_path):
    """
    벌크용: 윈도우를 메모리에 다 쌓지 않고 세션별로 생성해 즉시 CSV 에 스트리밍
    저장. 대규모(수백만 window)에서 build_windows 는 OOM 위험 → 이 함수 사용.
    반환: (윈도우 수, 등급 Counter).
    """
    from collections import Counter
    # 세션별 신호 로드 (한 번에 로드하되 window 는 안 쌓음)
    sessions = {}
    order = []
    meta_of = {}
    with open(csv_path, encoding="utf-8") as fp:
        for r in csv.DictReader(fp):
            sid = int(r["session_id"])
            if sid not in sessions:
                sessions[sid] = {k: [] for k in DYNAMIC_SIGNALS + CONTEXT_SIGNALS}
                sessions[sid]["_minute"] = []
                order.append(sid)
                meta_of[sid] = r
            for k in DYNAMIC_SIGNALS + CONTEXT_SIGNALS:
                sessions[sid][k].append(float(r[k]))
            sessions[sid]["_minute"].append(int(r["minute_idx"]))

    header = None
    wid = 0
    dist = Counter()
    fp_out = open(out_path, "w", newline="", encoding="utf-8")
    writer = None

    for sid in order:
        s = sessions[sid]
        meta = meta_of[sid]
        ordr = np.argsort(s["_minute"])
        sig = {k: np.asarray(s[k])[ordr] for k in DYNAMIC_SIGNALS + CONTEXT_SIGNALS}
        n = len(sig["hr_mean_bpm"])
        e1_min, e2_min = _teacher_e1e2_perminute(sig)

        session_rows = []
        for w in WINDOW_SIZES:
            m = n - w + 1
            if m <= 0:
                continue
            feats = {}
            for k in DYNAMIC_SIGNALS:
                mean, mx, mn, std, slope = _sliding_stats(sig[k], w)
                feats[f"{k}__mean"] = np.round(mean, 4)
                feats[f"{k}__max"] = np.round(mx, 4)
                feats[f"{k}__min"] = np.round(mn, 4)
                feats[f"{k}__std"] = np.round(std, 4)
                feats[f"{k}__slope"] = np.round(slope, 4)
            for k in CONTEXT_SIGNALS:
                feats[f"{k}__last"] = np.round(sig[k][np.arange(m) + (w - 1)], 4)
            idx = np.arange(m)[:, None] + np.arange(w)[None, :]
            y_e1 = e1_min[idx].max(axis=1)
            y_e2 = e2_min[idx].max(axis=1)
            rep = np.maximum(y_e1, y_e2)
            for j in range(m):
                r_ = rep[j]
                _, risk_lab = risk_level(r_)
                fatigue = ("즉시 중단" if r_ >= 0.85 else
                           "휴식 권고" if r_ >= 0.65 else "정상")
                rec = {"window_id": wid, "session_id": sid,
                       "persona_name": meta["persona_name"], "age": meta["age"],
                       "situation": meta["situation"], "window_size": w,
                       "start_min": j}
                for fk, fv in feats.items():
                    rec[fk] = float(fv[j])
                rec["y_e1"] = round(float(y_e1[j]), 4)
                rec["y_e2"] = round(float(y_e2[j]), 4)
                rec["y_risk_level"] = risk_lab
                rec["y_fatigue_state"] = fatigue
                rec["y_outcome"] = ""
                rec["label_disagreement_flag"] = ""
                session_rows.append(rec)
                dist[risk_lab] += 1
                wid += 1
        if writer is None and session_rows:
            header = list(session_rows[0].keys())
            writer = csv.DictWriter(fp_out, fieldnames=header)
            writer.writeheader()
        if session_rows:
            writer.writerows(session_rows)  # 세션 단위로 flush (메모리 해제)

    fp_out.close()
    return wid, dist


def build_windows(csv_path):
    """벡터화 window 생성. 기존 build_windows 와 동일 스키마·값."""
    # 세션별 신호 로드
    sessions = {}
    order = []
    meta_of = {}
    with open(csv_path, encoding="utf-8") as fp:
        for r in csv.DictReader(fp):
            sid = int(r["session_id"])
            if sid not in sessions:
                sessions[sid] = {k: [] for k in DYNAMIC_SIGNALS + CONTEXT_SIGNALS}
                sessions[sid]["_minute"] = []
                order.append(sid)
                meta_of[sid] = r
            for k in DYNAMIC_SIGNALS + CONTEXT_SIGNALS:
                sessions[sid][k].append(float(r[k]))
            sessions[sid]["_minute"].append(int(r["minute_idx"]))

    rows = []
    wid = 0
    for sid in order:
        s = sessions[sid]
        meta = meta_of[sid]
        # minute_idx 정렬
        ordr = np.argsort(s["_minute"])
        sig = {k: np.asarray(s[k])[ordr] for k in DYNAMIC_SIGNALS + CONTEXT_SIGNALS}
        n = len(sig["hr_mean_bpm"])

        # 분당 e1/e2 (한 번만)
        e1_min, e2_min = _teacher_e1e2_perminute(sig)

        for w in WINDOW_SIZES:
            m = n - w + 1
            if m <= 0:
                continue
            # X: 동적 신호 통계
            feats = {}
            for k in DYNAMIC_SIGNALS:
                mean, mx, mn, std, slope = _sliding_stats(sig[k], w)
                feats[f"{k}__mean"] = np.round(mean, 4)
                feats[f"{k}__max"] = np.round(mx, 4)
                feats[f"{k}__min"] = np.round(mn, 4)
                feats[f"{k}__std"] = np.round(std, 4)
                feats[f"{k}__slope"] = np.round(slope, 4)
            # context: last 값 (창 끝)
            for k in CONTEXT_SIGNALS:
                last = sig[k][np.arange(m) + (w - 1)]
                feats[f"{k}__last"] = np.round(last, 4)
            # y: window 내 e1/e2 max
            idx = np.arange(m)[:, None] + np.arange(w)[None, :]
            y_e1 = e1_min[idx].max(axis=1)
            y_e2 = e2_min[idx].max(axis=1)
            rep = np.maximum(y_e1, y_e2)

            for j in range(m):
                r_ = rep[j]
                _, risk_lab = risk_level(r_)
                fatigue = ("즉시 중단" if r_ >= 0.85 else
                           "휴식 권고" if r_ >= 0.65 else "정상")
                rec = {
                    "window_id": wid,
                    "session_id": sid,
                    "persona_name": meta["persona_name"],
                    "age": meta["age"],
                    "situation": meta["situation"],
                    "window_size": w,
                    "start_min": j,
                }
                for fk, fv in feats.items():
                    rec[fk] = float(fv[j])
                rec["y_e1"] = round(float(y_e1[j]), 4)
                rec["y_e2"] = round(float(y_e2[j]), 4)
                rec["y_risk_level"] = risk_lab
                rec["y_fatigue_state"] = fatigue
                rec["y_outcome"] = ""
                rec["label_disagreement_flag"] = ""
                rows.append(rec)
                wid += 1
    return rows


if __name__ == "__main__":
    import time
    from collections import Counter
    csv_in = os.path.join(_SYNTH, "sessions", "synth_sessions.csv")
    t0 = time.time()
    rows = build_windows(csv_in)
    print(f"총 window: {len(rows):,}  ({time.time()-t0:.0f}초)")
    print("등급 분포:", dict(Counter(r["y_risk_level"] for r in rows)))
