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
            "65세 남성 사용자가 여름 오후 청계산을 등산 중입니다.<br/>"
            "오르막 이후 심박수가 상승하고 이동량이 감소합니다.<br/>"
            "AI는 워치, GPS, 기상, 사고 데이터를 함께 분석해 피로 및 탈진 위험을 감지하고 가까운 쉼터에서 휴식을 권고합니다."
        ),
        notice_html=(
            "이번 대시보드는 F1 시나리오를 기준으로 구성한 데모입니다.<br/>"
            "이후 다른 S·A·F·E 시나리오도 동일한 패널 흐름으로 확장하고, "
            "다음 단계에서 실시간 API 연동과 DB 저장을 연결할 예정입니다."
        ),
    )
