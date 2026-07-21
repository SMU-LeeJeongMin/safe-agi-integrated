# 실시간 모니터링 session_state 헬퍼
# (시나리오, 관찰 대상)별로 재생 위치와 주입 상태를 격리 보관한다.

from __future__ import annotations

from typing import Any

import streamlit as st


# session_state 헬퍼
def _state_key(scenario_id: str, target: str, name: str) -> str:
    return f"monitor::{scenario_id}::{target}::{name}"


def _get_state(scenario_id: str, target: str, name: str, default: Any) -> Any:
    return st.session_state.get(_state_key(scenario_id, target, name), default)


def _set_state(scenario_id: str, target: str, name: str, value: Any) -> None:
    st.session_state[_state_key(scenario_id, target, name)] = value
