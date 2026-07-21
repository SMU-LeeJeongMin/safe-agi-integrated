# E2 대시보드 제목 및 시나리오 요약 (골격)

from __future__ import annotations

from components.panel_kit import render_scenario_header


def render_title_panel() -> None:
    render_scenario_header(
        eyebrow="E2 SCENARIO DASHBOARD",
        title="E2 시나리오: 기상 급변 + 상태 이상",
        summary_html=(
            "기상 변화 데이터와 사용자의 생체 신호를 동시에 감시해 복합 위험 상황을 분석합니다.<br/>"
            "기상 악화와 생체 이상이 동시에 발생하면 두 요인을 결합한 복합 위험 점수로 임계치 초과 여부를 판정합니다.<br/>"
            "AI는 위험 수준에 따라 대기 및 하산 권고에서 시작해, 응답이 확인되지 않으면 E-Call을 자동 발동합니다."
        ),
    )
