# 대시보드 제목 및 F1 시나리오 요약

import pandas as pd
import streamlit as st


def render_title_panel(row: pd.Series | None = None, dto5: dict | None = None, report: dict | None = None) -> None:
    st.markdown("<div class='safe-eyebrow'>F1 SCENARIO DASHBOARD</div>", unsafe_allow_html=True)
    st.title("F1 시나리오: 피로 및 심박 이상 감지")

    st.markdown(
        """
        <div class="safe-card soft">
            <h3>시나리오 요약</h3>
            <div class="safe-muted">
            65세 남성 사용자가 여름 오후 청계산을 등산 중입니다.<br/>
            오르막 이후 심박수가 상승하고 이동량이 감소합니다.<br/>
            AI는 워치, GPS, 기상, 사고 데이터를 함께 분석해 피로 및 탈진 위험을 감지하고 가까운 쉼터에서 휴식을 권고합니다.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div style="height:22px;"></div>
        <div style="background:#eef5ff; border-radius:10px; padding:18px 20px;
                    color:#1f3b5d; line-height:1.65; font-size:1.02rem;">
            이번 대시보드는 F1 시나리오를 기준으로 구성한 데모입니다.<br/>
            이후 다른 S·A·F·E 시나리오도 동일한 패널 흐름으로 확장하고,
            다음 단계에서 실시간 API 연동과 DB 저장을 연결할 예정입니다.
        </div>
        """,
        unsafe_allow_html=True,
    )
