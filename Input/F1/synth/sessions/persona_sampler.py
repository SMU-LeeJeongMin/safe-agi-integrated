# -*- coding: utf-8 -*-
"""
persona_sampler.py — 국건영 정박 페르소나 샘플러 (Phase 2)
============================================================
tasks.train_personas() 의 균등난수 페르소나를 대체한다.
연령대×성별 국건영(KNHANES) 실측 분포에서 몸(안정심박·체력·질환)을 샘플링해
tasks.Persona 와 100% 호환되는 객체를 생성한다.

교체 명세:
  기존:  tasks.train_personas(n, seed)   — 균등난수(나이30~76, rest_hr50~82 균등)
  교체:  sample_personas(n, seed)        — 국건영 연령대×성별 분포 정박

정박 소스 (dist_*_knhanes.csv):
  - 안정심박 rest_hr  ← HE_mPLS (연령대×성별 부트스트랩)
  - 체력 fitness      ← BMI 역상관 유도 (BMI 높을수록 체력 낮게), 정박=HE_BMI 분포
  - hr_std            ← 국건영 통합 std 13.6 기준 개인화(±)
  - 질환 flags        ← HE_HP/HE_DM_HbA1c/HE_HCHOL 유병률 (⚠️ 조정자 전용, y 아님)

원칙:
  - 10대 제외 (성인과 안정심박 패턴 상이).
  - 연령대 균등(20s~70s) 기본, 가중치 조정 가능.
  - 질환은 사전확률·민감도 조정자로만 기록. 학습 정답 오용 금지(순환참조 방지).
  - 모든 값 국건영 실측 범위 이탈 금지.
"""
import csv
import os
import sys
from dataclasses import dataclass, field

import numpy as np

# 레포 루트를 경로에 추가해 효준님 tasks.Persona 재사용.
# session_builder.py 와 동일 패턴 (이 파일: Input/F1/synth/sessions/persona_sampler.py).
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
_DEFAULT_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", "..", ".."))
_REPO = os.environ.get("SAFE_AGI_REPO", _DEFAULT_REPO)
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

# tasks.Persona 재사용 (호환 보장). 독립 실행/미발견 대비 fallback 포함.
try:
    from Model.maml.tasks import Persona as _TaskPersona
    _HAS_TASK = True
except Exception:
    _HAS_TASK = False

_HERE = os.path.dirname(os.path.abspath(__file__))
KNHANES_SUMMARY = os.environ.get(
    "KNHANES_SUMMARY",
    os.path.join(_HERE, "dist_summary_knhanes.csv"))
KNHANES_SAMPLES = os.environ.get(
    "KNHANES_SAMPLES",
    os.path.join(_HERE, "dist_samples_knhanes.csv"))

# 성인 연령대 (10대 제외 — 원칙)
ADULT_BANDS = ["20s", "30s", "40s", "50s", "60s", "70s"]
GENDERS = ["M", "F"]

# BMI → 체력(fitness) 매핑 범위 (tasks.Persona.fitness 0.7~1.3 규격)
FIT_HI, FIT_LO = 1.30, 0.70

# Non-EEG SpO2 정박 (dist_summary_noneeg.csv: all/all)
NONEEG_SPO2_MEAN = 95.9
NONEEG_SPO2_STD = 1.71


@dataclass
class PersonaMeta:
    """tasks.Persona + Phase 2 확장 메타(질환 조정자·정박 출처)."""
    name: str
    age: int
    rest_hr: float
    hr_std: float
    fitness: float
    age_band: str
    gender: str
    bmi: float
    # 국건영 전 변수 정박 (Phase 2 전부반영)
    height_cm: float = 0.0      # HE_ht
    weight_kg: float = 0.0      # HE_wt
    sbp: float = 0.0            # HE_sbp 수축기혈압
    dbp: float = 0.0            # HE_dbp 이완기혈압
    waist_cm: float = 0.0       # HE_wc 허리둘레
    tg: float = 0.0             # HE_TG 중성지방
    # 질환 조정자 (y 아님 — 사전확률/민감도 조정 전용)
    cond_hypertension: int = 0
    cond_diabetes: int = 0
    cond_hchol: int = 0
    # SpO2 기저 (Non-EEG 정박)
    spo2_base: float = 0.0
    # 체력 산출 근거 (체형 유도값 — 측정 아님, 실측 체력 도착 시 교체지점)
    fitness_origin: str = "BODY_INFERRED(BMI+WC)"
    # 정박 메타
    label_origin: str = "MEASURED->SCENARIO_VIRTUAL"  # 분포=측정, 개체=합성
    anchor_note: str = ""

    @property
    def max_hr(self) -> float:
        return 220.0 - self.age

    def to_task_persona(self):
        """tasks.synth_session 이 기대하는 Persona 로 변환."""
        if _HAS_TASK:
            return _TaskPersona(self.name, self.age, self.rest_hr,
                                self.hr_std, self.fitness)
        return self  # tasks 없으면 self 반환(동일 속성 보유)


