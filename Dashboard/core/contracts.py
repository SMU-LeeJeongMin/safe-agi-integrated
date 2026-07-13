# Dashboard 내부에서만 사용하는 시나리오 라우팅과 외부 산출물 계약 정의

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class SourceCandidates:
    """외부 Input/Model 산출물 하나에 대한 후보 경로 목록."""

    env_var: str
    candidates: tuple[Path, ...] = ()
    required: bool = False


@dataclass(frozen=True)
class ScenarioSourceSpec:
    scenario_id: str
    features: SourceCandidates
    inference: SourceCandidates
    report: SourceCandidates | None = None
    # 오프라인 가중치 설명 산출물 (모델 학습 시 1회 export, 대시보드는 읽기만 함)
    explanation: SourceCandidates | None = None


@dataclass(frozen=True)
class ScenarioDefinition:
    scenario_id: str
    title: str
    renderer_module: str | None
    enabled: bool
    source_spec: ScenarioSourceSpec | None = None


@dataclass(frozen=True)
class ResolvedSource:
    kind: str
    env_var: str
    required: bool
    configured_path: Path | None
    resolved_path: Path | None
    candidates: tuple[Path, ...]

    @property
    def exists(self) -> bool:
        return self.resolved_path is not None


@dataclass
class ScenarioPayload:
    """선택된 시나리오 하나에 대해 로드된 산출물 묶음."""

    scenario_id: str
    features: pd.DataFrame = field(default_factory=pd.DataFrame)
    dto5_sequence: list[dict[str, Any]] = field(default_factory=list)
    report: dict[str, Any] = field(default_factory=dict)
    explanation: dict[str, Any] = field(default_factory=dict)
    sources: dict[str, ResolvedSource] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def item_count(self) -> int:
        if not self.features.empty and self.dto5_sequence:
            return min(len(self.features), len(self.dto5_sequence))
        if not self.features.empty:
            return len(self.features)
        return len(self.dto5_sequence)

    @property
    def connected(self) -> bool:
        required = [source for source in self.sources.values() if source.required]
        return bool(required) and all(source.exists for source in required)

    def row_at(self, index: int) -> pd.Series:
        if self.features.empty:
            return pd.Series(dtype="object")
        safe_index = min(max(int(index), 0), len(self.features) - 1)
        return self.features.iloc[safe_index]

    def dto5_at(self, index: int) -> dict[str, Any]:
        if not self.dto5_sequence:
            return {}
        safe_index = min(max(int(index), 0), len(self.dto5_sequence) - 1)
        value = self.dto5_sequence[safe_index]
        return value if isinstance(value, dict) else {}
