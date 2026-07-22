# 실시간 모니터링 페이지 (BETA)
# 특정 관찰 대상(세션/사용자)을 선택해 유입값을 스트리밍으로 관찰하고,
# 워치 유입값을 인위적으로 변동시키는 이벤트 주입으로 위험 반응을 확인

# 성능 원칙:
#  - 이 페이지 모듈은 monitor 페이지 진입 시점에만 import된다 (main.py lazy import)
#  - 자동 갱신은 st.fragment(run_every=...)로 갱신 영역만 부분 rerun
#    → 9종 시나리오가 붙어도 다른 페이지 성능에 영향을 주지 않음
#  - 차트는 최근 window 구간만 slice해서 그림 (전체 시계열 렌더 금지)

from __future__ import annotations

from typing import Any, Callable
from urllib.parse import quote

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.layout import render_risk_gauge, safe_html
from components.sidebar import render_sidebar_topbar
from components.panel_kit import render_location_map, render_subsection
from components.sidebar import render_sidebar_links
from core.registry import SCENARIOS
from core import trainset
from scenarios.common import render_back_buttons, render_payload_messages, render_source_waiting_card
from monitor.charts import (
    _metric_card,
    _render_metric_sparkline,
    _render_risk_event_chart,
    _series_with_injection,
)
from monitor.history import _render_alert_log, _render_anomaly_history
from monitor.injection import (
    INJECT_HR_RANGE,
    INJECT_HR_STEP,
    INJECT_SPO2_RANGE,
    INJECT_SPO2_STEP,
    INJECT_STEPS_RANGE,
    INJECT_STEPS_STEP,
    _injected_feature_dict,
)
from monitor.session_list import _render_session_list
from monitor.session_registry import discover_sessions, load_entry_payload
from monitor.state import _get_state, _set_state, wallclock_pos, WALLCLOCK_SECONDS_PER_MINUTE
from utils.explanation import format_profile, to_float

# F1 모델 함수는 Model/ (B 영역)의 확정 공식을 그대로 재사용한다.
from Model.f1_model import compute_e1_e2, judge_fatigue

REFRESH_OPTIONS = {"수동": None, "2초": 2, "5초": 5}


# 수신 소스 모드. CSV 리플레이는 미래 데이터를 미리 알지만 실시간 소스는 알 수 없다.
# safe_db 폴링 또는 REST 수신으로 전환 시 False로 바꾸면 리플레이 전용 UI(빨리 감기)가 숨겨진다.
SOURCE_IS_REPLAY = True










# 세션 좌표 기반 산 이름 표시용 참조 좌표 (대략적 중심점, 근접 판정 전용).
# 산출물(Input)에 산 이름 필드가 추가되면 그 값을 우선 사용하도록 교체 예정.
MOUNTAIN_REFS = [
    ("청계산", 37.42, 127.06),
    ("관악산", 37.44, 126.96),
    ("북한산", 37.66, 126.98),
    ("도봉산", 37.70, 127.01),
    ("수락산", 37.69, 127.08),
    ("불암산", 37.66, 127.09),
]


def _nearest_mountain(lat: float, lon: float, max_deg: float = 0.09) -> str | None:
    """세션 좌표에서 가장 가까운 참조 산 이름. 반경(약 10km) 밖이면 None."""
    if not lat or not lon:
        return None
    best_name, best_dist = None, max_deg
    for name, m_lat, m_lon in MOUNTAIN_REFS:
        dist = ((lat - m_lat) ** 2 + (lon - m_lon) ** 2) ** 0.5
        if dist < best_dist:
            best_name, best_dist = name, dist
    return best_name


