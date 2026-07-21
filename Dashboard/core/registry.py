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

def _skeleton_source(scenario_id: str) -> ScenarioSourceSpec:
    """골격 시나리오용 표준 산출물 경로 규격.

    파일이 아직 없으면 페이지는 '연결 대기' 안내와 placeholder panel을 표시하고,
    담당자가 Input/Model 산출물을 표준 경로에 두면 같은 화면 구조에 값이 연결된다.
    """
    lower = scenario_id.lower()
    return ScenarioSourceSpec(
        scenario_id=scenario_id,
        features=SourceCandidates(
            env_var=f"SAFE_DASHBOARD_{scenario_id}_FEATURES",
            candidates=_paths(
                f"Input/{scenario_id}/outputs/{lower}_minute_features.csv",
                f"Input/{scenario_id}/outputs/features.csv",
            ),
            required=True,
        ),
        inference=SourceCandidates(
            env_var=f"SAFE_DASHBOARD_{scenario_id}_DTO5",
            candidates=_paths(
                f"Model/{scenario_id}/outputs/dto5_sequence.json",
                f"Input/{scenario_id}/outputs/dto5_sequence.json",
            ),
            required=True,
        ),
        report=SourceCandidates(
            env_var=f"SAFE_DASHBOARD_{scenario_id}_REPORT",
            candidates=_paths(f"Input/{scenario_id}/outputs/validation_report.json"),
            required=False,
        ),
    )


SCENARIOS: dict[str, ScenarioDefinition] = {
    "A1": ScenarioDefinition("A1", "낭떠러지 및 낙석 위험 구역 접근", "scenarios.a1.page", True, A1_SOURCE),
    "A2": ScenarioDefinition("A2", "야생동물 출몰 지역 진입", "scenarios.a2.page", True, _skeleton_source("A2")),
    "A5": ScenarioDefinition("A5", "과거 사고 다수 발생 지역 진입", "scenarios.a5.page", True, _skeleton_source("A5")),
    "F1": ScenarioDefinition("F1", "피로 및 심박 이상 감지", "scenarios.f1.page", True, F1_SOURCE),
    "F2": ScenarioDefinition("F2", "위험 점수 임계치 초과", "scenarios.f2.page", True, _skeleton_source("F2")),
    "F3": ScenarioDefinition("F3", "일몰 시간 임박", "scenarios.f3.page", True, _skeleton_source("F3")),
    "F4": ScenarioDefinition("F4", "산행 코스 재추천", "scenarios.f4.page", True, _skeleton_source("F4")),
    "E1": ScenarioDefinition("E1", "복합 이상 감지 + 무응답", "scenarios.e1.page", True, _skeleton_source("E1")),
    "E2": ScenarioDefinition("E2", "기상 급변 + 상태 이상", "scenarios.e2.page", True, _skeleton_source("E2")),
}


def get_scenario(scenario_id: str | None) -> ScenarioDefinition:
    normalized = (scenario_id or "F1").upper()
    return SCENARIOS.get(normalized, SCENARIOS["F1"])
