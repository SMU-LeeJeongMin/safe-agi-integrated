# [7] InferenceResult 저장 Panel
# 현재 선택된 결과를 Dashboard 파일시스템에 쓰지 않고 화면 세션에서 비교 및 다운로드

import json
import uuid
from datetime import datetime

import pandas as pd
import streamlit as st

from components.panel_kit import INFERENCE_SAVE_LABEL, render_saved_records, render_panel_banner, render_soft_notice

from utils.time_utils import format_kst
from utils.explanation import get_nested

_STORAGE_KEY = "f1_inference_results"


def flatten_for_save(row: pd.Series, dto5: dict, reason_text: str, source: str = "actual") -> dict:
    nearest_shelter = get_nested(dto5, ["fatigue", "nearest_shelter"], None)

    if not isinstance(nearest_shelter, dict):
        nearest_shelter = {}

    alerts = dto5.get("alerts") or []
    first_alert = alerts[0] if alerts else {}

    return {
        "inference_id": str(uuid.uuid4()),
        "source": source,
        "uuid": row.get("uuid"),
        "ts": str(row.get("ts")),
        "ts_kst": format_kst(row.get("ts")),
        "user_lat": row.get("user_lat"),
        "user_lon": row.get("user_lon"),
        "hr_mean_bpm": row.get("hr_mean_bpm"),
        "spo2_min_pct": row.get("spo2_min_pct"),
        "steps_1min": row.get("steps_1min"),
        "heat_index": row.get("heat_index"),
        "accident_prior": row.get("accident_prior"),
        "risk_representative": get_nested(dto5, ["risk", "representative"]),
        "risk_level": get_nested(dto5, ["risk", "level"]),
        "risk_label": get_nested(dto5, ["risk", "label"]),
        "fatigue_state": get_nested(dto5, ["fatigue", "state"]),
        "fatigue_confidence": get_nested(dto5, ["fatigue", "confidence"]),
        "nearest_shelter_name": nearest_shelter.get("name"),
        "nearest_shelter_distance_m": nearest_shelter.get("distance_m"),
        "nearest_shelter_est_min": nearest_shelter.get("est_min"),
        "alert_title": first_alert.get("title"),
        "alert_message": first_alert.get("message"),
        "reason_text": reason_text,
        "dto5_json": json.dumps(dto5, ensure_ascii=False),
        "saved_at": datetime.now().isoformat(timespec="seconds"),
    }


def save_inference_result(record: dict) -> None:
    if _STORAGE_KEY not in st.session_state:
        st.session_state[_STORAGE_KEY] = []
    st.session_state[_STORAGE_KEY].append(dict(record))


def load_saved_results() -> pd.DataFrame:
    records = st.session_state.get(_STORAGE_KEY, [])
    return pd.DataFrame(records)


def render_inferenceresult_panel(row: pd.Series, dto5: dict, reason_text: str) -> None:
    render_panel_banner(7, "InferenceResult 저장 Panel", "실제 분석 결과와 What-if 결과를 저장해 이후 비교 및 검증할 수 있도록 기록하는 panel")

    render_soft_notice(
        "현재 화면 세션에서 실제 결과와 What-If 결과를 비교하고 CSV로 내려받으며, DB 저장은 추후 서버 REST API로 연결합니다."
    )

    st.markdown('<div class="infer-save-gap"></div>', unsafe_allow_html=True)
    if st.button(INFERENCE_SAVE_LABEL, type="primary"):
        record = flatten_for_save(row, dto5, reason_text)
        save_inference_result(record)
        st.success("현재 시점의 InferenceResult를 화면 세션에 저장했습니다.")

    saved_df = load_saved_results()
    if saved_df.empty:
        st.caption("아직 저장된 InferenceResult가 없습니다.")
        return

    render_saved_records(
        saved_df,
        summary_columns=[
            "source",
            "ts_kst",
            "hr_mean_bpm",
            "spo2_min_pct",
            "risk_label",
            "fatigue_state",
            "alert_title",
            "nearest_shelter_name",
        ],
        file_prefix="inference_results_demo",
        records=st.session_state.get(_STORAGE_KEY, []),
        source_caption="source: actual은 실제 선택 시점 결과, whatif는 What-If Simulating 재분석 결과입니다.",
    )