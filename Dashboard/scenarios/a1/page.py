# A1 시나리오

from __future__ import annotations

import streamlit as st

from components.sidebar import render_sidebar
from core.contracts import ScenarioDefinition, ScenarioPayload
from scenarios.a1.mapper import build_context
from scenarios.a1.dto1_input_panel import render_dto1_input_panel
from scenarios.a1.dto5_panel import render_dto5_panel
from scenarios.a1.feature_engineering_panel import render_feature_engineering_panel
from scenarios.a1.inferenceresult_panel import render_inferenceresult_panel
from scenarios.a1.model_explanation_panel import render_model_explanation_panel
from scenarios.a1.personalization_panel import render_personalization_panel
from scenarios.a1.title_panel import render_title_panel
from scenarios.a1.whatif_panel import render_whatif_panel
from scenarios.common import render_anchor, render_back_buttons, render_payload_messages, render_source_waiting_card


def render(payload: ScenarioPayload, definition: ScenarioDefinition) -> None:
    del definition

    selected_idx = render_sidebar(payload.features, payload.dto5_sequence, scenario_code="A1")
    row = payload.row_at(selected_idx)
    dto5 = payload.dto5_at(selected_idx)
    context = build_context(row, dto5)

    render_back_buttons()
    render_payload_messages(payload)

    render_anchor("dashboard-top")
    render_title_panel(context)
    if not payload.connected:
        st.markdown('<div style="height:22px;"></div>', unsafe_allow_html=True)
        render_source_waiting_card(payload, "A1")

    render_anchor("dto1-input-panel")
    st.divider()
    render_dto1_input_panel(context)

    render_anchor("feature-engineering-panel")
    st.divider()
    render_feature_engineering_panel(context, payload)

    render_anchor("model-explanation-panel")
    st.divider()
    render_model_explanation_panel(context)

    render_anchor("whatif-simulating-panel")
    st.divider()
    render_whatif_panel(context)

    render_anchor("maml-personalization-panel")
    st.divider()
    render_personalization_panel(context)

    render_anchor("dto5-output-panel")
    st.divider()
    render_dto5_panel(context)

    render_anchor("inferenceresult-save-panel")
    st.divider()
    render_inferenceresult_panel(context)
