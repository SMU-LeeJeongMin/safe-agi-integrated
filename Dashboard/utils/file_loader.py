# CSV/JSON 데이터 로딩 utility 파일
# \data에 들어있는 입력 데이터 파일들을 읽어옴

import json
from typing import Any

import pandas as pd
import streamlit as st

from file_location import FEATURE_PATH, DTO5_PATH, REPORT_PATH


@st.cache_data
def load_features() -> pd.DataFrame:
    if not FEATURE_PATH.exists():
        raise FileNotFoundError(f"파일이 없습니다: {FEATURE_PATH}")

    df = pd.read_csv(FEATURE_PATH)

    if "ts" in df.columns:
        df["ts"] = pd.to_datetime(df["ts"], errors="coerce")

    return df


@st.cache_data
def load_dto5_sequence() -> list[dict[str, Any]]:
    if not DTO5_PATH.exists():
        raise FileNotFoundError(f"파일이 없습니다: {DTO5_PATH}")

    with open(DTO5_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in ["results", "data", "items", "sequence", "dto5_sequence"]:
            if key in data and isinstance(data[key], list):
                return data[key]

    raise ValueError("dto5_sequence.json은 list 또는 list를 포함한 dict 형태여야 합니다.")


@st.cache_data
def load_validation_report() -> dict[str, Any]:
    if not REPORT_PATH.exists():
        return {}

    with open(REPORT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data if isinstance(data, dict) else {}