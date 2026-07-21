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


# ── 벽시계(라이브 시뮬레이션) 모드 ──────────────────────────────────
# 재생 위치를 session_state가 아니라 현재 시각에서 계산한다.
#   - 모든 세션이 관찰 여부와 무관하게 "동시에" 진행된다
#   - 페이지 이탈, 새로고침, 재접속과 무관하게 시계 기준 위치로 이어진다
#   - 세션마다 고정 오프셋을 두어 40개 세션이 서로 다른 구간을 재생한다
# 세션 길이(total)를 넘으면 처음으로 순환한다 (연속 관제 데모용).

import time as _time

WALLCLOCK_SECONDS_PER_MINUTE = 2  # 실제 2초 = 데이터 1분


def wallclock_offset(scenario_id: str, target: str) -> int:
    """세션별 고정 오프셋. 식별자 기반이라 항상 같은 값이 나온다."""
    key = f"{scenario_id}::{target}"
    return sum(ord(ch) * (i + 7) for i, ch in enumerate(key))


def wallclock_pos(total: int, scenario_id: str, target: str) -> int:
    """현재 벽시계 기준 재생 위치 (0 <= pos < total)."""
    if total <= 0:
        return 0
    tick = int(_time.time()) // WALLCLOCK_SECONDS_PER_MINUTE
    return int((tick + wallclock_offset(scenario_id, target)) % total)