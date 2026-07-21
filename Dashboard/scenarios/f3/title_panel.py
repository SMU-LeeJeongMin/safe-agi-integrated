# F3 대시보드 제목 및 시나리오 요약 (골격)

from __future__ import annotations

from components.panel_kit import render_scenario_header


def render_title_panel() -> None:
    render_scenario_header(
        eyebrow="F3 SCENARIO DASHBOARD",
        title="F3 시나리오: 일몰 시간 임박",
        summary_html=(
            "현재 위치, 이동 속도, 남은 경로와 해당 지역의 일몰 시각을 함께 분석합니다.<br/>"
            "남은 일광 시간과 현재 페이스 기준 하산 소요 시간을 비교해 일몰 전 하산 가능 여부를 판정합니다.<br/>"
            "AI는 일몰 내 하산이 어렵다고 판단되면 하산을 권고하고 최단 하산 경로를 안내해 야간 산행을 예방합니다."
        ),
    )
