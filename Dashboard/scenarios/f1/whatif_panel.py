# [4] What-If Simulating Panel
# 입력값이 바뀌었을 때 실제 F1 모델 재계산 결과를 비교 (VS 게이지 레이아웃)

import pandas as pd
import streamlit as st

from Model.f1_model import infer_f1

from components.panel_kit import render_panel_banner, render_subsection
from utils.explanation import build_whatif_features, get_nested, to_float


# 등급 텍스트 색 (기존 zone 팔레트와 동일)
GRADE_COLORS = {"정상": "#16734f", "주의": "#8a5900", "경고": "#b42318", "위험": "#8f1010"}

# 지표 정의: (표시명, 단위, 슬라이더 범위, 스텝, row 컬럼, 포맷)
METRICS = [
    ("심박수", "bpm", (60.0, 180.0), 1.0, "hr_mean_bpm", "{:.0f}"),
    ("SpO2", "%", (85.0, 100.0), 1.0, "spo2_min_pct", "{:.0f}"),
    ("걸음수", "보", (0.0, 100.0), 1.0, "steps_1min", "{:.0f}"),
    ("체감온도", "", (20.0, 40.0), 0.5, "heat_index", "{:.1f}"),
]


def _format_risk_value(value: object) -> str:
    try:
        return f"{float(value):.4f}"
    except Exception:
        return str(value)


def _pct(value: float, lo: float, hi: float) -> float:
    if hi <= lo:
        return 0.0
    return max(0.0, min(1.0, (value - lo) / (hi - lo))) * 100


def _status_line(risk_value: object, label: object, state: object) -> str:
    color = GRADE_COLORS.get(str(label), "#16734f")
    return (
        '<div class="whatif-side-status">'
        f'대표 위험도 <b>{_format_risk_value(risk_value)}</b>'
        f'&nbsp;&nbsp;위험 등급 <b style="color:{color};">{label}</b>'
        f'&nbsp;&nbsp;피로 상태 <b>{state}</b>'
        '</div>'
    )


