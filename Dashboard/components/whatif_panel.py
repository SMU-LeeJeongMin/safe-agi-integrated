# [4] What-If Simulating Panel
# 입력값이 바뀌었을 때 실제 F1 모델 재계산 결과를 비교한다.

import pandas as pd
import streamlit as st

from Model.f1_model import infer_f1
from utils.xAI import build_whatif_features, get_nested, to_float


def _format_risk_value(value: object) -> str:
    try:
        return f"{float(value):.4f}"
    except Exception:
        return str(value)


def _result_card(title: str, risk_value: object, label: object, state: object, class_name: str = "soft") -> None:
    st.markdown(
        f"""
        <div class="safe-card {class_name}">
            <h4>{title}</h4>
            <div class="big">{_format_risk_value(risk_value)}</div>
            <div class="safe-muted">위험 등급: <b>{label}</b><br/>피로 상태: <b>{state}</b></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_whatif_panel(row: pd.Series, dto5: dict) -> None:
    st.header("[4] What-If Simulating Panel")
    st.markdown(
        '<div class="panel-description">입력값을 바꿨을 때 모델 결과가 어떻게 달라지는지 확인하는 panel</div>',
        unsafe_allow_html=True,
    )

    current_hr = to_float(row.get("hr_mean_bpm"), 120.0)
    current_spo2 = to_float(row.get("spo2_min_pct"), 95.0)
    current_steps = to_float(row.get("steps_1min"), 30.0)
    current_heat_index = to_float(row.get("heat_index"), 28.0)

    current_risk = get_nested(dto5, ["risk", "representative"], 0)
    current_label = get_nested(dto5, ["risk", "label"], "-")
    current_state = get_nested(dto5, ["fatigue", "state"], "-")

    left, right = st.columns([1, 1.15])

    with left:
        st.markdown("#### 현재 상태")
        st.markdown(
            f"""
            <div class="whatif-current-line">심박수: <b>{current_hr:.0f} bpm</b></div>
            <div class="whatif-current-line">SpO2: <b>{current_spo2:.0f}%</b></div>
            <div class="whatif-current-line">최근 1분 걸음 수: <b>{current_steps:.0f}보</b></div>
            <div class="whatif-current-line">Heat Index: <b>{current_heat_index:.1f}</b></div>
            """,
            unsafe_allow_html=True,
        )

    with right:
        st.markdown("#### 시뮬레이션 입력")
        c1, c2 = st.columns(2)
        with c1:
            changed_hr = st.slider("심박수", 60.0, 180.0, float(current_hr), 1.0)
            changed_spo2 = st.slider("SpO2", 85.0, 100.0, float(current_spo2), 1.0)
        with c2:
            changed_steps = st.slider("최근 1분 걸음 수", 0.0, 100.0, float(current_steps), 1.0)
            changed_heat_index = st.slider("Heat Index", 20.0, 40.0, float(current_heat_index), 0.5)

    run_key = f"whatif_result_{row.get('ts')}"
    if st.button("변경값으로 다시 분석하기", type="primary", use_container_width=True):
        whatif_features = build_whatif_features(
            row=row,
            changed_hr=changed_hr,
            changed_spo2=changed_spo2,
            changed_steps=changed_steps,
            changed_heat_index=changed_heat_index,
        )
        whatif_dto5 = infer_f1(whatif_features)
        st.session_state[run_key] = {
            "features": whatif_features,
            "dto5": whatif_dto5,
            "reason": (
                f"What-If 재추론: HR {current_hr:.0f}→{changed_hr:.0f}, "
                f"SpO2 {current_spo2:.0f}→{changed_spo2:.0f}, "
                f"걸음 {current_steps:.0f}→{changed_steps:.0f}, "
                f"heat {current_heat_index:.1f}→{changed_heat_index:.1f}"
            ),
        }

    result = st.session_state.get(run_key)
    if not result:
        st.info("슬라이더 값을 조정한 뒤 버튼을 누르면 실제 F1 모델이 다시 계산됩니다.")
        return

    whatif_features = result["features"]
    whatif_dto5 = result["dto5"]

    st.markdown('<div class="whatif-result-gap"></div>', unsafe_allow_html=True)
    st.markdown("#### 현재 결과 vs What-If 결과")
    c1, c2 = st.columns(2)
    with c1:
        _result_card("현재", current_risk, current_label, current_state, "amber")
    with c2:
        _result_card(
            "What-If 상태",
            get_nested(whatif_dto5, ["risk", "representative"], 0),
            get_nested(whatif_dto5, ["risk", "label"], "-"),
            get_nested(whatif_dto5, ["fatigue", "state"], "-"),
            "green",
        )

    st.markdown('<div class="whatif-info-gap"></div>', unsafe_allow_html=True)
    st.info("What-If 결과는 화면용 임의 규칙이 아니라, F1 모델 함수로 재계산한 값입니다.")

    st.markdown("#### What-If 결과 저장")
    if st.button("이 What-If 결과를 InferenceResult로 저장"):
        from components.inferenceresult_panel import flatten_for_save, save_inference_result

        whatif_row = pd.Series(whatif_features)
        record = flatten_for_save(whatif_row, whatif_dto5, result["reason"], source="whatif")
        save_inference_result(record)
        st.success("What-If 결과를 InferenceResult에 저장했습니다. [7] 패널에서 실제 결과(actual)와 비교할 수 있습니다.")
