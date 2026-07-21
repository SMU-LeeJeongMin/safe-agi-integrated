# [5] Meta Learning 개인화 Panel — A1 개인화 전후 비교

from __future__ import annotations

from typing import Any

import streamlit as st
from scenarios.common import render_panel_placeholder

from components.panel_kit import persona_card, risk_tone, render_panel_banner, render_subsection

from scenarios.a1.mapper import A1Context, first_value, nested, row_value
from scenarios.a1.formatting import _selected_alert_label, _fmt, _safe, _text



def _persona_card(title: str, subtitle: str, score: Any, label: str, interpretation: str, tone: str) -> str:
    return persona_card(
        title=title,
        subtitle=subtitle,
        metrics=[("개인화 입력", _text(label)), ("대표 점수", _fmt(score, 4))],
        risk_pill_class=risk_tone(label),
        risk_pill_text=f"상태: {_text(label)}",
        state_pill_text="외부 Model 결과",
        interpretation=interpretation,
        tone=tone,
    )



def render_personalization_panel(context: A1Context) -> None:
    personalization = context.personalization
    render_panel_banner(5, "Meta Learning 개인화 Panel", "연령 및 개인 심박 기준 등 A1 개인화 입력과 Model이 반환한 보정 결과를 확인하는 panel")
    # F1 디자인 이식 방향이 확정될 때까지 골격 시나리오와 동일한 자리표시로 둔다.
    # 기존 구현은 아래에 보존되어 있으며, 이 두 줄을 제거하면 복원된다.
    render_panel_placeholder("A1")
    return


    render_subsection("개인화 전후 흐름")
    st.markdown(
        """
        <div class="maml-flow">
            <div class="maml-flow-card">
                <span>공간 및 지형 기본 판단</span>
                <b>거리 및 이탈 및 경사 중심</b>
                <p>Input과 Model에서 전달된 A1 공간 점수를 기본 결과로 사용합니다.</p>
            </div>
            <div class="maml-flow-arrow">→</div>
            <div class="maml-flow-card">
                <span>개인화 보정</span>
                <b>연령 및 개인 기준 반영</b>
                <p>개인화 모델이 연결되면 외곽 주의 단계의 보정값과 근거를 표시합니다.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    before = first_value(personalization.get("before"), personalization.get("base_score"), context.spatial_score)
    after = first_value(personalization.get("after"), personalization.get("personalized_score"), context.adjusted_score)
    profile = _text(first_value(personalization.get("profile"), row_value(context.row, "age_group")), "미수신")
    label = _selected_alert_label(context)

    render_subsection("A1 개인화 결과 비교")
    st.markdown(
        '<div class="panel-description">아래 카드는 Model 산출물에 개인화 블록이 있을 때 값이 채워지며 Dashboard에서 임의 보정하지 않습니다.</div>',
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            _persona_card(
                "공간 기본값",
                "거리 및 이탈 및 경사 중심의 A1 원점수",
                before,
                label if before is not None else "미수신",
                "위험 지형 자체에 대한 판단 결과입니다.",
                "neutral",
            ),
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            _persona_card(
                "사용자 프로필",
                f"연령대/프로필: {profile}",
                personalization.get("profile_score"),
                profile,
                "연령 및 개인 특성 입력은 Model이 제공한 결과에만 반영합니다.",
                "low",
            ),
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            _persona_card(
                "개인화 후",
                "외부 MAML 또는 개인화 모델 결과",
                after,
                label if after is not None else "연결 대기",
                "안전 하드 룰은 유지하고 개인화 보정 결과만 표시합니다.",
                "high",
            ),
            unsafe_allow_html=True,
        )

    st.markdown('<div class="maml-detail-gap"></div>', unsafe_allow_html=True)
    with st.expander("개인화 결과 JSON 상세 보기"):
        if personalization:
            st.json(personalization)
        else:
            st.caption("DTO-5 또는 Model 결과에 personalization/maml 블록이 연결되면 표시됩니다.")
