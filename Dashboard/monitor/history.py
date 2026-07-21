# 알림 로그와 이상 이력 (수신 구간 기록 조회)

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st
from components.panel_kit import render_subsection

from utils.explanation import RISK_CAUTION, to_float
from utils.time_utils import format_kst


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
    render_subsection("알림 발송 로그 (표시 구간)")
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
