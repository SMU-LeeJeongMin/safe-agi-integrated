# [6] DTO-5 Output Panel
# 최종 AI 분석 결과가 아이나비 서버로 전달될 DTO-5 구조를 보여준다.

from __future__ import annotations

import html

import pandas as pd
import streamlit as st

from utils.xAI import to_float


def _safe(value: object) -> str:
    return html.escape("" if value is None else str(value))


def _fmt_float(value: object, digits: int = 4) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return "-"


def _tooltip_label(label: str, tooltip: str | None = None, tooltip_class: str = "") -> str:
    if not tooltip:
        return f'<div class="dto1-label">{_safe(label)}</div>'
    return (
        '<div class="dto1-label-row">'
        f'<span class="dto1-label">{_safe(label)}</span>'
        f'<span class="dto1-tooltip {tooltip_class}">i'
        f'<span class="dto1-tooltip-text">{tooltip}</span>'
        '</span>'
        '</div>'
    )


def _dto5_card(title: str, blocks: list[tuple[str, str, str | None, str | None]], class_name: str = "soft") -> str:
    body = []
    for label, value, note, tooltip in blocks:
        tooltip_class = "dto1-tooltip-wide" if tooltip and "청계산 POI/GIS" in tooltip else ""
        body.append(
            '<div class="dto5-field-block">'
            f'{_tooltip_label(label, tooltip, tooltip_class)}'
            f'<div class="dto1-value dto5-value">{_safe(value)}</div>'
            + (f'<div class="dto1-note dto5-note">{_safe(note)}</div>' if note else "")
            + '</div>'
        )
    return (
        f'<div class="safe-card {class_name} dto5-core-card">'
        f'<h4>{_safe(title)}</h4>'
        f'{"".join(body)}'
        '</div>'
    )


