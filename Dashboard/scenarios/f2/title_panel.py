# F2 대시보드 제목 및 시나리오 요약 (골격)

from __future__ import annotations

from components.panel_kit import render_scenario_header


def render_title_panel() -> None:
    render_scenario_header(
        eyebrow="F2 SCENARIO DASHBOARD",
        title="F2 시나리오: 위험 점수 임계치 초과",
        summary_html=(
            "심박, 피로, 스트레스, 환경 센서 데이터를 융합해 복합 위험 점수를 분 단위로 산출합니다.<br/>"
            "위험 임계치는 고정값이 아니라 메타러닝으로 사용자별 평소 패턴에 맞게 자동 보정된 개인화 기준을 적용합니다.<br/>"
            "AI는 개인 임계치 초과 시점을 감지해 속도 조절과 휴식을 권고하고 회복 중심 산행을 유도합니다."
        ),
    )
