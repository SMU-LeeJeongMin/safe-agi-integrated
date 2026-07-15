# -*- coding: utf-8 -*-
"""
distill.py — numpy MLP 회귀 모델 + 룰 지식증류 사전학습
========================================================
구조: 입력7 → 32(ReLU) → 16(ReLU) → 2(Sigmoid, e1·e2 ∈ 0~1)
- 순전파/역전파를 numpy로 직접 구현 (외부 딥러닝 프레임워크 없음).
- 교사 신호: 룰 엔진 compute_e1_e2 출력 (tasks.py에서 라벨로 생성됨).
- 입력에는 나이·개인 기준심박 등 개인특성 피처가 없음 → 사전학습 모델은
  "평균적인 사용자"의 매핑만 알고, 개인차는 MAML 적응이 흡수해야 함.

파라미터는 dict[str, np.ndarray]로 들고 다니는 함수형 설계
→ adapt.py(inner loop)/fomaml.py(outer loop)가 임의 지점에서
  loss_and_grads 를 호출할 수 있음.
"""
import numpy as np

SIZES = (7, 32, 16, 2)


# ── 파라미터 ──────────────────────────────────────────────
def init_params(seed=0, sizes=SIZES):
    """He 초기화된 파라미터 dict 생성."""
    rng = np.random.default_rng(seed)
    p = {}
    for i in range(len(sizes) - 1):
        fan_in = sizes[i]
        p[f"W{i}"] = rng.normal(0.0, np.sqrt(2.0 / fan_in), (fan_in, sizes[i + 1]))
        p[f"b{i}"] = np.zeros(sizes[i + 1])
    return p


def clone_params(params):
    return {k: v.copy() for k, v in params.items()}


# ── 순전파 / 역전파 ───────────────────────────────────────
def _sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))


def forward(params, X):
    """X:(n,7) → 예측 (n,2). e1,e2는 sigmoid로 0~1 보장."""
    h1 = np.maximum(0.0, X @ params["W0"] + params["b0"])
    h2 = np.maximum(0.0, h1 @ params["W1"] + params["b1"])
    return _sigmoid(h2 @ params["W2"] + params["b2"])


def loss_and_grads(params, X, Y):
    """MSE 손실과 전 파라미터의 gradient dict 반환 (수동 역전파)."""
    n = X.shape[0]
    # forward (중간값 보존)
    z1 = X @ params["W0"] + params["b0"]
    h1 = np.maximum(0.0, z1)
    z2 = h1 @ params["W1"] + params["b1"]
    h2 = np.maximum(0.0, z2)
    out = _sigmoid(h2 @ params["W2"] + params["b2"])

    diff = out - Y
    loss = float(np.mean(diff ** 2))

    # backward: dL/dout = 2·diff / (n·2출력)
    d_out = 2.0 * diff / diff.size
    d_z3 = d_out * out * (1.0 - out)             # sigmoid'
    g = {
        "W2": h2.T @ d_z3, "b2": d_z3.sum(axis=0),
    }
    d_h2 = d_z3 @ params["W2"].T
    d_z2 = d_h2 * (z2 > 0)                        # ReLU'
    g["W1"] = h1.T @ d_z2
    g["b1"] = d_z2.sum(axis=0)
    d_h1 = d_z2 @ params["W1"].T
    d_z1 = d_h1 * (z1 > 0)
    g["W0"] = X.T @ d_z1
    g["b0"] = d_z1.sum(axis=0)
    return loss, g, out


def sgd_step(params, grads, lr):
    """params - lr·grads 를 새 dict로 반환 (원본 불변)."""
    return {k: params[k] - lr * grads[k] for k in params}


# ── 입력 정규화 ────────────────────────────────────────────
class Normalizer:
    """학습 풀 기준 표준화. 통계는 사전학습 데이터에서만 fit."""

    def fit(self, X):
        self.mean = X.mean(axis=0)
        self.std = X.std(axis=0) + 1e-8
        return self

    def transform(self, X):
        return (X - self.mean) / self.std

    def to_dict(self):
        return {"mean": self.mean.tolist(), "std": self.std.tolist()}


# ── Adam (사전학습·outer loop 공용) ────────────────────────
class Adam:
    def __init__(self, params, lr=3e-3, b1=0.9, b2=0.999, eps=1e-8):
        self.lr, self.b1, self.b2, self.eps = lr, b1, b2, eps
        self.m = {k: np.zeros_like(v) for k, v in params.items()}
        self.v = {k: np.zeros_like(v) for k, v in params.items()}
        self.t = 0

    def step(self, params, grads):
        self.t += 1
        new = {}
        for k in params:
            self.m[k] = self.b1 * self.m[k] + (1 - self.b1) * grads[k]
            self.v[k] = self.b2 * self.v[k] + (1 - self.b2) * grads[k] ** 2
            m_hat = self.m[k] / (1 - self.b1 ** self.t)
            v_hat = self.v[k] / (1 - self.b2 ** self.t)
            new[k] = params[k] - self.lr * m_hat / (np.sqrt(v_hat) + self.eps)
        return new


# ── 지식증류 사전학습 ─────────────────────────────────────
def pretrain(tasks, epochs=400, lr=3e-3, seed=0, verbose=False):
    """
    학습 태스크 전체(support+query)를 풀링해 룰 출력(e1,e2)을 회귀.
    반환: (사전학습 params, Normalizer)
    """
    X = np.concatenate([np.vstack([t.X_support, t.X_query]) for t in tasks])
    Y = np.concatenate([np.vstack([t.Y_support, t.Y_query]) for t in tasks])
    norm = Normalizer().fit(X)
    Xn = norm.transform(X)

    params = init_params(seed)
    opt = Adam(params, lr=lr)
    for ep in range(epochs):
        loss, g, _ = loss_and_grads(params, Xn, Y)
        params = opt.step(params, g)
        if verbose and (ep % 100 == 0 or ep == epochs - 1):
            print(f"  [distill] epoch {ep:4d}  MSE={loss:.5f}")
    return params, norm


if __name__ == "__main__":
    from Model.maml.tasks import make_tasks, train_personas
    tasks = make_tasks(train_personas(10))
    params, norm = pretrain(tasks, epochs=300, verbose=True)
    t = tasks[0]
    pred = forward(params, norm.transform(t.X_query))
    print("query MAE:", float(np.mean(np.abs(pred - t.Y_query))))
