# A1 대시보드 제목 및 시나리오 요약 (시나리오 헤더 골격 호출)

from __future__ import annotations

from components.panel_kit import (
    render_scenario_header,
)
from scenarios.a1.mapper import A1Context
from scenarios.a1.formatting import _safe


def render_title_panel(context: A1Context) -> None:
    status = "외부 산출물 연결됨" if context.has_feature and context.has_dto5 else "Input / Model 연결 대기"
    render_scenario_header(
        eyebrow="A1 SCENARIO DASHBOARD",
        title="A1 시나리오: 낭떠러지 및 낙석 위험 구역 접근",
        summary_html=(
            "사용자의 현재 위치와 위험 POI, 지정 등산로 이탈, 경사 정보를 함께 확인합니다.<br/>"
            "A1 모델은 위험 지형 접근 여부를 판정하고 DTO-5 alerts[]에 경고 위치와 우회 가능 여부를 반환합니다.<br/>"
            "생체 정보는 공간 및 지형 판단을 보조하는 입력으로 사용되며 최종 값은 외부 Input 및 Model 산출물에서 받아 표시합니다."
        ),
        notice_html=(
            "F1에서 사용한 색상, 글씨 크기, 카드, 7개 패널 순서를 그대로 유지한 A1 화면입니다.<br/>"
            f"현재 연결 상태: <b>{_safe(status)}</b><br/>"
            "Dashboard 내부에는 mock CSV 및 JSON이나 A1 모델 계산 로직을 두지 않습니다."
        ),
    )
