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
            "실 safe_db에 적재된 청계산 산행 세션(여름 오전)을 분 단위로 분석합니다.<br/>"
            "사용자 프로필이 미등록(null)이라 판정 기준은 표준 페르소나(국건영 60대 남성, MaxHR 155)를 적용했습니다.<br/>"
            "AI는 워치, GPS, 기상, 사고 데이터를 종합해 피로 및 탈진 위험을 감지하고 가까운 쉼터에서 휴식을 권고합니다."
        ),
        notice_html=(
            "이번 대시보드는 실 safe_db 세션 산출물(Input/F1/outputs)을 기준으로 표시합니다.<br/>"
            "이후 다른 S·A·F·E 시나리오도 동일한 패널 흐름으로 확장하고, "
            "다음 단계에서 실시간 API 연동을 연결할 예정입니다."
        ),
    )
