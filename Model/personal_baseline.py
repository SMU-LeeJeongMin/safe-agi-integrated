# -*- coding: utf-8 -*-
"""
PersonalBaselineAdapter — MAML task 적응 계층 (inner loop)
==========================================================
B(모델) 파트 신규 모듈. 회의록 5번(개인 baseline → MAML task 연결점) 구현.

개념:
- 사용자 1명 = 1 task, 세션 초반 저강도 구간 심박 = support set
- prior(국건영 60대 실측: 안정시 58bpm, std 13.6)에서 시작해
  관측이 쌓일수록 개인값으로 이동하는 shrinkage 적응:

      adapted_mean = (1-λ)·prior_mean + λ·관측평균,   λ = n / (n + k)

- n=0이면 기존 v0(고정 상수)와 완전히 동일하게 동작
  → compute_e1_e2 교체 지점 규칙(입력 feature·출력 0~1·max) 그대로 보존
- outer loop(여러 task로 prior 자체를 메타 학습)는 60대 실데이터 확보 후
  장기 과제 (병렬 작업 문서에 명시). 여기서는 적응 구조까지만 구현.
"""
from dataclasses import dataclass, field


# prior: 국건영 2020~2024 60대 남성 실측 (n=398) — xAI.py 상수와 동일 근거
PRIOR_MEAN = 58.0
PRIOR_STD = 13.6

# support set 선별: 저강도 구간만 baseline 추정에 사용 (과부하 구간 오염 방지)
# 0.6 = 규격 F1 과부하 하한(MaxHR×0.6~0.8)의 하한값
SUPPORT_MAX_RATIO = 0.60

# shrinkage 강도 k: 관측 k분이 쌓이면 λ=0.5 (prior와 개인값 반반)
# 세션 초반 10~20분을 support 창으로 쓰는 설계에 맞춰 k=10 채택
SHRINKAGE_K = 10

# 표본 std가 안정되기 시작하는 최소 관측 수
MIN_N_FOR_STD = 5


@dataclass
class PersonalBaselineAdapter:
    """한 사용자(task)의 안정시 심박 baseline을 온라인 적응."""
    prior_mean: float = PRIOR_MEAN
    prior_std: float = PRIOR_STD
    k: int = SHRINKAGE_K
    _support: list = field(default_factory=list)

    # ── support set 수집 ──
    def observe(self, hr_bpm: float, hr_ratio_maxhr: float) -> bool:
        """저강도 구간(ratio < 0.6) 관측만 support set에 추가. 채택 여부 반환."""
        if hr_bpm is None or hr_ratio_maxhr is None:
            return False
        if hr_ratio_maxhr >= SUPPORT_MAX_RATIO:
            return False
        self._support.append(float(hr_bpm))
        return True

    @classmethod
    def from_support(cls, hr_list, **kwargs):
        """가상 페르소나/데모용: support 심박 리스트로 즉시 적응된 adapter 생성."""
        a = cls(**kwargs)
        a._support = [float(h) for h in hr_list]
        return a

    # ── 적응 파라미터 ──
    @property
    def n(self) -> int:
        return len(self._support)

    @property
    def lam(self) -> float:
        """prior→개인값 이동 비율. n=0이면 0 (완전 prior = 기존 v0 동작)."""
        return self.n / (self.n + self.k)

    @property
    def adapted_mean(self) -> float:
        if self.n == 0:
            return self.prior_mean
        obs_mean = sum(self._support) / self.n
        return (1 - self.lam) * self.prior_mean + self.lam * obs_mean

    @property
    def adapted_std(self) -> float:
        """표본 std는 소표본에서 불안정 → 동일 λ로 shrink, n<5면 prior 유지."""
        if self.n < MIN_N_FOR_STD:
            return self.prior_std
        m = sum(self._support) / self.n
        var = sum((x - m) ** 2 for x in self._support) / (self.n - 1)
        obs_std = max(var ** 0.5, 1.0)  # 퇴화 방지 하한
        return (1 - self.lam) * self.prior_std + self.lam * obs_std

    # ── 적응된 개인 z-score ──
    def hr_z(self, hr_bpm: float) -> float:
        return (float(hr_bpm) - self.adapted_mean) / self.adapted_std

    def summary(self) -> dict:
        """대시보드 표시용 적응 상태."""
        return {
            "support_n": self.n,
            "lambda": round(self.lam, 3),
            "prior_mean": self.prior_mean,
            "adapted_mean": round(self.adapted_mean, 1),
            "adapted_std": round(self.adapted_std, 2),
        }


def personalized_features(feature_row: dict, adapter: PersonalBaselineAdapter) -> dict:
    """
    기존 feature dict의 hr_z_personal만 adapter 기반으로 재계산해 사본 반환.
    infer_f1의 입력 스키마를 전혀 바꾸지 않음 → f1_model.py 수정 불필요.
    사용:  dto5 = infer_f1(personalized_features(f, adapter))
    """
    f = dict(feature_row)
    hr = f.get("hr_mean_bpm")
    if hr is not None:
        f["hr_z_personal"] = round(adapter.hr_z(hr), 4)
    return f


if __name__ == "__main__":
    # 회의록 5번 시나리오 검증: 같은 심박 145, 다른 baseline → 다른 z
    low = PersonalBaselineAdapter.from_support([72, 74, 76, 75, 73, 74, 75, 76, 74, 73])
    high = PersonalBaselineAdapter.from_support([96, 98, 100, 99, 97, 98, 99, 100, 98, 97])
    cold = PersonalBaselineAdapter()  # 관측 0 → 기존 v0와 동일

    print("=== 적응 상태 ===")
    for name, a in [("평소 낮음", low), ("평소 높음", high), ("관측 없음(v0)", cold)]:
        print(f"{name}: {a.summary()}  → hr=145의 z = {a.hr_z(145):.2f}")