def render_whatif_panel(row: pd.Series, dto5: dict) -> None:
    render_panel_banner(4, "What-If Simulating Panel", "입력값을 바꿨을 때 모델 결과가 어떻게 달라지는지 확인하는 panel")

    current = {
        "hr_mean_bpm": to_float(row.get("hr_mean_bpm"), 120.0),
        "spo2_min_pct": to_float(row.get("spo2_min_pct"), 95.0),
        "steps_1min": to_float(row.get("steps_1min"), 30.0),
        "heat_index": to_float(row.get("heat_index"), 28.0),
    }
    current_risk = get_nested(dto5, ["risk", "representative"], 0)
    current_label = get_nested(dto5, ["risk", "label"], "-")
    current_state = get_nested(dto5, ["fatigue", "state"], "-")

    # 슬라이더 키 초기화 및 현재 세션 값 읽기 (헤더의 What-If 등급 표시용)
    for _, _, _, _, col, _ in METRICS:
        st.session_state.setdefault(f"whatif::{col}", float(current[col]))
    changed = {col: float(st.session_state[f"whatif::{col}"]) for _, _, _, _, col, _ in METRICS}

    whatif_features = build_whatif_features(
        row=row,
        changed_hr=changed["hr_mean_bpm"],
        changed_spo2=changed["spo2_min_pct"],
        changed_steps=changed["steps_1min"],
        changed_heat_index=changed["heat_index"],
    )
    whatif_dto5 = infer_f1(whatif_features)

    render_subsection("입력값 변경 후 결과 비교하기")
    st.markdown('<div style="height:18px;"></div>', unsafe_allow_html=True)

    # ── 헤더: 지표 행과 같은 5열 그리드, 제목과 결과는 각 그래프 중앙 정렬 ──
    _sp1, head_l, head_c, head_r, _sp2 = st.columns([0.28, 1.15, 0.34, 1.15, 0.28], vertical_alignment="top")
    with head_l:
        st.markdown('<div class="whatif-side-title">현재 입력값</div>', unsafe_allow_html=True)
        st.markdown(_status_line(current_risk, current_label, current_state), unsafe_allow_html=True)
    with head_c:
        st.markdown('<div class="whatif-vs">VS</div>', unsafe_allow_html=True)
    with head_r:
        st.markdown('<div class="whatif-side-title">시뮬레이션 입력값</div>', unsafe_allow_html=True)
        st.markdown(
            _status_line(
                get_nested(whatif_dto5, ["risk", "representative"], 0),
                get_nested(whatif_dto5, ["risk", "label"], "-"),
                get_nested(whatif_dto5, ["fatigue", "state"], "-"),
            ),
            unsafe_allow_html=True,
        )

    st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)

    # ── 지표별 VS 게이지 행 ──
    # 오른쪽 게이지의 시각은 슬라이더 뒤에 ::before로 그린다:
    # 왼쪽 막대와 동일한 색(#c9d4bb 채움, #f1f0ec 바탕)의 gradient를
    # 파이썬이 아는 채움 비율(%)로 주입해 색과 디자인을 정확히 통일한다.
    gauge_styles = []
    for _, _, (lo, hi), _, col, _ in METRICS:
        pct = _pct(changed[col], lo, hi)
        gauge_styles.append(
            f'.st-key-wfbar_{col} div[data-baseweb="slider"] > div:first-child::before {{'
            'content:""; position:absolute; left:2px; right:2px; top:calc(50% + 10px);'
            'transform:translateY(-50%); height:26px; border-radius:999px; z-index:0;'
            f'background: linear-gradient(to right, #c9d4bb 0 {pct:.1f}%, #f1f0ec {pct:.1f}% 100%);'
            '}'
        )
    st.markdown("<style>" + "".join(gauge_styles) + "</style>", unsafe_allow_html=True)

    for label, unit, (lo, hi), step, col, fmt in METRICS:
        cur_val = current[col]
        new_val = changed[col]
        cur_pct = _pct(cur_val, lo, hi)
        unit_suffix = f" {unit}" if unit else ""

        v_l, bar_l, mid, bar_r, v_r = st.columns([0.28, 1.15, 0.34, 1.15, 0.28], vertical_alignment="center")
        with v_l:
            st.markdown(
                f'<div class="whatif-bar-value left">{fmt.format(cur_val)}{unit_suffix}</div>',
                unsafe_allow_html=True,
            )
        with bar_l:
            st.markdown(
                (
                    '<div class="whatif-track left">'
                    f'<div class="whatif-fill left" style="width:{cur_pct:.1f}%;"></div>'
                    '</div>'
                ),
                unsafe_allow_html=True,
            )
        with mid:
            st.markdown(f'<div class="whatif-metric-label">{label}</div>', unsafe_allow_html=True)
        with bar_r:
            with st.container(key=f"wfbar_{col}"):
                st.slider(
                    label,
                    min_value=lo,
                    max_value=hi,
                    step=step,
                    key=f"whatif::{col}",
                    label_visibility="collapsed",
                )
        with v_r:
            st.markdown(
                f'<div class="whatif-bar-value">{fmt.format(new_val)}{unit_suffix}</div>',
                unsafe_allow_html=True,
            )

    whatif_reason = (
        f"What-If 재추론: HR {current['hr_mean_bpm']:.0f}→{changed['hr_mean_bpm']:.0f}, "
        f"SpO2 {current['spo2_min_pct']:.0f}→{changed['spo2_min_pct']:.0f}, "
        f"걸음 {current['steps_1min']:.0f}→{changed['steps_1min']:.0f}, "
        f"heat {current['heat_index']:.1f}→{changed['heat_index']:.1f}"
    )

    st.markdown('<div style="height:20px;"></div>', unsafe_allow_html=True)
    render_subsection("What-If 결과 저장")
    if st.button("이 What-If 결과를 InferenceResult로 저장"):
        from scenarios.f1.inferenceresult_panel import flatten_for_save, save_inference_result

        whatif_row = pd.Series(whatif_features)
        record = flatten_for_save(whatif_row, whatif_dto5, whatif_reason, source="whatif")
        save_inference_result(record)
        st.success("What-If 결과를 InferenceResult에 저장했습니다. [7] 패널에서 실제 결과(actual)와 비교할 수 있습니다.")