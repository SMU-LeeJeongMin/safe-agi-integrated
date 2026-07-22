# 대시보드 왼쪽 사이드바 component
# 선택 시점과 전체 시나리오별 패널 이동 링크를 제공

from __future__ import annotations

from html import escape
from typing import Any

import pandas as pd
import streamlit as st

from core.registry import SCENARIOS
from components.layout import github_link_html
from utils.time_utils import format_kst


PANEL_NAV_LINKS = [
    ("시나리오 요약", "dashboard-top"),
    ("[1] DTO-1 Input Panel", "dto1-input-panel"),
    ("[2] Feature Engineering Panel", "feature-engineering-panel"),
    ("[3] Model Explanation Panel", "model-explanation-panel"),
    ("[4] What-If Simulating Panel", "whatif-simulating-panel"),
    ("[5] Meta Learning 개인화 Panel", "maml-personalization-panel"),
    ("[6] DTO-5 Output Panel", "dto5-output-panel"),
    ("[7] InferenceResult 저장 Panel", "inferenceresult-save-panel"),
]


def _panel_href(scenario_id: str, anchor: str, current_scenario: str) -> str:
    """현재 시나리오는 바로 이동하고, 다른 시나리오는 전환 후 이동한다."""
    if scenario_id == current_scenario:
        return f"#{anchor}"
    return f"?page=dashboard&scenario={scenario_id}#{anchor}"


def _render_scenario_panel_links(scenario_id: str, current_scenario: str) -> str:
    links = "".join(
        (
            f'<a href="{_panel_href(scenario_id, anchor, current_scenario)}" '
            f'target="_self">{escape(label)}</a>'
        )
        for label, anchor in PANEL_NAV_LINKS
    )
    return f'<div class="sidebar-nav scenario-sidebar-nav">{links}</div>'


def _render_all_scenario_navigation(current_scenario: str) -> None:
    """선택 화면과 같은 순서로 모든 시나리오 및 패널을 표시한다."""
    for number, (scenario_id, definition) in enumerate(SCENARIOS.items(), start=1):
        # expander 라벨은 마크다운으로 렌더링되어 "1. "이 순서 리스트로 파싱되며
        # 번호가 사라짐. "1\."로 점을 이스케이프해 일반 텍스트로 표시한다.
        with st.expander(
            f"{number}\\. [{scenario_id}] {definition.title}",
            expanded=scenario_id == current_scenario,
        ):
            st.markdown(
                _render_scenario_panel_links(scenario_id, current_scenario),
                unsafe_allow_html=True,
            )


def _dto_timestamp(dto5_sequence: list[dict[str, Any]], index: int) -> Any:
    if not dto5_sequence:
        return None
    safe_index = min(max(index, 0), len(dto5_sequence) - 1)
    item = dto5_sequence[safe_index]
    if not isinstance(item, dict):
        return None
    return item.get("timestamp") or item.get("ts") or item.get("trigger_ts")


@st.cache_data(show_spinner=False)
def _sookmyung_logo_b64() -> str:
    """사이드바 상단 바에 쓰는 숙명여대 로고(base64)."""
    import base64
    from pathlib import Path

    path = Path(__file__).resolve().parent.parent / "assets" / "sookmyung_logo.webp"
    return base64.b64encode(path.read_bytes()).decode("ascii")


