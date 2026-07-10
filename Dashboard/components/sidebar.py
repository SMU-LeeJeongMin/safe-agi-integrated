# 대시보드 왼쪽 사이드바 component
# 1분 단위 시점 index와 패널 위치 이동 링크를 제공한다.

import pandas as pd
import streamlit as st

from utils.time_utils import format_kst


PANEL_NAV_LINKS = [
    ("시나리오 요약 Panel", "dashboard-top"),
    ("[1] DTO-1 Input Panel", "dto1-input-panel"),
    ("[2] Feature Engineering Panel", "feature-engineering-panel"),
    ("[3] Model Explanation Panel", "model-explanation-panel"),
    ("[4] What-If Simulating Panel", "whatif-simulating-panel"),
    ("[5] MAML 개인화 Panel", "maml-personalization-panel"),
    ("[6] DTO-5 Output Panel", "dto5-output-panel"),
    ("[7] InferenceResult 저장 Panel", "inferenceresult-save-panel"),
]


def _render_panel_nav_links() -> str:
    links = "".join(
        f'<a href="#{anchor}" target="_self">{label}</a>'
        for label, anchor in PANEL_NAV_LINKS
    )
    return f'<div class="sidebar-nav">{links}</div>'


def render_sidebar(features: pd.DataFrame, dto5_sequence: list[dict]) -> int:
    st.sidebar.markdown(
        """
        <div class="sidebar-section-heading">시점 선택</div>
        <div class="sidebar-section-caption">분 단위 시점 index</div>
        """,
        unsafe_allow_html=True,
    )

    max_idx = min(len(features), len(dto5_sequence)) - 1

    selected_idx = st.sidebar.slider(
        "분 단위 시점 index",
        min_value=0,
        max_value=max_idx,
        value=max_idx,
        label_visibility="collapsed",
    )

    selected_ts = features.iloc[selected_idx].get("ts")
    st.sidebar.markdown(
        f"""
        <div class="sidebar-time-box">
            <div class="sidebar-time-label">선택 시점</div>
            <div class="sidebar-time-value">{format_kst(selected_ts)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.divider()
    st.sidebar.markdown(
        """
        <div class="sidebar-section-heading">Panel Navigation</div>
        <div class="sidebar-section-caption">패널 바로가기</div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(_render_panel_nav_links(), unsafe_allow_html=True)

    return selected_idx
