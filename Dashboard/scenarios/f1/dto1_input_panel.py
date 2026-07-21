# [1] DTO-1 Input Panel
# 선택된 시점의 사용자 정보, 위치 정보, 워치 입력값, 기상/사고 보정 입력값을 요약

import pandas as pd
import streamlit as st

from components.panel_kit import render_detail_expander, render_input_bubbles, render_panel_header, render_panel_banner
from core import trainset
from utils.explanation import format_id, format_profile, format_value, ref_hr_baseline, to_float
from utils.time_utils import format_kst, format_utc


def render_dto1_input_panel(
    row: pd.Series,
    features: pd.DataFrame | None = None,
    dto5_sequence: list[dict] | None = None,
) -> None:
    render_panel_banner(1, "DTO-1 Input Panel", "워치, GPS, 기상, 사고 데이터가 모델에 들어가기 전 어떤 값으로 들어왔는지 확인하는 panel")

    hr = to_float(row.get("hr_mean_bpm"))
    hr_max = to_float(row.get("hr_max_bpm"))
    spo2 = to_float(row.get("spo2_min_pct"))
    speed = to_float(row.get("speed_mean_mpm"))
    lat = to_float(row.get("user_lat"))
    lon = to_float(row.get("user_lon"))
    # 학습셋 세션은 uuid, age_group이 없으므로 원본 컬럼(session_id, persona_name, age)에서
    # 표시용으로만 파생한다 (성별은 학습셋 Phase 3 비식별 ID 도입 전까지 미등록이 정확한 표시).
    uuid_value = row.get("uuid")
    if (uuid_value is None or (isinstance(uuid_value, float) and pd.isna(uuid_value))) and row.get("persona_name") is not None:
        uuid_value = row.get("persona_name")
    age_group_value = row.get("age_group")
    if age_group_value is None or (isinstance(age_group_value, float) and pd.isna(age_group_value)):
        age_group_value = trainset.display_age_group(row.get("age"))

    uuid_display, uuid_tooltip = format_id(uuid_value)
    uuid_block = ("세션 ID", uuid_display, uuid_tooltip) if uuid_tooltip else ("세션 ID", uuid_display)

    baseline = ref_hr_baseline(row)
    user_items = [
        uuid_block,
        ("연령대", format_profile(age_group_value)),
        ("성별", format_profile(row.get("gender"))),
    ]
    if baseline["is_fallback"] is not None:
        baseline_tooltip = (
            "프로필 미등록으로 국민건강영양조사(KNHANES) 성인 전체 통계 기준을 적용"
            if baseline["is_fallback"]
            else "국민건강영양조사(KNHANES) 연령대별 통계 기준을 적용"
        )
        user_items.append((
            "판정 기준 심박",
            f"최대 {baseline['max_hr']:.0f} / 안정 {baseline['rest_hr']:.1f} bpm",
            baseline_tooltip,
        ))

    render_input_bubbles(
        [
            (
                "사용자 정보",
                user_items,
            ),
            (
                "생체 데이터",
                [
                    ("평균 심박수", f"{format_value(hr, 1)} bpm"),
                    ("최대 심박수", f"{format_value(hr_max, 1)} bpm"),
                    ("SpO2", f"{format_value(spo2, 1)}%"),
                ],
            ),
            (
                "이동 데이터",
                [
                    ("최근 1분 걸음 수", f"{format_value(row.get('steps_1min'), 0)} 보"),
                    ("평균 속도", f"{format_value(speed, 1)} m/min"),
                ],
            ),
            (
                "환경 데이터",
                [
                    ("heat_index", format_value(row.get("heat_index"), 1), "체감더위 기반 온열 위험 보정값"),
                    ("accident_prior", format_value(row.get("accident_prior"), 2), "여름 및 탈진성 산악사고 사전위험도", True),
                    ("위도", format_value(lat, 6)),
                    ("경도", format_value(lon, 6)),
                ],
            ),
        ],
        time_text=format_kst(row.get("ts")),
    )

    render_detail_expander(
        [
            {"구분": "세션", "항목": "uuid", "값": uuid_value},
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
            {"구분": "프로필", "항목": "age_group", "값": format_profile(age_group_value)},
            {"구분": "프로필", "항목": "gender", "값": format_profile(row.get("gender"))},
            {"구분": "판정 기준", "항목": "ref_max_hr", "값": f"{format_value(row.get('ref_max_hr'), 0)} bpm"},
            {"구분": "판정 기준", "항목": "ref_resting_hr", "값": f"{format_value(row.get('ref_resting_hr'), 1)} bpm"},
            {"구분": "판정 기준", "항목": "baseline_is_fallback", "값": str(row.get("baseline_is_fallback"))},
        ]
    )

    # 시간 흐름 그래프 ([2]에서 이동)
    if features is not None and not features.empty:
        from scenarios.f1.feature_engineering_panel import render_time_series_section
        render_time_series_section(row, features, dto5_sequence or [])