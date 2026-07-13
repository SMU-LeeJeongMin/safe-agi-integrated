# [6] DTO-5 Output Panel
# 최종 AI 분석 결과가 아이나비 서버로 전달될 DTO-5 구조

from __future__ import annotations

import pandas as pd
import streamlit as st

from components.panel_kit import (
    alert_wide_card,
    dto5_card,
    render_json_expander,
    render_location_map,
    render_panel_header,
)
from utils.explanation import to_float


def _fmt_float(value: object, digits: int = 4) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return "-"


def render_dto5_panel(row: pd.Series, dto5: dict, reason_text: str) -> None:
    del reason_text
    render_panel_header(
        "[6] DTO-5 Output Panel",
        "모델 판단 결과가 앱과 서버로 전달될 DTO-5 핵심 필드로 정리되는 과정을 보여주는 panel",
    )

    risk = dto5.get("risk", {})
    fatigue = dto5.get("fatigue", {})
    nearest_shelter = fatigue.get("nearest_shelter")
    alerts = dto5.get("alerts") or []
    first_alert = alerts[0] if alerts else {}

    st.markdown("#### DTO-5 핵심 필드")
    c1, c2, c3 = st.columns(3)
    with c1:
        e1_e2_tip = (
            f"e1_biometric: {_fmt_float(risk.get('e1_biometric'))}<br />"
            f"e2_combined: {_fmt_float(risk.get('e2_combined'))}"
        )
        st.markdown(
            dto5_card(
                "Risk",
                [
                    {"label": "representative", "value": _fmt_float(risk.get("representative")), "tooltip": e1_e2_tip},
                    {"label": "risk_label", "value": str(risk.get("label", "-"))},
                    {"label": "risk_level", "value": str(risk.get("level", "-"))},
                ],
                "soft",
            ),
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            dto5_card(
                "Fatigue",
                [
                    {"label": "피로 상태", "value": fatigue.get("state", "-")},
                    {
                        "label": "confidence",
                        "value": _fmt_float(fatigue.get("confidence")),
                        "tooltip": "피로 상태 판정에 대한 신뢰도<br />산출식: confidence = 0.5 + |representative - 0.65| × 1.5",
                        "wide": True,
                    },
                ],
                "amber",
            ),
            unsafe_allow_html=True,
        )
    with c3:
        if isinstance(nearest_shelter, dict):
            shelter_blocks = [
                {
                    "label": "추천 쉼터",
                    "value": nearest_shelter.get("name", "-"),
                    "tooltip": "청계산 POI/GIS 휴식지점 데이터에서<br />현재 위치 기준으로 선택",
                    "wide": True,
                },
                {"label": "거리", "value": f"{nearest_shelter.get('distance_m', '-')} m"},
                {"label": "예상 시간", "value": f"약 {nearest_shelter.get('est_min', '-')}분"},
            ]
        else:
            shelter_blocks = [{"label": "추천 쉼터", "value": "없음"}]
        st.markdown(dto5_card("Nearest Shelter", shelter_blocks, "soft"), unsafe_allow_html=True)

    st.markdown(
        alert_wide_card(
            first_alert.get("title", "현재 알림 없음"),
            first_alert.get("message", "현재 사용자에게 전달할 F1 알림이 없습니다."),
        ),
        unsafe_allow_html=True,
    )

    st.markdown('<div class="dto5-section-gap"></div>', unsafe_allow_html=True)
    st.markdown("#### 현재 위치와 추천 쉼터")
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
        st.info("현재 상태에서는 추천 쉼터가 없습니다.")

    render_json_expander(dto5)
