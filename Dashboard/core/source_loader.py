# 선택된 시나리오의 외부 Input/Model 산출물만 로드

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from core.contracts import ResolvedSource, ScenarioPayload, ScenarioSourceSpec, SourceCandidates
from core.registry import REPO_ROOT


def _resolve_env_path(raw_path: str) -> Path:
    path = Path(raw_path).expanduser()
    return path if path.is_absolute() else (REPO_ROOT / path).resolve()


def resolve_source(kind: str, spec: SourceCandidates) -> ResolvedSource:
    env_value = os.getenv(spec.env_var, "").strip()
    configured = _resolve_env_path(env_value) if env_value else None

    if configured is not None:
        resolved = configured if configured.exists() else None
        return ResolvedSource(
            kind=kind,
            env_var=spec.env_var,
            required=spec.required,
            configured_path=configured,
            resolved_path=resolved,
            candidates=spec.candidates,
        )

    resolved = next((candidate for candidate in spec.candidates if candidate.exists()), None)
    configured_path = spec.candidates[0] if spec.candidates else None
    return ResolvedSource(
        kind=kind,
        env_var=spec.env_var,
        required=spec.required,
        configured_path=configured_path,
        resolved_path=resolved,
        candidates=spec.candidates,
    )


def _fingerprint(path: Path) -> tuple[int, int]:
    stat = path.stat()
    return stat.st_mtime_ns, stat.st_size


@st.cache_data(show_spinner=False, max_entries=18)
def _read_feature_file(path_text: str, fingerprint: tuple[int, int]) -> pd.DataFrame:
    del fingerprint
    path = Path(path_text)
    suffix = path.suffix.lower()

    if suffix == ".csv":
        frame = pd.read_csv(path)
    elif suffix == ".jsonl":
        frame = pd.read_json(path, lines=True)
    elif suffix == ".json":
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            for key in ("features", "rows", "items", "data", "results"):
                if isinstance(raw.get(key), list):
                    raw = raw[key]
                    break
        frame = pd.DataFrame(raw)
    else:
        raise ValueError(f"지원하지 않는 feature 파일 형식입니다: {suffix}")

    for column in ("ts", "timestamp", "trigger_ts", "recorded_at"):
        if column in frame.columns:
            frame[column] = pd.to_datetime(frame[column], errors="coerce", utc=True, format="mixed")
    return frame


@st.cache_data(show_spinner=False, max_entries=40)
def _read_json_file(path_text: str, fingerprint: tuple[int, int]) -> Any:
    del fingerprint
    return json.loads(Path(path_text).read_text(encoding="utf-8"))


def _extract_dto5_sequence(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, list):
        return [dict(item) for item in raw if isinstance(item, dict)]

    if not isinstance(raw, dict):
        return []

    for key in ("results", "data", "items", "sequence", "dto5_sequence", "inference_results"):
        value = raw.get(key)
        if isinstance(value, list):
            return [dict(item) for item in value if isinstance(item, dict)]

    if raw.get("type") in {"inference_result", "processing", "error"} or "alerts" in raw:
        return [dict(raw)]
    return []


def load_scenario_payload(spec: ScenarioSourceSpec) -> ScenarioPayload:
    payload = ScenarioPayload(scenario_id=spec.scenario_id)

    feature_source = resolve_source("features", spec.features)
    dto5_source = resolve_source("dto5", spec.inference)
    report_source = resolve_source("report", spec.report) if spec.report else None
    explanation_source = resolve_source("explanation", spec.explanation) if spec.explanation else None

    payload.sources["features"] = feature_source
    payload.sources["dto5"] = dto5_source
    if report_source is not None:
        payload.sources["report"] = report_source
    if explanation_source is not None:
        payload.sources["explanation"] = explanation_source

    if feature_source.resolved_path is not None:
        try:
            payload.features = _read_feature_file(
                str(feature_source.resolved_path),
                _fingerprint(feature_source.resolved_path),
            )
        except Exception as exc: 
            payload.errors.append(f"Feature 파일을 읽지 못했습니다: {exc}")
    elif feature_source.required:
        payload.warnings.append(
            f"{spec.scenario_id} Feature 파일 연결 대기: {feature_source.env_var} 또는 Input/{spec.scenario_id}/outputs 경로를 확인하세요."
        )

    if dto5_source.resolved_path is not None:
        try:
            raw = _read_json_file(str(dto5_source.resolved_path), _fingerprint(dto5_source.resolved_path))
            payload.dto5_sequence = _extract_dto5_sequence(raw)
            if not payload.dto5_sequence:
                payload.errors.append("DTO-5 파일에서 추론 결과 배열을 찾지 못했습니다.")
        except Exception as exc:
            payload.errors.append(f"DTO-5 파일을 읽지 못했습니다: {exc}")
    elif dto5_source.required:
        payload.warnings.append(
            f"{spec.scenario_id} DTO-5 파일 연결 대기: {dto5_source.env_var} 또는 Model/{spec.scenario_id}/outputs 경로를 확인하세요."
        )

    if report_source is not None and report_source.resolved_path is not None:
        try:
            raw_report = _read_json_file(
                str(report_source.resolved_path),
                _fingerprint(report_source.resolved_path),
            )
            payload.report = dict(raw_report) if isinstance(raw_report, dict) else {}
        except Exception as exc:
            payload.warnings.append(f"검증 리포트를 읽지 못했습니다: {exc}")

    if explanation_source is not None and explanation_source.resolved_path is not None:
        try:
            raw_explanation = _read_json_file(
                str(explanation_source.resolved_path),
                _fingerprint(explanation_source.resolved_path),
            )
            payload.explanation = dict(raw_explanation) if isinstance(raw_explanation, dict) else {}
        except Exception as exc:
            payload.warnings.append(f"가중치 설명 산출물을 읽지 못했습니다: {exc}")

    if not payload.features.empty and payload.dto5_sequence and len(payload.features) != len(payload.dto5_sequence):
        payload.warnings.append(
            f"Feature 행 수({len(payload.features)})와 DTO-5 개수({len(payload.dto5_sequence)})가 다릅니다. 공통 범위까지만 표시합니다."
        )

    return payload
