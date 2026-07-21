# [4] What-If Simulating Panel — A1 재분석 요청값 구성

from __future__ import annotations

from typing import Any

import streamlit as st
from scenarios.common import render_panel_placeholder

from components.panel_kit import WHATIF_RERUN_LABEL, result_card, render_panel_banner, render_subsection, render_soft_notice

from scenarios.a1.mapper import A1Context, row_value, to_bool, to_float
from scenarios.a1.formatting import _selected_alert_label, _fmt, _fmt_bool, _safe, _text


def _result_card(title: str, risk_value: Any, label: Any, state: Any, class_name: str = "soft") -> None:
    risk_text = _fmt(risk_value, 4) if to_float(risk_value) is not None else "-"
    st.markdown(
        result_card(title, risk_text, [("판정 상태", _text(label)), ("요청 상태", _text(state))], class_name),
        unsafe_allow_html=True,
    )


def render_whatif_panel(context: A1Context) -> None:
    row = context.row
    render_panel_banner(4, "What-If Simulating Panel", "입력값을 바꿔 외부 Model/API에 전달할 A1 재분석 요청값을 구성하는 panel")
    # F1 디자인 이식 방향이 확정될 때까지 골격 시나리오와 동일한 자리표시로 둔다.
    # 기존 구현은 아래에 보존되어 있으며, 이 두 줄을 제거하면 복원된다.
    render_panel_placeholder("A1")
    return


    current_distance = to_float(row_value(row, "dist_to_hazard_m"))
    current_offtrail = to_float(row_value(row, "off_trail_dist_m"))
    current_slope = to_float(row_value(row, "slope_deg"))
    current_approach = to_bool(row_value(row, "approaching_flag"))
    connected = bool(row)

    left, right = st.columns([1, 1.15])
    with left:
        render_subsection("현재 상태")
        st.markdown(
            f"""
            <div class="whatif-current-line">위험 지점 거리: <b>{_safe(_fmt(current_distance, 1, ' m'))}</b></div>
            <div class="whatif-current-line">지정로 이탈: <b>{_safe(_fmt(current_offtrail, 1, ' m'))}</b></div>
            <div class="whatif-current-line">경사도: <b>{_safe(_fmt(current_slope, 1, '°'))}</b></div>
            <div class="whatif-current-line">접근 여부: <b>{_safe(_fmt_bool(current_approach, '접근 중', '멀어지는 중'))}</b></div>
            """,
            unsafe_allow_html=True,
        )

    with right:
        render_subsection("시뮬레이션 입력")
        c1, c2 = st.columns(2)
        with c1:
            changed_distance = st.slider(
                "위험 지점까지 거리 (m)",
                0.0,
                500.0,
                float(current_distance if current_distance is not None else 0.0),
                1.0,
                disabled=not connected,
                key="a1_whatif_distance",
            )
            changed_offtrail = st.slider(
                "지정로 이탈 거리 (m)",
                0.0,
                150.0,
                float(current_offtrail if current_offtrail is not None else 0.0),
                1.0,
                disabled=not connected,
                key="a1_whatif_offtrail",
            )
        with c2:
            changed_slope = st.slider(
                "경사도 (°)",
                0.0,
                60.0,
                float(min(max(current_slope if current_slope is not None else 0.0, 0.0), 60.0)),
                0.5,
                disabled=not connected,
                key="a1_whatif_slope",
            )
            changed_approach = st.checkbox(
                "위험 지점을 향해 접근 중",
                value=bool(current_approach) if current_approach is not None else False,
                disabled=not connected,
                key="a1_whatif_approach",
            )

    request_key = f"a1_whatif_request_{_text(row_value(row, 'uuid', 'session_id'), 'waiting')}"
    if st.button(WHATIF_RERUN_LABEL, type="primary", use_container_width=True, disabled=not connected):
        st.session_state[request_key] = {
            "scenario": "A1",
            "uuid": row_value(row, "uuid", "session_id"),
            "timestamp": str(row_value(row, "ts", "timestamp")),
            "features": {
                "dist_to_hazard_m": changed_distance,
                "off_trail_dist_m": changed_offtrail,
                "slope_deg": changed_slope,
                "approaching_flag": changed_approach,
                "hazard_type": row_value(row, "hazard_type"),
                "hazard_poi_id": row_value(row, "hazard_poi_id", "poi_id"),
            },
        }

    request = st.session_state.get(request_key)
    if not request:
        render_soft_notice("A1 Feature가 연결되면 값을 조정하고 Model/API용 재분석 요청을 만들 수 있습니다. Dashboard 자체에서는 점수를 계산하지 않습니다.")
        return

    st.markdown('<div class="whatif-result-gap"></div>', unsafe_allow_html=True)
    render_subsection("현재 결과 vs 재분석 요청")
    c1, c2 = st.columns(2)
    with c1:
        _result_card("현재", context.representative, _selected_alert_label(context), "DTO-5 수신값", "amber")
    with c2:
        _result_card("What-If 요청", None, "Model 응답 대기", "요청 Payload 생성", "green")

    st.markdown('<div class="whatif-info-gap"></div>', unsafe_allow_html=True)
    render_soft_notice("재분석 결과는 추후 서버 REST API 또는 Model 출력 파일에서 받아 같은 위치에 표시합니다.")
    with st.expander("Model/API 전달 요청 JSON 보기"):
        st.json(request)
