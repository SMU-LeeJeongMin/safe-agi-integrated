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
from Model.f1_model import infer_f1
from Model.personal_baseline import PersonalBaselineAdapter, personalized_features
from components.sidebar import render_sidebar_links
from core.registry import SCENARIOS, get_scenario
from core.source_loader import load_scenario_payload
from scenarios.common import render_back_buttons, render_payload_messages, render_source_waiting_card
from utils.time_utils import format_kst
from utils.explanation import RISK_CAUTION, RISK_DANGER, RISK_WARNING, ref_hr_baseline, to_bool, to_float

# F1 모델 함수는 Model/ (B 영역)의 확정 공식을 그대로 재사용한다.
from Model.f1_model import compute_e1_e2, judge_fatigue

REFRESH_OPTIONS = {"수동": None, "2초": 2, "5초": 5}

# 이벤트 주입 스텝 (버튼 1회당 변동량, 누를 때마다 누적)
INJECT_HR_STEP = 25.0      # 심박 ±bpm (기본 심박 대비 z점수 약 ±1.7 이동)
INJECT_SPO2_STEP = 6.0     # SpO2 ∓%p (실세션 98% 기준 1회에 경고 임계 95% 통과)
INJECT_HR_RANGE = (-75.0, 75.0)    # 누적 상하한
INJECT_SPO2_RANGE = (-6.0, 24.0)   # 누적 상하한 (음수 = SpO2 상승)
INJECT_STEPS_STEP = 10.0   # 걸음 수 ±보 (이동량 저하/재개 유도)
INJECT_STEPS_RANGE = (-100.0, 100.0)  # 누적 상하한

# 수신 소스 모드. CSV 리플레이는 미래 데이터를 미리 알지만 실시간 소스는 알 수 없다.
# safe_db 폴링 또는 REST 수신으로 전환 시 False로 바꾸면 리플레이 전용 UI(빨리 감기)가 숨겨진다.
SOURCE_IS_REPLAY = True


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


def _injected_feature_dict(row: pd.Series, hr_boost: float, spo2_drop: float, steps_delta: float) -> dict[str, Any]:
    baseline = ref_hr_baseline(row)
    hr_new = to_float(row.get("hr_mean_bpm")) + hr_boost
    spo2_new = min(100.0, max(0.0, to_float(row.get("spo2_min_pct")) - spo2_drop))
    ratio_new = hr_new / baseline["max_hr"] if baseline["max_hr"] else 0.0

    # 주의: hr_overload_5min은 원래 "5분 지속" 조건이지만, 주입 데모에서는
    # 지속 이력이 없어 비율 도달 여부로 근사한다 (화면에 근사임을 명시)
    overload_new = to_bool(row.get("hr_overload_5min")) or (hr_boost > 0 and ratio_new >= 0.6)

    return {
        "hr_mean_bpm": hr_new,
        "hr_ratio_maxhr": ratio_new,
        "hr_z_personal": (hr_new - baseline["rest_hr"]) / baseline["rest_std"] if baseline["rest_std"] else 0.0,
        "hr_overload_5min": overload_new,
        "spo2_min_pct": spo2_new,
        "spo2_grade": _spo2_grade(spo2_new),
        # 걸음 주입 시 속도는 What-if와 동일 비율(52 m/min ÷ 90 보/분)로 재계산
        "steps_1min": max(0.0, to_float(row.get("steps_1min")) + steps_delta),
        "speed_mean_mpm": (
            max(0.0, to_float(row.get("steps_1min")) + steps_delta) * (52.0 / 90.0)
            if steps_delta != 0
            else to_float(row.get("speed_mean_mpm"))
        ),
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


def _series_with_injection(
    features: pd.DataFrame,
    column: str,
    start: int,
    pos: int,
    inject_start: int | None,
    delta: float = 0.0,
    clamp_min: float | None = None,
) -> tuple[list[int], list[float]]:
    """window 구간 원값 시리즈에 주입 변동을 반영해 반환한다."""
    xs: list[int] = []
    ys: list[float] = []
    for idx in range(start, pos + 1):
        value = to_float(features.iloc[idx].get(column)) if idx < len(features) else 0.0
        if inject_start is not None and idx >= inject_start:
            value += delta
            if clamp_min is not None:
                value = max(clamp_min, value)
        xs.append(idx)
        ys.append(value)
    return xs, ys


def _render_metric_sparkline(
    label: str,
    unit: str,
    xs: list[int],
    ys: list[float],
    inject_start: int | None,
    key: str,
) -> None:
    """수치 카드 대체용 미니 라인차트. 현재값을 제목처럼 표시한다."""
    fig = go.Figure()
    safe_green = "#2e6b35"  # [2] 시계열 차트(style_feature_fig)와 동일 색
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines+markers",
                             line={"width": 2, "color": safe_green},
                             marker={"size": 4, "color": safe_green},
                             fill="tozeroy", fillcolor="rgba(46, 107, 53, 0.10)"))
    if inject_start is not None and xs and xs[0] <= inject_start <= xs[-1]:
        fig.add_vline(x=inject_start, line_dash="dot", line_color="#c47f17")
    # y축 범위를 데이터 주변으로 좁혀 변화가 보이게 하고, 옅은 눈금으로 스케일을 알려준다
    y_min, y_max = (min(ys), max(ys)) if ys else (0.0, 1.0)
    pad = max((y_max - y_min) * 0.35, 1.0)
    fig.update_layout(
        title={"text": f"{label} ({unit.strip()})", "font": {"size": 13}, "x": 0.02},
        height=150,
        margin={"l": 8, "r": 8, "t": 34, "b": 8},
        xaxis={"visible": False},
        yaxis={
            "visible": True, "range": [y_min - pad, y_max + pad],
            "nticks": 3, "tickfont": {"size": 14, "color": "#8a8f8a"},
            "gridcolor": "#eef1ee", "zeroline": False, "title": None,
        },
        plot_bgcolor="#ffffff",
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, key=key, config={"displayModeBar": False})


