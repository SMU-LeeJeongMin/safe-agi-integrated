# [6] DTO-5 Output Panel
# 최종 AI 분석 결과가 아이나비 서버로 전달될 DTO-5 구조

from __future__ import annotations

import pandas as pd
import streamlit as st

from components.panel_kit import (
    render_subsection,
    render_panel_banner,
    render_soft_notice,
    render_json_expander,
    render_location_map,
    render_panel_header,
    server_icon_b64,
)
from components.panel_kit import BUBBLE_COLORS
from utils.explanation import to_float


def _fmt_float(value: object, digits: int = 4) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return "-"


def _bubble_block(label: str, value: object, tooltip: str | None = None, wide: bool = False) -> str:
    """말풍선 내부 라벨+값 블록. 툴팁 HTML(<br /> 포함)을 그대로 허용한다."""
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


def render_dto5_panel(row: pd.Series, dto5: dict, reason_text: str) -> None:
    del reason_text
    render_panel_banner(6, "DTO-5 Output Panel", "모델 판단 결과가 앱과 서버로 전달될 DTO-5 핵심 필드로 정리되는 과정을 보여주는 panel")

    risk = dto5.get("risk", {})
    fatigue = dto5.get("fatigue", {})
    nearest_shelter = fatigue.get("nearest_shelter")
    alerts = dto5.get("alerts") or []
    first_alert = alerts[0] if alerts else {}

    render_subsection("DTO-5 핵심 필드")

    e1_e2_tip = (
        f"e1_biometric: {_fmt_float(risk.get('e1_biometric'))}<br />"
        f"e2_combined: {_fmt_float(risk.get('e2_combined'))}"
    )
    risk_html = (
        _bubble_block("representative", _fmt_float(risk.get("representative")), e1_e2_tip)
        + _bubble_block("risk_label", str(risk.get("label", "-")))
        + _bubble_block("risk_level", str(risk.get("level", "-")))
    )
    fatigue_html = (
        _bubble_block("fatigue_state", fatigue.get("state", "-"))
        + _bubble_block(
            "confidence",
            _fmt_float(fatigue.get("confidence")),
            "피로 상태 판정에 대한 신뢰도<br />산출식: confidence = 0.5 + |representative - 0.65| × 1.5",
            wide=True,
        )
    )
    if isinstance(nearest_shelter, dict):
        shelter_html = (
            _bubble_block(
                "추천 쉼터",
                nearest_shelter.get("name", "-"),
                "청계산 POI/GIS 휴식지점 데이터에서<br />현재 위치 기준으로 선택",
                wide=True,
            )
            + _bubble_block("거리", f"{nearest_shelter.get('distance_m', '-')} m")
            + _bubble_block("예상 시간", f"약 {nearest_shelter.get('est_min', '-')}분")
        )
    else:
        shelter_html = _bubble_block("추천 쉼터", "없음")
    alert_html = (
        _bubble_block("제목", first_alert.get("title", "현재 알림 없음"))
        + _bubble_block("메시지", first_alert.get("message", "현재 사용자에게 전달할 F1 알림이 없습니다."))
    )

    # 나비형 4분할 + 중앙 서버 아이콘
    st.markdown(
        (
            '<div class="dto5-quad">'
            + _quad_bubble(0, "Risk", risk_html)
            + _quad_bubble(1, "Fatigue", fatigue_html)
            + _quad_bubble(2, "Nearest Shelter", shelter_html)
            + _quad_bubble(3, "Alert", alert_html, horizontal=False)
            + '<div class="dto5-quad-center">'
            + f'<img src="data:image/png;base64,{server_icon_b64()}" alt="서버" />'
            + '</div>'
            + '</div>'
        ),
        unsafe_allow_html=True,
    )

    # DTO-5 상세 보기 (나비 구성 바로 아래로 이동)
    st.markdown('<div style="height:18px;"></div>', unsafe_allow_html=True)
    render_json_expander(dto5)

    st.markdown('<div class="dto5-section-gap"></div>', unsafe_allow_html=True)
    render_subsection("현재 위치와 추천 쉼터")
    if isinstance(nearest_shelter, dict) and nearest_shelter.get("lat") is not None:
        shelter_name = nearest_shelter.get("name") or "쉼터"
        render_location_map(
            points=[
                {"lat": to_float(row.get("user_lat")), "lon": to_float(row.get("user_lon")), "label": "현재 위치", "kind": "current"},
                {
                    "lat": to_float(nearest_shelter.get("lat")),
                    "lon": to_float(nearest_shelter.get("lon")),
                    "label": f"추천 쉼터: {shelter_name}",
                    "kind": "shelter",
                },
            ],
            zoom=13.25,
            legend=[("dot-blue", "현재 위치"), ("dot-red", "추천 쉼터")],
        )
    else:
        render_soft_notice("현재 상태에서는 추천 쉼터가 없습니다.")