# ── 국건영 로더 ──────────────────────────────────────────────
def _load_summary():
    """{(variable, 'band|gender'): row_dict}"""
    idx = {}
    with open(KNHANES_SUMMARY, encoding="utf-8-sig") as fp:
        for r in csv.DictReader(fp):
            idx[(r["variable"], r["condition_value"])] = r
    return idx


def _load_samples():
    """{(variable, 'band|gender'): np.array(values)} — 부트스트랩용."""
    store = {}
    with open(KNHANES_SAMPLES, encoding="utf-8-sig") as fp:
        for r in csv.DictReader(fp):
            key = (r["variable"], r["condition_value"])
            store.setdefault(key, []).append(float(r["value"]))
    return {k: np.asarray(v) for k, v in store.items()}


def _bootstrap(samples, summary, var, cell, rng, lo=None, hi=None):
    """
    var/cell 값 하나 샘플.
    samples 있으면 부트스트랩(실측 재현), 없으면 summary 정규근사.
    lo/hi 로 실측 범위 클리핑(이탈 금지).
    """
    key = (var, cell)
    if key in samples and len(samples[key]) > 0:
        val = float(rng.choice(samples[key]))
    elif key in summary:
        s = summary[key]
        mean = float(s["mean"])
        std = float(s["std"]) if s["std"] else 0.0
        val = rng.normal(mean, std) if std > 0 else mean
    else:
        return None
    # 명시적으로 넘긴 lo/hi 우선. 없을 때만 summary min/max 로 보완.
    if key in summary:
        s = summary[key]
        if lo is None:
            lo = float(s["min"]) if s["min"] else None
        if hi is None:
            hi = float(s["max"]) if s["max"] else None
    if lo is not None:
        val = max(lo, val)
    if hi is not None:
        val = min(hi, val)
    return val


def _prevalence(summary, var, cell):
    """유병률(0~1). 없으면 0."""
    r = summary.get((var, cell))
    if r and r["mean"]:
        return float(r["mean"])
    return 0.0


def _body_to_fitness(bmi, waist, summary, cell, rng):
    """
    체형(BMI + 허리둘레)으로 체력(fitness 0.7~1.3) 사전추정.

    ⚠️ 한계 (명시):
      - 국건영에 체력(심폐지구력·근력) 직접 측정 항목이 없어, 체형으로
        '사전추정'할 뿐 실측이 아니다. label_origin=BODY_INFERRED 로 표기.
      - BMI·허리둘레 둘 다 정상이나 비활동적인 마른 사람은 못 잡는다.
      - 실측 체력 데이터 도착 시 이 함수가 교체 지점.

    로직:
      - 1차: BMI 를 그 연령대 p05~p95 → fitness FIT_HI~FIT_LO 로 선형 대응.
      - 2차 보정(허리둘레): BMI 는 근육/지방을 구분 못 하므로 허리둘레로 보정.
          * BMI 높은데 허리 정상(<p50) = 근육형 → 체력 페널티 완화(+)
          * BMI·허리 둘 다 높음(>p50) = 복부비만형 → 체력 더 낮게(-)
    """
    s_bmi = summary.get(("HE_BMI", cell))
    s_wc = summary.get(("HE_wc", cell))
    if not s_bmi:
        return float(rng.uniform(FIT_LO, FIT_HI)), "BODY_INFERRED(fallback)"

    p05, p95 = float(s_bmi["p05"]), float(s_bmi["p95"])
    if p95 <= p05:
        return 1.0, "BODY_INFERRED"
    # 1차: BMI 기반 (BMI p05→p95 = fitness FIT_HI→FIT_LO)
    t = min(1.0, max(0.0, (bmi - p05) / (p95 - p05)))
    fit = FIT_HI + (FIT_LO - FIT_HI) * t

    # 2차: 허리둘레 보정 (근육형 vs 복부비만형 구분)
    if s_wc:
        wc_p50 = float(s_wc["p50"])
        wc_p95 = float(s_wc["p95"])
        if wc_p95 > wc_p50:
            # 허리가 p50 대비 얼마나 위/아래인지 (-1~+1 규모)
            wc_dev = (waist - wc_p50) / (wc_p95 - wc_p50)
            wc_dev = min(1.0, max(-1.0, wc_dev))
            # 보정폭 최대 ±0.12 (BMI 1차 판정을 뒤집지 않는 선)
            fit -= 0.12 * wc_dev  # 허리 크면 fit↓, 허리 작으면 fit↑
    fit = float(np.clip(fit + rng.normal(0, 0.03), FIT_LO, FIT_HI))
    return fit, "BODY_INFERRED(BMI+WC)"


