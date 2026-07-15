# -*- coding: utf-8 -*-
"""
run_demo.py — F1 MAML 프로토타입 전체 파이프라인 (7/15 미팅 시연)
=================================================================
1) 메타학습용 랜덤 페르소나 30명 + 시연용 스윕 페르소나 10명 태스크 생성
2) 룰(compute_e1_e2) 지식증류로 MLP 사전학습 (개인특성 피처 은닉)
3) FOMAML로 공통 초기점 θ 메타학습
4) 시연 사용자 10명 각각:
   [적응 전] 공통 θ 그대로 query 평가
   [적응 후] support 30분 3-step 적응 → query 평가
   → e1/e2 MAE + 위험 판정 일치율 비교표 콘솔 출력, results.json 저장

실행:  python Model/maml/run_demo.py   (또는 python -m Model.maml.run_demo)
"""
import json
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import numpy as np

from Model.dto5 import risk_level                       # 판정 일치율용 (룰 재사용)
from Model.maml.tasks import (demo_personas, load_base_session, make_tasks,
                              train_personas)
from Model.maml.distill import forward, pretrain
from Model.maml.adapt import adapt, INNER_STEPS, INNER_LR
from Model.maml.fomaml import meta_train

RESULTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results.json")


def _risk_labels(Y):
    """(n,2) e1,e2 → 위험 판정 라벨 배열. representative = max(e1,e2) 규칙 유지."""
    return np.array([risk_level(max(e1, e2))[1] for e1, e2 in Y])


def evaluate(params, task):
    """query에 대한 (MAE, 판정일치율) — 교사 룰 라벨 대비."""
    pred = forward(params, task.X_query)
    mae = float(np.mean(np.abs(pred - task.Y_query)))
    agree = float(np.mean(_risk_labels(pred) == _risk_labels(task.Y_query)))
    return mae, agree, pred


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    print("=" * 78)
    print("F1 MAML 프로토타입 — 적응 전/후 시연 (교사: 룰 compute_e1_e2, 개인특성 은닉)")
    print("=" * 78)

    base = load_base_session()

    # 1) 태스크 생성 (메타학습 30명 / 시연 10명, seed 분리)
    print("\n[1/4] 태스크 생성: 메타학습 페르소나 30명 + 시연 스윕 10명 (각 116분 세션)")
    meta_tasks = make_tasks(train_personas(30, seed=7), base=base, seed0=5000)
    demo_tasks = make_tasks(demo_personas(), base=base, seed0=1000)

    # 2) 지식증류 사전학습 → 정규화 통계는 메타학습 풀에서만 fit
    print("[2/4] 지식증류 사전학습: MLP(7→32→16→2), 교사=룰 e1/e2")
    theta0, norm = pretrain(meta_tasks, epochs=400, verbose=True)

    for t in meta_tasks + demo_tasks:       # 이후 단계는 정규화 입력 사용
        t.X_support = norm.transform(t.X_support)
        t.X_query = norm.transform(t.X_query)

    # 3) FOMAML outer loop
    print(f"[3/4] FOMAML 메타학습: inner {INNER_STEPS}-step (lr={INNER_LR}), outer Adam")
    theta = meta_train(theta0, meta_tasks, meta_iters=300, meta_batch=5, verbose=True)

    # 4) 시연 사용자 10명 평가
    print("[4/4] 시연 사용자 10명: 적응 전(공통 θ) vs 적응 후(support 30분 3-step)\n")
    header = (f"{'사용자':<8}{'나이':>4}{'기준HR':>7}{'체력':>6} | "
              f"{'MAE 전':>7}{'MAE 후':>8}{'개선':>7} | "
              f"{'일치율 전':>8}{'일치율 후':>9}")
    print(header)
    print("-" * len(header.encode("euc-kr", errors="replace")))

    results = []
    for t in demo_tasks:
        mae_b, agr_b, _ = evaluate(theta, t)
        theta_i = adapt(theta, t.X_support, t.Y_support)
        mae_a, agr_a, _ = evaluate(theta_i, t)
        p = t.persona
        print(f"{p.name:<8}{p.age:>4}{p.rest_hr:>7.0f}{p.fitness:>6.2f} | "
              f"{mae_b:>7.4f}{mae_a:>8.4f}{(mae_b - mae_a) / mae_b:>6.0%} | "
              f"{agr_b:>8.1%}{agr_a:>9.1%}")
        results.append({
            "user": p.name,
            "persona": {"age": p.age, "rest_hr": p.rest_hr,
                        "hr_std": p.hr_std, "fitness": p.fitness},
            "before": {"query_mae": round(mae_b, 4), "risk_label_agreement": round(agr_b, 4)},
            "after": {"query_mae": round(mae_a, 4), "risk_label_agreement": round(agr_a, 4)},
        })

    mb = float(np.mean([r["before"]["query_mae"] for r in results]))
    ma = float(np.mean([r["after"]["query_mae"] for r in results]))
    ab = float(np.mean([r["before"]["risk_label_agreement"] for r in results]))
    aa = float(np.mean([r["after"]["risk_label_agreement"] for r in results]))
    print("-" * 70)
    print(f"{'평균':<8}{'':>17} | {mb:>7.4f}{ma:>8.4f}{(mb - ma) / mb:>6.0%} | "
          f"{ab:>8.1%}{aa:>9.1%}")

    summary = {
        "setting": {
            "student_inputs": "개인특성(나이·MaxHR·기준심박·hr_z) 은닉, 관측 7피처",
            "teacher": "Model.f1_model.compute_e1_e2 (오라클: 진짜 개인특성 사용)",
            "support": "세션 초반 30분", "query": "나머지 86분",
            "inner": {"steps": INNER_STEPS, "lr": INNER_LR},
            "meta": {"iters": 300, "batch": 5, "train_personas": 30},
        },
        "mean": {
            "before": {"query_mae": round(mb, 4), "risk_label_agreement": round(ab, 4)},
            "after": {"query_mae": round(ma, 4), "risk_label_agreement": round(aa, 4)},
            "mae_improvement_pct": round((mb - ma) / mb * 100, 1),
        },
        "users": results,
    }
    with open(RESULTS_PATH, "w", encoding="utf-8") as fp:
        json.dump(summary, fp, ensure_ascii=False, indent=2)
    print(f"\nresults.json 저장 완료 → {RESULTS_PATH}")


if __name__ == "__main__":
    main()