def _render_live_area(
    payload,
    scenario_id: str,
    target: str,
    window: int,
    in_fragment: bool = False,
) -> None:
    """벽시계 기준 현재 수신 시점 상태를 렌더링한다.

    재생 위치는 상태 저장 없이 현재 시각에서 계산하므로(wallclock_pos),
    모든 세션이 동시에 진행되고 페이지 이탈이나 새로고침과 무관하게 이어진다.
    세션 끝에 도달하면 처음으로 순환한다.
    """
    features = payload.features
    dto5_sequence = payload.dto5_sequence
    total = payload.item_count
    if total <= 0:
        return

    pos = wallclock_pos(total, scenario_id, target)

    row = payload.row_at(pos)
    dto5 = payload.dto5_at(pos)
    risk = dto5.get("risk", {})
    fatigue = dto5.get("fatigue", {})
    rep = to_float(risk.get("representative"))

    live_class = ""
    live_text = "LIVE 스트리밍"
    # 연령대 표기: 기존 산출물은 age_group, 학습셋은 원본 age 컬럼을 사용한다 (표시용 파생)
    profile_value = row.get("age_group") if not features.empty else None
    if (profile_value is None or (isinstance(profile_value, float) and pd.isna(profile_value))) and not features.empty:
        profile_value = trainset.display_age_group(row.get("age"))
    age_text = format_profile(profile_value)
    user_lat = to_float(row.get("user_lat")) if not features.empty else 0.0
    user_lon = to_float(row.get("user_lon")) if not features.empty else 0.0
    loc_text = f", 위치 <b>{user_lat:.5f}, {user_lon:.5f}</b>" if (user_lat and user_lon) else ""
    st.markdown(
        (
            '<div class="safe-card" style="display:flex; align-items:center; gap:14px; flex-wrap:wrap; '
            'margin:2px 0 14px; padding:12px 16px; border:1px solid #e5e7eb; border-radius:14px; background:#ffffff;">'
            f'<span class="monitor-live-pill {live_class}"><span class="monitor-live-dot"></span>{safe_html(live_text)}</span>'
            f'<span class="safe-muted">관찰 대상 <b>{safe_html(target)}</b>, 연령대 <b>{safe_html(age_text)}</b>{loc_text}</span>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )

    # 이벤트 주입 상태
    hr_boost = float(_get_state(scenario_id, target, "hr_boost", 0.0))
    spo2_drop = float(_get_state(scenario_id, target, "spo2_drop", 0.0))
    steps_delta = float(_get_state(scenario_id, target, "steps_delta", 0.0))
    inject_active = hr_boost != 0 or spo2_drop != 0 or steps_delta != 0
    injection_supported = scenario_id == "F1" and not features.empty

    injected: dict[str, Any] | None = None
    injected_rep: float | None = None
    injected_state: str | None = None
    if injection_supported and inject_active:
        injected = _injected_feature_dict(row, hr_boost, spo2_drop, steps_delta)
        e1_new, e2_new = compute_e1_e2(injected)
        injected_rep = max(e1_new, e2_new)
        injected_state = judge_fatigue(injected)

    # 현재 상태 카드
    display_hr = injected["hr_mean_bpm"] if injected else to_float(row.get("hr_mean_bpm"))
    display_spo2 = injected["spo2_min_pct"] if injected else to_float(row.get("spo2_min_pct"))
    display_steps = injected["steps_1min"] if injected else to_float(row.get("steps_1min"))
    display_speed = injected["speed_mean_mpm"] if injected else to_float(row.get("speed_mean_mpm"))
    display_rep = injected_rep if injected_rep is not None else rep
    display_state = injected_state if injected_state is not None else str(fatigue.get("state", "-"))
    suffix = " (변동값 반영)" if injected else ""
    # 지표별 표기: 해당 지표에 실제 변동이 들어간 경우에만 붙인다
    hr_suffix = " (변동값 반영)" if hr_boost != 0 else ""
    spo2_suffix = " (변동값 반영)" if spo2_drop != 0 else ""
    steps_suffix = " (변동값 반영)" if steps_delta != 0 else ""

    inject_start = _get_state(scenario_id, target, "inject_start", None) if inject_active else None

    # ── 배치: 좌측 지도 + 위험도 비교, 우측 지표 카드 + 게이지 + 주입 + 알림 로그 ──
    map_col, metrics_col = st.columns([1.25, 1.75], gap="medium")

    with map_col:
        if user_lat and user_lon:
            points = [{"lat": user_lat, "lon": user_lon, "label": "현재 위치", "kind": "current"}]
            legend = [("dot-blue", "현재 위치")]
            mountain_name = _nearest_mountain(user_lat, user_lon)
            if mountain_name:
                legend.append(("icon:#1f7a5a:▲", mountain_name))
            shelter = fatigue.get("nearest_shelter")
            if isinstance(shelter, dict) and shelter.get("lat") is not None:
                shelter_name = shelter.get("name") or "쉼터"
                points.append(
                    {
                        "lat": to_float(shelter.get("lat")),
                        "lon": to_float(shelter.get("lon")),
                        "label": f"추천 쉼터: {shelter_name}",
                        "kind": "shelter",
                    }
                )
                legend.append(("dot-red", "추천 쉼터"))
            # 높이는 우측 컬럼(지표 카드 + 이벤트 주입)과 맞춘 값
            render_location_map(points=points, zoom=13.5, legend=legend, height=545)
        else:
            st.caption("위치 데이터가 연결되면 사용자의 현재 위치 지도가 표시됩니다.")

    with metrics_col:
        # 토글 도움말은 F1 시나리오와 동일한 (i) 툴팁 디자인 사용
        # F1과 동일한 구성: 라벨 텍스트와 (i) 툴팁을 한 마크업에 인라인 배치.
        # 토글 위젯은 스위치만 표시한다.
        switch_col, label_col = st.columns([0.07, 0.93], gap="small", vertical_alignment="center")
        with switch_col:
            graph_view = st.toggle(
                "수치를 그래프로 보기",
                value=True,
                key=f"monitor_graph_view::{scenario_id}",
                label_visibility="collapsed",
            )
        with label_col:
            # 컬럼 경계와 간격만큼 왼쪽으로 당겨 스위치 옆에 붙인다 (조정은 이 margin 값 하나)
            st.markdown(
                (
                    '<span style="display:inline-flex; align-items:center; gap:6px; margin-left:-16px; position:relative; top:5px;">'
                    '<span style="font-weight:400; font-size:.9rem; color:#31333f;">수치를 그래프로 보기</span>'
                    '<span class="dto1-tooltip" aria-label="설명 보기">i'
                    '<span class="dto1-tooltip-text">끄면 기존 숫자 카드로 표시합니다.</span>'
                    '</span>'
                    '</span>'
                ),
                unsafe_allow_html=True,
            )

        if graph_view and not features.empty:
            start = max(0, pos - window + 1)
            metric_rows = [
                ("심박수", "bpm", "hr_mean_bpm", hr_boost, None, f"{display_hr:.0f} bpm", f"워치 유입 평균 심박{hr_suffix}"),
                ("SpO2", "%", "spo2_min_pct", -spo2_drop, None, f"{display_spo2:.0f} %", f"분 최저 산소포화도{spo2_suffix}"),
                ("걸음 수", "보", "steps_1min", steps_delta, 0.0, f"{display_steps:.0f} 보", f"최근 1분 걸음 수{steps_suffix}"),
            ]
            # 원본 컬럼이 있는 지표만 표시하고, 전부 없으면 (다른 시나리오 학습셋 등)
            # 신호 컬럼을 추론해 범용 스파크라인으로 폴백한다.
            metric_rows = [m for m in metric_rows if m[2] in features.columns]
            if not metric_rows:
                for column in trainset.numeric_signal_columns(features)[:3]:
                    current = to_float(row.get(column))
                    metric_rows.append((column, "", column, 0.0, None, f"{current:.2f}", "학습셋 신호"))
            metric_cols = st.columns(3)
            for col_ctx, (label, unit, column, delta, clamp, value_text, value_sub) in zip(metric_cols, metric_rows):
                with col_ctx:
                    with st.container(border=True):
                        xs, ys = _series_with_injection(features, column, start, pos, inject_start, delta=delta, clamp_min=clamp)
                        _render_metric_sparkline(label, unit, xs, ys, inject_start, key=f"spark_{column}::{scenario_id}")
                        st.markdown(
                            (
                                f'<div style="padding: 0 6px 14px;">'
                                f'<div class="safe-muted" style="font-size: .9rem;">{safe_html(label)}</div>'
                                f'<div style="font-size: 1.5rem; font-weight: 700; line-height: 1.2;">{safe_html(value_text)}</div>'
                                f'<div class="safe-muted" style="font-size: .84rem;">{safe_html(value_sub)}</div>'
                                '</div>'
                            ),
                            unsafe_allow_html=True,
                        )
        else:
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(_metric_card("심박수", f"{display_hr:.0f} bpm", f"워치 유입 평균 심박{hr_suffix}"), unsafe_allow_html=True)
            with c2:
                st.markdown(_metric_card("SpO2", f"{display_spo2:.0f} %", f"분 최저 산소포화도{spo2_suffix}"), unsafe_allow_html=True)
            with c3:
                st.markdown(_metric_card("이동량", f"{display_steps:.0f}보, {display_speed:.0f} m/min", f"걸음 수와 GPS 속도{steps_suffix}"), unsafe_allow_html=True)

        # 이벤트 주입 컨트롤 (지표 카드 바로 아래)
        st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)
        render_subsection("이벤트 주입 (워치 유입값 인위 변동)")
        if injection_supported:
            st.markdown(
                '<div class="panel-description">버튼을 누르면 현재 시점 이후의 유입값에 변동이 적용되고, '
                '위험도가 즉시 재계산됩니다.</div>',
                unsafe_allow_html=True,
            )
            def _step_inject(name: str, step: float, bounds: tuple[float, float]) -> None:
                """누적 스텝 적용. 첫 주입 시점만 마커로 기록하고, 전부 원점이면 마커 해제."""
                lo, hi = bounds
                value = min(hi, max(lo, float(_get_state(scenario_id, target, name, 0.0)) + step))
                _set_state(scenario_id, target, name, value)
                _refresh_inject_start()
                st.rerun(scope="fragment" if in_fragment else "app")

            def _refresh_inject_start() -> None:
                active = (
                    float(_get_state(scenario_id, target, "hr_boost", 0.0)) != 0
                    or float(_get_state(scenario_id, target, "spo2_drop", 0.0)) != 0
                    or float(_get_state(scenario_id, target, "steps_delta", 0.0)) != 0
                )
                if active and _get_state(scenario_id, target, "inject_start", None) is None:
                    _set_state(scenario_id, target, "inject_start", pos)
                if not active:
                    _set_state(scenario_id, target, "inject_start", None)

            b1, b2, b3, b4 = st.columns(4)
            with b1:
                if st.button(f"심박 +{INJECT_HR_STEP:.0f}bpm", key="inject_hr_up", use_container_width=True):
                    _step_inject("hr_boost", INJECT_HR_STEP, INJECT_HR_RANGE)
                if st.button(f"심박 −{INJECT_HR_STEP:.0f}bpm", key="inject_hr_down", use_container_width=True):
                    _step_inject("hr_boost", -INJECT_HR_STEP, INJECT_HR_RANGE)
            with b2:
                if st.button(f"SpO2 +{INJECT_SPO2_STEP:.0f}%p", key="inject_spo2_up", use_container_width=True):
                    _step_inject("spo2_drop", -INJECT_SPO2_STEP, INJECT_SPO2_RANGE)
                if st.button(f"SpO2 −{INJECT_SPO2_STEP:.0f}%p", key="inject_spo2_down", use_container_width=True):
                    _step_inject("spo2_drop", INJECT_SPO2_STEP, INJECT_SPO2_RANGE)
            with b3:
                if st.button(f"걸음 수 +{INJECT_STEPS_STEP:.0f}보", key="inject_steps_up", use_container_width=True):
                    _step_inject("steps_delta", INJECT_STEPS_STEP, INJECT_STEPS_RANGE)
                if st.button(f"걸음 수 −{INJECT_STEPS_STEP:.0f}보", key="inject_steps_down", use_container_width=True):
                    _step_inject("steps_delta", -INJECT_STEPS_STEP, INJECT_STEPS_RANGE)
            with b4:
                if st.button("정상 복귀", key="inject_reset", use_container_width=True, type="primary"):
                    _set_state(scenario_id, target, "inject_start", None)
                    for name, default in (("hr_boost", 0.0), ("spo2_drop", 0.0), ("steps_delta", 0.0)):
                        _set_state(scenario_id, target, name, default)
                    st.rerun(scope="fragment" if in_fragment else "app")

            status_parts = []
            if hr_boost:
                status_parts.append(f"심박 {hr_boost:+.0f}bpm")
            if spo2_drop:
                status_parts.append(f"SpO2 {-spo2_drop:+.0f}%p")
            if steps_delta:
                status_parts.append(f"걸음 {steps_delta:+.0f}보")
            st.caption("현재 주입: " + (", ".join(status_parts) if status_parts else "없음"))
        else:
            st.caption(f"{scenario_id} 시나리오의 이벤트 주입은 해당 모델 함수 연결 시 활성화됩니다. 현재는 유입 스트림 관찰만 지원합니다.")

    # ── 전체 폭: 위험 구간 게이지 → 위험도 비교 및 이벤트 → 알림 발송 로그 ──
    st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)
    if injected_rep is not None:
        render_risk_gauge(injected_rep, secondary_score=rep, primary_label="변동", secondary_label="원본")
    else:
        render_risk_gauge(display_rep)

    st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)
    render_subsection(f"위험도 비교 및 이벤트 (최근 {window}분)")
    st.markdown(
        '<div class="panel-description">기본 모델과 Meta Learning 개인화 모델의 위험도를 함께 표시합니다. '
        '마름모 표시는 알림이 발생한 시점이며, 클릭하면 해당 기록을 보여줍니다.</div>',
        unsafe_allow_html=True,
    )
    _render_risk_event_chart(dto5_sequence, features, pos, window, scenario_id, target, inject_start)

    _render_alert_log(dto5_sequence, pos, window)

    _render_anomaly_history(dto5_sequence, features, pos)




