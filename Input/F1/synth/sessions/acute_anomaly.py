# -*- coding: utf-8 -*-
"""
acute_anomaly.py — 급성 고심박 스파이크 주입 (Phase 2)
========================================================
상황 축(risk_synth)의 '서서히 악화하는 탈진'과 별개로, 서사 없이 갑자기
치솟는 급성 고심박 이상을 세션의 약 5%에 주입한다.

정박: 느어아웅 실측(73,352건)의 연속변화>40bpm 스파이크 특성.
  - 실측 발생률 1.40%, 급등폭 평균 51(최대 130), 도달심박 평균 92·max 199.
  - 학습셋은 이상 케이스를 의도적으로 늘리므로 주입률 5%로 상향(문서 방침).

성격 구분 (⚠️ 중요):
  - 이것은 '생리적 급성 이상'(부정맥·급성 부하 등 F1 이 감지해야 할 대상)이다.
  - '센서 측정 이상'(워치 오류로 튀는 비생리값, F1 이 걸러낼 대상)은 여기서
    다루지 않는다 — 데이터 품질/전처리(missing_flags 등) 단계 몫으로 분리.

적용 위치: session_builder 에서 상황 축(risk_synth) 주입 후, 세션 확정 직전.
           상황축과 독립이므로 정상/주의/경고/위험 어느 세션에도 얹힐 수 있다.

라벨: 주입된 세션은 acute_anomaly_flag=1 로 표기(메타). 학습 시 이상 케이스
      식별·가중에 사용. y(정답)는 규칙 오라클이 심박 스파이크를 보고 자연히
      판정하므로 여기서 정답을 직접 만들지 않는다(순환참조 방지).
"""
import numpy as np

# 실측 정박 상수 (느어아웅 스파이크 특성)
SPIKE_RATE = 0.05           # 주입률 5% (실측 1.4% → 학습용 상향)
SPIKE_JUMP_MEAN = 50.0      # 급등폭 평균 (실측 51)
SPIKE_JUMP_STD = 18.0       # 급등폭 std (실측 p50 48, p95 74 근사)
SPIKE_JUMP_MAX = 90.0       # 급등폭 상한 (실측 극단 130 은 과도 → 90 제한)
SPIKE_DUR_MIN, SPIKE_DUR_MAX = 1, 3   # 스파이크 지속 분(짧고 급격)
RECOVERY_MIN = 2            # 스파이크 후 회복 분


def maybe_inject_spike(minutes, rng, max_hr, rate=SPIKE_RATE):
    """
    세션에 rate 확률로 급성 고심박 스파이크를 주입.

    minutes : dict[str, np.ndarray] — 상황축까지 적용된 세션
    rng     : np.random.Generator
    max_hr  : float — 페르소나 MaxHR (스파이크 도달 심박 상한)
    반환    : (minutes 사본, injected: bool)

    스파이크가 안 걸리면 원본 그대로 반환(injected=False).
    """
    out = {k: (np.array(v, dtype=float) if hasattr(v, "__len__") else v)
           for k, v in minutes.items()}
    if rng.random() >= rate:
        return out, False

    hr = np.array(out["hr_mean_bpm"], dtype=float)
    n = len(hr)
    if n < 6:
        return out, False

    # 스파이크 위치: 세션 중반부(초반 안정·후반 상황축 구간 피해 독립성 유지)
    dur = int(rng.integers(SPIKE_DUR_MIN, SPIKE_DUR_MAX + 1))
    start = int(rng.integers(n // 6, max(n // 6 + 1, n - dur - RECOVERY_MIN)))

    # 급등폭: 실측 분포에서 샘플, 상한 제한
    jump = float(np.clip(abs(rng.normal(SPIKE_JUMP_MEAN, SPIKE_JUMP_STD)),
                         30.0, SPIKE_JUMP_MAX))

    # 스파이크: 급등 → 유지 → 급회복. 도달 심박은 MaxHR 안으로 제한.
    base_level = hr[start]
    peak = min(base_level + jump, max_hr * 0.99)
    # 급등(1분): base→peak, 유지(dur), 회복(RECOVERY_MIN): peak→원래추세
    hr[start] = peak
    for j in range(1, dur):
        if start + j < n:
            hr[start + j] = peak + rng.normal(0, 3)
    # 회복 구간: peak 에서 원래 값으로 선형 복귀
    for j in range(RECOVERY_MIN):
        idx = start + dur + j
        if idx < n:
            t = (j + 1) / (RECOVERY_MIN + 1)
            hr[idx] = peak * (1 - t) + hr[idx] * t

    out["hr_mean_bpm"] = hr

    # 파생 심박비율 재계산 (있으면)
    if "hr_ratio_maxhr" in out and max_hr > 0:
        out["hr_ratio_maxhr"] = out["hr_mean_bpm"] / max_hr

    return out, True


if __name__ == "__main__":
    rng = np.random.default_rng(1)
    # 정상 곡선에 스파이크 주입 테스트
    base = np.full(116, 95.0)
    minutes = {"hr_mean_bpm": base.copy(), "hr_ratio_maxhr": base / 155}
    injected = 0
    peaks = []
    for i in range(1000):
        out, inj = maybe_inject_spike(
            {"hr_mean_bpm": base.copy(), "hr_ratio_maxhr": base / 155},
            np.random.default_rng(i), max_hr=155)
        if inj:
            injected += 1
            peaks.append(out["hr_mean_bpm"].max())
    print(f"주입률: {injected/1000*100:.1f}% (목표 5%)")
    print(f"스파이크 peak 심박: 평균{np.mean(peaks):.0f} "
          f"min{np.min(peaks):.0f} max{np.max(peaks):.0f} (MaxHR 155 이내)")
