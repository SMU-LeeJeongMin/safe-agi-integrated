# [6] DTO-5 Output Panel

from __future__ import annotations

import streamlit as st

from components.panel_kit import (
    alert_wide_card,
    dto5_card,
    render_json_expander,
    render_panel_header,
)
from scenarios.a1.mapper import A1Context, first_value, row_value
from scenarios.a1.formatting import _fmt, _fmt_bool, _text
from scenarios.a1.a1_map import render_a1_map


def render_dto5_panel(context: A1Context) -> None:
    row = context.row
    alert = context.alert
    location = context.location

    render_panel_header(
        "[6] DTO-5 Output Panel",
        "A1 모델 결과가 공식 DTO-5 alerts[]의 type, level, location, detour_available로 정리되는 과정을 보여주는 panel",
    )

    st.markdown("#### DTO-5 핵심 필드")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            dto5_card(
                "Alert",
                [
                    {"label": "type", "value": _text(alert.get("type"), "A1" if context.has_dto5 else "-")},
                    {"label": "level", "value": _text(context.alert_level)},
                    {"label": "title", "value": _text(alert.get("title"), "현재 알림 없음")},
                ],
                "soft",
            ),
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            dto5_card(
                "Location",
                [
                    {"label": "poi_id", "value": _text(first_value(location.get("poi_id"), row_value(row, "hazard_poi_id", "poi_id")))},
                    {"label": "lat", "value": _fmt(first_value(location.get("lat"), row_value(row, "hazard_lat")), 6)},
                    {"label": "lon", "value": _fmt(first_value(location.get("lon"), row_value(row, "hazard_lon")), 6)},
                ],
                "amber",
            ),
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            dto5_card(
                "Detour",
                [
                    {"label": "detour_available", "value": _fmt_bool(context.detour_available)},
                    {"label": "extra_min", "value": _fmt(context.detour_extra_min, 1, "분")},
                    {"label": "hazard_type", "value": _text(first_value(location.get("hazard_type"), row_value(row, "hazard_type")))},
                ],
                "soft",
            ),
            unsafe_allow_html=True,
        )

    st.markdown(
        alert_wide_card(
            _text(alert.get("title"), "현재 알림 없음"),
            _text(alert.get("message"), "현재 사용자에게 전달할 A1 알림이 없습니다."),
        ),
        unsafe_allow_html=True,
    )

    st.markdown('<div class="dto5-section-gap"></div>', unsafe_allow_html=True)
    st.markdown("#### 현재 위치와 위험 POI")
    render_a1_map(context)

    render_json_expander(context.dto5, empty_text="A1 DTO-5 파일이 연결되면 공식 JSON을 그대로 표시합니다.")
