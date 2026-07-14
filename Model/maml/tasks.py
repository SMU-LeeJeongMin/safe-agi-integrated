# -*- coding: utf-8 -*-
"""
tasks.py — 페르소나 스윕 기반 가상 사용자 태스크 생성
=====================================================
실 세션(Input/F1/outputs/fatigue_minute_features.csv, 116분)을 뼈대로,
나이·기준 안정심박·체력 수준이 다른 가상 사용자의 세션 시계열을 합성한다.

- 교사 라벨: 룰 엔진 compute_e1_e2 를 "개인특성을 아는 오라클"로 호출
  (persona의 진짜 MaxHR·기준심박으로 hr_ratio_maxhr / hr_z_personal 계산).
- 학생(MLP) 입력: 개인특성 피처를 은닉한 관측 7종만 사용
  → 모델은 support 30분 적응만으로 개인차를 흡수해야 함 (MAML 검증 포인트).
- 태스크 분할: 초반 30분 = support, 나머지 = query.
"""
import csv
import os
from dataclasses import dataclass, asdict

import numpy as np

import sys
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from Model.f1_model import compute_e1_e2  # 교사(라벨 생성기)로만 사용

BASE_CSV = os.path.join(_REPO_ROOT, "Input", "F1", "outputs", "fatigue_minute_features.csv")

# 학생 모델 입력 7종 — 개인특성(나이, MaxHR 비율, 개인 z-score)은 의도적으로 제외
STUDENT_FEATURES = [
    "hr_mean_bpm", "spo2_min_pct", "steps_1min", "speed_mean_mpm",
    "cumulative_min", "heat_index", "accident_prior",
]

SUPPORT_MIN = 30          # 초반 30분 = support set
BASE_REST_HR = 58.0       # 원본 세션의 기준 안정심박 (personal_baseline PRIOR와 동일 근거)


@dataclass
class Persona:
    name: str
    age: int          # 30~75
    rest_hr: float    # 기준 안정심박 (bpm)
    hr_std: float     # 개인 심박 변동 폭 (z-score 분모)
    fitness: float    # 체력 수준 0.7(낮음)~1.3(높음)

    @property
    def max_hr(self) -> float:
        return 220.0 - self.age


@dataclass
class Task:
    persona: Persona
    X_support: np.ndarray   # (30, 7)
    Y_support: np.ndarray   # (30, 2)  e1,e2 교사 라벨
    X_query: np.ndarray     # (86, 7)
    Y_query: np.ndarray     # (86, 2)


def load_base_session():
    """원본 116분 세션에서 합성에 필요한 컬럼만 numpy 배열로 로드."""
    cols = {k: [] for k in ["hr_mean_bpm", "spo2_min_pct", "steps_1min",
                            "speed_mean_mpm", "cumulative_min", "heat_index",
                            "accident_prior"]}
    with open(BASE_CSV, encoding="utf-8") as fp:
        for row in csv.DictReader(fp):
            for k in cols:
                cols[k].append(float(row[k]))
    return {k: np.asarray(v) for k, v in cols.items()}


def synth_session(base, p: Persona, rng: np.random.Generator):
    """페르소나 특성에 맞게 원본 세션을 변형한 분 단위 시계열 생성."""
    n = len(base["hr_mean_bpm"])

    # 심박: 원본의 '운동 강도(effort)'는 유지하되, 개인 기준심박에서 출발하고
    # 체력이 낮을수록 같은 강도에 심박이 더 크게 반응
    effort = base["hr_mean_bpm"] - BASE_REST_HR
    hr_gain = 1.0 / p.fitness
    hr = p.rest_hr + effort * hr_gain + rng.normal(0.0, 1.2, n)
    hr = np.clip(hr, p.rest_hr - 3.0, p.max_hr * 0.97)

    ratio = hr / p.max_hr

    # SpO2: 고강도 구간에서 저체력·고령일수록 더 떨어짐
    drop_k = 20.0 * (1.3 - p.fitness) * (p.age / 65.0)
    spo2 = base["spo2_min_pct"] - np.maximum(0.0, ratio - 0.6) * drop_k
    spo2 = np.clip(spo2 + rng.normal(0.0, 0.15, n), 89.0, 99.0)

    # 이동량: 체력에 비례해 걸음·속도 스케일
    move_mult = 0.75 + 0.45 * (p.fitness - 0.7) / 0.6
    steps = np.clip(base["steps_1min"] * move_mult + rng.normal(0.0, 2.0, n), 0, None)
    speed = np.clip(base["speed_mean_mpm"] * move_mult + rng.normal(0.0, 0.5, n), 0, None)

    return {
        "hr_mean_bpm": hr,
        "hr_ratio_maxhr": ratio,                         # 교사 전용 (은닉)
        "hr_z_personal": (hr - p.rest_hr) / p.hr_std,    # 교사 전용 (은닉)
        "spo2_min_pct": spo2,
        "steps_1min": steps,
        "speed_mean_mpm": speed,
        "cumulative_min": base["cumulative_min"],
        "heat_index": base["heat_index"],
        "accident_prior": base["accident_prior"],
    }


def teacher_labels(sess) -> np.ndarray:
    """룰 엔진 compute_e1_e2 를 분 단위로 호출해 (n,2) 라벨 생성."""
    n = len(sess["hr_mean_bpm"])
    labels = np.empty((n, 2))
    for i in range(n):
        f = {k: float(v[i]) for k, v in sess.items()}
        labels[i] = compute_e1_e2(f)
    return labels


def make_task(base, p: Persona, seed: int) -> Task:
    rng = np.random.default_rng(seed)
    sess = synth_session(base, p, rng)
    X = np.stack([sess[k] for k in STUDENT_FEATURES], axis=1)   # 개인특성 은닉
    Y = teacher_labels(sess)
    s = int(SUPPORT_MIN)
    return Task(p, X[:s], Y[:s], X[s:], Y[s:])


def demo_personas():
    """미팅 시연용 고정 스윕 10명: 나이 30→75, 기준심박·체력을 교차 변화."""
    ages = np.linspace(30, 75, 10).round().astype(int)
    rest_hrs = [55, 72, 60, 80, 52, 68, 76, 58, 65, 71]
    fits = [1.30, 0.85, 1.15, 0.70, 1.25, 0.95, 0.75, 1.10, 0.90, 0.80]
    stds = [9, 12, 10, 14, 8, 11, 13, 9, 11, 12]
    return [
        Persona(f"user{i+1:02d}", int(ages[i]), float(rest_hrs[i]),
                float(stds[i]), float(fits[i]))
        for i in range(10)
    ]


def train_personas(n=30, seed=7):
    """메타학습용 랜덤 페르소나 (시연 10명과 다른 seed로 분리)."""
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        out.append(Persona(
            name=f"train{i:02d}",
            age=int(rng.integers(30, 76)),
            rest_hr=float(rng.uniform(50, 82)),
            hr_std=float(rng.uniform(8, 14)),
            fitness=float(rng.uniform(0.7, 1.3)),
        ))
    return out


def make_tasks(personas, base=None, seed0=1000):
    base = base if base is not None else load_base_session()
    return [make_task(base, p, seed0 + i) for i, p in enumerate(personas)]


if __name__ == "__main__":
    tasks = make_tasks(demo_personas())
    for t in tasks:
        print(f"{t.persona.name}: age={t.persona.age} rest={t.persona.rest_hr:.0f} "
              f"fit={t.persona.fitness:.2f} | support {t.X_support.shape} "
              f"query {t.X_query.shape} | query e1 mean={t.Y_query[:,0].mean():.3f}")
