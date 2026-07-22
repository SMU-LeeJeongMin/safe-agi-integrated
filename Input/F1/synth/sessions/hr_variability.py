# -*- coding: utf-8 -*-
"""
hr_variability.py — 심박 곡선 변동성(요동) 노이즈 (Phase 2)
=============================================================
synth_session 이 만든 심박 곡선은 노이즈 std 1.2 로 지나치게 매끄럽다.
프로젝트 방침(3차 결과물 확정 3): "절대값 국건영 + 변동 패턴" 조합으로
'매끄러운 인위적 곡선'이 아니라 '실제 사람의 요동이 섞인 곡선'을 만든다.

적용 위치: session_builder 가 synth_session(사람축) 출력을 받은 직후,
           risk_synth(상황축) 주입 전. 즉 심박 곡선 후처리.

방식: AR(1) 자기상관 노이즈.
  - 백색노이즈(매 분 독립)는 분당 변화가 비현실적으로 커(±15~50) 배제.
  - AR(1)은 직전 분에서 조금씩 이동 → 실제 사람처럼 매끄럽게 요동
    (분당 변화 ~6bpm, 원본 느어아웅 연속 diff std 10.4 와 같은 계열).

⚠️ std 성질에 대한 한계 명시:
  - 노이즈 크기로 페르소나의 hr_std(국건영 연령대×성별 안정심박 std)를 쓴다.
  - 엄밀히 국건영 std 는 '개인 간(between-person) 변동'이고, 여기서 필요한 건
    '개인 내(within-person) 요동'이라 성질이 다르다.
  - 다만 (1) 두 값의 크기가 유사(60대남 국건영 13.5 ≈ 느어아웅 개인내 12),
    (2) 연령대별 차등 부여 가능, (3) 추가 데이터 불필요 —로 실용적 대리값.
  - 대표 인물(느어아웅) 실측 개인내 변동 곡선이 확보되면 이 함수가 교체 지점.
"""
import numpy as np

PHI_DEFAULT = 0.8   # 자기상관 계수 (0.8 → 분당변화 현실적, 곡선 매끄러움 유지)

# PAMAP2 활동별 심박 정박 (dist_summary_pamap2.csv).
# 정상 산행 강도는 서있기(휴식)~계단 범위. 안전범위 = 서있기 하단 ~ 계단 상단.
# 초반 안정 구간의 낮은 심박(개인차)은 정상으로 두되, 생리적 극단만 막는 경계.
PAMAP2_HR_LO = 60.0    # 서있기 min(68) 아래 여유 — 안정심박 낮은 개인 초반 허용
PAMAP2_HR_HI = 165.0   # 계단 p95(162) 근처 — 정상 강도 상한(위험은 상황축이 별도)


def _soft_clip(x, lo, hi, margin=8.0):
    """
    범위 밖 값을 완만히 압축(tanh). 안쪽은 그대로 두고, 밖으로 나간 만큼만
    부드럽게 눌러 곡선이 납작해지지 않게 한다(hard clip 의 뭉갬 방지).
    """
    y = x.copy()
    over = x > hi
    y[over] = hi + margin * np.tanh((x[over] - hi) / margin)
    under = x < lo
    y[under] = lo - margin * np.tanh((lo - x[under]) / margin)
    return y


