# A2 대시보드 제목 및 시나리오 요약 (골격)

from __future__ import annotations

from components.panel_kit import render_scenario_header


def render_title_panel() -> None:
    render_scenario_header(
        eyebrow="A2 SCENARIO DASHBOARD",
        title="A2 시나리오: 야생동물 출몰 지역 진입",
        summary_html=(
            "사용자의 위치를 야생동물 출몰 이력 구간과 대조하고 이동 패턴을 함께 분석합니다.<br/>"
            "출몰 구간 진입 여부와 평소와 다른 이동 패턴(급정지, 경로 이탈 등)을 결합해 위험 수준을 판정합니다.<br/>"
            "AI는 출몰 구간 진입 시 사전 경고하고, 이상 징후가 겹치면 경고 수준을 높여 안전한 이동을 안내합니다."
        ),
    )