def _render_map(row: pd.Series, nearest_shelter: dict) -> None:
    user_lat = to_float(row.get("user_lat"))
    user_lon = to_float(row.get("user_lon"))
    shelter_lat = to_float(nearest_shelter.get("lat"))
    shelter_lon = to_float(nearest_shelter.get("lon"))
    shelter_name = nearest_shelter.get("name") or "쉼터"

    map_df = pd.DataFrame(
        [
            {"lat": user_lat, "lon": user_lon, "label": "현재 위치", "kind": "current"},
            {"lat": shelter_lat, "lon": shelter_lon, "label": f"추천 쉼터: {shelter_name}", "kind": "shelter"},
        ]
    )

    st.markdown(
        """
        <div class="icon-row dto5-map-legend">
            <span><span class="legend-dot dot-blue"></span>현재 위치</span>
            <span><span class="legend-dot dot-red"></span>추천 쉼터</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    try:
        import pydeck as pdk

        scatter_df = map_df.copy()
        scatter_df["color"] = scatter_df["kind"].apply(
            lambda x: [36, 84, 166, 215] if x == "current" else [200, 62, 62, 225]
        )
        scatter_df["size"] = scatter_df["kind"].apply(lambda x: 75 if x == "current" else 92)

        text_df = map_df.copy()
        text_df["lat"] = text_df["lat"] + 0.00018

        center_lat = (user_lat + shelter_lat) / 2
        center_lon = (user_lon + shelter_lon) / 2

        view_state = pdk.ViewState(
            latitude=center_lat,
            longitude=center_lon,
            zoom=13.25,
            pitch=0,
        )

        deck = pdk.Deck(
            map_style=None,
            initial_view_state=view_state,
            layers=[
                pdk.Layer(
                    "ScatterplotLayer",
                    data=scatter_df,
                    get_position="[lon, lat]",
                    get_radius="size",
                    get_fill_color="color",
                    pickable=True,
                ),
                pdk.Layer(
                    "TextLayer",
                    data=text_df,
                    get_position="[lon, lat]",
                    get_text="label",
                    get_size=15,
                    get_color=[20, 35, 63, 255],
                    get_text_anchor="middle",
                    get_alignment_baseline="bottom",
                ),
            ],
            tooltip={"text": "{label}"},
        )
        st.pydeck_chart(deck, use_container_width=True)
    except Exception:
        fallback_df = pd.DataFrame(
            [
                {"lat": user_lat, "lon": user_lon, "color": "#2454a6", "size": 40},
                {"lat": shelter_lat, "lon": shelter_lon, "color": "#c83e3e", "size": 48},
            ]
        )
        st.map(fallback_df, latitude="lat", longitude="lon", color="color", size="size")

def _confidence_tooltip(value: object, representative: object) -> str:
    return (
        '<div class="dto1-label-row">'
        '<span class="dto1-label">confidence</span>'
        '<span class="dto1-tooltip dto1-tooltip-wide">i'
        '<span class="dto1-tooltip-text">피로 상태 판정에 대한 신뢰도<br />산출식: confidence = 0.5 + |representative - 0.65| × 1.5</span>'
        '</span>'
        '</div>'
        f'<div class="dto1-value dto5-value">{_safe(_fmt_float(value))}</div>'
    )


def _alert_wide_card(title: str, message: str) -> str:
    return (
        '<div class="safe-card green dto5-alert-wide">'
        '<h4>Alerts</h4>'
        '<div class="dto5-alert-grid">'
        '<div>'
        '<div class="dto1-label">알림 제목</div>'
        f'<div class="dto1-value dto5-alert-title">{_safe(title)}</div>'
        '</div>'
        '<div>'
        '<div class="dto1-label">알림 문구</div>'
        f'<div class="dto5-alert-message">{_safe(message)}</div>'
        '</div>'
        '</div>'
        '</div>'
    )


def render_dto5_panel(row: pd.Series, dto5: dict, reason_text: str) -> None:
    st.header("[6] DTO-5 Output Panel")
    st.markdown(
        '<div class="panel-description">모델 판단 결과가 앱과 서버로 전달될 DTO-5 핵심 필드로 정리되는 과정을 보여주는 panel</div>',
        unsafe_allow_html=True,
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
            _dto5_card(
                "Risk",
                [
                    ("representative", _fmt_float(risk.get("representative")), None, e1_e2_tip),
                    ("risk_label", str(risk.get("label", "-")), None, None),
                    ("risk_level", str(risk.get("level", "-")), None, None),
                ],
                "soft",
            ),
            unsafe_allow_html=True,
        )
    with c2:
        fatigue_html = (
            '<div class="safe-card amber dto5-core-card">'
            '<h4>Fatigue</h4>'
            '<div class="dto5-field-block">'
            '<div class="dto1-label">피로 상태</div>'
            f'<div class="dto1-value dto5-value">{_safe(fatigue.get("state", "-"))}</div>'
            '</div>'
            '<div class="dto5-field-block">'
            f'{_confidence_tooltip(fatigue.get("confidence"), risk.get("representative"))}'
            '</div>'
            '</div>'
        )
        st.markdown(fatigue_html, unsafe_allow_html=True)
    with c3:
        if isinstance(nearest_shelter, dict):
            shelter_blocks = [
                ("추천 쉼터", nearest_shelter.get("name", "-"), None, "청계산 POI/GIS 휴식지점 데이터에서<br />현재 위치 기준으로 선택"),
                ("거리", f"{nearest_shelter.get('distance_m', '-')} m", None, None),
                ("예상 시간", f"약 {nearest_shelter.get('est_min', '-')}분", None, None),
            ]
        else:
            shelter_blocks = [("추천 쉼터", "없음", None, None)]
        st.markdown(_dto5_card("Nearest Shelter", shelter_blocks, "soft"), unsafe_allow_html=True)

    st.markdown(
        _alert_wide_card(
            first_alert.get("title", "현재 알림 없음"),
            first_alert.get("message", "현재 사용자에게 전달할 F1 알림이 없습니다."),
        ),
        unsafe_allow_html=True,
    )

    st.markdown('<div class="dto5-section-gap"></div>', unsafe_allow_html=True)
    st.markdown("#### 현재 위치와 추천 쉼터")
    if isinstance(nearest_shelter, dict) and nearest_shelter.get("lat") is not None:
        _render_map(row, nearest_shelter)
    else:
        st.info("현재 상태에서는 추천 쉼터가 없습니다.")

    with st.expander("DTO-5 JSON 상세 보기"):
        st.json(dto5)
