# [1] DTO-1 Input Panel
# 선택된 시점의 사용자 정보, 위치 정보, 워치 입력값, 기상/사고 보정 입력값을 요약

import pandas as pd
import streamlit as st

from components.panel_kit import render_detail_expander, render_input_cards, render_panel_header, render_time_card
from utils.explanation import format_id, format_value, to_float
from utils.time_utils import format_kst, format_utc


def render_dto1_input_panel(row: pd.Series) -> None:
    render_panel_header(
        "[1] DTO-1 Input Panel",
        "워치, GPS, 기상, 사고 데이터가 모델에 들어가기 전 어떤 값으로 들어왔는지 확인하는 panel",
    )
    render_time_card(format_kst(row.get("ts")))

    hr = to_float(row.get("hr_mean_bpm"))
    hr_max = to_float(row.get("hr_max_bpm"))
    spo2 = to_float(row.get("spo2_min_pct"))
    speed = to_float(row.get("speed_mean_mpm"))
    lat = to_float(row.get("user_lat"))
    lon = to_float(row.get("user_lon"))
    uuid_display, uuid_tooltip = format_id(row.get("uuid"))
    uuid_block = ("세션 ID", uuid_display, uuid_tooltip) if uuid_tooltip else ("세션 ID", uuid_display)

    render_input_cards(
        [
            (
                "soft",
                "사용자 정보",
                [
                    uuid_block,
                    ("연령대", str(row.get("age_group"))),
                    ("성별", str(row.get("gender"))),
                ],
            ),
            (
                "amber",
                "워치 데이터",
                [
                    ("평균 심박수", f"{format_value(hr, 1)} bpm"),
                    ("최대 심박수", f"{format_value(hr_max, 1)} bpm"),
                    ("SpO2", f"{format_value(spo2, 1)}%"),
                ],
            ),
            (
                "soft",
                "이동 데이터",
                [
                    ("최근 1분 걸음 수", f"{format_value(row.get('steps_1min'), 0)} 보"),
                    ("평균 속도", f"{format_value(speed, 1)} m/min"),
                ],
            ),
            (
                "green",
                "환경 데이터",
                [
                    ("heat_index", format_value(row.get("heat_index"), 1), "체감더위 기반 온열 위험 보정값"),
                    ("accident_prior", format_value(row.get("accident_prior"), 2), "여름 및 탈진성 산악사고 사전위험도"),
                    ("위도", format_value(lat, 6)),
                    ("경도", format_value(lon, 6)),
                ],
            ),
        ]
    )

    render_detail_expander(
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