# ── 메인 샘플러 ──────────────────────────────────────────────
def sample_personas(n=30, seed=7, band_weights=None, genders=None):
    """
    국건영 정박 페르소나 n명 생성. train_personas 시그니처 호환.

    band_weights : {'20s':w, ...} 연령대 가중(기본 균등). 10대 자동 제외.
    genders      : ['M','F'] 성별 풀(기본 균등).
    """
    rng = np.random.default_rng(seed)
    summary = _load_summary()
    samples = _load_samples()

    bands = [b for b in ADULT_BANDS]
    if band_weights:
        w = np.array([band_weights.get(b, 0.0) for b in bands], dtype=float)
    else:
        w = np.ones(len(bands))
    w = w / w.sum()
    genders = genders or GENDERS

    # 연령대 중앙 나이 (Fox MaxHR 계산용)
    band_mid = {"20s": 25, "30s": 35, "40s": 45,
                "50s": 55, "60s": 65, "70s": 75}

    out = []
    for i in range(n):
        band = str(rng.choice(bands, p=w))
        gender = str(rng.choice(genders))
        cell = f"{band}|{gender}"

        # 나이: 연령대 내 균등(경계 포함)
        base_age = band_mid[band]
        age = int(base_age + rng.integers(-4, 5))  # ±4년 분산
        age = max(20, min(79, age))

        # 안정심박: HE_mPLS 부트스트랩 (연령대×성별). 국건영 실측 분포를 그대로
        # 유지(개인차 반영 원칙). 생리적으로 불가능한 값만 막는 최소 안전선
        # (40~130bpm)만 적용 — p95 클리핑은 하지 않음(분포 왜곡 방지).
        rest_hr = _bootstrap(samples, summary, "HE_mPLS", cell, rng,
                             lo=40, hi=130)
        if rest_hr is None:
            rest_hr = 58.0

        # BMI: 키·몸무게에서 계산 (독립샘플 시 개인 내 모순 발생 → 계산으로 정합)
        height = _bootstrap(samples, summary, "HE_ht", cell, rng) or 165.0
        weight = _bootstrap(samples, summary, "HE_wt", cell, rng) or 65.0
        bmi = weight / ((height / 100.0) ** 2)
        # 허리둘레: fitness 보정에 쓰므로 먼저 뽑음
        waist = _bootstrap(samples, summary, "HE_wc", cell, rng) or 84.0
        # 체력: BMI+허리둘레 병용 사전추정 (체형 유도값, 측정 아님)
        fitness, fit_origin = _body_to_fitness(bmi, waist, summary, cell, rng)

        # hr_std: 국건영 셀 std 있으면 그 스케일, 없으면 통합 13.6
        s_mpls = summary.get(("HE_mPLS", cell))
        cell_std = float(s_mpls["std"]) if (s_mpls and s_mpls["std"]) else 13.6
        # tasks 규격(8~14)에 맞춰 개인 변동폭 정규화
        hr_std = float(np.clip(cell_std * rng.uniform(0.7, 1.0), 8.0, 14.0))

        # 질환 조정자 (유병률 기반 베르누이) — ⚠️ y 아님
        cond_hp = int(rng.random() < _prevalence(summary, "HE_HP", cell))
        cond_dm = int(rng.random() < _prevalence(summary, "HE_DM_HbA1c", cell))
        cond_hc = int(rng.random() < _prevalence(summary, "HE_HCHOL", cell))

        # ── 국건영 나머지 변수 정박 (키·몸무게·허리둘레는 위에서 확보) ──
        tg = _bootstrap(samples, summary, "HE_TG", cell, rng) or 120.0

        # 혈압: 고혈압 조정자와 정합. flag=1 이면 분포 상단(p75~) 에서 샘플,
        #      flag=0 이면 정상역 중심. 근거없는 모순(정상혈압+고혈압flag) 방지.
        s_sbp = summary.get(("HE_sbp", cell))
        s_dbp = summary.get(("HE_dbp", cell))
        if cond_hp and s_sbp:
            sbp = rng.uniform(float(s_sbp["p75"]), float(s_sbp["p95"]))
            dbp = rng.uniform(float(s_dbp["p75"]), float(s_dbp["p95"])) if s_dbp else 85.0
        else:
            # flag=0(비고혈압): 정상역 상한(p50~p75)에서 샘플. 상단 꼬리(고혈압
            # 수치)를 배제해 '비고혈압인데 고혈압 수치' 모순 방지.
            if s_sbp:
                sbp = rng.uniform(float(s_sbp["p25"]), float(s_sbp["p75"]))
                dbp = rng.uniform(float(s_dbp["p25"]), float(s_dbp["p75"])) if s_dbp else 76.0
            else:
                sbp, dbp = 118.0, 76.0

        # SpO2 기저: Non-EEG 정박 (연령·성별 무관 전체 분포). 세션 SpO2 곡선의
        #           개인 기저선으로 사용 → synth_session 이 이 기저에서 하강.
        spo2_base = float(np.clip(rng.normal(NONEEG_SPO2_MEAN, NONEEG_SPO2_STD),
                                  93.0, 99.0))

        out.append(PersonaMeta(
            name=f"kn{i:03d}",
            age=age,
            rest_hr=round(float(rest_hr), 1),
            hr_std=round(hr_std, 1),
            fitness=round(fitness, 3),
            age_band=band,
            gender=gender,
            bmi=round(float(bmi), 1),
            height_cm=round(float(height), 1),
            weight_kg=round(float(weight), 1),
            sbp=round(float(sbp), 1),
            dbp=round(float(dbp), 1),
            waist_cm=round(float(waist), 1),
            tg=round(float(tg), 1),
            cond_hypertension=cond_hp,
            cond_diabetes=cond_dm,
            cond_hchol=cond_hc,
            spo2_base=round(float(spo2_base), 1),
            fitness_origin=fit_origin,
            anchor_note=f"HE_mPLS/{cell} 부트스트랩, 체력={fit_origin}, "
                        f"SpO2기저={spo2_base:.1f}(NonEEG)",
        ))
    return out


