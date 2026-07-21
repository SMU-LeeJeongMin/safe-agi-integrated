# F4 대시보드 제목 및 시나리오 요약 (골격)

from __future__ import annotations

from components.panel_kit import render_scenario_header


def render_title_panel() -> None:
    render_scenario_header(
        eyebrow="F4 SCENARIO DASHBOARD",
        title="F4 시나리오: 산행 코스 재추천",
        summary_html=(
            "산행 중 누적되는 생체 신호와 이동 기록으로 사용자의 현재 체력 상태와 컨디션을 추정합니다.<br/>"
            "코스 난이도, 남은 거리, 개인 체력 프로필을 함께 고려해 현재 상태에 적합한 코스를 재평가합니다.<br/>"
            "AI는 더 적합한 코스가 있으면 추천 목록(top3)을 반환하고, 사용자는 앱에서 코스를 선택해 경로를 변경할 수 있습니다."
        ),
    )
