# 대시보드 실행 파일
# streamlit run dashboard/main.py 명령어로 실행

import sys
from pathlib import Path

import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from utils.file_loader import (
    load_features,
    load_dto5_sequence,
    load_validation_report,
)
from utils.xAI import make_reason_text

from components.layout import (
    inject_global_css,
    render_intro_page,
    render_scenario_select_page,
)
from components.sidebar import render_sidebar
from components.title_panel import render_title_panel
from components.dto1_input_panel import render_dto1_input_panel
from components.feature_engineering_panel import render_feature_engineering_panel
from components.model_explanation_panel import render_model_explanation_panel
from components.whatif_panel import render_whatif_panel
from components.personalization_panel import render_personalization_panel
from components.dto5_panel import render_dto5_panel
from components.inferenceresult_panel import render_inferenceresult_panel


PANEL_RENDERERS = {
    "DTO-1 Input Panel": "dto1",
    "Feature Engineering Panel": "feature",
    "Model Explanation Panel": "model",
    "What-If Simulating Panel": "whatif",
    "MAML 개인화 Panel": "maml",
    "DTO-5 Output Panel": "dto5",
    "InferenceResult 저장 Panel": "save",
}


def _show_panel(panel_key: str, selected_panel: str) -> bool:
    if selected_panel == "전체 보기":
        return True
    return PANEL_RENDERERS.get(selected_panel) == panel_key


def _back_buttons() -> None:
    st.markdown(
        """
        <div style="display:flex; gap:10px; align-items:center; margin:0 0 24px 0;">
            <a href="?page=intro" target="_self"
               style="display:inline-flex; align-items:center; justify-content:center;
                      min-width:92px; padding:8px 15px; border:1px solid #d0d5dd;
                      border-radius:8px; color:#1f2937; text-decoration:none;
                      background:#ffffff; font-weight:500; line-height:1.2;">처음으로</a>
            <a href="?page=scenario" target="_self"
               style="display:inline-flex; align-items:center; justify-content:center;
                      min-width:118px; padding:8px 15px; border:1px solid #d0d5dd;
                      border-radius:8px; color:#1f2937; text-decoration:none;
                      background:#ffffff; font-weight:500; line-height:1.2;">시나리오 선택</a>
        </div>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(
        page_title="산행안전 AI 대시보드",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_global_css()

    if "page" not in st.session_state:
        st.session_state["page"] = "intro"

    # Introduction Page의 CTA 버튼은 ?page=scenario 링크를 사용합니다.
    # 쿼리 파라미터를 session_state로 반영한 뒤 주소창은 다시 정리합니다.
    query_page = st.query_params.get("page")
    if query_page in {"intro", "scenario", "dashboard"}:
        st.session_state["page"] = query_page
        st.query_params.clear()

    page = st.session_state["page"]

    if page == "intro":
        render_intro_page()
        return

    if page == "scenario":
        render_scenario_select_page()
        return

    features = load_features()
    dto5_sequence = load_dto5_sequence()
    report = load_validation_report()

    if len(features) != len(dto5_sequence):
        st.warning(
            f"feature 행 수({len(features)})와 DTO-5 개수({len(dto5_sequence)})가 다릅니다."
        )

    selected_idx = render_sidebar(features, dto5_sequence)

    row = features.iloc[selected_idx]
    dto5 = dto5_sequence[selected_idx]
    reason_text = make_reason_text(row, dto5)

    _back_buttons()
    st.markdown('<span id="dashboard-top" class="panel-anchor"></span>', unsafe_allow_html=True)
    render_title_panel(row=row, dto5=dto5, report=report)

    st.markdown('<span id="dto1-input-panel" class="panel-anchor"></span>', unsafe_allow_html=True)
    st.divider()
    render_dto1_input_panel(row)

    st.markdown('<span id="feature-engineering-panel" class="panel-anchor"></span>', unsafe_allow_html=True)
    st.divider()
    render_feature_engineering_panel(row, features, dto5_sequence)

    st.markdown('<span id="model-explanation-panel" class="panel-anchor"></span>', unsafe_allow_html=True)
    st.divider()
    render_model_explanation_panel(row, dto5, reason_text)

    st.markdown('<span id="whatif-simulating-panel" class="panel-anchor"></span>', unsafe_allow_html=True)
    st.divider()
    render_whatif_panel(row, dto5)

    st.markdown('<span id="maml-personalization-panel" class="panel-anchor"></span>', unsafe_allow_html=True)
    st.divider()
    render_personalization_panel(row, dto5)

    st.markdown('<span id="dto5-output-panel" class="panel-anchor"></span>', unsafe_allow_html=True)
    st.divider()
    render_dto5_panel(row, dto5, reason_text)

    st.markdown('<span id="inferenceresult-save-panel" class="panel-anchor"></span>', unsafe_allow_html=True)
    st.divider()
    render_inferenceresult_panel(row, dto5, reason_text)


if __name__ == "__main__":
    main()
