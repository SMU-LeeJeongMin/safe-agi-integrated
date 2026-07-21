# A5 대시보드 제목 및 시나리오 요약 (골격)

from __future__ import annotations

from components.panel_kit import render_scenario_header


def render_title_panel() -> None:
    render_scenario_header(
        eyebrow="A5 SCENARIO DASHBOARD",
        title="A5 시나리오: 과거 사고 다수 발생 지역 진입",
        summary_html=(
            "사용자의 현재 경로를 과거 산악 사고 이력 데이터와 대조해 사고 다발 구간 진입을 감지합니다.<br/>"
            "구간별 사고 빈도와 유형을 기반으로 산출한 사고 위험도(accident prior)를 판정에 활용합니다.<br/>"
            "AI는 사고 다발 구간 진입 전에 미리 주의를 안내해 사용자가 경계심을 갖고 통과하도록 돕습니다."
        ),
    )
