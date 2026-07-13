# [5] MAML 개인화 Panel (inner loop)
# 같은 현재 입력이라도 사용자별 baseline이 달라지면 위험도 계산이 달라지는 효과

from __future__ import annotations

import html

import pandas as pd
import streamlit as st

from components.panel_kit import persona_card, risk_tone

from Model.f1_model import infer_f1
from Model.personal_baseline import PersonalBaselineAdapter, personalized_features
from utils.explanation import get_nested

# 가상 페르소나 support set (세션 초반 저강도 구간 심박 10분 관측 가정)
PERSONA_LOW = [72, 74, 76, 75, 73, 74, 75, 76, 74, 73]
PERSONA_HIGH = [104, 106, 108, 107, 105, 106, 107, 108, 106, 105]


def _safe(text: object) -> str:
    return html.escape("" if text is None else str(text))


def _fmt_score(value: object) -> str:
    try:
        return f"{float(value):.4f}"
    except Exception:
        return "-"


def _fmt_bpm(value: float) -> str:
    return f"{float(value):.1f} bpm"



def _support_mean(values: list[float]) -> float:
    return sum(values) / len(values)


def _persona_card(
    *,
    title: str,
    subtitle: str,
    adapter: PersonalBaselineAdapter,
    dto5: dict,
    interpretation: str,
    tone: str,
) -> str:
    risk_score = get_nested(dto5, ["risk", "representative"], 0)
    risk_label = get_nested(dto5, ["risk", "label"], "-")
    fatigue_state = get_nested(dto5, ["fatigue", "state"], "-")
    baseline_label = (
        '조정된 기준 심박 <span class="dto1-tooltip maml-tooltip dto1-tooltip-wide">i'
        '<span class="dto1-tooltip-text">개인화 후 모델이 사용하는 기준 심박<br />'
        '계산: (1-개인화 반영률)×60대 평균 기준 심박 + 개인화 반영률×초반 산행 심박 평균</span></span>'
    )
    return persona_card(
        title=title,
        subtitle=subtitle,
        metrics=[(baseline_label, _fmt_bpm(adapter.adapted_mean)), ("위험도", _fmt_score(risk_score))],
        risk_pill_class=risk_tone(str(risk_label)),
        risk_pill_text=f"risk_label: {risk_label}",
        state_pill_text=str(fatigue_state),
        interpretation=interpretation,
        tone=tone,
    )



def _summary_df(adapters: list[tuple[str, PersonalBaselineAdapter]]) -> pd.DataFrame:
    rows = []
    for name, adapter in adapters:
        summary = adapter.summary()
        rows.append(
            {
                "비교 대상": name,
                "사용한 초반 관측 수": summary.get("support_n"),
                "개인화 반영률": f"{float(summary.get('lambda', 0)) * 100:.1f}%",
                "기존 기준 심박": summary.get("prior_mean"),
                "조정된 기준 심박": summary.get("adapted_mean"),
                "조정된 변동 폭": summary.get("adapted_std"),
            }
        )
    return pd.DataFrame(rows)


def render_personalization_panel(row: pd.Series, dto5: dict) -> None:
    st.header("[5] MAML 개인화 Panel")
    st.markdown(
        '<div class="panel-description">사용자별 평소 심박 기준을 반영해 같은 입력도 다르게 판단될 수 있음을 비교하는 panel</div>',
        unsafe_allow_html=True,
    )

    row_dict = row.to_dict()
    row_dict["ts"] = str(row_dict.get("ts"))
    adapter_v0 = PersonalBaselineAdapter()  # 관측 0 → 기존 v0와 동일
    adapter_low = PersonalBaselineAdapter.from_support(PERSONA_LOW)
    adapter_high = PersonalBaselineAdapter.from_support(PERSONA_HIGH)

    dto5_v0 = infer_f1(row_dict)
    dto5_low = infer_f1(personalized_features(row_dict, adapter_low))
    dto5_high = infer_f1(personalized_features(row_dict, adapter_high))

    st.markdown("#### 개인화 전후 흐름")
    st.markdown(
        (
            '<div class="maml-flow">'
            '<div class="maml-flow-card">'
            '<span>기본 모델</span>'
            '<b>모든 사용자에게 같은 기준 적용</b>'
            '<p>국민건강영양조사 60대 남성 평균 기준 심박 58 bpm에서 시작합니다.</p>'
            '</div>'
            '<div class="maml-flow-arrow">→</div>'
            '<div class="maml-flow-card">'
            '<span>개인화 모델</span>'
            '<b>초반 산행 심박으로 개인 기준 조정 <span class="dto1-tooltip maml-tooltip dto1-tooltip-wide">i<span class="dto1-tooltip-text">산행 초반 10~20분 심박을 개인 기준으로 사용<br />관측 10분부터 개인 심박 특성을 절반 정도 반영</span></span></b>'
            '<p>평소 심박이 낮은 사람과 높은 사람의 위험도를 다르게 계산합니다.</p>'
            '</div>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )

    st.markdown("#### 동일 시점 위험도 비교")
    st.markdown(
        '<div class="panel-description">아래 카드는 같은 현재 입력을 세 가지 기준으로 다시 계산한 결과입니다.</div>',
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            _persona_card(
                title="기본 모델",
                subtitle="60대 평균 심박 기준 사용",
                adapter=adapter_v0,
                dto5=dto5_v0,
                interpretation="아직 개인 데이터가 없으므로 모든 사용자에게 같은 기준을 적용합니다.",
                tone="neutral",
            ),
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            _persona_card(
                title="평소 심박 낮은 사용자",
                subtitle=f"초반 산행 심박 평균 {_support_mean(PERSONA_LOW):.1f} bpm 반영",
                adapter=adapter_low,
                dto5=dto5_low,
                interpretation="평소 기준이 낮아 같은 심박도 더 큰 부담으로 해석될 수 있습니다.",
                tone="low",
            ),
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            _persona_card(
                title="평소 심박 높은 사용자",
                subtitle=f"초반 산행 심박 평균 {_support_mean(PERSONA_HIGH):.1f} bpm 반영",
                adapter=adapter_high,
                dto5=dto5_high,
                interpretation="평소 기준이 높아 같은 심박도 상대적으로 덜 위험하게 해석될 수 있습니다.",
                tone="high",
            ),
            unsafe_allow_html=True,
        )

    st.markdown('<div class="maml-detail-gap"></div>', unsafe_allow_html=True)
    with st.expander("개인화 계산 상세 보기"):
        st.markdown(
            """
            - **사용한 초반 관측 수**: 개인 기준을 만들 때 사용한 저강도 구간 심박 개수입니다.  
            - **개인화 반영률**: 집단 기준과 개인 관측값을 얼마나 섞을지 정하는 비율입니다.  
            - **조정된 기준 심박**: 개인화 후 모델이 사용하는 기준 심박입니다.  
            - **조정된 변동 폭**: 개인화 후 심박 변동성을 반영한 값입니다.
            """
        )
        detail_df = _summary_df(
            [
                ("기본 모델", adapter_v0),
                ("평소 심박 낮은 사용자", adapter_low),
                ("평소 심박 높은 사용자", adapter_high),
            ]
        )
        st.dataframe(detail_df, use_container_width=True, hide_index=True)
