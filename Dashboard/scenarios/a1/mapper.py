# 외부 필드 → 화면 값 연결만 수행

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Mapping

import pandas as pd


def as_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def nested(data: Mapping[str, Any] | None, *path: str) -> Any:
    current: Any = data
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def first_value(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        try:
            if pd.isna(value):
                continue
        except Exception:
            pass
        return value
    return None


def row_value(row: Mapping[str, Any], *names: str) -> Any:
    return first_value(*(row.get(name) for name in names))


def to_float(value: Any) -> float | None:
    try:
        if value is None or pd.isna(value):
            return None
        return float(value)
    except Exception:
        return None


def to_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y", "예", "접근", "approaching"}:
            return True
        if normalized in {"false", "0", "no", "n", "아니오", "이탈", "leaving"}:
            return False
    return None


def parse_json_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except Exception:
        return value


def _select_alert(dto5: Mapping[str, Any]) -> dict[str, Any]:
    alerts = dto5.get("alerts")
    if not isinstance(alerts, list):
        return {}

    candidates = [item for item in alerts if isinstance(item, Mapping)]
    for item in candidates:
        alert_type = str(item.get("type", "")).upper()
        if alert_type in {"A1", "APPROACH_WARNING"}:
            return dict(item)
    return dict(candidates[0]) if candidates else {}


def _normalize_contributions(value: Any) -> list[dict[str, Any]]:
    value = parse_json_value(value)
    rows: list[dict[str, Any]] = []
    if isinstance(value, Mapping):
        for feature, contribution in value.items():
            rows.append({"feature": str(feature), "contribution": contribution})
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, Mapping):
                rows.append(
                    {
                        "feature": item.get("feature") or item.get("name") or item.get("key") or "-",
                        "contribution": item.get("contribution")
                        if item.get("contribution") is not None
                        else item.get("importance", item.get("weight")),
                    }
                )
    return rows


def _normalize_rules(value: Any) -> list[dict[str, Any]]:
    value = parse_json_value(value)
    if isinstance(value, Mapping):
        return [{"rule": str(key), "result": result} for key, result in value.items()]
    if isinstance(value, list):
        rows: list[dict[str, Any]] = []
        for item in value:
            if isinstance(item, Mapping):
                rows.append(dict(item))
            else:
                rows.append({"rule": str(item)})
        return rows
    return []


@dataclass
class A1Context:
    row: dict[str, Any] = field(default_factory=dict)
    dto5: dict[str, Any] = field(default_factory=dict)
    alert: dict[str, Any] = field(default_factory=dict)
    location: dict[str, Any] = field(default_factory=dict)
    explanation: dict[str, Any] = field(default_factory=dict)
    personalization: dict[str, Any] = field(default_factory=dict)
    contributions: list[dict[str, Any]] = field(default_factory=list)
    rules: list[dict[str, Any]] = field(default_factory=list)
    spatial_score: float | None = None
    adjusted_score: float | None = None
    representative: float | None = None
    alert_level: Any = None
    detour_available: bool | None = None
    detour_extra_min: float | None = None

    @property
    def has_feature(self) -> bool:
        return bool(self.row)

    @property
    def has_dto5(self) -> bool:
        return bool(self.dto5)

    @property
    def reason_text(self) -> str:
        return str(
            first_value(
                self.explanation.get("reason"),
                self.explanation.get("summary"),
                self.alert.get("message"),
                "외부 A1 Model explanation 연결 대기",
            )
        )


def build_context(row: pd.Series | Mapping[str, Any], dto5: Mapping[str, Any] | None) -> A1Context:
    row_dict = row.to_dict() if isinstance(row, pd.Series) else dict(row or {})
    dto5_dict = dict(dto5 or {})
    alert = _select_alert(dto5_dict)
    location = as_mapping(alert.get("location"))
    explanation = as_mapping(dto5_dict.get("explanation"))
    personalization = as_mapping(
        first_value(dto5_dict.get("personalization"), dto5_dict.get("maml"), dto5_dict.get("personalized"))
    )

    spatial_score = to_float(
        first_value(
            nested(dto5_dict, "scores", "a1_spatial"),
            nested(dto5_dict, "scores", "a1"),
            nested(dto5_dict, "risk", "a1_spatial"),
            nested(dto5_dict, "risk", "a1"),
            row_value(row_dict, "a1_spatial_score", "a1_score", "a1"),
        )
    )
    adjusted_score = to_float(
        first_value(
            nested(dto5_dict, "scores", "a1_adjusted"),
            nested(dto5_dict, "scores", "a2"),
            nested(dto5_dict, "risk", "a1_adjusted"),
            nested(dto5_dict, "risk", "a2"),
            row_value(row_dict, "a1_adjusted_score", "a2_score", "a2"),
        )
    )
    representative = to_float(
        first_value(
            nested(dto5_dict, "scores", "representative"),
            nested(dto5_dict, "risk", "representative"),
            row_value(row_dict, "representative_score", "risk_representative", "representative"),
        )
    )

    contributions = _normalize_contributions(
        first_value(
            explanation.get("contributions"),
            explanation.get("feature_importance"),
            dto5_dict.get("contributions"),
            row_dict.get("contributions"),
        )
    )
    rules = _normalize_rules(
        first_value(
            explanation.get("rules"),
            explanation.get("applied_rules"),
            dto5_dict.get("rules"),
            row_dict.get("applied_rules"),
        )
    )

    return A1Context(
        row=row_dict,
        dto5=dto5_dict,
        alert=alert,
        location=location,
        explanation=explanation,
        personalization=personalization,
        contributions=contributions,
        rules=rules,
        spatial_score=spatial_score,
        adjusted_score=adjusted_score,
        representative=representative,
        alert_level=first_value(alert.get("level"), nested(dto5_dict, "risk", "level")),
        detour_available=to_bool(first_value(alert.get("detour_available"), row_value(row_dict, "detour_available"))),
        detour_extra_min=to_float(
            first_value(
                nested(alert, "detour", "extra_min"),
                alert.get("detour_extra_min"),
                row_value(row_dict, "detour_extra_min"),
            )
        ),
    )
