# -*- coding: utf-8 -*-
"""
spo2_baseline.py — SpO2 기저·변동 정박 (Phase 2)
==================================================
synth_session 의 SpO2 는 원본 데모 곡선(base["spo2_min_pct"])에서 출발해,
페르소나의 spo2_base(Non-EEG 정박값)를 쓰지 않는다. 이 모듈은 SpO2 곡선의
정상 기저선을 페르소나별 Non-EEG 정박값으로 교체하고, 실측 변동(std 1.71)을
요동으로 입힌다.

역할 분담 (⚠️ Non-EEG 한계 반영):
  - Non-EEG 는 저산소를 의도 유발한 데이터가 아니라 값이 정상범위(95~100)에
    몰린다(문서 확인). 따라서 F1 경고(90~94)·위험(<90) 구간은 못 채운다.
  - 이 모듈은 '정상 SpO2 기저·변동'만 Non-EEG 로 정박한다.
  - 경고·위험 하강은 risk_synth(상황 축)가 주입한다 — Non-EEG 밖 영역, 가상 명시.

적용 위치: session_builder 에서 synth_session 출력 직후, risk_synth 주입 전.
           심박 변동성(hr_variability)과 같은 후처리 층.

정박 소스: dist_summary_noneeg.csv (SpO2 all/all: 평균 95.9, std 1.71).
"""
import numpy as np

# Non-EEG SpO2 정박 상수 (dist_summary_noneeg.csv, all/all)
NONEEG_SPO2_MEAN = 95.9
NONEEG_SPO2_STD = 1.71

PHI_DEFAULT = 0.7            # SpO2 요동 자기상관 (심박보다 느리게 변함)
SPO2_NORMAL_FLOOR = 93.0    # 정상 기저의 하한 (경고 진입 전). 이 아래는 상황축 몫.
SPO2_CEIL = 99.0


def apply_spo2_baseline(minutes, spo2_base, rng, phi=PHI_DEFAULT):
    """
    SpO2 곡선의 정상 기저선을 페르소나 Non-EEG 정박값으로 교체 + 실측 변동 부여.

    minutes   : dict[str, np.ndarray] — synth_session 출력('spo2_min_pct' 포함)
    spo2_base : float — 페르소나 SpO2 기저 (Non-EEG 정박, 없으면 NONEEG_SPO2_MEAN)
    rng       : np.random.Generator
    반환      : minutes 사본 (spo2_min_pct 를 기저+변동으로 재구성)

    ⚠️ 이 함수는 정상 기저만 만든다. 경고·위험 하강은 이후 risk_synth 가 주입.
       따라서 하한을 SPO2_NORMAL_FLOOR(93) 로 두어 정상범위를 벗어나지 않게 하고,
       위험 구간 생성은 상황 축에 위임한다.
    """
    out = {k: (np.array(v, dtype=float) if hasattr(v, "__len__") else v)
           for k, v in minutes.items()}
    n = len(out["spo2_min_pct"])
    if n < 1:
        return out

    if spo2_base is None or spo2_base <= 0:
        spo2_base = NONEEG_SPO2_MEAN

    # 기존 곡선의 '운동 강도에 따른 하강 형태'는 유지하되(생리적으로 타당),
    # 절대 기저선만 spo2_base 로 이동. 원본 곡선의 base 대비 편차를 보존.
    old = np.array(minutes["spo2_min_pct"], dtype=float)
    old_base = np.median(old)          # 원본 곡선의 기저(중앙값 근사)
    shape = old - old_base             # 강도 하강 형태(편차)

    # 새 기저 = spo2_base, 형태는 유지
    spo2 = spo2_base + shape

    # Non-EEG 실측 변동(std 1.71)을 AR(1) 요동으로 (정상 기저 위에만)
    innov = NONEEG_SPO2_STD * np.sqrt(max(0.0, 1.0 - phi ** 2))
    dev = np.zeros(n)
    for i in range(1, n):
        dev[i] = phi * dev[i - 1] + rng.normal(0.0, innov)
    spo2 = spo2 + dev

    # 정상범위 유지: 경고·위험(<93)은 상황 축 몫이므로 여기서는 하한 93.
    out["spo2_min_pct"] = np.clip(spo2, SPO2_NORMAL_FLOOR, SPO2_CEIL)
    return out


if __name__ == "__main__":
    rng = np.random.default_rng(1)
    # 원본 데모 SpO2 (정상~약간 하강)
    base_spo2 = np.concatenate([np.full(40, 98.0), np.full(40, 96.0), np.full(36, 97.0)])
    minutes = {"spo2_min_pct": base_spo2}
    for sb in [94.6, 95.9, 97.4]:
        out = apply_spo2_baseline(minutes, sb, np.random.default_rng(2))
        s = out["spo2_min_pct"]
        d = np.abs(np.diff(s))
        print(f"spo2_base={sb}: 결과 평균{s.mean():.1f} min{s.min():.1f} max{s.max():.1f} "
              f"분당변화 평균{d.mean():.2f} (정상범위 93~99 유지)")
    print()
    print("Non-EEG 정박: 평균 95.9 근처, 변동 std 1.71 반영, 하한 93(경고미만은 상황축)")
