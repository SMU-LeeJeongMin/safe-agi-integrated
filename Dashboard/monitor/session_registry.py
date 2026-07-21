# 실시간 모니터링용 다중 세션 탐색 및 로딩
#
# Dashboard는 Input/Model 산출물을 읽기만 한다 (레이어 원칙).
# 다중 세션 표준 경로 규격:
#   Input/<시나리오ID>/outputs/sessions/<세션ID>/
#     - dto5_sequence.json                (필수)
#     - <id>_minute_features.csv 등       (선택, FEATURE_CANDIDATES 참고)
# 위 경로에 세션 디렉터리가 없으면 기존 단일 산출물(레지스트리 후보 경로)을
# 세션 1건으로 취급한다. 담당자가 다중 세션을 규격에 맞춰 내보내는 순간
# 코드 수정 없이 리스트가 채워진다.

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from core.contracts import ScenarioPayload
from core.registry import REPO_ROOT, SCENARIOS
from core.source_loader import (
    _extract_dto5_sequence,
    _fingerprint,
    _read_feature_file,
    _read_json_file,
    load_scenario_payload,
    resolve_source,
)
from utils.explanation import RISK_CAUTION, RISK_DANGER, RISK_WARNING, to_float
from core import trainset


@dataclass(frozen=True)
class SessionEntry:
    scenario_id: str
    session_id: str
    features_path: Path | None
    dto5_path: Path
    from_sessions_dir: bool
    # Input/<ID>/synth 학습셋 세션이면 원본 session_id 정수 (아니면 None).
    # 학습셋 세션은 개별 파일이 아니라 통합 CSV에서 리더(core.trainset)로
    # 원본 컬럼 그대로 읽는다.
    synth_session_id: int | None = None

    @property
    def key(self) -> str:
        return f"{self.scenario_id}::{self.session_id}"

    @property
    def is_synth(self) -> bool:
        return self.synth_session_id is not None


def _feature_candidates(scenario_id: str) -> tuple[str, ...]:
    lower = scenario_id.lower()
    return (
        f"{lower}_minute_features.csv",
        "fatigue_minute_features.csv",
        "features.csv",
    )


@st.cache_data(show_spinner=False, max_entries=120)
def _peek_profile(path_text: str, fingerprint: tuple[int, int]) -> dict[str, Any]:
    """features 첫 행에서 세션 메타(uuid, 연령대)만 가볍게 읽는다."""
    del fingerprint
    try:
        head = pd.read_csv(path_text, nrows=1)
    except Exception:
        return {}
    if head.empty:
        return {}
    row = head.iloc[0]
    return {
        "uuid": str(row.get("uuid")) if pd.notna(row.get("uuid")) else None,
        "age_group": str(row.get("age_group")) if pd.notna(row.get("age_group")) else None,
    }


def _default_session_id(features_path: Path | None, scenario_id: str) -> str:
    if features_path is not None and features_path.exists():
        meta = _peek_profile(str(features_path), _fingerprint(features_path))
        if meta.get("uuid"):
            return str(meta["uuid"])
    return f"{scenario_id.lower()}_demo_user"


def discover_sessions(scenario_ids: list[str]) -> list[SessionEntry]:
    """선택한 시나리오들의 세션 목록을 표준 경로 규격으로 탐색한다."""
    entries: list[SessionEntry] = []
    for scenario_id in scenario_ids:
        seen_dto5: set[Path] = set()

        sessions_root = REPO_ROOT / "Input" / scenario_id / "outputs" / "sessions"
        if sessions_root.is_dir():
            for session_dir in sorted(p for p in sessions_root.iterdir() if p.is_dir()):
                dto5_path = session_dir / "dto5_sequence.json"
                if not dto5_path.exists():
                    continue
                features_path = next(
                    (session_dir / name for name in _feature_candidates(scenario_id) if (session_dir / name).exists()),
                    None,
                )
                entries.append(
                    SessionEntry(scenario_id, session_dir.name, features_path, dto5_path, True)
                )
                seen_dto5.add(dto5_path.resolve())

        definition = SCENARIOS.get(scenario_id)
        if definition is None or definition.source_spec is None:
            continue
        spec = definition.source_spec
        dto5_source = resolve_source("dto5", spec.inference)
        if dto5_source.resolved_path is None:
            continue
        if dto5_source.resolved_path.resolve() in seen_dto5:
            continue
        feature_source = resolve_source("features", spec.features)
        session_id = _default_session_id(feature_source.resolved_path, scenario_id)
        entries.append(
            SessionEntry(
                scenario_id,
                session_id,
                feature_source.resolved_path,
                dto5_source.resolved_path,
                False,
            )
        )

    # Input/<ID>/synth 학습셋 세션 (전 시나리오 공통 규격, 통합 CSV를 리더로 읽음).
    # 구 outputs/ 산출물이 삭제되어 표준 경로 세션이 비더라도 목록이 유지되고,
    # 이후 시나리오(A2, F4, E1 등)가 같은 구조로 산출되면 코드 수정 없이 노출된다.
    for scenario_id in scenario_ids:
        if not trainset.available(scenario_id):
            continue
        sessions_path = trainset.sessions_csv(scenario_id)
        labels_path = trainset.windows_csv(scenario_id) or sessions_path
        existing_keys = {entry.key for entry in entries}
        for meta in trainset.list_sessions(scenario_id):
            entry = SessionEntry(
                scenario_id=scenario_id,
                session_id=str(meta["label"]),
                features_path=sessions_path,
                dto5_path=labels_path,
                from_sessions_dir=False,
                synth_session_id=int(meta["session_id"]),
            )
            if entry.key not in existing_keys:
                entries.append(entry)
    return entries


