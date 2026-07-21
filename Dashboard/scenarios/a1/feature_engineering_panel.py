# [2] Feature Engineering Panel — A1 feature 카드와 시계열, 지도

from __future__ import annotations

from typing import Mapping

import pandas as pd
import plotly.express as px
import streamlit as st
from scenarios.common import render_panel_placeholder

from components.panel_kit import feature_card, render_panel_banner, render_subsection, render_soft_notice

from core.contracts import ScenarioPayload
from scenarios.a1.mapper import A1Context, parse_json_value, row_value
from scenarios.a1.formatting import _fmt, _fmt_bool, _safe
from scenarios.a1.a1_map import render_a1_map
from utils.time_utils import to_kst_timestamp


def _feature_card_html(field: str, title: str, value: str, description: str, source: str) -> str:
    return feature_card(field=field, title=title, value=value, tooltip=description, box_label="출처", box_text=source)




def render_feature_engineering_panel(context: A1Context, payload: ScenarioPayload) -> None:
    row = context.row
    render_panel_banner(2, "Feature Engineering Panel", "Input 단계에서 산출된 위험 지점 거리, 지정로 이탈, 경사, 접근 상태를 확인하는 panel")
    # F1 디자인 이식 방향이 확정될 때까지 골격 시나리오와 동일한 자리표시로 둔다.
    # 기존 구현은 아래에 보존되어 있으며, 이 두 줄을 제거하면 복원된다.
    render_panel_placeholder("A1")
    return


    render_subsection("A1 시나리오에 사용되는 대표 Feature")
    cards = [
        ("dist_to_hazard_m", "위험 지점까지 거리", _fmt(row_value(row, "dist_to_hazard_m"), 1, " m"), "최근접 낭떠러지 및 낙석 POI까지의 거리", "Input/A1 feature"),
        ("off_trail_dist_m", "지정로 이탈 거리", _fmt(row_value(row, "off_trail_dist_m"), 1, " m"), "사용자 위치와 지정 등산로 사이 거리", "Input/A1 feature"),
        ("slope_deg", "현재 경사도", _fmt(row_value(row, "slope_deg"), 1, "°"), "GPX 및 고도 및 지형 파이프라인에서 전달된 경사도", "Input/A1 feature"),
        ("approaching_flag", "위험 지점 접근 여부", _fmt_bool(row_value(row, "approaching_flag"), "접근 중", "멀어지는 중"), "진행 방향과 위험 POI 방향을 비교한 외부 산출값", "Input/A1 feature"),
    ]
    columns = st.columns(4)
    for column, item in zip(columns, cards):
        with column:
            st.markdown(_feature_card_html(*item), unsafe_allow_html=True)

    st.markdown('<div class="feature-table-gap"></div>', unsafe_allow_html=True)
    render_subsection("사용자 위치와 위험 POI")
    render_a1_map(context)

    render_subsection("시간 흐름 그래프")
    st.markdown(
        '<div class="panel-description">그래프의 시간축은 한국시간(KST) 기준입니다. 회색 점선은 현재 선택한 시점을 의미합니다.</div>',
        unsafe_allow_html=True,
    )

    features = payload.features.copy()
    if features.empty:
        render_soft_notice("A1 Feature 시계열 파일이 연결되면 거리 및 이탈 및 경사 변화 그래프가 표시됩니다.")
    else:
        time_col = "ts" if "ts" in features.columns else "timestamp" if "timestamp" in features.columns else None
        if time_col:
            features["ts_kst"] = [to_kst_timestamp(value) for value in features[time_col]]
            x_col = "ts_kst"
        else:
            features["index"] = range(len(features))
            x_col = "index"

        selected_ts = to_kst_timestamp(row_value(row, "ts", "timestamp"))
        chart_specs = [
            ([name for name in ["dist_to_hazard_m", "off_trail_dist_m"] if name in features.columns], "거리 Feature 변화", "거리 (m)"),
            ([name for name in ["slope_deg", "accident_density"] if name in features.columns], "지형 및 사고 Feature 변화", "값"),
        ]
        for y_columns, title, y_title in chart_specs:
            if not y_columns:
                continue
            melted = features[[x_col, *y_columns]].melt(id_vars=x_col, var_name="feature", value_name="value")
            fig = px.line(melted, x=x_col, y="value", color="feature", markers=True, title=title)
            fig.update_layout(
                font=dict(size=16),
                title_font=dict(size=20),
                legend_font=dict(size=15),
                margin=dict(l=20, r=20, t=58, b=34),
                yaxis_title=y_title,
            )
            if selected_ts is not None and time_col:
                fig.add_vline(x=selected_ts, line_dash="dash", line_color="#98a2b3")
            st.plotly_chart(fig, use_container_width=True)

    with st.expander("전체 feature table 보기"):
        if payload.features.empty:
            st.caption("A1 Feature 파일이 아직 연결되지 않았습니다.")
        else:
            st.dataframe(payload.features, use_container_width=True)

    quality = parse_json_value(row_value(row, "missing_flags", "data_quality", "quality_flags"))
    with st.expander("Data Quality 상세 보기"):
        if isinstance(quality, Mapping):
            st.dataframe(
                pd.DataFrame([{"검증 항목": key, "결과": value} for key, value in quality.items()]),
                use_container_width=True,
                hide_index=True,
            )
        elif isinstance(quality, list):
            st.dataframe(pd.DataFrame(quality), use_container_width=True, hide_index=True)
        else:
            st.caption("Input 산출물에 품질 검증 필드가 연결되면 표시됩니다.")
