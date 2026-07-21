# 실시간 모니터링 차트 조각
# 스파크라인, 기본 vs Meta Learning 위험도 비교 차트, 카드 HTML을 담당한다.

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.layout import safe_html
from components.panel_kit import metric_card
from Model.f1_model import compute_e1_e2
from Model.personal_baseline import PersonalBaselineAdapter, personalized_features
from monitor.history import _anomaly_indices
from monitor.state import _get_state, _set_state
from utils.explanation import RISK_CAUTION, RISK_DANGER, RISK_WARNING, complete_f1_inputs, ref_hr_baseline, to_bool, to_float
from utils.time_utils import format_kst


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
                dto5 = infer_f1(personalized_features(complete_f1_inputs(row), adapter))
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

    - 기본 모델 위험도(회색)와 Meta Learning 개인화 위험도(초록)를 겹쳐 비교
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
        minute = item.get("minute")
        full = format_kst(ts) if ts is not None else (f"{int(minute)}분" if minute is not None else str(idx))
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
            x=xs, y=maml_ys, mode="lines+markers", name="Meta Learning 개인화",
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
