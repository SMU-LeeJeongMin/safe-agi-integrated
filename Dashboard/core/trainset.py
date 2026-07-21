# Input/<시나리오ID>/synth/ 학습셋 범용 리더

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from core.registry import REPO_ROOT
from core.source_loader import _fingerprint

# 세션 CSV의 메타 컬럼 (신호 컬럼 추론 시 제외 대상)
SESSION_META_COLUMNS = ("session_id", "persona_name", "age", "situation", "minute_idx")
# window CSV의 메타 컬럼
WINDOW_META_COLUMNS = (
    "window_id",
    "session_id",
    "persona_name",
    "age",
    "situation",
    "window_size",
    "start_min",
)

RISK_LABEL_TO_LEVEL = {"정상": 0, "주의": 1, "경고": 2, "위험": 3}
LEVEL_TO_RISK_LABEL = {v: k for k, v in RISK_LABEL_TO_LEVEL.items()}

TRAINSET_NOTE = (
    "학습셋 세션(Input/{scenario_id}/synth) 관찰 중: 위험도와 상태는 규칙 오라클 정답(y) 기준이며 "
    "모델 추론 결과가 아닙니다. 위치와 실측 시각 등 학습셋에 없는 항목은 표시되지 않습니다."
)
NO_LABELS_NOTE = "이 학습셋에는 정답 라벨(windows/)이 없어 신호 시계열만 표시합니다."


# ── 경로 탐색 ──────────────────────────────────────────────────────────

def trainset_root(scenario_id: str) -> Path:
    return REPO_ROOT / "Input" / scenario_id / "synth"


def _first_csv(directory: Path) -> Path | None:
    if not directory.is_dir():
        return None
    candidates = sorted(directory.glob("*.csv"))
    return candidates[0] if candidates else None


def sessions_csv(scenario_id: str) -> Path | None:
    return _first_csv(trainset_root(scenario_id) / "sessions")


def windows_csv(scenario_id: str) -> Path | None:
    return _first_csv(trainset_root(scenario_id) / "windows")


def available(scenario_id: str) -> bool:
    return sessions_csv(scenario_id) is not None


