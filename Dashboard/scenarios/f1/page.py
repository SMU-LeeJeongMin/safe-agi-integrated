# F1 시나리오

from __future__ import annotations

import streamlit as st

from core.contracts import ScenarioDefinition, ScenarioPayload
from scenarios.common import (
    render_anchor,
    render_back_buttons,
    render_payload_messages,
    render_source_waiting_card,
    render_trainset_picker,
)

# F1이 선택된 뒤에만 import된다.
from components.sidebar import render_sidebar
from scenarios.f1.title_panel import render_title_panel
from scenarios.f1.dto1_input_panel import render_dto1_input_panel
from scenarios.f1.feature_engineering_panel import render_feature_engineering_panel
from scenarios.f1.model_explanation_panel import render_model_explanation_panel
from scenarios.f1.whatif_panel import render_whatif_panel
from scenarios.f1.personalization_panel import render_personalization_panel
from scenarios.f1.dto5_panel import render_dto5_panel
from scenarios.f1.inferenceresult_panel import render_inferenceresult_panel
from utils.explanation import make_reason_text


def render(payload: ScenarioPayload, definition: ScenarioDefinition) -> None:
    del definition

    # 학습셋(Input/F1/synth)이 있으면 사이드바에서 관찰 대상(사용자, 상황)을
    # 선택하게 하고, 선택된 세션으로 payload를 교체한다.
    payload = render_trainset_picker(payload, "F1")

    selected_idx = render_sidebar(
        payload.features,
        payload.dto5_sequence,
        scenario_code="F1",
    )

    render_back_buttons()
    render_payload_messages(payload)

    if payload.item_count <= 0:
        render_anchor("dashboard-top")
        render_title_panel(row=None, dto5=None, report=payload.report)
        render_source_waiting_card(payload, "F1")
        return

    row = payload.row_at(selected_idx)
    dto5 = payload.dto5_at(selected_idx)
    reason_text = make_reason_text(row, dto5)

    render_anchor("dashboard-top")
    render_title_panel(row=row, dto5=dto5, report=payload.report)
    st.markdown('<div style="height:44px;"></div>', unsafe_allow_html=True)

    render_anchor("dto1-input-panel")
    render_dto1_input_panel(row, payload.features, payload.dto5_sequence)

    render_anchor("feature-engineering-panel")
    st.markdown('<div style="height:38px;"></div>', unsafe_allow_html=True)
    render_feature_engineering_panel(row, payload.features, payload.dto5_sequence)

    render_anchor("model-explanation-panel")
    st.markdown('<div style="height:38px;"></div>', unsafe_allow_html=True)
    render_model_explanation_panel(row, dto5, reason_text, explanation=payload.explanation)

    render_anchor("whatif-simulating-panel")
    st.markdown('<div style="height:38px;"></div>', unsafe_allow_html=True)
    render_whatif_panel(row, dto5)

    render_anchor("maml-personalization-panel")
    st.markdown('<div style="height:38px;"></div>', unsafe_allow_html=True)
    render_personalization_panel(row, dto5)

    render_anchor("dto5-output-panel")
    st.markdown('<div style="height:38px;"></div>', unsafe_allow_html=True)
    render_dto5_panel(row, dto5, reason_text)

    render_anchor("inferenceresult-save-panel")
    st.markdown('<div style="height:38px;"></div>', unsafe_allow_html=True)
    render_inferenceresult_panel(row, dto5, reason_text)