def render_sidebar_topbar(current_url: str | None = None) -> None:
    """사이드바 최상단 바를 렌더링한다.

    왼쪽에 숙명여대 로고, 오른쪽에 홈(시나리오 선택 이동)과 뒤로가기 아이콘.
    components.html(iframe)은 샌드박스 때문에 부모 창 이동이 막혀
    순수 링크와 세션 기반 자체 히스토리로 구현한다.
    current_url을 넘기면 방문 기록에 쌓여 뒤로가기 대상이 된다.
    """
    history: list[str] = st.session_state.setdefault("_nav_history", [])
    if current_url:
        if not history or history[-1] != current_url:
            history.append(current_url)
            if len(history) > 8:
                del history[: len(history) - 8]
    back_href = history[-2] if len(history) >= 2 else "?page=scenario"

    home_svg = (
        '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#ffffff"'
        ' stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M3 10.5 12 3l9 7.5" /><path d="M5.5 9.5V21h13V9.5" />'
        '</svg>'
    )
    back_svg = (
        '<svg width="27" height="27" viewBox="0 0 24 24" fill="none" stroke="#ffffff"'
        ' stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M20 5H9L3 12l6 7h11a1 1 0 0 0 1-1V6a1 1 0 0 0-1-1Z" />'
        '<path d="m11.5 9.5 5 5M16.5 9.5l-5 5" />'
        '</svg>'
    )
    st.sidebar.markdown(
        (
            '<div class="sidebar-topbar">'
            f'<img src="data:image/webp;base64,{_sookmyung_logo_b64()}" alt="숙명여자대학교" />'
            '<div class="sidebar-topbar-icons">'
            f'<a href="?page=scenario" target="_self" title="시나리오 선택으로 이동" aria-label="시나리오 선택으로 이동">{home_svg}</a>'
            f'<a href="{back_href}" target="_self" title="뒤로가기" aria-label="뒤로가기">{back_svg}</a>'
            '</div>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


def render_sidebar_links() -> None:
    """공통 작업 링크(GitHub 등)를 사이드바 최하단에 고정 표시한다."""
    st.sidebar.divider()
    with st.sidebar.container(key="sb_links"):
        st.markdown(
            """
            <div class="sidebar-section-heading">Links</div>
            <div class="sidebar-section-caption">공통 작업 레포 바로가기</div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(github_link_html(), unsafe_allow_html=True)


def render_sidebar(
    features: pd.DataFrame,
    dto5_sequence: list[dict],
    scenario_code: str = "F1",
) -> int:
    current_scenario = scenario_code.upper()

    if not features.empty and dto5_sequence:
        item_count = min(len(features), len(dto5_sequence))
    elif not features.empty:
        item_count = len(features)
    else:
        item_count = len(dto5_sequence)

    # 섹션 흰색 상자 스타일링을 위한 키 컨테이너 (기본 상태에서는 투명)
    with st.sidebar.container(key="sb_time_select"):
        st.markdown(
            """
            <div class="sidebar-section-heading">시점 선택</div>
            <div class="sidebar-section-caption">분 단위 시점 index</div>
            """,
            unsafe_allow_html=True,
        )
        if item_count > 1:
            selected_idx = st.slider(
                "분 단위 시점 index",
                min_value=0,
                max_value=item_count - 1,
                value=item_count - 1,
                label_visibility="collapsed",
                key=f"{current_scenario}_time_index",
            )
        else:
            selected_idx = st.slider(
                "분 단위 시점 index",
                min_value=0,
                max_value=1,
                value=0,
                disabled=True,
                label_visibility="collapsed",
                key=f"{current_scenario}_time_index_waiting",
            )

    selected_ts = None
    if not features.empty:
        safe_index = min(selected_idx, len(features) - 1)
        row = features.iloc[safe_index]
        selected_ts = row.get("ts", row.get("timestamp"))
    if selected_ts is None:
        selected_ts = _dto_timestamp(dto5_sequence, selected_idx)

    selected_time_text = format_kst(selected_ts) if selected_ts is not None else "데이터 연결 대기"
    with st.sidebar.container(key="sb_time_value"):
        st.markdown(
            f"""
            <div class="sidebar-time-box">
                <div class="sidebar-time-label">선택 시점</div>
                <div class="sidebar-time-value">{selected_time_text}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.sidebar.divider()
    with st.sidebar.container(key="sb_panel_nav"):
        st.markdown(
            """
            <div class="sidebar-section-heading">Panel Navigation</div>
            <div class="sidebar-section-caption">전체 시나리오 및 Panel 바로가기</div>
            """,
            unsafe_allow_html=True,
        )
        _render_all_scenario_navigation(current_scenario)
        st.markdown(
            (
                '<div class="sidebar-nav sidebar-nav-monitor" style="margin-top:10px;">'
                '<a href="?page=monitor" target="_self">실시간 모니터링 (BETA)</a>'
                '</div>'
            ),
            unsafe_allow_html=True,
        )

    render_sidebar_links()

    return selected_idx