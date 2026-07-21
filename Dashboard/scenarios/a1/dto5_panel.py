# [6] DTO-5 Output Panel

from __future__ import annotations

import streamlit as st

from components.panel_kit import (
    server_icon_b64,
    BUBBLE_COLORS,
    render_panel_banner,
    render_subsection,
    alert_wide_card,
    dto5_card,
    render_json_expander,
    render_panel_header,
)
from scenarios.a1.mapper import A1Context, first_value, row_value
from scenarios.a1.formatting import _fmt, _fmt_bool, _text
from scenarios.a1.a1_map import render_a1_map


def _bubble_block(label: str, value: object, tooltip: str | None = None, wide: bool = False) -> str:
    """말풍선 내부 라벨+값 블록. 툴팁 HTML을 그대로 허용한다."""
    if tooltip:
        wide_class = " dto1-tooltip-wide" if wide else ""
        label_html = (
            '<div class="dto1-label-row">'
            f'<div class="dto1-label">{label}</div>'
            f'<span class="dto1-tooltip{wide_class}" aria-label="설명 보기">i'
            f'<span class="dto1-tooltip-text">{tooltip}</span>'
            '</span>'
            '</div>'
        )
    else:
        label_html = f'<div class="dto1-label">{label}</div>'
    return f'<div class="dto1-block">{label_html}<div class="dto1-value">{value}</div></div>'


def _quad_bubble(index: int, title: str, blocks_html: str, horizontal: bool = True) -> str:
    color = BUBBLE_COLORS[index % len(BUBBLE_COLORS)]
    if horizontal:
        blocks_html = f'<div class="dto5-quad-row">{blocks_html}</div>'
    return (
        f'<div class="dto1-bubble dto5-quad-bubble" style="--bubble:{color};">'
        f'<div class="dto1-bubble-title">{title}</div>'
        f'{blocks_html}'
        '</div>'
    )


def render_dto5_panel(context: A1Context) -> None:
    row = context.row
    alert = context.alert
    location = context.location

    render_panel_banner(6, "DTO-5 Output Panel", "A1 모델 결과가 공식 DTO-5 alerts[]의 type, level, location, detour_available로 정리되는 과정을 보여주는 panel")

    render_subsection("DTO-5 핵심 필드")

    alert_core_html = (
        _bubble_block("type", _text(alert.get("type"), "A1" if context.has_dto5 else "-"))
        + _bubble_block("level", _text(context.alert_level))
        + _bubble_block("title", _text(alert.get("title"), "현재 알림 없음"))
    )
    location_html = (
        _bubble_block("poi_id", _text(first_value(location.get("poi_id"), row_value(row, "hazard_poi_id", "poi_id"))))
        + _bubble_block("lat", _fmt(first_value(location.get("lat"), row_value(row, "hazard_lat")), 6))
        + _bubble_block("lon", _fmt(first_value(location.get("lon"), row_value(row, "hazard_lon")), 6))
    )
    detour_html = (
        _bubble_block("detour_available", _fmt_bool(context.detour_available))
        + _bubble_block("extra_min", _fmt(context.detour_extra_min, 1, "분"))
        + _bubble_block("hazard_type", _text(first_value(location.get("hazard_type"), row_value(row, "hazard_type"))))
    )
    message_html = (
        _bubble_block("제목", _text(alert.get("title"), "현재 알림 없음"))
        + _bubble_block("메시지", _text(alert.get("message"), "현재 사용자에게 전달할 A1 알림이 없습니다."))
    )

    st.markdown(
        (
            '<div class="dto5-quad">'
            + _quad_bubble(0, "Alert", alert_core_html)
            + _quad_bubble(1, "Location", location_html)
            + _quad_bubble(2, "Detour", detour_html)
            + _quad_bubble(3, "Message", message_html, horizontal=False)
            + '<div class="dto5-quad-center">'
            + f'<img src="data:image/png;base64,{server_icon_b64()}" alt="서버" />'
            + '</div>'
            + '</div>'
        ),
        unsafe_allow_html=True,
    )

    st.markdown('<div style="height:18px;"></div>', unsafe_allow_html=True)
    render_json_expander(context.dto5, empty_text="A1 DTO-5 파일이 연결되면 공식 JSON을 그대로 표시합니다.")

    render_subsection("현재 위치와 위험 POI")
    render_a1_map(context)
