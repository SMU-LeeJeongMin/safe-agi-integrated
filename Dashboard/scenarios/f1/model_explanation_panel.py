# [3] Model Explanation Panel
# 모델이 해당 시점에서 특정 위험 등급과 피로 상태를 판단한 이유를 설명

from __future__ import annotations

import html
from typing import Any

import pandas as pd
import streamlit as st

from components.layout import render_risk_gauge
from components.panel_kit import (
    formula_line,
    model_detail_button_label,
    metric_card,
    render_contribution_card,
    render_contribution_section_header,
    render_offline_weight_explanation,
    step_card,
)
from Model.f1_model import (
    ACCU_REF_MIN,
    HEAT_BASE,
    HEAT_RANGE,
    K_PERSONAL_STD,
    SPEED_BASELINE,
    SPO2_FLOOR_RANGE,
    SPO2_REF,
    STEP_BASELINE,
    W,
)
from utils.explanation import (
    HR_OVERLOAD_RATIO,
    RISK_CAUTION,
    RISK_DANGER,
    RISK_WARNING,
    to_bool,
    to_float,
)


def _clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(x)))


def _safe(value: object) -> str:
    return html.escape("" if value is None else str(value))


def _risk_zone_text(rep: float) -> str:
    if rep < RISK_CAUTION:
        return f"현재 대표 위험도 {rep:.4f}는 정상 구간입니다."
    if rep < RISK_WARNING:
        return f"현재 대표 위험도 {rep:.4f}는 주의 구간입니다."
    if rep < RISK_DANGER:
        return f"현재 대표 위험도 {rep:.4f}는 경고 구간입니다."
    return f"현재 대표 위험도 {rep:.4f}는 위험 구간입니다."


def _risk_zone_class(rep: float) -> str:
    if rep < RISK_CAUTION:
        return "risk-zone-normal"
    if rep < RISK_WARNING:
        return "risk-zone-caution"
    if rep < RISK_DANGER:
        return "risk-zone-warning"
    return "risk-zone-danger"


def _score_components(row: pd.Series) -> dict[str, float]:
    """model/f1_model.py와 같은 정규화 흐름을 화면 설명용으로 계산한다."""
    hr_ratio = _clip(to_float(row.get("hr_ratio_maxhr")))
    spo2 = to_float(row.get("spo2_min_pct"))
    spo2_drop = _clip((SPO2_REF - spo2) / SPO2_FLOOR_RANGE) if spo2 else 0.0
    hr_z_norm = _clip(to_float(row.get("hr_z_personal")) / K_PERSONAL_STD)

    step_drop = _clip((STEP_BASELINE - to_float(row.get("steps_1min"))) / STEP_BASELINE)
    speed_drop = _clip((SPEED_BASELINE - to_float(row.get("speed_mean_mpm"))) / SPEED_BASELINE)
    move = _clip(0.5 * step_drop + 0.5 * speed_drop)

    accu = _clip(to_float(row.get("cumulative_min")) / ACCU_REF_MIN)
    heat_index = to_float(row.get("heat_index"))
    heat = _clip((heat_index - HEAT_BASE) / HEAT_RANGE) if heat_index else 0.0
    accident_prior = _clip(to_float(row.get("accident_prior")))
    env = _clip(0.6 * heat + 0.4 * accident_prior)

    e1_calc = _clip(0.5 * hr_ratio + 0.3 * spo2_drop + 0.2 * hr_z_norm)
    e2_calc = _clip(W["bio"] * e1_calc + W["move"] * move + W["accu"] * accu + W["env"] * env)

    return {
        "hr_ratio": hr_ratio,
        "spo2_drop": spo2_drop,
        "hr_z_norm": hr_z_norm,
        "step_drop": step_drop,
        "speed_drop": speed_drop,
        "move": move,
        "accu": accu,
        "heat": heat,
        "accident_prior": accident_prior,
        "env": env,
        "e1_calc": e1_calc,
        "e2_calc": e2_calc,
    }


def _render_step_card(title: str, summary: str, value: object, formulas: list[tuple[str, str]]) -> None:
    st.markdown(step_card(title, summary, value, formulas), unsafe_allow_html=True)



def _fatigue_rule_text(row: pd.Series, fatigue_state: str) -> str:
    overload = to_bool(row.get("hr_overload_5min"))
    spo2_grade = str(row.get("spo2_grade"))
    rest_due = to_bool(row.get("rest_due_90min"))
    return (
        f"과부하 5분 지속 = {overload}\n"
        f"SpO2 등급 = {spo2_grade}\n"
        f"90분 휴식 주기 = {rest_due}"
    )


