# -*- coding: utf-8 -*-
"""
fomaml.py — outer loop: FOMAML(1차 근사) 메타학습
==================================================
각 메타 반복:
  1) 학습 태스크 배치 샘플
  2) 태스크별 inner loop 적응 (adapt.py, support 30분 × 3-step)
  3) 적응된 θ'ᵢ에서 query 손실의 gradient 계산
  4) FOMAML 근사: ∇θ ≈ 평균 ∇θ'ᵢ L_query  (2차 미분 생략)
  5) Adam으로 공통 초기점 θ 갱신

→ "3-step 적응했을 때 query가 가장 잘 맞는" 초기점을 학습.
"""
import numpy as np

from Model.maml.adapt import adapt, INNER_STEPS, INNER_LR
from Model.maml.distill import Adam, loss_and_grads


def meta_train(params, tasks, meta_iters=300, meta_batch=5,
               inner_steps=INNER_STEPS, inner_lr=INNER_LR,
               meta_lr=1e-3, seed=0, verbose=False):
    """
    FOMAML 메타학습. params(사전학습 θ)에서 시작해 갱신된 θ 반환.
    tasks의 X는 미리 정규화되어 있어야 함 (run_demo에서 처리).
    """
    rng = np.random.default_rng(seed)
    opt = Adam(params, lr=meta_lr)

    for it in range(meta_iters):
        idx = rng.choice(len(tasks), size=min(meta_batch, len(tasks)), replace=False)
        meta_grads = None
        q_losses = []
        for i in idx:
            t = tasks[i]
            theta_i = adapt(params, t.X_support, t.Y_support,
                            steps=inner_steps, lr=inner_lr)
            q_loss, g, _ = loss_and_grads(theta_i, t.X_query, t.Y_query)
            q_losses.append(q_loss)
            if meta_grads is None:
                meta_grads = {k: v.copy() for k, v in g.items()}
            else:
                for k in meta_grads:
                    meta_grads[k] += g[k]
        for k in meta_grads:
            meta_grads[k] /= len(idx)
        params = opt.step(params, meta_grads)

        if verbose and (it % 50 == 0 or it == meta_iters - 1):
            print(f"  [fomaml] iter {it:4d}  query MSE(적응 후)={np.mean(q_losses):.5f}")
    return params
