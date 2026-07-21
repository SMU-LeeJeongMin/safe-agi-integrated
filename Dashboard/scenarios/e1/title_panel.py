# E1 대시보드 제목 및 시나리오 요약 (골격)

from __future__ import annotations

from components.panel_kit import render_scenario_header


def render_title_panel() -> None:
    render_scenario_header(
        eyebrow="E1 SCENARIO DASHBOARD",
        title="E1 시나리오: 복합 이상 감지 + 무응답",
        summary_html=(
            "심박 급변, 충격(낙상), 장시간 움직임 없음 등 긴급 트리거 신호를 실시간으로 감시합니다.<br/>"
            "이상 신호가 2개 이상 동시 발생하면 사고 가능성으로 판정하고 사용자 응답 여부를 단계적으로 확인합니다.<br/>"
            "AI는 응답이 없으면 긴급 연락처 알림을 거쳐 119 자동 신고까지 단계적으로 에스컬레이션해 골든타임을 확보합니다."
        ),
    )
