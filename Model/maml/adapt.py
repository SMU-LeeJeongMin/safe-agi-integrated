# -*- coding: utf-8 -*-
"""
adapt.py — inner loop: 사용자별 support 30분 적응
=================================================
공통 초기점 θ에서 출발해, 해당 사용자의 세션 초반 30분(support set)에
대한 손실로 3-step 풀배치 경사하강 → 개인화된 파라미터 θ' 반환.

- 개인특성 피처가 입력에 없으므로, 이 3-step이 개인차(기준심박·체력·나이)를
  흡수하는 유일한 통로 = MAML의 검증 포인트.
- 평가(run_demo)와 메타학습(fomaml)이 같은 INNER_STEPS/INNER_LR을 쓰도록
  기본값을 여기 한 곳에 둔다.
"""
from Model.maml.distill import loss_and_grads, sgd_step

INNER_STEPS = 3
INNER_LR = 0.5


def adapt(params, X_support, Y_support, steps=INNER_STEPS, lr=INNER_LR):
    """support로 steps회 경사하강한 적응 파라미터 반환 (원본 params 불변)."""
    theta = params
    for _ in range(steps):
        _, grads, _ = loss_and_grads(theta, X_support, Y_support)
        theta = sgd_step(theta, grads, lr)
    return theta
