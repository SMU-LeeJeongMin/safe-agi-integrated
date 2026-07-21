# [2] Feature Engineering Panel
# DTO-1 기반 입력값이 모델 입력 feature로 어떻게 변환되었는지 

import html

import pandas as pd
import plotly.express as px
import streamlit as st
from html import escape

from components.panel_kit import feature_card, style_feature_fig, render_panel_banner, render_subsection
from utils.time_utils import to_kst_timestamp
from utils.explanation import build_feature_calculations, get_nested


KEY_FEATURES = ["hr_ratio_maxhr", "hr_z_personal", "hr_overload_5min", "spo2_grade"]


FEATURE_HELP = {
    "hr_ratio_maxhr": {
        "title": "현재 심박 부담도",
        "desc": "기준 최대심박수 대비 현재 평균 심박수의 부담 정도",
        "formula": "평균 심박수 ÷ 기준 최대심박수(연령대별, 미등록 시 성인 전체)",
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




def _render_feature_bands(calc_by_feature: dict[str, dict]) -> None:
    """대표 feature 4개를 좌우 번갈아 배치되는 라운드 밴드로 렌더링한다.

    밴드 안: 라벨(i 툴팁), 값, 공식, 현재 시점 실제 값이 대입된 계산.
    밴드 밖: 점선 커넥터와 feature 이름.
    """
    rows_html: list[str] = []
    for i, feature in enumerate(KEY_FEATURES):
        item = calc_by_feature.get(feature)
        if not item:
            continue
        title = _feature_title(feature)
        desc = _feature_desc(feature)
        formula = FEATURE_HELP.get(feature, {}).get("formula", item.get("계산 과정", "-"))
        value = item.get("값", "-")
        calc = item.get("계산 과정", "-")
        tooltip_html = (
            '<span class="dto1-tooltip" aria-label="설명 보기">i'
            f'<span class="dto1-tooltip-text">{escape(desc)}</span>'
            '</span>'
            if desc
            else ""
        )
        # 첫 행은 feature명이 왼쪽(밴드가 오른쪽)에서 시작하도록 교대
        reverse_class = " reverse" if i % 2 == 0 else ""
        rows_html.append(
            f'<div class="feature-band-row{reverse_class}">'
            '<div class="feature-band">'
            f'<div class="feature-band-label">{escape(title)}{tooltip_html}</div>'
            f'<div class="feature-band-value">{escape(str(value))}</div>'
            '<div class="feature-band-sub">공식</div>'
            f'<div class="feature-band-text">{escape(formula)}</div>'
            '<div class="feature-band-sub">현재 시점 계산</div>'
            f'<div class="feature-band-text">{escape(calc)} = {escape(str(value))}</div>'
            '</div>'
            '<div class="feature-band-connector"><span class="knot"></span><span class="line"></span></div>'
            f'<div class="feature-band-name">{escape(feature)}</div>'
            '</div>'
        )
    st.markdown("".join(rows_html), unsafe_allow_html=True)


def render_feature_engineering_panel(
    row: pd.Series,
    features: pd.DataFrame,
    dto5_sequence: list[dict],
) -> None:
    render_panel_banner(2, "Feature Engineering Panel", "입력값을 모델이 판단할 수 있는 1분 단위 feature로 변환하는 과정을 보여주는 panel")

    calc_rows = build_feature_calculations(row)
    calc_by_feature = {item["feature"]: item for item in calc_rows}

    render_subsection("F1 시나리오에 사용되는 대표 Feature")
    st.markdown(
        '<div class="panel-description">F1은 "이 사람이 평소보다 힘들어하는가"를 판단합니다. '
        '그래서 심박 절대값이 아니라 개인 기준 대비 비율(ratio, z)로 변환합니다.</div>',
        unsafe_allow_html=True,
    )
    _render_feature_bands(calc_by_feature)

    st.markdown('<div class="feature-table-gap"></div>', unsafe_allow_html=True)
    with st.expander("전체 feature table 보기"):
        st.markdown(
            '<div class="panel-description">왼쪽 index 0~115는 산행 중 116개의 1분 시점을 의미하고, 20 feature는 모델 입력으로 사용하는 20개 컬럼을 의미합니다.</div>',
            unsafe_allow_html=True,
        )
        st.dataframe(features, use_container_width=True)


def render_time_series_section(
    row: pd.Series,
    features: pd.DataFrame,
    dto5_sequence: list[dict],
) -> None:
    """시간 흐름 그래프 섹션. [1] DTO-1 Input Panel에서 호출한다."""
    render_subsection("시간별 데이터 흐름 그래프")

    n = min(len(features), len(dto5_sequence))
    graph_df = features.iloc[:n].copy()
    # 시간축: 실측 산출물은 ts(UTC -> KST), 학습셋은 원본 minute_idx(산행 경과 분)를 그대로 쓴다.
    has_ts = "ts" in graph_df.columns
    if has_ts:
        graph_df["ts_kst"] = [to_kst_timestamp(x) for x in graph_df["ts"]]
        x_axis_label = "한국시간"
    else:
        graph_df["ts_kst"] = (
            graph_df["minute_idx"] if "minute_idx" in graph_df.columns else pd.Series(range(n))
        )
        x_axis_label = "산행 경과(분)"

    graph_df["risk_representative"] = [
        get_nested(x, ["risk", "representative"], 0)
        for x in dto5_sequence[:n]
    ]

    graph_df["fatigue_state"] = [
        get_nested(x, ["fatigue", "state"], "없음")
        for x in dto5_sequence[:n]
    ]

    if has_ts:
        selected_ts = to_kst_timestamp(row.get("ts"))
        format_kst_text = selected_ts.strftime("%Y-%m-%d %H:%M") + " KST" if selected_ts is not None else ""
        axis_title = f"현재 시점: {format_kst_text}" if selected_ts is not None else x_axis_label
    else:
        minute = row.get("minute_idx")
        selected_ts = None if minute is None or pd.isna(minute) else int(minute)
        axis_title = f"현재 시점: {selected_ts}분차" if selected_ts is not None else x_axis_label

    # 현재 시점 표시 색: [1] 말풍선의 연한 초록과 통일
    SELECTED_LINE_COLOR = "#a3b285"

    def add_selected_line(fig):
        if selected_ts is not None:
            fig.add_vline(x=selected_ts, line_dash="dash", line_color=SELECTED_LINE_COLOR)
        fig.update_xaxes(
            title_text=axis_title,
            title_font=dict(color=SELECTED_LINE_COLOR),
        )
        return style_feature_fig(fig)

    tab1, tab2, tab3, tab4 = st.tabs(["심박수", "SpO2", "위험도", "걸음/속도"])

    with tab1:
        fig_hr = px.line(
            graph_df,
            x="ts_kst",
            y="hr_mean_bpm",
            title="시간별 평균 심박수 변화",
            labels={"ts_kst": x_axis_label, "hr_mean_bpm": "평균 심박수(bpm)"},
        )
        st.plotly_chart(add_selected_line(fig_hr), use_container_width=True)

    with tab2:
        fig_spo2 = px.line(
            graph_df,
            x="ts_kst",
            y="spo2_min_pct",
            title="시간별 SpO2 변화",
            labels={"ts_kst": x_axis_label, "spo2_min_pct": "SpO2(%)"},
        )
        st.plotly_chart(add_selected_line(fig_spo2), use_container_width=True)

    with tab3:
        fig_risk = px.line(
            graph_df,
            x="ts_kst",
            y="risk_representative",
            title="시간별 대표 위험도 변화",
            labels={"ts_kst": x_axis_label, "risk_representative": "대표 위험도"},
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
                labels={"ts_kst": x_axis_label, "steps_1min": "걸음 수"},
            )
            st.plotly_chart(add_selected_line(fig_steps), use_container_width=True)

        with col_b:
            fig_speed = px.line(
                graph_df,
                x="ts_kst",
                y="speed_mean_mpm",
                title="시간별 평균 속도",
                labels={"ts_kst": x_axis_label, "speed_mean_mpm": "속도(m/min)"},
            )
            st.plotly_chart(add_selected_line(fig_speed), use_container_width=True)