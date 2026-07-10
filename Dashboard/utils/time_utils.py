# 시간 표시 유틸리티
# 내부 데이터는 UTC로 저장하고, 시연 화면에서는 한국시간(KST, UTC+9)을 기본 표기로 사용한다.

from __future__ import annotations

from typing import Any

import pandas as pd


def to_kst_timestamp(value: Any):
    """UTC 또는 timezone 정보가 포함된 시각 값을 Asia/Seoul 시각으로 변환한다."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        ts = pd.to_datetime(value)
        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        else:
            ts = ts.tz_convert("UTC")
        return ts.tz_convert("Asia/Seoul")
    except Exception:
        return None


def format_kst(value: Any, with_tz: bool = True) -> str:
    ts = to_kst_timestamp(value)
    if ts is None:
        return "-"
    suffix = " KST" if with_tz else ""
    return ts.strftime("%Y-%m-%d %H:%M") + suffix


def format_utc(value: Any, with_tz: bool = True) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "-"
    try:
        ts = pd.to_datetime(value)
        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        else:
            ts = ts.tz_convert("UTC")
        suffix = " UTC" if with_tz else ""
        return ts.strftime("%Y-%m-%d %H:%M") + suffix
    except Exception:
        return str(value)
