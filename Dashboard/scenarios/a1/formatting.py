# A1 화면 표기용 공통 포맷 함수

from __future__ import annotations

import html
from typing import Any

import pandas as pd

from scenarios.a1.mapper import A1Context, first_value, nested, to_bool, to_float


def _safe(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def _text(value: Any, default: str = "-") -> str:
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except Exception:
        pass
    text = str(value).strip()
    return text if text else default


def _fmt(value: Any, digits: int = 1, suffix: str = "") -> str:
    number = to_float(value)
    if number is None:
        return "-"
    return f"{number:.{digits}f}{suffix}"


def _fmt_bool(value: Any, true_text: str = "예", false_text: str = "아니오") -> str:
    normalized = to_bool(value)
    if normalized is None:
        return "-"
    return true_text if normalized else false_text


def _selected_alert_label(context: A1Context) -> str:
    return _text(
        first_value(
            nested(context.dto5, "risk", "label"),
            context.alert.get("label"),
            context.alert.get("title"),
        ),
        "미평가",
    )
