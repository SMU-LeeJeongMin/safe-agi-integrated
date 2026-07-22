# 뒤로가기, 연결 대기 카드 등 페이지 공통 조각

from __future__ import annotations

import html

import streamlit as st

from core.contracts import ScenarioPayload
from core import trainset


LEGACY_SOURCE_OPTION = "기존 산출물 (outputs)"


def render_trainset_picker(payload: ScenarioPayload, scenario_id: str) -> ScenarioPayload:
    """사이드바에서 학습셋 관찰 대상(사용자, 세션 상황)을 고르게 하고 payload를 교체한다.

    - Input/<ID>/synth 학습셋이 없으면 UI 없이 기존 payload를 그대로 돌려준다.
    - 기존 outputs 산출물이 연결되어 있으면 그것도 선택지로 유지한다.
      (outputs가 삭제된 뒤에는 학습셋 세션이 기본 선택이 된다.)
    - 학습셋은 사용자(페르소나) 10명 x 상황 4종 구조이므로
      사용자 선택 -> 상황 선택의 2단으로 나눈다.
    """
    if not trainset.available(scenario_id):
        return payload

    metas = trainset.list_sessions(scenario_id)
    if not metas:
        return payload

    # 사용자(페르소나) 단위 그룹핑
    users: dict[str, list[dict]] = {}
    for meta in metas:
        persona = meta.get("persona_name") or f"session{meta['session_id']:02d}"
        users.setdefault(persona, []).append(meta)

    def _user_label(persona: str) -> str:
        sessions = users[persona]
        age = sessions[0].get("age")
        age_text = f" ({int(age)}세)" if age is not None else ""
        return f"{persona}{age_text}"

    has_legacy = payload.item_count > 0
    user_options = ([LEGACY_SOURCE_OPTION] if has_legacy else []) + sorted(users)

    with st.sidebar.container(key=f"sb_trainset_picker_{scenario_id}"):
        st.markdown(
            f"""
            <div class="sidebar-section-heading">관찰 대상 선택</div>
            <div class="sidebar-section-caption">학습셋 사용자 {len(users)}명, 세션 {len(metas)}개</div>
            """,
            unsafe_allow_html=True,
        )
        selected_user = st.selectbox(
            "관찰 사용자",
            options=user_options,
            format_func=lambda v: v if v == LEGACY_SOURCE_OPTION else _user_label(v),
            key=f"{scenario_id}_trainset_user",
            label_visibility="collapsed",
        )
        if selected_user == LEGACY_SOURCE_OPTION:
            st.sidebar.divider()
            return payload

        sessions = users[selected_user]
        session_labels = {
            int(meta["session_id"]): (
                f"{meta['situation']} 상황" if meta.get("situation") else f"세션 {meta['session_id']:02d}"
            )
            for meta in sessions
        }
        selected_session_id = st.selectbox(
            "세션 상황",
            options=list(session_labels),
            format_func=lambda sid: session_labels[sid],
            key=f"{scenario_id}_trainset_session_{selected_user}",
            label_visibility="collapsed",
        )
    st.sidebar.divider()
    return trainset.build_payload(scenario_id, int(selected_session_id))


def render_back_buttons() -> None:
    """상단 이동 버튼은 사이드바 상단 바(로고, 홈, 뒤로가기)로 대체되어 더 이상 그리지 않는다."""
    return None


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
    from components.sidebar import render_sidebar, render_sidebar_topbar

    render_sidebar_topbar(f"?page=dashboard&scenario={scenario_id}")
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
        st.markdown('<div style="height:96px;"></div>', unsafe_allow_html=True)
        clean_title = title.split("] ", 1)[1] if "] " in title else title
        render_panel_banner(index + 1, clean_title, description)
        render_panel_placeholder(scenario_id)