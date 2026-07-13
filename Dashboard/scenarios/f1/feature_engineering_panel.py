# [2] Feature Engineering Panel
# DTO-1 기반 입력값이 모델 입력 feature로 어떻게 변환되었는지 

import html

import pandas as pd
import plotly.express as px
import streamlit as st

from components.panel_kit import feature_card, style_feature_fig
from utils.time_utils import to_kst_timestamp
from utils.explanation import build_feature_calculations, get_nested


KEY_FEATURES = ["hr_ratio_maxhr", "hr_z_personal", "hr_overload_5min", "spo2_grade"]


FEATURE_HELP = {
    "hr_ratio_maxhr": {
        "title": "현재 심박 부담도",
        "desc": "65세 기준 최대심박수 대비 현재 평균 심박수의 부담 정도",
        "formula": "평균 심박수 ÷ 65세 기준 최대심박수",
    },
    "hr_z_personal": {
        "title": "개인 기준 대비 상승",
        "desc": "개인 기준 심박 대비 현재 심박수 상승 정도를 표준화한 값",
        "formula": "(현재 심박수 - 기준 심박수) ÷ 표준편차",
    },
    "hr_overload_5min": {
        "title": "5분 과부하 지속 여부",
        "desc": "심박 부담이 높은 상태가 5분 이상 이어졌는지에 대한 여부",
        "formula": "심박 부담도 ≥ 0.85 상태가 5분 이상 지속되는지 판단",
    },
    "spo2_grade": {
        "title": "산소포화도 등급",
        "desc": "SpO2 값을 정상, 경고, 위험 등급으로 변환한 feature",
        "formula": "95% 이상 정상 / 90~94% 경고 / 90% 미만 위험",
    },
}


def _feature_title(feature: str) -> str:
    return FEATURE_HELP.get(feature, {}).get("title", feature)


def _feature_desc(feature: str) -> str:
    return FEATURE_HELP.get(feature, {}).get("desc", "")



def _feature_summary(feature: str, item: dict[str, str]) -> str:
    formula = FEATURE_HELP.get(feature, {}).get("formula", item.get("계산 과정", "-"))
    return feature_card(
        field=feature,
        title=_feature_title(feature),
        value=item.get("값", "-"),
        tooltip=_feature_desc(feature),
        box_label="공식",
        box_text=formula,
    )




def render_feature_engineering_panel(
    row: pd.Series,
    features: pd.DataFrame,
    dto5_sequence: list[dict],
) -> None:
    st.header("[2] Feature Engineering Panel")
    st.markdown(
        '<div class="panel-description">입력값을 모델이 판단할 수 있는 1분 단위 feature로 변환하는 과정을 보여주는 panel</div>',
        unsafe_allow_html=True,
    )

    calc_rows = build_feature_calculations(row)
    calc_by_feature = {item["feature"]: item for item in calc_rows}

    st.markdown("#### F1 시나리오에 사용되는 대표 Feature")
    cols = st.columns(4)
    for col, feature in zip(cols, KEY_FEATURES):
        item = calc_by_feature.get(feature)
        if not item:
            continue
        with col:
            st.markdown(_feature_summary(feature, item), unsafe_allow_html=True)

    st.markdown('<div class="feature-table-gap"></div>', unsafe_allow_html=True)
    with st.expander("전체 feature table 보기"):
        st.markdown(
            '<div class="panel-description">왼쪽 index 0~115는 산행 중 116개의 1분 시점을 의미하고, 20 feature는 모델 입력으로 사용하는 20개 컬럼을 의미합니다.</div>',
            unsafe_allow_html=True,
        )
        st.dataframe(features, use_container_width=True)

    st.markdown("#### 시간 흐름 그래프")
    st.markdown(
        '<div class="panel-description">그래프의 시간축은 한국시간(KST) 기준입니다. 회색 점선은 현재 선택한 1분 시점을 의미합니다.</div>',
        unsafe_allow_html=True,
    )

    n = min(len(features), len(dto5_sequence))
    graph_df = features.iloc[:n].copy()
    graph_df["ts_kst"] = [to_kst_timestamp(x) for x in graph_df["ts"]]

    graph_df["risk_representative"] = [
        get_nested(x, ["risk", "representative"], 0)
        for x in dto5_sequence[:n]
    ]

    graph_df["fatigue_state"] = [
        get_nested(x, ["fatigue", "state"], "없음")
        for x in dto5_sequence[:n]
    ]

    selected_ts = to_kst_timestamp(row.get("ts"))

    def add_selected_line(fig):
        if selected_ts is not None:
            fig.add_vline(x=selected_ts, line_dash="dash", line_color="gray")
        return style_feature_fig(fig)

    tab1, tab2, tab3, tab4 = st.tabs(["심박수", "SpO2", "위험도", "걸음/속도"])

    with tab1:
        fig_hr = px.line(
            graph_df,
            x="ts_kst",
            y="hr_mean_bpm",
            title="시간별 평균 심박수 변화",
            labels={"ts_kst": "한국시간", "hr_mean_bpm": "평균 심박수(bpm)"},
        )
        st.plotly_chart(add_selected_line(fig_hr), use_container_width=True)

    with tab2:
        fig_spo2 = px.line(
            graph_df,
            x="ts_kst",
            y="spo2_min_pct",
            title="시간별 SpO2 변화",
            labels={"ts_kst": "한국시간", "spo2_min_pct": "SpO2(%)"},
        )
        st.plotly_chart(add_selected_line(fig_spo2), use_container_width=True)

    with tab3:
        fig_risk = px.line(
            graph_df,
            x="ts_kst",
            y="risk_representative",
            title="시간별 대표 위험도 변화",
            labels={"ts_kst": "한국시간", "risk_representative": "대표 위험도"},
        )
        st.plotly_chart(add_selected_line(fig_risk), use_container_width=True)

    with tab4:
        col_a, col_b = st.columns(2)

        with col_a:
            fig_steps = px.line(
                graph_df,
                x="ts_kst",
                y="steps_1min",
                title="시간별 최근 1분 걸음 수",
                labels={"ts_kst": "한국시간", "steps_1min": "걸음 수"},
            )
            st.plotly_chart(add_selected_line(fig_steps), use_container_width=True)

        with col_b:
            fig_speed = px.line(
                graph_df,
                x="ts_kst",
                y="speed_mean_mpm",
                title="시간별 평균 속도",
                labels={"ts_kst": "한국시간", "speed_mean_mpm": "속도(m/min)"},
            )
            st.plotly_chart(add_selected_line(fig_speed), use_container_width=True)