def render_model_explanation_panel(
    row: pd.Series,
    dto5: dict,
    reason_text: str,
    explanation: dict[str, Any] | None = None,
) -> None:
    st.header("[3] Model Explanation Panel")
    st.markdown(
        '<div class="panel-description">변환된 feature를 기반으로 위험도와 피로 상태가 어떻게 계산되는지 보여주는 panel</div>',
        unsafe_allow_html=True,
    )

    risk = dto5.get("risk", {})
    fatigue = dto5.get("fatigue", {})
    e1 = to_float(risk.get("e1_biometric"))
    e2 = to_float(risk.get("e2_combined"))
    rep = to_float(risk.get("representative"))
    fatigue_state = fatigue.get("state", "-")
    comp = _score_components(row)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            metric_card("e1_biometric", f"{e1:.4f}", "생체 신호만 반영한 위험 점수"),
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            metric_card("e2_combined", f"{e2:.4f}", "생체, 이동량, 누적 시간, 환경을 반영한 종합 점수"),
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            metric_card("representative", f"{rep:.4f}", "e1과 e2 중 더 큰 값을 대표 위험도로 사용"),
            unsafe_allow_html=True,
        )

    st.markdown('<div class="model-section-gap"></div>', unsafe_allow_html=True)
    st.markdown("#### Risk_label 등급과 판단 근거")
    render_risk_gauge(rep)
    st.markdown(
        (
            f'<div class="safe-card risk-zone-card {_risk_zone_class(rep)}">'
            f'<b>{_safe(_risk_zone_text(rep))}</b><br/>'
            '<span class="safe-muted">위험 등급은 전체 위험 수준이고, 피로 상태는 F1 시나리오에서 사용자에게 안내할 행동 판단입니다.</span>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )
    st.markdown('<div class="whatif-info-gap"></div>', unsafe_allow_html=True)
    st.info(reason_text)

    st.markdown('<div class="model-section-gap"></div>', unsafe_allow_html=True)
    run_key = f"model_run_visible_{row.get('ts')}"
    if st.button(model_detail_button_label("F1"), type="primary"):
        st.session_state[run_key] = True

    if st.session_state.get(run_key):
        st.markdown("#### 모델 계산 단계")
        s1, s2, s3, s4 = st.columns(4)
        with s1:
            _render_step_card(
                "Step 1. e1_biometric",
                "심박 부담도, SpO2 저하, 개인 기준 편차를 사용합니다.",
                f"{e1:.4f}",
                [
                    ("공식", "0.5×심박 부담도 + 0.3×SpO2 저하 + 0.2×개인 편차"),
                    (
                        "대입",
                        f"0.5×{comp['hr_ratio']:.3f} + 0.3×{comp['spo2_drop']:.3f} + 0.2×{comp['hr_z_norm']:.3f} = {e1:.4f}",
                    ),
                ],
            )
        with s2:
            _render_step_card(
                "Step 2. e2_combined",
                "생체 점수에 이동량, 누적 산행 시간, 환경 보정을 추가합니다.",
                f"{e2:.4f}",
                [
                    ("공식", "0.55×e1 + 0.20×이동 저하 + 0.15×누적 + 0.10×환경"),
                    (
                        "대입",
                        f"0.55×{e1:.4f} + 0.20×{comp['move']:.3f} + 0.15×{comp['accu']:.3f} + 0.10×{comp['env']:.3f} = {e2:.4f}",
                    ),
                ],
            )
        with s3:
            _render_step_card(
                "Step 3. representative",
                "두 위험 점수 중 더 큰 값을 최종 대표 위험도로 선택합니다.",
                f"{rep:.4f}",
                [
                    ("공식", "max(e1_biometric, e2_combined)"),
                    ("대입", f"max({e1:.4f}, {e2:.4f}) = {rep:.4f}"),
                ],
            )
        with s4:
            _render_step_card(
                "Step 4. fatigue.state",
                "심박 과부하, SpO2 등급, 휴식 주기를 함께 확인합니다.",
                fatigue_state,
                [
                    ("규칙", "과부하 지속, SpO2 경고, 90분 도래 여부를 확인"),
                    ("현재", _fatigue_rule_text(row, str(fatigue_state))),
                ],
            )
        st.markdown('<div class="model-after-steps-gap"></div>', unsafe_allow_html=True)
        render_contribution_section_header()

        e1_items = [
            ("심박 부담도", 0.5, comp["hr_ratio"], "green"),
            ("SpO2 저하", 0.3, comp["spo2_drop"], ""),
            ("개인 기준 편차", 0.2, comp["hr_z_norm"], "amber"),
        ]
        e2_items = [
            ("생체 (e1)", W["bio"], comp["e1_calc"], "green"),
            ("이동량 저하", W["move"], comp["move"], ""),
            ("누적 산행 시간", W["accu"], comp["accu"], "amber"),
            ("환경 (더위 및 사고 이력)", W["env"], comp["env"], "gray"),
        ]
        left, right = st.columns(2)
        with left:
            render_contribution_card(
                f"e1_biometric 기여도 분해 ({e1:.4f})",
                "생체 신호만 반영한 점수입니다. 심박 부담, SpO2 저하, 개인 기준 편차 세 항목으로 구성됩니다.",
                e1_items,
                bottom_label="가중치 출처",
                bottom_text="정의서 F1 확정 공식 (0.5, 0.3, 0.2)",
            )
        with right:
            render_contribution_card(
                f"e2_combined 기여도 분해 ({e2:.4f})",
                "생체 점수(e1)에 이동량, 누적 산행 시간, 환경 조건을 더한 종합 점수입니다.",
                e2_items,
                bottom_label="가중치 출처",
                bottom_text="회의 확정 가중치 (0.55, 0.20, 0.15, 0.10)",
            )

        st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)
        render_offline_weight_explanation(explanation, scenario_id="F1")
    else:
        st.info("버튼을 누르면 e1, e2, representative, fatigue.state 계산 단계와 항목별 기여도 분해, 학습 가중치 근거를 확인할 수 있습니다.")

