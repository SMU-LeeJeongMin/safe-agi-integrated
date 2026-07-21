# E1 시나리오 (골격: panel 구현 전 placeholder 화면)

from __future__ import annotations

from core.contracts import ScenarioDefinition, ScenarioPayload
from scenarios.e1.title_panel import render_title_panel
from scenarios.common import render_skeleton_page


def render(payload: ScenarioPayload, definition: ScenarioDefinition) -> None:
    del definition
    render_skeleton_page(payload, "E1", render_title_panel)
