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


# ---------- 골격(스켈레톤) 페이지 공통 조각 ----------
# 아직 전용 panel이 구현되지 않은 시나리오가 A1과 같은 화면 구조(앵커 7개)를
# 유지한 채 진입 가능하도록 하는 공통 렌더러.
# 각 panel이 구현되면 scenarios/<id>/page.py에서 해당 placeholder 호출만
# 실제 panel 호출로 교체하면 된다.

SKELETON_PANELS = [
    ("dto1-input-panel", "[1] DTO-1 Input Panel",
     "워치, GPS, 환경 데이터가 모델에 들어가기 전 어떤 값으로 들어왔는지 확인하는 panel"),
    ("feature-engineering-panel", "[2] Feature Engineering Panel",
     "입력 신호가 판정에 사용되는 feature로 가공되는 과정을 보여주는 panel"),
    ("model-explanation-panel", "[3] Model Explanation Panel",
     "모델이 위험도를 계산한 근거와 요소별 기여도를 설명하는 panel"),
    ("whatif-simulating-panel", "[4] What-If Simulating Panel",
     "입력값을 조정하며 판정이 어떻게 달라지는지 시뮬레이션하는 panel"),
    ("maml-personalization-panel", "[5] Meta Learning 개인화 Panel",
     "개인 기준 반영 전후의 판정 차이를 비교하는 panel"),
    ("dto5-output-panel", "[6] DTO-5 Output Panel",
     "모델 결과가 공식 DTO-5 규격으로 정리되는 과정을 보여주는 panel"),
    ("inferenceresult-save-panel", "[7] InferenceResult 저장 Panel",
     "추론 결과가 InferenceResult로 저장되는 구조를 보여주는 panel"),
]


def render_panel_placeholder(scenario_id: str) -> None:
    """panel 구현 전 자리 표시 카드. 산출물 및 panel 연결 시 교체된다."""
    st.markdown(
        f"""
        <div class="safe-card" style="background:#eef1e8; border-color:#dfe6d6;">
            <div class="safe-muted" style="color:#33402c;">
                <span class="safe-pill" style="background:#dfe6d6; color:#33402c;">구현 예정</span><br/><br/>
                Input/{html.escape(scenario_id)} 및 Model/{html.escape(scenario_id)} 산출물이 연결되고
                panel이 구현되면 이 위치에 실제 값이 표시됩니다.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_skeleton_page(payload: ScenarioPayload, scenario_id: str, render_title) -> None:
    """A1과 동일한 화면 골격(사이드바, 요약, panel 앵커 7개)을 placeholder로 렌더링한다."""
    from components.panel_kit import render_panel_banner
    from components.sidebar import render_sidebar

    render_sidebar(payload.features, payload.dto5_sequence, scenario_code=scenario_id)

    render_back_buttons()
    render_payload_messages(payload)

    render_anchor("dashboard-top")
    render_title()
    if not payload.connected:
        st.markdown('<div style="height:22px;"></div>', unsafe_allow_html=True)
        render_source_waiting_card(payload, scenario_id)

    st.markdown('<div style="height:6px;"></div>', unsafe_allow_html=True)
    for index, (anchor, title, description) in enumerate(SKELETON_PANELS):
        render_anchor(anchor)
        st.markdown('<div style="height:38px;"></div>', unsafe_allow_html=True)
        clean_title = title.split("] ", 1)[1] if "] " in title else title
        render_panel_banner(index + 1, clean_title, description)
        render_panel_placeholder(scenario_id)