def _summary(directory: Path) -> dict[str, Any]:
    if not directory.is_dir():
        return {}
    for path in sorted(directory.glob("*summary*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                return raw
        except Exception:
            continue
    return {}


def sessions_summary(scenario_id: str) -> dict[str, Any]:
    return _summary(trainset_root(scenario_id) / "sessions")


def windows_summary(scenario_id: str) -> dict[str, Any]:
    return _summary(trainset_root(scenario_id) / "windows")


# ── 로딩 (캐시) ────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False, max_entries=12)
def _read_csv(path_text: str, fingerprint: tuple[int, int]) -> pd.DataFrame:
    del fingerprint
    return pd.read_csv(path_text)


def sessions_frame(scenario_id: str) -> pd.DataFrame:
    path = sessions_csv(scenario_id)
    if path is None:
        return pd.DataFrame()
    return _read_csv(str(path), _fingerprint(path))


@st.cache_data(show_spinner=False, max_entries=12)
def _read_minute_labels(path_text: str, fingerprint: tuple[int, int]) -> pd.DataFrame:
    """window 학습셋에서 분 단위(window_size == 1) 정답 행만 유지한다.

    window_size 컬럼이 없으면 전 행을 분 단위로 간주한다.
    """
    del fingerprint
    frame = pd.read_csv(path_text)
    if "window_size" in frame.columns:
        frame = frame[frame["window_size"] == 1].copy()
    sort_keys = [c for c in ("session_id", "start_min", "minute_idx") if c in frame.columns]
    if sort_keys:
        frame = frame.sort_values(sort_keys)
    return frame.reset_index(drop=True)


def minute_labels_frame(scenario_id: str) -> pd.DataFrame:
    path = windows_csv(scenario_id)
    if path is None:
        return pd.DataFrame()
    return _read_minute_labels(str(path), _fingerprint(path))


# ── 컬럼 의미 (summary 우선, 추론 폴백) ────────────────────────────────

def signal_columns(scenario_id: str) -> list[str]:
    declared = sessions_summary(scenario_id).get("signal_columns")
    frame = sessions_frame(scenario_id)
    if isinstance(declared, list) and declared:
        return [c for c in declared if c in frame.columns]
    return numeric_signal_columns(frame)


def numeric_signal_columns(frame: pd.DataFrame) -> list[str]:
    """메타를 제외한 수치 컬럼을 신호로 간주하는 폴백 추론."""
    if frame.empty:
        return []
    exclude = set(SESSION_META_COLUMNS) | set(WINDOW_META_COLUMNS)
    return [
        c
        for c in frame.columns
        if c not in exclude and pd.api.types.is_numeric_dtype(frame[c])
    ]


def y_columns(scenario_id: str) -> list[str]:
    declared = windows_summary(scenario_id).get("y_columns")
    frame = minute_labels_frame(scenario_id)
    if isinstance(declared, list) and declared:
        return [c for c in declared if c in frame.columns]
    return [c for c in frame.columns if c.startswith("y_")]


# ── 세션 접근 (원본 그대로) ────────────────────────────────────────────

def list_sessions(scenario_id: str) -> list[dict[str, Any]]:
    """세션 메타 목록. 필드는 원본 이름을 유지하고, 목록 표기용 label만 파생한다."""
    frame = sessions_frame(scenario_id)
    if frame.empty or "session_id" not in frame.columns:
        return []
    metas: list[dict[str, Any]] = []
    for session_id, group in frame.groupby("session_id", sort=True):
        head = group.iloc[0]
        persona = head.get("persona_name")
        metas.append(
            {
                "session_id": int(session_id),
                "persona_name": None if pd.isna(persona) else str(persona),
                "age": head.get("age"),
                "situation": None if pd.isna(head.get("situation")) else str(head.get("situation")),
                "rows": int(len(group)),
                "label": display_session_label(int(session_id), persona),
            }
        )
    return metas


def session_frame(scenario_id: str, session_id: int) -> pd.DataFrame:
    """세션 1개의 행을 원본 컬럼 그대로 반환한다 (분 순서 정렬만 수행)."""
    frame = sessions_frame(scenario_id)
    if frame.empty or "session_id" not in frame.columns:
        return pd.DataFrame()
    session = frame[frame["session_id"] == int(session_id)].copy()
    if "minute_idx" in session.columns:
        session = session.sort_values("minute_idx")
    return session.reset_index(drop=True)


def session_minute_labels(scenario_id: str, session_id: int) -> pd.DataFrame:
    labels = minute_labels_frame(scenario_id)
    if labels.empty or "session_id" not in labels.columns:
        return pd.DataFrame()
    return labels[labels["session_id"] == int(session_id)].reset_index(drop=True)


# ── 정답 라벨 -> DTO-5 투영 (팀 계약 구조로만 감싼다) ──────────────────

def _risk_level_and_label(value: Any) -> tuple[int | None, str | None]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None, None
    if isinstance(value, str):
        return RISK_LABEL_TO_LEVEL.get(value), value
    try:
        level = int(value)
        return level, LEVEL_TO_RISK_LABEL.get(level)
    except (TypeError, ValueError):
        return None, str(value)


def session_dto5(scenario_id: str, session_id: int) -> list[dict[str, Any]]:
    """분 단위 규칙 오라클 정답을 DTO-5 시퀀스로 투영한다.

    사용하는 y 컬럼: y_e1, y_e2, y_risk_level, y_fatigue_state (있는 것만).
    ts는 학습셋에 실측 시각이 없으므로 None으로 두며, 차트는 분 index로
    폴백 표기한다. minute 필드에 원본 start_min 또는 minute_idx를 싣는다.
    """
    rows = session_minute_labels(scenario_id, session_id)
    if rows.empty:
        return []

    sequence: list[dict[str, Any]] = []
    for _, row in rows.iterrows():
        e1 = row.get("y_e1")
        e2 = row.get("y_e2")
        scores = [round(float(v), 4) for v in (e1, e2) if v is not None and not pd.isna(v)]
        level, label = _risk_level_and_label(row.get("y_risk_level"))
        fatigue_state = row.get("y_fatigue_state")
        minute = row.get("start_min", row.get("minute_idx"))
        sequence.append(
            {
                "uuid": None,
                "ts": None,
                "minute": None if pd.isna(minute) else int(minute),
                "course_recommendation": None,
                "risk": {
                    "e1_biometric": scores[0] if len(scores) >= 1 else None,
                    "e2_combined": scores[1] if len(scores) >= 2 else None,
                    "representative": max(scores) if scores else None,
                    "level": level if level is not None else 0,
                    "label": label if label is not None else "-",
                    "source": "rule_oracle",
                },
                "fatigue": {
                    "state": None if pd.isna(fatigue_state) else str(fatigue_state),
                    "confidence": None,
                    "nearest_shelter": None,
                },
                "descent_warning": {
                    "required": False,
                    "reason": None,
                    "remaining_daylight_min": None,
                },
                "alerts": [],
            }
        )
    return sequence


# ── 표시용 파생 (데이터 가공 아님, 화면 문구 전용) ─────────────────────

def display_session_label(session_id: int, persona: Any) -> str:
    persona_text = None if persona is None or (isinstance(persona, float) and pd.isna(persona)) else str(persona)
    base = f"synth{int(session_id):02d}"
    return f"{base}_{persona_text}" if persona_text else base


def display_age_group(age: Any) -> str | None:
    """age 값(예: 30)을 화면 표기용 연령대 문구(예: '30대')로 만든다."""
    try:
        if age is None or pd.isna(age):
            return None
        decade = (int(age) // 10) * 10
    except (TypeError, ValueError):
        return None
    return f"{decade}대"


def trainset_note(scenario_id: str) -> str:
    return TRAINSET_NOTE.format(scenario_id=scenario_id)


def build_payload(scenario_id: str, session_id: int):
    """학습셋 세션 1개를 ScenarioPayload로 구성한다.

    monitor(세션 리스트)와 시나리오 페이지(사이드바 선택)가 공용으로 사용한다.
    신호는 원본 컬럼 그대로, 정답 라벨은 DTO-5 계약으로 투영해 싣는다.
    """
    from core.contracts import ScenarioPayload

    payload = ScenarioPayload(scenario_id=scenario_id)
    try:
        payload.features = session_frame(scenario_id, session_id)
    except Exception as exc:
        payload.errors.append(f"학습셋 세션 신호를 읽지 못했습니다: {exc}")
    try:
        payload.dto5_sequence = session_dto5(scenario_id, session_id)
    except Exception as exc:
        payload.errors.append(f"학습셋 정답 라벨을 읽지 못했습니다: {exc}")
    if not payload.dto5_sequence:
        payload.warnings.append(NO_LABELS_NOTE)
    elif not payload.features.empty and len(payload.features) != len(payload.dto5_sequence):
        payload.warnings.append(
            f"신호 행 수({len(payload.features)})와 정답 라벨 개수({len(payload.dto5_sequence)})가 다릅니다. 공통 범위까지만 표시합니다."
        )
    return payload