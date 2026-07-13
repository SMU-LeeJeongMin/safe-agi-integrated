# 뒤로가기, 연결 대기 카드 등 페이지 공통 조각

from __future__ import annotations

import html

import streamlit as st

from core.contracts import ScenarioPayload


def render_back_buttons() -> None:
    """기존 Dashboard 상단 이동 버튼을 그대로 유지한 컴포넌트."""
    st.markdown(
        """
        <div style="display:flex; gap:10px; align-items:center; margin:0 0 24px 0;">
            <a href="?page=intro" target="_self"
               style="display:inline-flex; align-items:center; justify-content:center;
                      min-width:92px; padding:8px 15px; border:1px solid #d0d5dd;
                      border-radius:8px; color:#1f2937; text-decoration:none;
                      background:#ffffff; font-weight:500; line-height:1.2;">처음으로</a>
            <a href="?page=scenario" target="_self"
               style="display:inline-flex; align-items:center; justify-content:center;
                      min-width:118px; padding:8px 15px; border:1px solid #d0d5dd;
                      border-radius:8px; color:#1f2937; text-decoration:none;
                      background:#ffffff; font-weight:500; line-height:1.2;">시나리오 선택</a>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_anchor(anchor: str) -> None:
    st.markdown(
        f'<span id="{html.escape(anchor)}" class="panel-anchor"></span>',
        unsafe_allow_html=True,
    )


def render_payload_messages(payload: ScenarioPayload) -> None:
    for message in payload.errors:
        st.error(message)
    for message in payload.warnings:
        st.warning(message)


def render_source_waiting_card(payload: ScenarioPayload, scenario_id: str) -> None:
    feature_source = payload.sources.get("features")
    dto5_source = payload.sources.get("dto5")

    feature_hint = (
        str(feature_source.configured_path)
        if feature_source and feature_source.configured_path
        else f"Input/{scenario_id}/outputs"
    )
    dto5_hint = (
        str(dto5_source.configured_path)
        if dto5_source and dto5_source.configured_path
        else f"Model/{scenario_id}/outputs"
    )

    st.markdown(
        f"""
        <div class="safe-card soft">
            <h3>{html.escape(scenario_id)} 데이터 연결 대기</h3>
            <div class="safe-muted">
                Dashboard 내부에는 mock CSV 및 JSON을 두지 않습니다.<br/>
                Feature 후보 경로: <b>{html.escape(feature_hint)}</b><br/>
                DTO-5 후보 경로: <b>{html.escape(dto5_hint)}</b><br/>
                외부 산출물이 연결되면 같은 화면 구조에 값만 표시됩니다.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
