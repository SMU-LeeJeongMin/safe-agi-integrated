# [1] DTO-1 Input Panel
# 선택된 시점의 사용자 정보, 위치 정보, 워치 입력값, 기상/사고 보정 입력값을 요약해 보여준다.

import pandas as pd
import streamlit as st

from utils.time_utils import format_kst, format_utc
from utils.xAI import format_value, to_float


def _metric_block(label: str, value: str, note: str | None = None) -> str:
    tooltip_html = (
        '<span class="dto1-tooltip" aria-label="설명 보기">i'
        f'<span class="dto1-tooltip-text">{note}</span>'
        '</span>'
        if note
        else ""
    )
    return (
        '<div class="dto1-metric-block">'
        '<div class="dto1-label-row">'
        f'<span class="dto1-label">{label}</span>'
        f'{tooltip_html}'
        '</div>'
        f'<div class="dto1-value">{value}</div>'
        '</div>'
    )


def _card_html(kind: str, title: str, body: str) -> str:
    return (
        f'<div class="safe-card {kind} dto1-card">'
        f'<h4>{title}</h4>'
        f'{body}'
        '</div>'
    )


def render_dto1_input_panel(row: pd.Series) -> None:
    st.header("[1] DTO-1 Input Panel")
    st.markdown(
        '<div class="panel-description">워치·GPS·기상·사고 데이터가 모델에 들어가기 전 어떤 값으로 들어왔는지 확인하는 panel</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        (
            '<div class="safe-card soft dto1-time-card">'
            '<b>현재 시점</b>'
            f'<span class="dto1-time-value">{format_kst(row.get("ts"))}</span>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )

    hr = to_float(row.get("hr_mean_bpm"))
    hr_max = to_float(row.get("hr_max_bpm"))
    spo2 = to_float(row.get("spo2_min_pct"))
    speed = to_float(row.get("speed_mean_mpm"))
    lat = to_float(row.get("user_lat"))
    lon = to_float(row.get("user_lon"))

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        user_body = "".join(
            [
                _metric_block("세션 ID", str(row.get("uuid"))),
                _metric_block("연령대", str(row.get("age_group"))),
                _metric_block("성별", str(row.get("gender"))),
            ]
        )
        st.markdown(_card_html("soft", "사용자 정보", user_body), unsafe_allow_html=True)

    with col2:
        watch_body = "".join(
            [
                _metric_block("평균 심박수", f"{format_value(hr, 1)} bpm"),
                _metric_block("최대 심박수", f"{format_value(hr_max, 1)} bpm"),
                _metric_block("SpO2", f"{format_value(spo2, 1)}%"),
            ]
        )
        st.markdown(_card_html("amber", "워치 데이터", watch_body), unsafe_allow_html=True)

    with col3:
        movement_body = "".join(
            [
                _metric_block("최근 1분 걸음 수", f"{format_value(row.get('steps_1min'), 0)} 보"),
                _metric_block("평균 속도", f"{format_value(speed, 1)} m/min"),
            ]
        )
        st.markdown(_card_html("soft", "이동 데이터", movement_body), unsafe_allow_html=True)

    with col4:
        env_body = "".join(
            [
                _metric_block("heat_index", format_value(row.get("heat_index"), 1), "체감더위 기반 온열 위험 보정값"),
                _metric_block("accident_prior", format_value(row.get("accident_prior"), 2), "여름·탈진성 산악사고 사전위험도"),
                _metric_block("위도", format_value(lat, 6)),
                _metric_block("경도", format_value(lon, 6)),
            ]
        )
        st.markdown(_card_html("green", "환경 데이터", env_body), unsafe_allow_html=True)

    st.markdown('<div class="dto1-expander-gap"></div>', unsafe_allow_html=True)

    with st.expander("원본 입력 상세 보기"):
        detail_df = pd.DataFrame(
            [
                {"구분": "세션", "항목": "uuid", "값": row.get("uuid")},
                {"구분": "시간", "항목": "KST", "값": format_kst(row.get("ts"))},
                {"구분": "시간", "항목": "UTC", "값": format_utc(row.get("ts"))},
                {"구분": "위치", "항목": "user_lat", "값": format_value(row.get("user_lat"), 6)},
                {"구분": "위치", "항목": "user_lon", "값": format_value(row.get("user_lon"), 6)},
                {"구분": "워치", "항목": "hr_mean_bpm", "값": f"{format_value(row.get('hr_mean_bpm'), 1)} bpm"},
                {"구분": "워치", "항목": "hr_max_bpm", "값": f"{format_value(row.get('hr_max_bpm'), 1)} bpm"},
                {"구분": "워치", "항목": "spo2_min_pct", "값": f"{format_value(row.get('spo2_min_pct'), 1)}%"},
                {"구분": "이동", "항목": "steps_1min", "값": f"{format_value(row.get('steps_1min'), 0)} 보"},
                {"구분": "이동", "항목": "speed_mean_mpm", "값": f"{format_value(row.get('speed_mean_mpm'), 1)} m/min"},
                {"구분": "환경", "항목": "heat_index", "값": format_value(row.get("heat_index"), 1)},
                {"구분": "환경", "항목": "accident_prior", "값": format_value(row.get("accident_prior"), 2)},
                {"구분": "프로필", "항목": "age_group", "값": row.get("age_group")},
                {"구분": "프로필", "항목": "gender", "값": row.get("gender")},
            ]
        )
        st.dataframe(detail_df, use_container_width=True, hide_index=True)