def apply_hr_variability(minutes, hr_std, rng, phi=PHI_DEFAULT, rest_hr=58.0):
    """
    심박 곡선에 개인 변동성(강도 비례 AR(1) 요동)을 입힌다.

    minutes : dict[str, np.ndarray] — synth_session 출력(키 'hr_mean_bpm' 포함)
    hr_std  : float — 페르소나 연령대 국건영 심박 std (요동 크기)
    rng     : np.random.Generator
    rest_hr : float — 페르소나 안정심박 (강도 계산 기준. 노이즈 강도 비례용)
    반환    : minutes 사본 (hr_mean_bpm 에 변동성 적용, hr_ratio_maxhr 재계산)

    설계:
      - 강도 비례: 안정 구간(rest 근처)은 노이즈 작게(0.4배), 고강도는 크게(1.0배).
        실제로도 쉴 때보다 운동 중 심박 변동이 크다. 고정 std 는 저심박 개인을
        비현실적으로 흔들어(심박 51 등) 꼬리를 만들었으므로 강도 비례로 교체.
      - PAMAP2 안전범위 soft clip: 강도 비례로도 안 잡히는 극단(rest_hr 극단값
        페르소나 등)을 산행 활동 범위로 완만히 압축. 낮은 초반 심박(안정 구간
        개인차)은 정상으로 두되, 생리적 극단(>PA_HI, <PA_LO)만 막는다.
    """
    out = {k: (np.array(v, dtype=float) if hasattr(v, "__len__") else v)
           for k, v in minutes.items()}
    hr = np.array(out["hr_mean_bpm"], dtype=float)
    n = len(hr)
    if n < 2 or hr_std <= 0:
        return out

    # 강도 계수: 안정(rest)=0.4배 ~ 고강도(rest+60)=1.0배
    effort = np.clip((hr - rest_hr) / 60.0, 0.0, 1.0)
    scale = 0.4 + 0.6 * effort

    # AR(1) 강도 비례 노이즈
    innov_std = hr_std * np.sqrt(max(0.0, 1.0 - phi ** 2))
    dev = np.zeros(n)
    for i in range(1, n):
        dev[i] = phi * dev[i - 1] + rng.normal(0.0, innov_std * scale[i])

    hr2 = hr + dev
    # PAMAP2 안전범위 soft clip (극단만 압축, 초반 저심박 개인차는 유지)
    hr2 = _soft_clip(hr2, PAMAP2_HR_LO, PAMAP2_HR_HI)
    out["hr_mean_bpm"] = hr2

    # 파생 심박비율이 있으면 재계산 (max_hr 는 세션 메타에서 알 수 없으므로
    # 기존 ratio 스케일을 유지: 새 hr / (기존 hr / 기존 ratio))
    if "hr_ratio_maxhr" in out:
        old_ratio = np.array(minutes["hr_ratio_maxhr"], dtype=float)
        old_hr = np.array(minutes["hr_mean_bpm"], dtype=float)
        with np.errstate(divide="ignore", invalid="ignore"):
            max_hr = np.where(old_ratio > 0, old_hr / old_ratio, np.nan)
        max_hr = np.nanmedian(max_hr)
        if np.isfinite(max_hr) and max_hr > 0:
            out["hr_ratio_maxhr"] = out["hr_mean_bpm"] / max_hr

    # 개인편차(z-score)는 변동 전 원본 유지.
    # 근거: hr_z 는 '개인이 자기 안정심박 대비 얼마나 부하받았나'라는 강도 서사
    # 지표다. 이는 상황축(정상/주의/경고/위험)이 정하는 것이지, 분 단위 변동
    # 노이즈가 좌우할 값이 아니다. 변동은 심박 절대값(hr_mean_bpm)에만 반영하고,
    # 개인편차는 원래 강도 곡선 기준을 유지한다.
    # (이전에 변동 후 심박으로 z 를 재계산했더니 정상세션 hr_z 가 11까지 튀어
    #  위험세션과 겹치고 등급 구분이 무너졌다 — 이를 바로잡음.)
    # hr_z_personal 은 out 초기화 시 원본이 이미 복사돼 있으므로 별도 처리 불필요.

    return out


if __name__ == "__main__":
    rng = np.random.default_rng(1)
    # 매끄러운 앵커 심박 (테스트용)
    anchor = np.concatenate([np.full(40, 85), np.full(40, 135), np.full(36, 110)])
    minutes = {"hr_mean_bpm": anchor.astype(float)}
    for hr_std in [9.5, 12.1, 14.0]:
        out = apply_hr_variability(minutes, hr_std, np.random.default_rng(2))
        d = np.abs(np.diff(out["hr_mean_bpm"]))
        print(f"hr_std={hr_std}: 적용후 값std {out['hr_mean_bpm'].std():.1f} "
              f"분당변화 평균 {d.mean():.1f} 최대 {d.max():.1f}")