# 페이지 엔트리
def render_monitor_page() -> None:
    # 사이드바 상단 바 (로고, 홈, 뒤로가기)
    render_sidebar_topbar("?page=monitor")

    # 사이드바: 관찰 설정
    st.sidebar.markdown(
        """
        <div class="sidebar-section-heading">관찰 설정</div>
        <div class="sidebar-section-caption">실시간 모니터링 대상과 갱신 주기</div>
        """,
        unsafe_allow_html=True,
    )
    enabled_ids = [sid for sid, d in SCENARIOS.items() if d.enabled and d.source_spec is not None]
    scenario_filter = st.sidebar.multiselect(
        "시나리오 필터",
        enabled_ids,
        default=[],
        key="monitor_scenario_filter",
        placeholder="전체 시나리오",
    )
    scan_ids = scenario_filter or enabled_ids

    refresh_label = st.sidebar.selectbox("자동 갱신", list(REFRESH_OPTIONS.keys()), index=1)
    interval = REFRESH_OPTIONS[refresh_label]
    window = st.sidebar.slider("표시 구간 (분)", min_value=5, max_value=60, value=10, step=5)

    # 산행 세션 리스트 (관찰 설정 바로 아래)
    st.sidebar.divider()
    entries = discover_sessions(scan_ids)
    selected_key = st.session_state.get("monitor_selected_session")
    with st.sidebar:
        selected_key = _render_session_list(entries, selected_key)
    st.session_state["monitor_selected_session"] = selected_key

    render_sidebar_links()

    # 본문 헤더
    render_back_buttons()
    st.markdown(
        (
            '<div class="scenario-hero">'
            '<div class="scenario-hero-eyebrow">REALTIME MONITORING</div>'
            '<div class="scenario-hero-title">실시간 모니터링</div>'
            '<div class="scenario-hero-sub">특정 관찰 대상을 선택해 워치 유입값을 분 단위 스트림으로 관찰하는 화면입니다.<br />'
            '이벤트 주입 버튼으로 유입값을 인위적으로 변동시켜 모델의 위험 반응을 확인할 수 있습니다.</div>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )
    if not entries:
        st.markdown(
            '<div class="panel-description">표시할 세션이 없습니다. '
            'Input/&lt;시나리오&gt;/outputs 단일 산출물 또는 outputs/sessions/&lt;세션ID&gt;/ 규격의 산출물이 연결되면 목록이 채워집니다.</div>',
            unsafe_allow_html=True,
        )
        return

    entry = next((e for e in entries if e.key == selected_key), entries[0])
    scenario_id = entry.scenario_id
    target = entry.session_id
    payload = load_entry_payload(entry)

    _render_stream_column(payload, scenario_id, target, window, interval)


def _render_stream_column(payload, scenario_id: str, target: str, window: int, interval) -> None:
    """우측 스트림 영역: 선택된 세션의 재생 컨트롤과 라이브 화면."""
    render_payload_messages(payload)

    if payload.item_count <= 0:
        render_source_waiting_card(payload, scenario_id)
        return

    # 벽시계 모드: 모든 세션이 현재 시각 기준으로 동시에 진행된다.
    # 재생, 일시정지, 처음부터 같은 리플레이 조작은 실시간 개념과 맞지 않아 제거했다.
    st.markdown('<div style="height:18px;"></div>', unsafe_allow_html=True)
    st.caption(
        f"라이브 시뮬레이션: 실제 {WALLCLOCK_SECONDS_PER_MINUTE}초 = 산행 1분. "
        "세션 끝에 도달하면 처음으로 순환합니다."
    )

    # 라이브 영역: fragment 부분 갱신 (지원 시)
    if interval is not None and hasattr(st, "fragment"):

        @st.fragment(run_every=interval)
        def _live_fragment() -> None:
            _render_live_area(payload, scenario_id, target, window, in_fragment=True)

        _live_fragment()
    else:
        _render_live_area(payload, scenario_id, target, window)
        if st.button("지금 시점으로 갱신", key="monitor_step", use_container_width=False):
            st.rerun()