def _maml_risk_series(
    features: pd.DataFrame,
    baseline: dict[str, Any],
    start: int,
    pos: int,
) -> list[float]:
    """0~pos 관측을 누적한 MAML adapter로 window 구간의 개인화 위험도를 계산한다.

    adapter는 저강도 구간의 심박만 support로 채택하고(관측이 쌓일수록 개인 기준으로 이동),
    각 시점의 위험도는 [5] 패널과 동일하게 personalized_features + infer_f1로 산출한다.
    """
    adapter = PersonalBaselineAdapter(prior_mean=baseline["rest_hr"], prior_std=baseline["rest_std"])
    out: list[float] = []
    for idx in range(pos + 1):
        row = features.iloc[idx]
        adapter.observe(to_float(row.get("hr_mean_bpm")), to_float(row.get("hr_ratio_maxhr")))
        if idx >= start:
            try:
                dto5 = infer_f1(personalized_features(row.to_dict(), adapter))
                out.append(to_float((dto5.get("risk") or {}).get("representative")))
            except Exception:
                out.append(float("nan"))
    return out


def _render_risk_event_chart(
    dto5_sequence: list[dict[str, Any]],
    features: pd.DataFrame,
    pos: int,
    window: int,
    scenario_id: str,
    target: str,
    inject_start: int | None,
) -> None:
    """위험도 추이와 이벤트를 하나로 합친 차트.

    - 기본 모델 위험도(회색)와 MAML 개인화 위험도(초록)를 겹쳐 비교
    - 알림 발생 시점은 마름모 마커로 표시하고, 클릭하면 아래에 기록 상세를 보여줌
    - 실시간 소스 전제: 수신된 범위(0~pos)만 사용
    """
    start = max(0, pos - window + 1)
    xs: list[int] = []
    base_ys: list[float] = []
    labels: list[str] = []
    short_labels: list[str] = []
    for idx in range(start, pos + 1):
        item = dto5_sequence[idx] if idx < len(dto5_sequence) else {}
        base_ys.append(to_float((item.get("risk") or {}).get("representative")))
        ts = item.get("ts")
        if ts is None and not features.empty and idx < len(features):
            ts = features.iloc[idx].get("ts")
        xs.append(idx)
        full = format_kst(ts) if ts is not None else str(idx)
        labels.append(full)
        # 축 눈금은 시:분만 사용 (전체 시각은 hover에 표시)
        short_labels.append(full[-9:-4] if full.endswith(" KST") and len(full) >= 9 else full)

    maml_ys = _maml_risk_series(features, ref_hr_baseline(features.iloc[min(pos, len(features) - 1)]), start, pos) if not features.empty else []

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=xs, y=base_ys, mode="lines+markers", name="기본 모델",
        line=dict(color="#9aa19a", width=2), marker=dict(size=5, color="#9aa19a"),
        customdata=labels, hovertemplate="%{customdata}<br>기본 %{y:.4f}<extra></extra>",
    ))
    if maml_ys:
        fig.add_trace(go.Scatter(
            x=xs, y=maml_ys, mode="lines+markers", name="MAML 개인화",
            line=dict(color="#2e6b35", width=2.6), marker=dict(size=6, color="#2e6b35"),
            customdata=labels, hovertemplate="%{customdata}<br>개인화 %{y:.4f}<extra></extra>",
        ))
    # 알림 이벤트 마커 (수신 범위 내)
    alerts, _ = _anomaly_indices(dto5_sequence[: pos + 1])
    window_alerts = [i for i in alerts if start <= i <= pos]
    if window_alerts:
        fig.add_trace(go.Scatter(
            x=window_alerts,
            y=[base_ys[i - start] for i in window_alerts],
            mode="markers", name="알림 발생",
            marker=dict(size=13, color="#a83d3d", symbol="diamond"),
            hovertemplate="%{x}분<extra>클릭해 기록 보기</extra>",
        ))
    if inject_start is not None and start <= inject_start <= pos:
        fig.add_trace(go.Scatter(
            x=[inject_start],
            y=[base_ys[inject_start - start]],
            mode="markers", name="변동 주입",
            marker=dict(size=13, color="#c47f17", symbol="triangle-up"),
            hovertemplate="%{x}분<extra>변동 주입 시점</extra>",
        ))
    for y_value, label in ((RISK_CAUTION, "주의 0.50"), (RISK_WARNING, "경고 0.65"), (RISK_DANGER, "위험 0.85")):
        fig.add_hline(y=y_value, line_dash="dash", line_color="gray", line_width=1.2,
                      annotation_text=label, annotation_position="top right",
                      annotation_font=dict(size=13, color="gray"))
    fig.update_layout(
        height=420,
        margin=dict(l=10, r=16, t=10, b=10),
        yaxis=dict(range=[0, 1], title=None, gridcolor="#edf1f7", tickfont=dict(size=14)),
        xaxis=dict(
            title=None, showgrid=False, tickmode="array",
            # 라벨이 겹치지 않게 최대 12개로 솎아내고 [2] 차트처럼 대각선 표기
            tickvals=[x for i, x in enumerate(xs) if i % max(1, len(xs) // 12) == 0],
            ticktext=[t for i, t in enumerate(short_labels) if i % max(1, len(xs) // 12) == 0],
            tickangle=-45, tickfont=dict(size=14),
        ),
        plot_bgcolor="#ffffff",
        showlegend=True,
        legend=dict(orientation="h", y=1.08, font=dict(size=15)),
        clickmode="event+select",
    )
    event = st.plotly_chart(
        fig, use_container_width=True,
        key=f"risk_event::{scenario_id}::{target}",
        config={"displayModeBar": False},
        on_select="rerun", selection_mode="points",
    )
    # 클릭한 이벤트의 기록 상세 표시
    points = (event or {}).get("selection", {}).get("points", [])
    clicked = [int(pt.get("x")) for pt in points if int(pt.get("x", -1)) in window_alerts]
    if clicked:
        idx = clicked[0]
        item = dto5_sequence[idx]
        risk = item.get("risk") or {}
        alert_lines = "".join(
            f"<br/><b>{safe_html(str(a.get('title', a.get('type', '알림'))))}</b>: {safe_html(str(a.get('message', '-')))}"
            for a in (item.get("alerts") or []) if isinstance(a, dict)
        )
        st.markdown(
            (
                f'<div class="safe-card risk-zone-card risk-zone-{_risk_pill_class(to_float(risk.get("representative")))}">'
                f'<b>{safe_html(format_kst(item.get("ts")))} 이벤트 기록</b> — '
                f'위험도 {to_float(risk.get("representative")):.4f} ({safe_html(str(risk.get("label", "-")))}), '
                f'판정 {safe_html(str((item.get("fatigue") or {}).get("state", "-")))}'
                f'{alert_lines}'
                '</div>'
            ),
            unsafe_allow_html=True,
        )


def _anomaly_indices(dto5_sequence: list[dict[str, Any]]) -> tuple[list[int], list[int]]:
    """(알림 발동 index 목록, 주의 이상 index 목록)을 반환한다."""
    alerts: list[int] = []
    cautions: list[int] = []
    for i, item in enumerate(dto5_sequence or []):
        if item.get("alerts"):
            alerts.append(i)
        try:
            if int((item.get("risk") or {}).get("level", 0)) >= 1:
                cautions.append(i)
        except (TypeError, ValueError):
            continue
    return alerts, cautions


def _render_alert_log(dto5_sequence: list[dict[str, Any]], pos: int, window: int) -> None:
    start = max(0, pos - window + 1)
    rows: list[dict[str, Any]] = []
    for idx in range(start, pos + 1):
        item = dto5_sequence[idx] if idx < len(dto5_sequence) else {}
        risk = item.get("risk") or {}
        alerts = item.get("alerts") or []
        # 실제 알림이 발송된 시점만 기록한다 (등급 상승만으로는 미기록, 트래픽 과부하 방지)
        if not alerts:
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
    st.markdown("#### 알림 발송 로그 (표시 구간)")
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.markdown(
            '<div class="panel-description">표시 구간 내 발송된 알림이 없습니다.</div>',
            unsafe_allow_html=True,
        )


def _render_anomaly_history(
    dto5_sequence: list[dict[str, Any]],
    features: pd.DataFrame,
    pos: int,
) -> None:
    """지금까지 수신한 구간에서 알림이 발생한 시점을 표로 모아 보여준다.

    같은 사용자가 다른 날 같은 산을 오를 때 참고할 수 있도록,
    발생 시각과 산행 경과, 당시 신체/환경 수치와 위치를 함께 기록한다.
    """
    alerts_idx, _ = _anomaly_indices(dto5_sequence[: pos + 1])
    with st.expander(f"이상 징후 발생 기록 (수신 전체, {len(alerts_idx)}건)"):
        if not alerts_idx:
            st.markdown(
                '<div class="panel-description">지금까지 수신한 구간에 발생한 알림이 없습니다.</div>',
                unsafe_allow_html=True,
            )
            return
        rows: list[dict[str, Any]] = []
        for idx in alerts_idx:
            item = dto5_sequence[idx]
            risk = item.get("risk") or {}
            fatigue = item.get("fatigue") or {}
            feat = features.iloc[idx] if idx < len(features) else None
            rows.append({
                "발생 시각": format_kst(item.get("ts")),
                "산행 경과(분)": f"{to_float(feat.get('cumulative_min')):.0f}" if feat is not None else "-",
                "위험 등급": str(risk.get("label", "-")),
                "피로 상태": str(fatigue.get("state", "-")),
                "대표 위험도": f"{to_float(risk.get('representative')):.4f}",
                "평균 심박(bpm)": f"{to_float(feat.get('hr_mean_bpm')):.0f}" if feat is not None else "-",
                "체감더위": f"{to_float(feat.get('heat_index')):.1f}" if feat is not None else "-",
                "위도": f"{to_float(feat.get('user_lat')):.5f}" if feat is not None else "-",
                "경도": f"{to_float(feat.get('user_lon')):.5f}" if feat is not None else "-",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.markdown(
            '<div class="panel-description">동일한 산을 다시 오를 때, 어느 지점과 경과 시간대에 무리가 왔는지 참고할 수 있습니다.</div>',
            unsafe_allow_html=True,
        )


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

    graph_view = st.toggle(
        "수치를 그래프로 보기",
        value=True,
        key=f"monitor_graph_view::{scenario_id}",
        help="끄면 기존 숫자 카드로 표시합니다.",
    )

    inject_start = _get_state(scenario_id, target, "inject_start", None) if inject_active else None
    if graph_view and not features.empty:
        start = max(0, pos - window + 1)
        metric_rows = [
            ("심박수", "bpm", "hr_mean_bpm", hr_boost, None, f"{display_hr:.0f} bpm", f"워치 유입 평균 심박{hr_suffix}"),
            ("SpO2", "%", "spo2_min_pct", -spo2_drop, None, f"{display_spo2:.0f} %", f"분 최저 산소포화도{spo2_suffix}"),
            ("걸음 수", "보", "steps_1min", steps_delta, 0.0, f"{display_steps:.0f} 보", f"최근 1분 걸음 수{steps_suffix}"),
        ]
        for label, unit, column, delta, clamp, value_text, value_sub in metric_rows:
            with st.container(border=True):
                chart_col, value_col = st.columns([4, 1], vertical_alignment="center")
                with chart_col:
                    xs, ys = _series_with_injection(features, column, start, pos, inject_start, delta=delta, clamp_min=clamp)
                    _render_metric_sparkline(label, unit, xs, ys, inject_start, key=f"spark_{column}::{scenario_id}")
                with value_col:
                    st.markdown(
                        (
                            f'<div style="padding: 2px 6px;">'
                            f'<div class="safe-muted" style="font-size: 0.95rem;">{safe_html(label)}</div>'
                            f'<div style="font-size: 1.9rem; font-weight: 700; line-height: 1.2;">{safe_html(value_text)}</div>'
                            f'<div class="safe-muted" style="font-size: 0.9rem;">{safe_html(value_sub)}</div>'
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

    # 현재 시점 위험 구간 게이지 (수치 그래프 바로 아래)
    if injected_rep is not None:
        render_risk_gauge(injected_rep, secondary_score=rep, primary_label="변동", secondary_label="원본")
    else:
        render_risk_gauge(display_rep)

    # 이벤트 주입 컨트롤
    st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)
    st.markdown('<div style="height:18px;"></div>', unsafe_allow_html=True)
    st.markdown("#### 이벤트 주입 (워치 유입값 인위 변동)")
    if injection_supported:
        st.markdown(
            (
                '<div class="panel-description">버튼을 누르면 현재 시점 이후의 유입값에 변동이 적용되고, '
                'F1 확정 공식(compute_e1_e2, judge_fatigue)으로 위험도가 즉시 재계산됩니다.<br />'
                '심박 과부하 5분 지속 조건은 주입 데모에서는 비율 도달 여부로 근사합니다.</div>'
            ),
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

    # 위험도와 이벤트 (기본/MAML 비교 + 이벤트 기록)
    st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)
    st.markdown(f'<h4>위험도 비교 및 이벤트 (최근 {window}분)</h4>', unsafe_allow_html=True)
    st.markdown(
        '<div class="panel-description">기본 모델과 MAML 개인화 모델의 위험도를 함께 표시합니다. '
        '마름모 표시는 알림이 발생한 시점이며, 클릭하면 해당 기록을 보여줍니다.</div>',
        unsafe_allow_html=True,
    )
    _render_risk_event_chart(dto5_sequence, features, pos, window, scenario_id, target, inject_start)

    _render_alert_log(dto5_sequence, pos, window)

    _render_anomaly_history(dto5_sequence, features, pos)


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
    window = st.sidebar.slider("표시 구간 (분)", min_value=5, max_value=60, value=10, step=5)

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
    ctrl1, ctrl2, ctrl3, _spacer = st.columns([1, 1, 1.4, 2.6])
    with ctrl1:
        if st.button("일시정지" if playing else "재생", key="monitor_toggle", use_container_width=True, type="primary"):
            _set_state(scenario_id, target, "playing", not playing)
            st.rerun()
    with ctrl2:
        if st.button("처음부터", key="monitor_restart", use_container_width=True):
            _set_state(scenario_id, target, "pos", 0)
            st.rerun()
    with ctrl3:
        # 미래 이상 시점으로의 이동은 전체 데이터를 미리 아는 리플레이에서만 가능하다.
        # 실시간 소스 전환(SOURCE_IS_REPLAY=False) 시 이 버튼은 표시되지 않는다.
        if SOURCE_IS_REPLAY:
            alerts, cautions = _anomaly_indices(payload.dto5_sequence)
            targets_idx = alerts or cautions  # 알림이 있으면 알림 기준, 없으면 주의 기준
            if st.button("다음 이상 시점 (리플레이)", key="monitor_ff", use_container_width=True, disabled=not targets_idx):
                current = int(_get_state(scenario_id, target, "pos", 0))
                nxt = next((i for i in targets_idx if i > current), targets_idx[-1])
                _set_state(scenario_id, target, "pos", nxt)
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