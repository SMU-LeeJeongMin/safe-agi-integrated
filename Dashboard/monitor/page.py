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

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.layout import render_risk_gauge, safe_html
from components.panel_kit import metric_card
from components.sidebar import render_sidebar_links
from core.registry import SCENARIOS, get_scenario
from core.source_loader import load_scenario_payload
from scenarios.common import render_back_buttons, render_payload_messages, render_source_waiting_card
from utils.time_utils import format_kst
from utils.explanation import HR_BASELINE, HR_STD, MAX_HR_60S, RISK_CAUTION, RISK_DANGER, RISK_WARNING, to_bool, to_float

# F1 모델 함수는 Model/ (B 영역)의 확정 공식을 그대로 재사용한다.
from Model.f1_model import compute_e1_e2, judge_fatigue

REFRESH_OPTIONS = {"수동": None, "2초": 2, "5초": 5}

# 이벤트 주입 프리셋 (워치 유입값 인위 변동)
INJECT_HR_BOOST = 25.0     # 심박 급상승 (+bpm)
INJECT_SPO2_DROP = 6.0     # SpO2 저하 (−%p)


# session_state 헬퍼
def _state_key(scenario_id: str, target: str, name: str) -> str:
    return f"monitor::{scenario_id}::{target}::{name}"


def _get_state(scenario_id: str, target: str, name: str, default: Any) -> Any:
    return st.session_state.get(_state_key(scenario_id, target, name), default)


def _set_state(scenario_id: str, target: str, name: str, value: Any) -> None:
    st.session_state[_state_key(scenario_id, target, name)] = value


# F1 이벤트 주입 재계산 (Model/f1_model.py 확정 공식 재사용)
def _spo2_grade(value: float) -> str:
    if value >= 95:
        return "정상"
    if value >= 90:
        return "경고"
    return "위험"


def _injected_feature_dict(row: pd.Series, hr_boost: float, spo2_drop: float, freeze: bool) -> dict[str, Any]:
    hr_new = to_float(row.get("hr_mean_bpm")) + hr_boost
    spo2_new = max(0.0, to_float(row.get("spo2_min_pct")) - spo2_drop)
    ratio_new = hr_new / MAX_HR_60S if MAX_HR_60S else 0.0

    # 주의: hr_overload_5min은 원래 "5분 지속" 조건이지만, 주입 데모에서는
    # 지속 이력이 없어 비율 도달 여부로 근사한다 (화면에 근사임을 명시)
    overload_new = to_bool(row.get("hr_overload_5min")) or (hr_boost > 0 and ratio_new >= 0.6)

    return {
        "hr_mean_bpm": hr_new,
        "hr_ratio_maxhr": ratio_new,
        "hr_z_personal": (hr_new - HR_BASELINE) / HR_STD if HR_STD else 0.0,
        "hr_overload_5min": overload_new,
        "spo2_min_pct": spo2_new,
        "spo2_grade": _spo2_grade(spo2_new),
        "steps_1min": 0.0 if freeze else to_float(row.get("steps_1min")),
        "speed_mean_mpm": 0.0 if freeze else to_float(row.get("speed_mean_mpm")),
        "cumulative_min": to_float(row.get("cumulative_min")),
        "rest_due_90min": to_bool(row.get("rest_due_90min")),
        "heat_index": to_float(row.get("heat_index")),
        "accident_prior": to_float(row.get("accident_prior")),
    }


def _risk_pill_class(rep: float) -> str:
    if rep < RISK_CAUTION:
        return "normal"
    if rep < RISK_WARNING:
        return "caution"
    if rep < RISK_DANGER:
        return "warning"
    return "danger"


def _risk_pill_label(rep: float) -> str:
    if rep < RISK_CAUTION:
        return "정상"
    if rep < RISK_WARNING:
        return "주의"
    if rep < RISK_DANGER:
        return "경고"
    return "위험"


# 렌더 블록
def _metric_card(label: str, value: str, note: str) -> str:
    return metric_card(label, value, note, card_class="monitor-metric-card")


