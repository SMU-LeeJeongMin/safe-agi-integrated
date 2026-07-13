# 선택된 시나리오의 페이지 모듈만 지연 import하는 로더

from __future__ import annotations

from importlib import import_module
from typing import Callable

from core.contracts import ScenarioDefinition, ScenarioPayload

Renderer = Callable[[ScenarioPayload, ScenarioDefinition], None]


def load_renderer(definition: ScenarioDefinition) -> Renderer:
    if not definition.renderer_module:
        raise ValueError(f"{definition.scenario_id} 시나리오 renderer가 아직 등록되지 않았습니다.")
    module = import_module(definition.renderer_module)
    renderer = getattr(module, "render", None)
    if not callable(renderer):
        raise AttributeError(f"{definition.renderer_module}.render 함수를 찾지 못했습니다.")
    return renderer