if __name__ == "__main__":
    from collections import Counter
    ps = sample_personas(n=24, seed=7)
    print(f"생성: {len(ps)}명")
    print("연령대:", dict(Counter(p.age_band for p in ps)))
    print("성별:", dict(Counter(p.gender for p in ps)))
    print()
    print(f"{'name':7s} {'band':5s} {'g':1s} {'age':3s} {'rest':5s} "
          f"{'std':4s} {'fit':5s} {'bmi':5s} {'HP/DM/HC'}")
    for p in ps[:12]:
        print(f"{p.name:7s} {p.age_band:5s} {p.gender:1s} {p.age:3d} "
              f"{p.rest_hr:5.1f} {p.hr_std:4.1f} {p.fitness:5.3f} "
              f"{p.bmi:5.1f} {p.cond_hypertension}/{p.cond_diabetes}/{p.cond_hchol}")
    # 실측 대조: 60대남 안정심박 평균 확인
    import numpy as np
    m60 = [p.rest_hr for p in sample_personas(n=500, seed=1)
           if p.age_band == "60s" and p.gender == "M"]
    if m60:
        print(f"\n검증 60대남 rest_hr 평균={np.mean(m60):.1f} "
              f"(국건영 58.4 기대, 실측주인공 68 포함범위)")
