# [7] InferenceResult 저장 Panel — A1 저장 레코드 정의

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

import pandas as pd
import streamlit as st
from scenarios.common import render_panel_placeholder

from components.panel_kit import (
    render_panel_banner,
    render_soft_notice,
    INFERENCE_SAVE_LABEL,
    render_saved_records,
)
from scenarios.a1.mapper import A1Context, first_value, nested, row_value
from utils.time_utils import format_kst


def _flatten_record(context: A1Context) -> dict[str, Any]:
    row = context.row
    alert = context.alert
    location = context.location
    return {
        "inference_id": str(uuid.uuid4()),
        "scenario": "A1",
        "uuid": row_value(row, "uuid", "session_id"),
        "ts": str(row_value(row, "ts", "timestamp")),
        "ts_kst": format_kst(row_value(row, "ts", "timestamp")),
        "user_lat": first_value(row_value(row, "user_lat", "gps_lat"), nested(context.dto5, "user_location", "lat")),
        "user_lon": first_value(row_value(row, "user_lon", "gps_lon"), nested(context.dto5, "user_location", "lon")),
        "hazard_type": first_value(row_value(row, "hazard_type"), location.get("hazard_type")),
        "hazard_poi_id": first_value(row_value(row, "hazard_poi_id", "poi_id"), location.get("poi_id")),
        "dist_to_hazard_m": row_value(row, "dist_to_hazard_m"),
        "off_trail_dist_m": row_value(row, "off_trail_dist_m"),
        "slope_deg": row_value(row, "slope_deg"),
        "approaching_flag": row_value(row, "approaching_flag"),
        "a1_spatial_score": context.spatial_score,
        "a1_adjusted_score": context.adjusted_score,
        "representative_score": context.representative,
        "alert_level": context.alert_level,
        "alert_title": alert.get("title"),
        "alert_message": alert.get("message"),
        "detour_available": context.detour_available,
        "reason_text": context.reason_text,
        "dto5_json": json.dumps(context.dto5, ensure_ascii=False),
        "saved_at": datetime.now().isoformat(timespec="seconds"),
    }


def render_inferenceresult_panel(context: A1Context) -> None:
    render_panel_banner(7, "InferenceResult 저장 Panel", "현재 선택 시점의 A1 Feature와 DTO-5 결과를 비교 및 검증용 레코드로 내려받는 panel")
    # F1 디자인 이식 방향이 확정될 때까지 골격 시나리오와 동일한 자리표시로 둔다.
    # 기존 구현은 아래에 보존되어 있으며, 이 두 줄을 제거하면 복원된다.
    render_panel_placeholder("A1")
    return


    render_soft_notice(
        "Dashboard 폴더 안에 별도 CSV를 누적 생성하지 않습니다. "
        "현재 화면 세션에서만 결과를 모아 CSV 또는 JSON으로 내려받고, DB 저장은 추후 서버 REST API로 연결합니다."
    )

    storage_key = "a1_inference_results"
    if storage_key not in st.session_state:
        st.session_state[storage_key] = []

    st.markdown('<div class="infer-save-gap"></div>', unsafe_allow_html=True)
    if st.button(INFERENCE_SAVE_LABEL, type="primary", disabled=not (context.has_feature or context.has_dto5)):
        st.session_state[storage_key].append(_flatten_record(context))
        st.success("현재 시점의 A1 InferenceResult를 화면 세션에 저장했습니다.")

    records = st.session_state.get(storage_key, [])
    if not records:
        st.caption("아직 저장된 A1 InferenceResult가 없습니다.")
        return

    saved_df = pd.DataFrame(records)
    render_saved_records(
        saved_df,
        summary_columns=[
            "ts_kst",
            "hazard_type",
            "dist_to_hazard_m",
            "off_trail_dist_m",
            "representative_score",
            "alert_level",
            "alert_title",
            "detour_available",
        ],
        file_prefix="a1_inference_results",
        records=records,
    )
