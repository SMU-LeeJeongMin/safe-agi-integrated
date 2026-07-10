# [7] InferenceResult 저장 Panel
# 현재 선택된 시점의 입력값, feature, DTO-5 결과, 판단 근거를 InferenceResult 형태로 저장한다.

import json
import uuid
from datetime import datetime

import pandas as pd
import streamlit as st

from file_location import INFERENCE_SAVE_PATH
from utils.time_utils import format_kst
from utils.xAI import get_nested


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
    new_df = pd.DataFrame([record])

    if INFERENCE_SAVE_PATH.exists():
        old_df = pd.read_csv(INFERENCE_SAVE_PATH)
        out_df = pd.concat([old_df, new_df], ignore_index=True)
    else:
        out_df = new_df

    out_df.to_csv(INFERENCE_SAVE_PATH, index=False, encoding="utf-8-sig")


def load_saved_results() -> pd.DataFrame:
    if not INFERENCE_SAVE_PATH.exists():
        return pd.DataFrame()

    return pd.read_csv(INFERENCE_SAVE_PATH)


def render_inferenceresult_panel(row: pd.Series, dto5: dict, reason_text: str) -> None:
    st.header("[7] InferenceResult 저장 Panel")
    st.markdown(
        '<div class="panel-description">실제 분석 결과와 What-if 결과를 저장해 이후 비교·검증할 수 있도록 기록하는 panel</div>',
        unsafe_allow_html=True,
    )

    st.info(
        "현재는 분석 결과 비교를 위해 로컬 CSV 파일에 저장합니다.\n"
        "다음 단계에서는 동일한 스키마를 PostgreSQL DB 저장으로 연결합니다."
    )

    st.markdown('<div class="infer-save-gap"></div>', unsafe_allow_html=True)
    if st.button("현재 시점 InferenceResult 저장", type="primary"):
        record = flatten_for_save(row, dto5, reason_text)
        save_inference_result(record)
        st.success("현재 시점의 InferenceResult를 저장했습니다.")

    saved_df = load_saved_results()
    if saved_df.empty:
        st.caption("아직 저장된 InferenceResult가 없습니다.")
        return

    st.markdown("#### 저장된 InferenceResult 요약")
    summary_cols = [
        "source",
        "ts_kst",
        "hr_mean_bpm",
        "spo2_min_pct",
        "risk_label",
        "fatigue_state",
        "alert_title",
        "nearest_shelter_name",
    ]
    existing_summary_cols = [c for c in summary_cols if c in saved_df.columns]
    st.dataframe(saved_df[existing_summary_cols], use_container_width=True, hide_index=True)

    if "source" in saved_df.columns and saved_df["source"].nunique() > 1:
        st.caption("source: actual은 실제 선택 시점 결과, whatif는 What-If Simulating 재분석 결과입니다.")

    with st.expander("전체 저장 컬럼 보기"):
        st.dataframe(saved_df, use_container_width=True)

    with st.expander("저장 파일 다운로드"):
        st.download_button(
            label="inference_results_demo.csv 다운로드",
            data=saved_df.to_csv(index=False, encoding="utf-8-sig"),
            file_name="inference_results_demo.csv",
            mime="text/csv",
        )
