# [3] Model Explanation Panel — A1 점수와 판단 근거 (골격 호출)

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st
from scenarios.common import render_panel_placeholder

from components.layout import render_risk_gauge
from components.panel_kit import (
    render_panel_banner,
    render_subsection,
    render_soft_notice,
    metric_card,
    model_detail_button_label,
    render_contribution_card,
    render_contribution_section_header,
    render_offline_weight_explanation,
    step_card,
)
from scenarios.a1.mapper import A1Context, row_value, to_float
from scenarios.a1.formatting import _fmt, _fmt_bool, _text


def _model_metric_card(label: str, value: Any, description: str) -> str:
    display = _fmt(value, 4) if to_float(value) is not None else "-"
    return metric_card(label, display, description)


def _step_card(title: str, summary: str, value: Any, rows: list[tuple[str, Any]]) -> str:
    value_text = _fmt(value, 4) if to_float(value) is not None else _text(value)
    return step_card(title, summary, value_text, rows)


def render_model_explanation_panel(context: A1Context) -> None:
    row = context.row
    render_panel_banner(3, "Model Explanation Panel", "외부 A1 Model이 반환한 공간 점수, 보정 점수, 대표값과 최종 판단 근거를 보여주는 panel")
    # F1 디자인 이식 방향이 확정될 때까지 골격 시나리오와 동일한 자리표시로 둔다.
    # 기존 구현은 아래에 보존되어 있으며, 이 두 줄을 제거하면 복원된다.
    render_panel_placeholder("A1")
    return


    cols = st.columns(3)
    metrics = [
        ("A1 Spatial Score", context.spatial_score, "거리 및 이탈 및 경사 등 공간 및 지형 기반 점수"),
        ("A1 Adjusted Score", context.adjusted_score, "생체 및 환경 보정이 포함된 경우의 점수"),
        ("representative", context.representative, "A1 최종 판단에 사용된 대표 점수"),
    ]
    for column, metric in zip(cols, metrics):
        with column:
            st.markdown(_model_metric_card(*metric), unsafe_allow_html=True)

    st.markdown('<div class="model-section-gap"></div>', unsafe_allow_html=True)
    render_subsection("대표 점수 위치와 판단 근거")
    if context.representative is not None:
        render_risk_gauge(context.representative)
        st.caption("게이지 구간은 현재 F1 공통 UI를 그대로 사용하며, A1 임계값 규격 확정 시 표시 문구만 교체합니다.")
    else:
        st.caption("외부 A1 Model 산출물이 연결되면 대표 점수 위치가 게이지로 표시됩니다.")
    st.markdown('<div class="whatif-info-gap"></div>', unsafe_allow_html=True)
    render_soft_notice(context.reason_text)

    st.markdown('<div class="model-section-gap"></div>', unsafe_allow_html=True)
    run_key = f"a1_model_detail_{_text(row_value(row, 'ts', 'timestamp'), 'waiting')}"
    if st.button(model_detail_button_label("A1"), type="primary"):
        st.session_state[run_key] = True

    if st.session_state.get(run_key):
        contribution_text = " / ".join(
            f"{item.get('feature')}: {_text(item.get('contribution'))}" for item in context.contributions[:4]
        ) or "explanation.contributions 연결 대기"
        rule_text = " / ".join(_text(item.get("rule", item.get("name"))) for item in context.rules[:4]) or "applied_rules 연결 대기"
        columns = st.columns(4)
        step_values = [
            (
                "Step 1. 공간 입력",
                "위험 POI 거리와 지정로 이탈 정보를 Input 산출물에서 확인합니다.",
                _fmt(row_value(row, "dist_to_hazard_m"), 1, " m"),
                [("위험 지점 거리", _fmt(row_value(row, "dist_to_hazard_m"), 1, " m")), ("지정로 이탈", _fmt(row_value(row, "off_trail_dist_m"), 1, " m"))],
            ),
            (
                "Step 2. 지형 및 접근",
                "경사도와 접근 여부는 Input 파이프라인에서 계산된 값을 그대로 표시합니다.",
                _fmt(row_value(row, "slope_deg"), 1, "°"),
                [("접근 여부", _fmt_bool(row_value(row, "approaching_flag"), "접근 중", "멀어지는 중")), ("기여도", contribution_text)],
            ),
            (
                "Step 3. representative",
                "Model이 반환한 최종 대표값을 사용합니다.",
                context.representative,
                [("A1 Spatial", _fmt(context.spatial_score, 4)), ("A1 Adjusted", _fmt(context.adjusted_score, 4))],
            ),
            (
                "Step 4. alerts[]",
                "DTO-5 A1 Alert의 level, location, detour_available을 확인합니다.",
                _text(context.alert_level),
                [("적용 규칙", rule_text), ("현재 Alert", _text(context.alert.get("title"), "알림 없음"))],
            ),
        ]
        for column, step in zip(columns, step_values):
            with column:
                st.markdown(_step_card(*step), unsafe_allow_html=True)

        st.markdown('<div class="model-after-steps-gap"></div>', unsafe_allow_html=True)
        render_contribution_section_header()
        render_contribution_card(
            "A1 기여도 분해",
            "A1 위험 점수를 구성하는 항목별 몫을 보여주는 자리입니다.",
            [],
            waiting_text=(
                "A1 가중치 공식(거리, 이탈, 경사, 접근 여부 등)이 확정되면 "
                "각 항목의 기여도 막대가 이 자리에 표시됩니다."
            ),
        )
        st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)
        render_offline_weight_explanation(None, scenario_id="A1")
    else:
        render_soft_notice("버튼을 누르면 외부 Feature 및 Model 및 DTO-5 필드가 연결되는 계산 흐름과 기여도 분해, 학습 가중치 근거를 확인할 수 있습니다.")

    st.markdown('<div class="model-after-steps-gap"></div>', unsafe_allow_html=True)
    render_subsection("적용된 판정 규칙")
    if context.rules:
        st.dataframe(pd.DataFrame(context.rules), use_container_width=True, hide_index=True)
    else:
        st.caption("Model 결과에 rules 또는 applied_rules가 아직 없습니다.")
