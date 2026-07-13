# 시나리오 레지스트리.
# 앱 시작 시에는 가벼운 메타데이터만 import하고,
# 시나리오 페이지 모듈은 해당 시나리오가 선택된 뒤에 import

from __future__ import annotations

from pathlib import Path

from core.contracts import ScenarioDefinition, ScenarioSourceSpec, SourceCandidates

DASHBOARD_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = DASHBOARD_DIR.parent


def _paths(*relative_paths: str) -> tuple[Path, ...]:
    return tuple(REPO_ROOT / relative_path for relative_path in relative_paths)


F1_SOURCE = ScenarioSourceSpec(
    scenario_id="F1",
    features=SourceCandidates(
        env_var="SAFE_DASHBOARD_F1_FEATURES",
        candidates=_paths(
            "Input/F1/outputs/fatigue_minute_features.csv",
            "Input/F1/outputs/features.csv",
        ),
        required=True,
    ),
    inference=SourceCandidates(
        env_var="SAFE_DASHBOARD_F1_DTO5",
        candidates=_paths(
            "Input/F1/outputs/dto5_sequence.json",
            "Model/F1/outputs/dto5_sequence.json",
            "Model/outputs/F1/dto5_sequence.json",
        ),
        required=True,
    ),
    report=SourceCandidates(
        env_var="SAFE_DASHBOARD_F1_REPORT",
        candidates=_paths(
            "Input/F1/outputs/validation_report.json",
            "Model/F1/outputs/validation_report.json",
        ),
        required=False,
    ),
    explanation=SourceCandidates(
        env_var="SAFE_DASHBOARD_F1_EXPLANATION",
        candidates=_paths(
            "Model/F1/outputs/explanation.json",
            "Model/outputs/F1/explanation.json",
            "Input/F1/outputs/explanation.json",
        ),
        required=False,
    ),
)

A1_SOURCE = ScenarioSourceSpec(
    scenario_id="A1",
    features=SourceCandidates(
        env_var="SAFE_DASHBOARD_A1_FEATURES",
        candidates=_paths(
            "Input/A1/outputs/a1_minute_features.csv",
            "Input/A1/outputs/a1_features.csv",
            "Input/A1/outputs/features.csv",
        ),
        required=True,
    ),
    inference=SourceCandidates(
        env_var="SAFE_DASHBOARD_A1_DTO5",
        candidates=_paths(
            "Model/A1/outputs/dto5_a1_sequence.json",
            "Model/A1/outputs/dto5_sequence.json",
            "Input/A1/outputs/dto5_a1_sequence.json",
            "Input/A1/outputs/dto5_sequence.json",
        ),
        required=True,
    ),
    report=SourceCandidates(
        env_var="SAFE_DASHBOARD_A1_REPORT",
        candidates=_paths(
            "Input/A1/outputs/validation_report.json",
            "Model/A1/outputs/validation_report.json",
        ),
        required=False,
    ),
    explanation=SourceCandidates(
        env_var="SAFE_DASHBOARD_A1_EXPLANATION",
        candidates=_paths(
            "Model/A1/outputs/explanation.json",
            "Input/A1/outputs/explanation.json",
        ),
        required=False,
    ),
)

SCENARIOS: dict[str, ScenarioDefinition] = {
    "A1": ScenarioDefinition("A1", "낭떠러지 및 낙석 위험 구역 접근", "scenarios.a1.page", True, A1_SOURCE),
    "A2": ScenarioDefinition("A2", "야생동물 출몰 지역 진입", None, False, None),
    "A5": ScenarioDefinition("A5", "과거 사고 다수 발생 지역 진입", None, False, None),
    "F1": ScenarioDefinition("F1", "피로 및 심박 이상 감지", "scenarios.f1.page", True, F1_SOURCE),
    "F2": ScenarioDefinition("F2", "위험 점수 임계치 초과", None, False, None),
    "F3": ScenarioDefinition("F3", "일몰 시간 임박", None, False, None),
    "F4": ScenarioDefinition("F4", "산행 코스 재추천", None, False, None),
    "E1": ScenarioDefinition("E1", "복합 이상 감지 + 무응답", None, False, None),
    "E2": ScenarioDefinition("E2", "기상 급변 + 상태 이상", None, False, None),
}


def get_scenario(scenario_id: str | None) -> ScenarioDefinition:
    normalized = (scenario_id or "F1").upper()
    return SCENARIOS.get(normalized, SCENARIOS["F1"])