def _render_risk_chart(
    dto5_sequence: list[dict[str, Any]],
    features: pd.DataFrame,
    pos: int,
    window: int,
    injected_rep: float | None,
) -> None:
    start = max(0, pos - window + 1)
    xs: list[Any] = []
    ys: list[float] = []
    for idx in range(start, pos + 1):
        item = dto5_sequence[idx] if idx < len(dto5_sequence) else {}
        rep = to_float((item.get("risk") or {}).get("representative"))
        ts = item.get("ts")
        if ts is None and not features.empty and idx < len(features):
            ts = features.iloc[idx].get("ts")
        xs.append(format_kst(ts) if ts is not None else idx)
        ys.append(rep)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=xs,
            y=ys,
            mode="lines+markers",
            name="representative",
            line=dict(color="#2454a6", width=2.4),
            marker=dict(size=5),
        )
    )
    if injected_rep is not None and xs:
        fig.add_trace(
            go.Scatter(
                x=[xs[-1]],
                y=[injected_rep],
                mode="markers",
                name="이벤트 주입 반영",
                marker=dict(color="#c83e3e", size=11, symbol="diamond"),
            )
        )
    for y_value, color, label in (
        (RISK_CAUTION, "#ad741b", "주의 0.50"),
        (RISK_WARNING, "#a83d3d", "경고 0.65"),
        (RISK_DANGER, "#7a1f1f", "위험 0.85"),
    ):
        fig.add_hline(y=y_value, line_dash="dot", line_color=color, line_width=1.2,
                      annotation_text=label, annotation_position="right",
                      annotation_font=dict(size=11, color=color))
    fig.update_layout(
        height=320,
        margin=dict(l=10, r=10, t=10, b=10),
        yaxis=dict(range=[0, 1], title=None, gridcolor="#edf1f7"),
        xaxis=dict(title=None, showgrid=False),
        plot_bgcolor="#ffffff",
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _render_alert_log(dto5_sequence: list[dict[str, Any]], pos: int, window: int) -> None:
    start = max(0, pos - window + 1)
    rows: list[dict[str, Any]] = []
    for idx in range(start, pos + 1):
        item = dto5_sequence[idx] if idx < len(dto5_sequence) else {}
        risk = item.get("risk") or {}
        level = int(to_float(risk.get("level")))
        alerts = item.get("alerts") or []
        if level <= 0 and not alerts:
            continue
        message = ", ".join(str(a.get("message", a.get("type", ""))) for a in alerts if isinstance(a, dict)) or "-"
        rows.append(
            {
                "시각": format_kst(item.get("ts")),
                "위험 등급": str(risk.get("label", "-")),
                "대표 위험도": f"{to_float(risk.get('representative')):.4f}",
                "알림": message,
            }
        )
    st.markdown("#### 알림 로그 (표시 구간)")
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.caption("표시 구간 내 위험 등급 상승 또는 알림이 없습니다.")


def _render_live_area(
    payload,
    scenario_id: str,
    target: str,
    window: int,
    playing: bool,
    advance: bool,
    in_fragment: bool = False,
) -> None:
    """스트림 위치를 한 칸 진행시키고 현재 시점 상태를 렌더링한다."""
    features = payload.features
    dto5_sequence = payload.dto5_sequence
    total = payload.item_count
    if total <= 0:
        return

    pos = int(_get_state(scenario_id, target, "pos", 0))
    if advance and playing:
        pos = min(pos + 1, total - 1)
        _set_state(scenario_id, target, "pos", pos)
    pos = min(pos, total - 1)

    row = payload.row_at(pos)
    dto5 = payload.dto5_at(pos)
    risk = dto5.get("risk", {})
    fatigue = dto5.get("fatigue", {})
    rep = to_float(risk.get("representative"))

    reached_end = pos >= total - 1
    live_class = "" if (playing and not reached_end) else "paused"
    live_text = "LIVE 스트리밍" if (playing and not reached_end) else ("스트림 종료" if reached_end else "일시정지")
    ts_text = format_kst(row.get("ts")) if not features.empty else format_kst(dto5.get("ts"))
    st.markdown(
        (
            '<div style="display:flex; align-items:center; gap:14px; flex-wrap:wrap; margin:2px 0 14px;">'
            f'<span class="monitor-live-pill {live_class}"><span class="monitor-live-dot"></span>{safe_html(live_text)}</span>'
            f'<span class="safe-muted">관찰 대상 <b>{safe_html(target)}</b>, 현재 시점 <b>{safe_html(ts_text)}</b> ({pos + 1}/{total}분)</span>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )

    # 이벤트 주입 상태
    hr_boost = float(_get_state(scenario_id, target, "hr_boost", 0.0))
    spo2_drop = float(_get_state(scenario_id, target, "spo2_drop", 0.0))
    freeze = bool(_get_state(scenario_id, target, "freeze", False))
    inject_active = hr_boost > 0 or spo2_drop > 0 or freeze
    injection_supported = scenario_id == "F1" and not features.empty

    injected: dict[str, Any] | None = None
    injected_rep: float | None = None
    injected_state: str | None = None
    if injection_supported and inject_active:
        injected = _injected_feature_dict(row, hr_boost, spo2_drop, freeze)
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
    suffix = " (주입 반영)" if injected else ""

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(_metric_card("심박수", f"{display_hr:.0f} bpm", f"워치 유입 평균 심박{suffix}"), unsafe_allow_html=True)
    with c2:
        st.markdown(_metric_card("SpO2", f"{display_spo2:.0f} %", f"분 최저 산소포화도{suffix}"), unsafe_allow_html=True)
    with c3:
        st.markdown(_metric_card("이동량", f"{display_steps:.0f}보, {display_speed:.0f} m/min", f"걸음 수와 GPS 속도{suffix}"), unsafe_allow_html=True)
    with c4:
        st.markdown(
            _metric_card("대표 위험도", f"{display_rep:.4f} ({_risk_pill_label(display_rep)})", f"판정 상태: {display_state}{suffix}"),
            unsafe_allow_html=True,
        )

    # 이벤트 주입 컨트롤
    st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)
    st.markdown("#### 이벤트 주입 (워치 유입값 인위 변동)")
    if injection_supported:
        st.markdown(
            (
                '<div class="monitor-inject-note">버튼을 누르면 현재 시점 이후의 유입값에 변동이 적용되고, '
                'F1 확정 공식(compute_e1_e2, judge_fatigue)으로 위험도가 즉시 재계산됩니다.<br />'
                '심박 과부하 5분 지속 조건은 주입 데모에서는 비율 도달 여부로 근사합니다.</div>'
            ),
            unsafe_allow_html=True,
        )
        b1, b2, b3, b4 = st.columns(4)
        with b1:
            if st.button(f"심박 급상승 +{INJECT_HR_BOOST:.0f}bpm", key="inject_hr", use_container_width=True):
                _set_state(scenario_id, target, "hr_boost", INJECT_HR_BOOST)
                st.rerun(scope="fragment" if in_fragment else "app")
        with b2:
            if st.button(f"SpO2 저하 −{INJECT_SPO2_DROP:.0f}%p", key="inject_spo2", use_container_width=True):
                _set_state(scenario_id, target, "spo2_drop", INJECT_SPO2_DROP)
                st.rerun(scope="fragment" if in_fragment else "app")
        with b3:
            if st.button("이동 정지", key="inject_freeze", use_container_width=True):
                _set_state(scenario_id, target, "freeze", True)
                st.rerun(scope="fragment" if in_fragment else "app")
        with b4:
            if st.button("정상 복귀", key="inject_reset", use_container_width=True, type="primary"):
                for name, default in (("hr_boost", 0.0), ("spo2_drop", 0.0), ("freeze", False)):
                    _set_state(scenario_id, target, name, default)
                st.rerun(scope="fragment" if in_fragment else "app")
        if injected is not None and injected_rep is not None:
            st.markdown(
                (
                    f'<div class="safe-card risk-zone-card risk-zone-{_risk_pill_class(injected_rep)}">'
                    f'<b>주입 반영 대표 위험도 {injected_rep:.4f} ({_risk_pill_label(injected_rep)}), 판정 {safe_html(str(injected_state))}</b><br/>'
                    f'<span class="safe-muted">원본 유입값 기준 위험도는 {rep:.4f} ({_risk_pill_label(rep)})입니다.</span>'
                    '</div>'
                ),
                unsafe_allow_html=True,
            )
    else:
        st.caption(f"{scenario_id} 시나리오의 이벤트 주입은 해당 모델 함수 연결 시 활성화됩니다. 현재는 유입 스트림 관찰만 지원합니다.")

    # 위험도 추이 + 게이지
    st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)
    st.markdown(f"#### 대표 위험도 추이 (최근 {window}분)")
    _render_risk_chart(dto5_sequence, features, pos, window, injected_rep)
    render_risk_gauge(display_rep)

    _render_alert_log(dto5_sequence, pos, window)


# 페이지 엔트리
def render_monitor_page() -> None:
    # 사이드바: 관찰 설정
    st.sidebar.markdown(
        """
        <div class="sidebar-section-heading">관찰 설정</div>
        <div class="sidebar-section-caption">실시간 모니터링 대상과 갱신 주기</div>
        """,
        unsafe_allow_html=True,
    )
    enabled_ids = [sid for sid, d in SCENARIOS.items() if d.enabled and d.source_spec is not None]
    scenario_id = st.sidebar.selectbox("시나리오", enabled_ids, index=enabled_ids.index("F1") if "F1" in enabled_ids else 0)

    definition = get_scenario(scenario_id)
    payload = load_scenario_payload(definition.source_spec)

    targets: list[str] = []
    if not payload.features.empty and "uuid" in payload.features.columns:
        targets = [str(v) for v in payload.features["uuid"].dropna().unique().tolist()]
    if not targets:
        targets = [f"{scenario_id.lower()}_demo_user"]
    target = st.sidebar.selectbox("관찰 대상 (세션/사용자)", targets)

    refresh_label = st.sidebar.selectbox("자동 갱신", list(REFRESH_OPTIONS.keys()), index=1)
    interval = REFRESH_OPTIONS[refresh_label]
    window = st.sidebar.slider("표시 구간 (분)", min_value=10, max_value=60, value=30, step=5)

    render_sidebar_links()

    # 본문 헤더
    render_back_buttons()
    st.markdown("<div class='safe-eyebrow'>REALTIME MONITORING</div>", unsafe_allow_html=True)
    st.title("실시간 모니터링")
    st.markdown(
        (
            '<div class="panel-description">특정 관찰 대상을 선택해 워치 유입값을 분 단위 스트림으로 관찰하는 화면입니다.<br />'
            '이벤트 주입 버튼으로 유입값을 인위적으로 변동시켜 모델의 위험 반응을 확인할 수 있습니다.</div>'
        ),
        unsafe_allow_html=True,
    )
    render_payload_messages(payload)

    if payload.item_count <= 0:
        render_source_waiting_card(payload, scenario_id)
        return

    # 재생 컨트롤 (전체 페이지 rerun 대상)
    total = payload.item_count
    playing = bool(_get_state(scenario_id, target, "playing", True))
    ctrl1, ctrl2, _spacer = st.columns([1, 1, 4])
    with ctrl1:
        if st.button("일시정지" if playing else "재생", key="monitor_toggle", use_container_width=True, type="primary"):
            _set_state(scenario_id, target, "playing", not playing)
            st.rerun()
    with ctrl2:
        if st.button("처음부터", key="monitor_restart", use_container_width=True):
            _set_state(scenario_id, target, "pos", 0)
            st.rerun()

    # 라이브 영역: fragment 부분 갱신 (지원 시)
    if interval is not None and hasattr(st, "fragment"):

        @st.fragment(run_every=interval)
        def _live_fragment() -> None:
            _render_live_area(payload, scenario_id, target, window, playing, advance=True, in_fragment=True)

        _live_fragment()
    else:
        _render_live_area(payload, scenario_id, target, window, playing, advance=False)
        if st.button("다음 시점 ▶", key="monitor_step", use_container_width=False):
            pos = int(_get_state(scenario_id, target, "pos", 0))
            _set_state(scenario_id, target, "pos", min(pos + 1, total - 1))
            st.rerun()
