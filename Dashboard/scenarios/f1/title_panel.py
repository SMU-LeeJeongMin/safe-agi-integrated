# 대시보드 제목 및 F1 시나리오 요약

import pandas as pd
import streamlit as st

from components.panel_kit import render_scenario_header


def render_title_panel(row: pd.Series | None = None, dto5: dict | None = None, report: dict | None = None) -> None:
    del row, dto5, report
    render_scenario_header(
        eyebrow="F1 SCENARIO DASHBOARD",
        title="F1 시나리오: 피로 및 심박 이상 감지",
        summary_html=(
            "산행 세션에서 수집되는 심박, 혈중산소, 걸음 및 이동 데이터를 분 단위로 분석합니다.<br/>"
            "심박 판정 기준은 개인 프로필 기반 baseline을 적용하며, 프로필 미등록 시 국민건강영양조사 통계 기반 연령대별 기준(연령 미상 시 성인 전체 기준)으로 대체합니다.<br/>"
            "AI는 생체, 위치, 기상, 사고 이력 데이터를 종합해 피로 및 탈진 위험을 감지하고 가장 가까운 쉼터에서의 휴식을 권고합니다."
        ),
    )
