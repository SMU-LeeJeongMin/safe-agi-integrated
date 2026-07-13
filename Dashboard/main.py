# 대시보드 실행 파일
# streamlit run Dashboard/main.py 명령어로 실행

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_DIR = Path(__file__).resolve().parent

for path in (REPO_ROOT, DASHBOARD_DIR):
    path_text = str(path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)

from components.layout import inject_global_css, render_intro_page, render_scenario_select_page
from core.registry import get_scenario
from core.router import load_renderer
from core.source_loader import load_scenario_payload


def _query_value(name: str) -> str | None:
    value = st.query_params.get(name)
    if isinstance(value, list):
        return value[0] if value else None
    return value


def main() -> None:
    st.set_page_config(
        page_title="산행안전 AI 대시보드",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_global_css()

    if "page" not in st.session_state:
        st.session_state["page"] = "intro"

    query_page = _query_value("page")
    query_scenario = _query_value("scenario")

    query_applied = False
    if query_page in {"intro", "scenario", "dashboard", "monitor"}:
        st.session_state["page"] = query_page
        query_applied = True
    if query_scenario:
        st.session_state["selected_scenario"] = query_scenario.upper()
        query_applied = True
    if query_applied:
        st.query_params.clear()

    page = st.session_state["page"]

    if page == "intro":
        render_intro_page()
        return

    if page == "scenario":
        render_scenario_select_page()
        return

    if page == "monitor":
        from monitor.page import render_monitor_page

        render_monitor_page()
        return

    selected_scenario = st.session_state.get("selected_scenario", "F1")
    definition = get_scenario(selected_scenario)

    if not definition.enabled or definition.source_spec is None:
        st.session_state["page"] = "scenario"
        st.warning(f"{definition.scenario_id} 시나리오는 아직 준비 중입니다.")
        render_scenario_select_page()
        return

    payload = load_scenario_payload(definition.source_spec)
    renderer = load_renderer(definition)
    renderer(payload, definition)


if __name__ == "__main__":
    main()