def risk_grade(representative: float) -> str:
    if representative < RISK_CAUTION:
        return "정상"
    if representative < RISK_WARNING:
        return "주의"
    if representative < RISK_DANGER:
        return "경고"
    return "위험"


def session_snapshot(entry: SessionEntry, pos: int) -> dict[str, Any]:
    """세션 리스트 표시에 필요한 현재 수신 시점 상태 요약."""
    if entry.is_synth:
        return _synth_snapshot(entry, pos)
    try:
        raw = _read_json_file(str(entry.dto5_path), _fingerprint(entry.dto5_path))
        sequence = _extract_dto5_sequence(raw)
    except Exception:
        sequence = []
    total = len(sequence)
    safe_pos = min(max(int(pos), 0), total - 1) if total else 0
    representative = 0.0
    if total:
        risk = sequence[safe_pos].get("risk") or {}
        representative = to_float(risk.get("representative"))

    age_group = None
    if entry.features_path is not None and entry.features_path.exists():
        meta = _peek_profile(str(entry.features_path), _fingerprint(entry.features_path))
        age_group = meta.get("age_group")

    return {
        "total": total,
        "pos": safe_pos,
        "representative": representative,
        "grade": risk_grade(representative) if total else "-",
        "age_group": age_group or "미등록",
    }


def _synth_snapshot(entry: SessionEntry, pos: int) -> dict[str, Any]:
    """학습셋 세션용 리스트 요약. 위험도는 규칙 오라클 정답 기준."""
    try:
        sequence = trainset.session_dto5(entry.scenario_id, entry.synth_session_id)
    except Exception:
        sequence = []
    total = len(sequence)
    safe_pos = min(max(int(pos), 0), total - 1) if total else 0
    representative = 0.0
    if total:
        risk = sequence[safe_pos].get("risk") or {}
        representative = to_float(risk.get("representative"))

    age_group = None
    try:
        meta = next(
            (m for m in trainset.list_sessions(entry.scenario_id) if m["session_id"] == entry.synth_session_id),
            None,
        )
        if meta:
            age_group = trainset.display_age_group(meta.get("age"))
    except Exception:
        pass

    return {
        "total": total,
        "pos": safe_pos,
        "representative": representative,
        "grade": risk_grade(representative) if total else "-",
        "age_group": age_group or "미등록",
    }


def load_entry_payload(entry: SessionEntry) -> ScenarioPayload:
    """선택된 세션의 관찰용 payload를 만든다.

    기본 단일 산출물 세션은 기존 로더를 그대로 사용해 report 등 부가 산출물과
    경고 메시지 동작을 유지하고, sessions 디렉터리 세션은 필요한 두 파일만 읽는다.
    학습셋 세션은 통합 CSV를 원본 컬럼 그대로 읽고(core.trainset),
    정답 라벨만 DTO-5 계약 구조로 투영한다.
    """
    if entry.is_synth:
        return trainset.build_payload(entry.scenario_id, entry.synth_session_id)

    if not entry.from_sessions_dir:
        definition = SCENARIOS.get(entry.scenario_id)
        if definition is not None and definition.source_spec is not None:
            return load_scenario_payload(definition.source_spec)

    payload = ScenarioPayload(scenario_id=entry.scenario_id)
    if entry.features_path is not None and entry.features_path.exists():
        try:
            payload.features = _read_feature_file(
                str(entry.features_path), _fingerprint(entry.features_path)
            )
        except Exception as exc:
            payload.errors.append(f"세션 feature 파일을 읽지 못했습니다: {exc}")
    try:
        raw = _read_json_file(str(entry.dto5_path), _fingerprint(entry.dto5_path))
        payload.dto5_sequence = _extract_dto5_sequence(raw)
    except Exception as exc:
        payload.errors.append(f"세션 DTO-5 파일을 읽지 못했습니다: {exc}")

    if not payload.features.empty and payload.dto5_sequence and len(payload.features) != len(payload.dto5_sequence):
        payload.warnings.append(
            f"Feature 행 수({len(payload.features)})와 DTO-5 개수({len(payload.dto5_sequence)})가 다릅니다. 공통 범위까지만 표시합니다."
        )
    return payload
