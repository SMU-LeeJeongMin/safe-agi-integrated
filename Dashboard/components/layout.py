# 공통 레이아웃 및 스타일 컴포넌트 (CSS)

from __future__ import annotations

import base64
import html
from pathlib import Path
from typing import Iterable

import streamlit as st


PANEL_OPTIONS = [
    "시나리오 요약 Panel",
    "[1] DTO-1 Input Panel",
    "[2] Feature Engineering Panel",
    "[3] Model Explanation Panel",
    "[4] What-If Simulating Panel",
    "[5] Meta Learning 개인화 Panel",
    "[6] DTO-5 Output Panel",
    "[7] InferenceResult 저장 Panel",
]

SCENARIOS = [
    # 4번째 값: 시연 가능 여부(선택 화면 pill 표기용). 모든 시나리오는 골격 화면으로 진입 가능.
    ("A1", "낭떠러지 및 낙석 위험 구역 접근", "위험 구역 접근 시 생체 반응 + 지형 분석 → 경고 및 우회 경로", False),
    ("A2", "야생동물 출몰 지역 진입", "야생동물 출몰 지역 진입 시 이상 행동 패턴 감지 → 즉각 경고", False),
    ("A5", "과거 사고 다수 발생 지역 진입", "과거 사고 다수 발생 지역 진입 감지 → 경고 및 주의 안내", False),
    ("F1", "피로 및 심박 이상 감지", "이상 징후 감지 → 휴식 권고, 속도 및 경로 조절", True),
    ("F2", "위험 점수 임계치 초과", "위험 점수 임계치 초과 → 휴식 권고 및 회복 중심 산행 유도", False),
    ("F3", "일몰 시간 임박", "일몰 시간 임박 → 하산 권고, 야간 산행 예방", False),
    ("F4", "산행 코스 재추천", "개인 체력 기반 코스 실시간 재추천", False),
    ("E1", "복합 이상 감지 + 무응답", "복합 생체 및 물리 이상 감지 + 무응답 → 단계적 확인 후 자동 구조 요청", False),
    ("E2", "기상 급변 + 상태 이상", "기상 급변 + 사용자 상태 이상 동시 발생 → 임계치 초과 시 E-Call 자동 발동", False),
]


ASSET_DIR = Path(__file__).resolve().parents[1] / "assets"

# 공통 작업 레포 링크 (단일 URL)
GITHUB_REPO_URL = "https://github.com/SMU-LeeJeongMin/safe-agi-integrated"
GITHUB_LINK_LABEL = "SAFE AI Project"


def github_link_html(extra_class: str = "") -> str:
    """GitHub 아이콘 + 'SAFE AI Project' 문구로 구성된 링크 HTML을 반환한다."""
    icon_uri = _asset_data_uri("Github.png", "image/png")
    icon_img = f'<img src="{icon_uri}" alt="GitHub" />' if icon_uri else ""
    class_attr = f"project-link {extra_class}".strip()
    return (
        f'<a class="{class_attr}" href="{GITHUB_REPO_URL}" target="_blank" '
        f'rel="noopener noreferrer" aria-label="공통 GitHub 레포로 이동">'
        f'{icon_img}<span>{GITHUB_LINK_LABEL}</span></a>'
    )


def _asset_data_uri(filename: str, mime: str) -> str:
    """Streamlit HTML/CSS에서 쓸 base64 data URI를 반환한다."""
    path = ASSET_DIR / filename
    if not path.exists():
        return ""
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def inject_global_css() -> None:
    st.markdown(
        """
        <style>
        /* Pretendard 가변 폰트 (로컬 서빙): static/fonts/PretendardVariable.woff2,
           .streamlit/config.toml의 enableStaticServing = true 전제.
           아이콘 폰트와 코드 폰트는 적용 대상에서 제외 */
        @font-face {
            font-family: "Pretendard Variable";
            font-weight: 45 920;
            font-style: normal;
            font-display: swap;
            src: local("Pretendard Variable"),
                 url("app/static/fonts/PretendardVariable.woff2") format("woff2-variations");
        }
        html, body,
        [data-testid="stAppViewContainer"] *:not([data-testid="stIconMaterial"]):not([class*="material-symbols"]):not(code):not(pre):not(kbd):not(samp),
        [data-testid="stSidebar"] *:not([data-testid="stIconMaterial"]):not([class*="material-symbols"]):not(code):not(pre) {
            font-family: "Pretendard Variable", Pretendard, "Malgun Gothic", "Apple SD Gothic Neo", sans-serif !important;
        }
        :root {
            --safe-navy: #10233f;
            --safe-blue: #2e6b35;  /* 구 파란 브랜드색을 진초록으로 재지정 (변수명은 호환 유지) */
            --safe-sky: #eef1e8;
            --safe-green: #1f7a5a;
            --safe-red: #c83e3e;
            --safe-amber: #ad741b;
            --safe-gray: #667085;
            --safe-border: #e2e5dc;
            --safe-card: #ffffff;
        }
        .block-container { padding-top: 3.4rem; max-width: 1320px; }
        .main .block-container { font-size: 1.06rem; }
        .main .block-container p, .main .block-container li { font-size: 1.06rem; line-height: 1.65; }
        .main .block-container div[data-testid="stMarkdownContainer"] { font-size: 1.06rem; }
        h1 { font-size: 2.75rem !important; letter-spacing: -0.035em; }
        h2, h3 { letter-spacing: -0.025em; }
        [data-testid="stMetricValue"] { font-size: 2.25rem; }
        [data-testid="stMetricLabel"] { font-size: 1.06rem; }
        .safe-hero {
            border: 1px solid var(--safe-border);
            border-radius: 28px;
            padding: 42px 44px;
            background: linear-gradient(135deg, #f4f6f0 0%, #ffffff 46%, #eff7f1 100%);
            box-shadow: 0 18px 48px rgba(16, 35, 63, 0.12);
            margin-bottom: 22px;
        }
        .safe-eyebrow { color: var(--safe-blue); font-weight: 800; letter-spacing: .08em; font-size: .9rem; }
        .safe-title { color: var(--safe-navy); font-size: 3.35rem; line-height: 1.08; font-weight: 900; margin: 10px 0 12px; letter-spacing: -0.05em; }
        .safe-subtitle { color: #344054; font-size: 1.25rem; line-height: 1.65; max-width: 880px; }
        .safe-card {
            border: 1px solid var(--safe-border);
            border-radius: 20px;
            padding: 20px 22px;
            background: var(--safe-card);
            box-shadow: 0 8px 24px rgba(16, 35, 63, 0.06);
            height: 100%;
        }
        .safe-card.soft { background: #f8f9f4; }
        .safe-card.green { background: #f2fbf7; border-color: #cdebdc; }

        /* 패널 제목 배너: 왼쪽 큰 번호 + 오른쪽 사선 초록 리본 */
        .panel-banner {
            display: flex;
            align-items: center;
            gap: 20px;
            margin: 2px 0 20px;
        }
        .panel-banner-num {
            flex: 0 0 76px;
            font-size: 3.4rem;
            font-weight: 900;
            color: #2e6b35;
            line-height: .95;
            letter-spacing: -0.03em;
        }

        /* panel 내부 소제목: 얇은 사다리꼴 리본을 글씨 하단에 배치 */
        .panel-subsection {
            margin: 30px 0 14px;
        }
        .panel-subsection span {
            display: inline-block;
            position: relative;
            font-size: 1.25rem;
            font-weight: 800;
            color: #1f2937;
            padding: 0 4px 10px 2px;
        }
        .panel-subsection span::after {
            content: "";
            position: absolute;
            left: 0;
            right: -30px;
            bottom: 0;
            height: 8px;
            background: #2e6b35;
            clip-path: polygon(0 0, 100% 0, calc(100% - 14px) 100%, 0 100%);
            border-radius: 2px;
        }
        .panel-banner-body {
            flex: 1;
            background: #2e6b35;
            color: #ffffff;
            padding: 14px 52px 14px 22px;
            clip-path: polygon(0 0, 100% 0, calc(100% - 40px) 100%, 0 100%);
            border-radius: 4px;
        }
        .panel-banner-title {
            font-size: 1.55rem;
            font-weight: 800;
            line-height: 1.25;
        }
        .panel-banner-desc {
            font-size: .95rem;
            color: rgba(255, 255, 255, 0.88);
            margin-top: 3px;
        }

        /* 연한 초록 안내 박스 (파란 info 대체) */
        .soft-notice {
            background: #eef1e8;
            border: 1px solid #dfe6d6;
            border-radius: 12px;
            padding: 14px 16px;
            color: #33402c;
        }

        /* [6] DTO-5: 나비형 4분할 + 중앙 서버 아이콘 */
        .dto5-quad {
            position: relative;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 18px;
            margin: 6px 0 10px;
        }
        .dto5-quad-bubble {
            min-height: 190px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }
        .dto5-quad-row {
            display: flex;
            flex-wrap: wrap;
            gap: 6px 52px;
        }
        .dto5-quad .dto5-quad-bubble:nth-child(1) .dto5-quad-row,
        .dto5-quad .dto5-quad-bubble:nth-child(3) .dto5-quad-row {
            justify-content: flex-end;
        }
        .dto5-quad .dto1-bubble::after {
            display: none; /* 말풍선 꼬리는 사용하지 않음 */
        }
        /* 꽃잎 구도: 바깥과 중앙 대각 모서리는 뾰족, 나머지 두 모서리는 크게 둥글린다 */
        .dto5-quad .dto5-quad-bubble:nth-child(1) { border-radius: 6px 64px 6px 64px; }
        .dto5-quad .dto5-quad-bubble:nth-child(2) { border-radius: 64px 6px 64px 6px; }
        .dto5-quad .dto5-quad-bubble:nth-child(3) { border-radius: 64px 6px 64px 6px; }
        .dto5-quad .dto5-quad-bubble:nth-child(4) { border-radius: 6px 64px 6px 64px; }
        /* 글씨는 중앙(서버 아이콘) 쪽으로 정렬하되 중앙과 여유를 둔다 */
        .dto5-quad .dto5-quad-bubble:nth-child(1),
        .dto5-quad .dto5-quad-bubble:nth-child(3) {
            text-align: right;
            padding-right: 130px;
        }
        .dto5-quad .dto5-quad-bubble:nth-child(1) .dto1-label-row,
        .dto5-quad .dto5-quad-bubble:nth-child(3) .dto1-label-row {
            justify-content: flex-end;
        }
        .dto5-quad .dto5-quad-bubble:nth-child(2),
        .dto5-quad .dto5-quad-bubble:nth-child(4) {
            padding-left: 130px;
        }
        .dto5-quad-center {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 122px;
            height: 122px;
            border-radius: 999px;
            background: #ffffff;
            box-shadow: 0 0 0 12px #ffffff;
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 2;
        }
        .dto5-quad-center img {
            width: 62px;
            height: 62px;
        }

        /* [4] What-If: VS 게이지 레이아웃 */
        .whatif-vs {
            text-align: center;
            font-size: 1.9rem;
            font-weight: 900;
            color: #1f2937;
            padding-top: 14px;
            line-height: 1.1;
        }
        .whatif-side-title {
            text-align: center;
            font-size: 1.2rem;
            font-weight: 800;
            color: #1f2937;
            margin: 0 0 2px;
        }
        .whatif-side-status {
            text-align: center;
            color: #475467;
            font-size: 1rem;
            margin: 0 0 4px;
        }
        .whatif-side-status b { color: #111827; }
        .whatif-track {
            height: 26px;
            border-radius: 999px;
            /* 파란기 없는 웜 그레이 바탕 */
            background: #f1f0ec;
            overflow: hidden;
        }
        .whatif-track.left {
            display: flex;
            justify-content: flex-end;
        }
        .whatif-fill {
            height: 100%;
            border-radius: 999px;
        }
        .whatif-fill.left { background: #9aa19a; }
        .whatif-metric-label {
            text-align: center;
            font-size: 1.06rem;
            font-weight: 800;
            color: #2e6b35;
        }
        .whatif-bar-value {
            font-size: 1.06rem;
            font-weight: 700;
            color: #111827;
            white-space: nowrap;
        }
        .whatif-bar-value.left { text-align: right; }
        /* 오른쪽 게이지: 슬라이더 자체를 26px 알약 막대로 스타일링.
           채움은 테마 primary에 filter를 걸어 연한 초록 톤으로, 바탕은 밝은 웜 그레이로 보인다. */
        [class*="st-key-wfbar_"] [data-testid="stSlider"] {
            padding: 0;
        }
        [class*="st-key-wfbar_"] div[data-baseweb="slider"] {
            height: 30px;
            align-items: center;
            padding-top: 0;
            padding-bottom: 0;
        }
        [class*="st-key-wfbar_"] [data-testid="stSlider"] {
            min-height: 30px;
        }
        [class*="st-key-wfbar_"] div[data-baseweb="slider"] > div:first-child {
            position: relative;
        }
        /* 네이티브 트랙은 투명화하고, 실제 게이지는 파이썬이 주입하는
           ::before 알약(왼쪽 막대와 동일한 색 gradient)이 그린다 */
        [class*="st-key-wfbar_"] div[data-baseweb="slider"] > div:first-child > div {
            background: transparent !important;
        }
        [class*="st-key-wfbar_"] div[data-baseweb="slider"] {
            z-index: 1;
        }
        [class*="st-key-wfbar_"] [data-testid="stSliderTickBarMin"],
        [class*="st-key-wfbar_"] [data-testid="stSliderTickBarMax"],
        [class*="st-key-wfbar_"] [data-testid="stSliderThumbValue"] {
            display: none;
        }
        [class*="st-key-wfbar_"] div[data-baseweb="slider"] [role="slider"] {
            width: 24px;
            height: 24px;
            background: #2e6b35;
            border: 2px solid #ffffff;
            box-shadow: 0 1px 5px rgba(0, 0, 0, 0.3);
            cursor: grab;
        }
        [class*="st-key-wfbar_"] div[data-baseweb="slider"] [role="slider"]:active {
            cursor: grabbing;
        }

        /* [2] Feature: 좌우 번갈아 배치되는 라운드 밴드 */
        .feature-band-row {
            display: flex;
            align-items: center;
            margin: 18px 0;
        }
        .feature-band-row.reverse {
            flex-direction: row-reverse;
        }
        .feature-band {
            flex: 0 0 62%;
            background: #e4e9db;
            padding: 20px 30px;
        }
        .feature-band-row:not(.reverse) .feature-band {
            border-radius: 0 999px 999px 0;
            margin-left: -1rem;
            padding-left: calc(1rem + 30px);
            padding-right: 56px;
        }
        .feature-band-row.reverse .feature-band {
            border-radius: 999px 0 0 999px;
            margin-right: -1rem;
            padding-right: calc(1rem + 30px);
            padding-left: 56px;
        }
        .feature-band-label {
            color: #667085;
            font-size: 1rem;
            font-weight: 500;
        }
        .feature-band-value {
            color: #111827;
            font-size: 1.2rem;
            font-weight: 800;
            margin: 2px 0 10px;
        }
        .feature-band-sub {
            color: #667085;
            font-size: 1rem;
            font-weight: 500;
            margin-top: 6px;
        }
        .feature-band-text {
            color: #1f2937;
            font-size: 1.1rem;
            font-weight: 700;
            line-height: 1.45;
        }
        .feature-band-connector {
            flex: 1;
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 0 16px;
        }
        .feature-band-row.reverse .feature-band-connector {
            flex-direction: row-reverse;
        }
        .feature-band-connector .knot {
            flex: 0 0 auto;
            width: 15px;
            height: 15px;
            border-radius: 999px;
            background: #c9d4bb;
        }
        .feature-band-connector .line {
            flex: 1;
            border-top: 3px dashed #c9d4bb;
        }
        .feature-band-name {
            flex: 0 0 auto;
            font-weight: 800;
            color: #2e6b35;
            font-size: 1.2rem;
            letter-spacing: .02em;
        }
        /* 오른쪽에 놓이는 feature 이름과 점선 사이 간격 */
        .feature-band-row:not(.reverse) .feature-band-name {
            margin-left: 14px;
        }

        /* [1] Input: 말풍선 4개 + 중앙 워치 구도 */
        .dto1-bubble-row {
            display: flex;
            gap: 18px;
            align-items: stretch;
            flex-wrap: wrap;
            margin: 6px 0 0;
        }
        .dto1-bubble {
            position: relative;
            flex: 1 1 0;
            min-width: 200px;
            background: var(--bubble, #e2e8d9);
            border-radius: 26px;
            padding: 18px 18px 20px;
        }
        .dto1-bubble-title {
            font-weight: 800;
            color: #2e6b35;
            font-size: 1.2rem;
            margin-bottom: 10px;
        }
        .dto1-bubble .dto1-value {
            font-size: 1.2rem;
        }
        .dto1-bubble::after {
            content: "";
            position: absolute;
            bottom: -16px;
            width: 0;
            height: 0;
            border: 17px solid transparent;
            border-top-color: var(--bubble, #e2e8d9);
            border-bottom: 0;
        }
        .dto1-bubble:nth-child(1)::after { right: 24px; transform: skewX(28deg); }
        .dto1-bubble:nth-child(2)::after { right: 34%; transform: skewX(14deg); }
        .dto1-bubble:nth-child(3)::after { left: 34%; transform: skewX(-14deg); }
        .dto1-bubble:nth-child(4)::after { left: 24px; transform: skewX(-28deg); }
        .dto1-watch {
            display: flex;
            justify-content: center;
            margin: 30px 0 6px;
        }
        .dto1-watch img {
            width: 96px;
            height: 96px;
        }
        .dto1-watch-time {
            text-align: center;
            color: #33402c;
            line-height: 1.45;
            margin: 0 0 22px;
        }
        .dto1-watch-time .time-label {
            font-weight: 800;
            color: #2e6b35;
            font-size: .95rem;
        }
        .dto1-watch-time .time-value {
            font-size: 1rem;
            font-weight: 600;
        }

        /* 시나리오 헤더: 초록 배너 + 겹치는 요약 카드 */
        .scenario-hero {
            /* 테마 primary(#2e6b35) 기준 초록. 본문 컨테이너 패딩(1rem)만큼
               좌우로 당겨 가로 가득 배치한다. */
            background: linear-gradient(135deg, #2e6b35 0%, #1d4a26 100%);
            border-radius: 0;
            margin-left: -1rem;
            margin-right: -1rem;
            padding: 32px calc(1rem + 34px) 88px;
            color: #ffffff;
        }
        .scenario-hero-eyebrow {
            color: rgba(255, 255, 255, 0.78);
            font-weight: 800;
            letter-spacing: .08em;
            font-size: .9rem;
        }
        .scenario-hero-title {
            color: #ffffff !important;
            font-size: 2.7rem;
            line-height: 1.15;
            font-weight: 900;
            letter-spacing: -0.04em;
            margin: 10px 0 0;
            padding: 0;
        }
        .scenario-hero-summary {
            position: relative;
            z-index: 2;
            margin: -62px 24px 0;
        }
        .safe-card.amber { background: #fff8ec; border-color: #f1d19a; }
        .safe-card.red { background: #fff3f3; border-color: #efc0c0; }
        .safe-card h3, .safe-card h4 { margin-top: 0; color: var(--safe-navy); }
        .safe-card h3 { font-size: 1.55rem; }
        .safe-card h4 { font-size: 1.2rem; }
        .safe-card .big { font-size: 2.05rem; font-weight: 900; color: var(--safe-navy); }

        .panel-description {
            color: #98a2b3;
            font-size: 1rem;
            line-height: 1.65;
            margin: -8px 0 18px;
        }
        .dto1-time-card {
            margin: 0 0 16px;
        }
        .dto1-time-value {
            display: inline-block;
            margin-left: 18px;
        }
        .dto1-time-muted {
            color: #667085;
            margin-left: 12px;
        }
        .dto1-card {
            min-height: 410px;
            height: 410px;
            box-sizing: border-box;
            overflow: visible;
        }
        [data-testid="column"]:has(.dto1-card),
        [data-testid="stVerticalBlock"]:has(.dto1-card),
        [data-testid="stHorizontalBlock"]:has(.dto1-card),
        [data-testid="column"]:has(.feature-card),
        [data-testid="stVerticalBlock"]:has(.feature-card),
        [data-testid="stHorizontalBlock"]:has(.feature-card),
        [data-testid="column"]:has(.model-metric-card),
        [data-testid="stVerticalBlock"]:has(.model-metric-card),
        [data-testid="stHorizontalBlock"]:has(.model-metric-card),
        [data-testid="column"]:has(.model-step-card),
        [data-testid="stVerticalBlock"]:has(.model-step-card),
        [data-testid="stHorizontalBlock"]:has(.model-step-card),
        [data-testid="column"]:has(.maml-persona-card),
        [data-testid="stVerticalBlock"]:has(.maml-persona-card),
        [data-testid="stHorizontalBlock"]:has(.maml-persona-card) {
            overflow: visible !important;
        }
        .dto1-main-value {
            color: var(--safe-navy);
            font-size: 1.72rem;
            font-weight: 900;
            line-height: 1.22;
            margin: 26px 0 16px;
        }
        .dto1-metric-block {
            margin: 13px 0 15px;
        }
        .dto1-label-row {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            margin-bottom: 3px;
        }
        .dto1-label {
            color: #667085;
            font-size: 1rem;
            font-weight: 500;
            line-height: 1.35;
        }
        .dto1-tooltip {
            position: relative;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 16px;
            height: 16px;
            border-radius: 999px;
            background: #f1f0ec;
            color: #667085;
            font-size: .72rem;
            font-weight: 800;
            cursor: help;
        }
        .dto1-tooltip-text {
            visibility: hidden;
            opacity: 0;
            position: absolute;
            left: 50%;
            bottom: calc(100% + 8px);
            transform: translateX(-50%);
            min-width: 230px;
            max-width: 280px;
            padding: 9px 11px;
            border-radius: 10px;
            background: #10233f;
            color: #ffffff;
            font-size: .9rem;
            font-weight: 600;
            line-height: 1.45;
            box-shadow: 0 10px 24px rgba(16, 35, 63, .18);
            z-index: 9999;
            white-space: normal;
            word-break: keep-all;
        }
        .dto1-tooltip.dto1-tooltip-wide .dto1-tooltip-text {
            min-width: 480px;
            max-width: 620px;
            white-space: nowrap;
        }
        .dto1-tooltip.dto1-tooltip-nowrap .dto1-tooltip-text {
            min-width: max-content;
            max-width: none;
            white-space: nowrap;
        }
        .dto1-tooltip:hover .dto1-tooltip-text {
            visibility: visible;
            opacity: 1;
        }
        .dto1-expander-gap {
            height: 24px;
        }

        .feature-card {
            min-height: 290px;
            height: 290px;
            box-sizing: border-box;
            overflow: visible;
        }
        .feature-metric-block {
            margin-top: 18px;
        }
        .feature-table-gap {
            height: 28px;
        }
        .feature-plain-desc {
            color: #667085;
            font-size: 1rem;
            font-weight: 500;
            line-height: 1.45;
            margin-top: 12px;
            word-break: keep-all;
        }
        .feature-formula-box {
            border-top: 1px solid #edf1f7;
            margin-top: 22px;
            padding-top: 12px;
        }
        .feature-formula-row {
            margin-bottom: 10px;
        }
        .feature-formula-label {
            display: block;
            color: #667085;
            font-size: .95rem;
            font-weight: 500;
            margin-bottom: 3px;
        }
        .feature-formula-text {
            display: block;
            color: #475467;
            font-size: 1rem;
            line-height: 1.45;
            font-weight: 500;
            word-break: keep-all;
        }
        .dto1-value {
            color: var(--safe-navy);
            font-size: 1.72rem;
            font-weight: 900;
            line-height: 1.18;
        }
        .dto1-note {
            color: #667085;
            font-size: 1rem;
            font-weight: 500;
            line-height: 1.5;
            margin-top: 3px;
            word-break: keep-all;
        }
        .safe-muted { color: var(--safe-gray); font-size: 1.06rem; line-height: 1.65; }
        .safe-pill {
            display: inline-flex; align-items: center; gap: 6px;
            padding: 6px 11px; border-radius: 999px; background: #eef1e8;
            border: 1px solid #dfe6d6; color: #33402c; font-weight: 800; font-size: .84rem;
        }
        .safe-pill.gray { background: #f2f4f7; border-color: #e4e7ec; color: #667085; }
        .safe-pill.green { background: #eaf8f0; border-color: #c7ead5; color: #16734f; }
        .safe-pill.amber { background: #fff4db; border-color: #f3d28b; color: #8a5900; }
        /* 시나리오 선택: 표지 카드 위로 종이가 덮이는 hover 연출 */
        .scenario-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 16px;
        }
        a.scenario-card, a.scenario-card:hover { text-decoration: none; }
        .scenario-card {
            position: relative;
            display: block;
            height: 214px;
            border: 1px solid var(--safe-border);
            border-radius: 20px;
            background: #ffffff;
            box-sizing: border-box;
            overflow: hidden;
            box-shadow: 0 8px 22px rgba(16,35,63,.06);
        }
        .scenario-face {
            display: flex;
            flex-direction: column;
            height: 100%;
            padding: 18px 18px 16px;
            box-sizing: border-box;
        }
        .scenario-code { font-size: .9rem; color: #2e6b35; font-weight: 900; letter-spacing: .04em; }
        .scenario-title { font-size: 1.12rem; font-weight: 900; color: #1f2937; margin: 6px 0 8px; line-height: 1.35; word-break: keep-all; }
        .scenario-status { margin-top: auto; padding-top: 12px; }
        /* 종이: 크림색 배경과 연초록 괘선, hover 시 살짝 기울며 카드를 덮음 */
        .scenario-paper {
            position: absolute;
            left: -5%;
            top: 0;
            width: 110%;
            height: 106%;
            box-sizing: border-box;
            /* 좌우 5% 돌출과 회전 기울기를 감안해 안쪽 여백을 넉넉히 확보 */
            padding: 24px 42px 28px;
            background: #f7f5ef;
            border-bottom: 1px solid #e3ded2;
            transform: translateY(-114%);
            transition: transform .45s cubic-bezier(.25, .8, .3, 1);
            display: flex;
            flex-direction: column;
        }
        .scenario-card:hover .scenario-paper,
        .scenario-card:focus-visible .scenario-paper {
            transform: translateY(-3%) rotate(-1.1deg);
        }
        .scenario-paper::before {
            content: "";
            position: absolute;
            inset: 0;
            background: repeating-linear-gradient(0deg, transparent 0 30px, rgba(46, 107, 53, .06) 30px 31px);
            pointer-events: none;
        }
        /* SCENARIO 코드 왼쪽, 종이 위 테두리에서 늘어뜨린 책갈피 (하단 V 홈) */
        .scenario-paper-ribbon {
            position: absolute;
            top: 0;
            left: 42px;
            width: 16px;
            height: 46px;
            background: #2e6b35;
            clip-path: polygon(0 0, 100% 0, 100% 100%, 50% calc(100% - 8px), 0 100%);
        }
        .scenario-paper-code {
            position: relative;
            font-size: .78rem;
            font-weight: 800;
            color: #33402c;
            letter-spacing: .07em;
            margin-top: 2px;
            margin-left: 28px;
        }
        .scenario-paper-desc { position: relative; font-size: .95rem; color: #33402c; line-height: 1.55; margin-top: 8px; word-break: keep-all; }
        .scenario-paper-meta { position: relative; font-size: .84rem; color: #7a8471; line-height: 1.5; margin-top: 8px; word-break: keep-all; }
        .scenario-paper-open {
            position: relative;
            margin-top: auto;
            align-self: flex-end;
            font-size: .9rem;
            font-weight: 800;
            color: #2e6b35;
        }
        .scenario-arrow { display: inline-block; margin-top: 4px; }
        div.stButton > button[kind="primary"],
        div.stButton > button[data-testid="baseButton-primary"] {
            background: #2e6b35 !important;
            border-color: #2e6b35 !important;
            color: #ffffff !important;
            font-weight: 900 !important;
        }
        div.stButton > button[kind="primary"]:hover,
        div.stButton > button[data-testid="baseButton-primary"]:hover {
            background: #367b3f !important;
            border-color: #367b3f !important;
            color: #ffffff !important;
        }
        .pipeline-strip {
            display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 8px; margin: 18px 0 10px;
        }
        .pipeline-step {
            border: 1px solid var(--safe-border); border-radius: 14px; padding: 12px 10px; background: #ffffff; text-align: center;
            font-weight: 800; font-size: .84rem; color: var(--safe-navy);
        }
        .pipeline-step span { display: block; color: var(--safe-gray); font-size: .76rem; font-weight: 700; margin-bottom: 3px; }
        .risk-gauge-wrap { position: relative; margin: 22px 0 20px; padding-top: 30px; }
        .risk-gauge {
            position: relative;
            height: 34px;
            border-radius: 999px;
            overflow: hidden;
            border: 1px solid #dfe6d6;
            background: linear-gradient(to right, #e8f5ed 0%, #e8f5ed 50%, #fff4db 50%, #fff4db 65%, #ffe0e0 65%, #ffe0e0 85%, #f2b6b6 85%, #f2b6b6 100%);
        }
        .risk-marker {
            position: absolute;
            top: -8px;
            width: 4px;
            height: 50px;
            background: #111827;
            border-radius: 99px;
            box-shadow: 0 0 0 2px #fff;
        }
        .risk-marker-label {
            position: absolute;
            top: 0;
            transform: translateX(-50%);
            font-size: 1.06rem;
            font-weight: 900;
            white-space: nowrap;
            letter-spacing: -0.01em;
        }
        .risk-axis {
            position: relative;
            height: 44px;
            margin-top: 2px;
        }
        .risk-axis .risk-label {
            position: absolute;
            top: 0;
            transform: translateX(-50%);
            color: #344054;
            font-size: 1.06rem;
            font-weight: 600;
            white-space: nowrap;
        }
        .risk-axis .risk-tick {
            position: absolute;
            top: 24px;
            transform: translateX(-50%);
            color: #667085;
            font-size: 1rem;
            font-weight: 500;
            white-space: nowrap;
        }
        .risk-axis .risk-tick.first { transform: translateX(0); }
        .risk-axis .risk-tick.last { transform: translateX(-100%); }
        .risk-zone-card {
            transition: background-color .16s ease, border-color .16s ease;
        }
        .risk-zone-normal {
            background: #f2fbf7 !important;
            border-color: #cdebdc !important;
        }
        .risk-zone-normal b { color: #16734f; }
        .risk-zone-caution {
            background: #fff8ec !important;
            border-color: #f1d19a !important;
        }
        .risk-zone-caution b { color: #8a5900; }
        .risk-zone-warning {
            background: #fff3f3 !important;
            border-color: #efc0c0 !important;
        }
        .risk-zone-warning b { color: #b42318; }
        .risk-zone-danger {
            background: #ffe9e9 !important;
            border-color: #e99a9a !important;
        }
        .risk-zone-danger b { color: #8f1010; }
        .model-button-gap { height: 14px; }
        .model-section-gap { height: 34px; }
        .model-after-steps-gap { height: 34px; }
        .model-importance-item {
            margin: 0 0 22px;
        }
        .model-importance-title {
            color: var(--safe-navy);
            font-size: 1.2rem;
            font-weight: 800;
            line-height: 1.45;
        }
        .model-importance-title span {
            color: #475467;
            font-weight: 600;
        }
        .model-importance-reason {
            color: #667085;
            font-size: 1.06rem;
            line-height: 1.65;
            margin-top: 8px;
        }
        .model-metric-card {
            min-height: 160px;
            height: 160px;
            box-sizing: border-box;
            overflow: visible;
        }
        .model-metric-value { margin-top: 4px; }
        .model-metric-desc {
            color: #667085;
            font-size: 1rem;
            font-weight: 500;
            line-height: 1.45;
            margin-top: 18px;
            word-break: keep-all;
        }
        .model-step-card {
            min-height: 430px;
            height: 430px;
            box-sizing: border-box;
            overflow: visible;
        }
        .model-step-summary {
            color: #475467;
            font-size: 1rem;
            line-height: 1.58;
            min-height: 76px;
            word-break: keep-all;
            font-weight: 500;
        }
        .model-step-value {
            margin: 12px 0 16px;
        }
        .model-formula-line {
            border-top: 1px solid #edf1f7;
            padding-top: 8px;
            margin-top: 8px;
        }
        .model-formula-label {
            display: block;
            color: #667085;
            font-size: .95rem;
            font-weight: 500;
            margin-bottom: 4px;
        }
        .model-formula-text {
            display: block;
            color: #475467;
            font-size: 1rem;
            line-height: 1.5;
            font-weight: 500;
            word-break: keep-all;
        }

        .whatif-current-line {
            color: var(--safe-navy);
            font-size: 1.12rem;
            line-height: 1.75;
            margin: 0 0 10px;
        }
        .whatif-current-line b {
            font-size: 1.12rem;
            font-weight: 900;
        }
        .main [data-testid="stSlider"] label,
        .main [data-testid="stSlider"] label p {
            font-size: 1.06rem !important;
            color: var(--safe-navy) !important;
            font-weight: 600 !important;
        }
        .main [data-testid="stSlider"] [data-testid="stTickBarMin"],
        .main [data-testid="stSlider"] [data-testid="stTickBarMax"] {
            font-size: 1rem !important;
        }
        .main [data-testid="stSlider"] {
            font-size: 1.06rem !important;
        }
        .whatif-result-gap { height: 28px; }
        .whatif-info-gap { height: 18px; }

        .maml-hero-card {
            border: 1px solid #cdebdc;
            border-radius: 24px;
            padding: 24px 26px;
            background: linear-gradient(135deg, #f2fbf7 0%, #ffffff 58%, #fff8ec 100%);
            box-shadow: 0 12px 30px rgba(16, 35, 63, 0.08);
            display: grid;
            grid-template-columns: minmax(0, 1.7fr) minmax(240px, .7fr);
            gap: 22px;
            align-items: center;
            margin-bottom: 28px;
        }
        .maml-hero-title {
            color: var(--safe-navy);
            font-size: 1.55rem;
            font-weight: 900;
            letter-spacing: -.02em;
            margin-bottom: 8px;
        }
        .maml-hero-desc {
            color: #667085;
            font-size: 1.06rem;
            line-height: 1.65;
            word-break: keep-all;
        }
        .maml-current-box {
            border: 1px solid #e2e5dc;
            border-radius: 18px;
            background: rgba(255,255,255,.78);
            padding: 18px 20px;
        }
        .maml-current-box span {
            display: block;
            color: #667085;
            font-size: 1rem;
            font-weight: 600;
            margin-bottom: 4px;
        }
        .maml-current-box b {
            display: block;
            color: var(--safe-navy);
            font-size: 2.1rem;
            line-height: 1.15;
        }
        .maml-current-box em {
            display: block;
            color: #475467;
            font-style: normal;
            font-size: 1rem;
            line-height: 1.5;
            margin-top: 8px;
        }
        .maml-flow {
            display: grid;
            grid-template-columns: minmax(0, 1fr) 64px minmax(0, 1fr);
            gap: 18px;
            align-items: center;
            margin: 8px 0 28px;
        }
        .maml-flow-card {
            border: 1px solid var(--safe-border);
            border-radius: 20px;
            background: #ffffff;
            padding: 20px 22px;
            min-height: 142px;
            box-shadow: 0 8px 24px rgba(16, 35, 63, .05);
        }
        .maml-flow-card.highlight {
            background: #f2fbf7;
            border-color: #cdebdc;
        }
        .maml-flow-card span {
            color: #667085;
            font-size: .95rem;
            font-weight: 700;
        }
        .maml-flow-card b {
            display: block;
            color: var(--safe-navy);
            font-size: 1.2rem;
            margin: 8px 0 8px;
        }
        .maml-flow-card p {
            color: #667085;
            font-size: 1rem;
            line-height: 1.55;
            margin: 0;
            word-break: keep-all;
        }
        .maml-flow-arrow {
            color: #2e6b35;
            font-size: 2.4rem;
            font-weight: 900;
            text-align: center;
        }
        .maml-persona-card {
            border: 1px solid var(--safe-border);
            border-radius: 22px;
            background: #ffffff;
            padding: 22px 22px 20px;
            min-height: 340px;
            box-shadow: 0 10px 28px rgba(16,35,63,.06);
        }
        .maml-persona-card.neutral { background: #f8f9f4; }
        .maml-persona-card.low { background: #fff8ec; border-color: #f1d19a; }
        .maml-persona-card.high { background: #f2fbf7; border-color: #cdebdc; }
        .maml-persona-title {
            color: var(--safe-navy);
            font-size: 1.2rem;
            font-weight: 900;
            margin-bottom: 6px;
        }
        .maml-persona-subtitle {
            color: #667085;
            font-size: 1rem;
            line-height: 1.5;
            min-height: 48px;
            word-break: keep-all;
        }
        .maml-divider {
            height: 1px;
            background: #e7edf7;
            margin: 16px 0;
        }
        .maml-metric-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 14px;
            margin-bottom: 16px;
        }
        .maml-metric-row > div > span {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            color: #667085;
            font-size: .95rem;
            font-weight: 600;
            margin-bottom: 5px;
        }
        .maml-metric-row .dto1-tooltip {
            display: inline-flex !important;
            flex: 0 0 auto;
        }
        .maml-metric-row b {
            display: block;
            color: var(--safe-navy);
            font-size: 1.42rem;
            font-weight: 900;
            line-height: 1.25;
        }

        .maml-tooltip .dto1-tooltip-text {
            min-width: 500px;
            max-width: 620px;
            background: #10233f !important;
            color: #ffffff !important;
            font-weight: 600 !important;
            white-space: normal;
        }
        .maml-detail-gap {
            height: 24px;
        }

        .maml-result-row {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 16px;
        }
        .maml-risk-pill,
        .maml-state-pill {
            display: inline-flex;
            border-radius: 999px;
            padding: 7px 12px;
            font-size: .9rem;
            font-weight: 800;
            border: 1px solid #e4e7ec;
            background: #ffffff;
            color: #344054;
        }
        .maml-risk-pill.normal { background: #eaf8f0; border-color: #c7ead5; color: #16734f; }
        .maml-risk-pill.caution { background: #fff4db; border-color: #f3d28b; color: #8a5900; }
        .maml-risk-pill.warning { background: #fff3f3; border-color: #efc0c0; color: #b42318; }
        .maml-risk-pill.danger { background: #ffe9e9; border-color: #e99a9a; color: #8f1010; }
        .maml-interpretation {
            color: #475467;
            font-size: 1rem;
            line-height: 1.55;
            word-break: keep-all;
        }
        @media (max-width: 900px) {
            .maml-hero-card,
            .maml-flow {
                grid-template-columns: 1fr;
            }
            .maml-flow-arrow { transform: rotate(90deg); }
        }

        .status-hit { color: #16734f; font-weight: 900; }
        .status-miss { color: #667085; font-weight: 800; }
        .app-preview {
            border-radius: 28px; border: 1px solid #dfe6d6; background: #f8f9f4; padding: 22px;
            box-shadow: inset 0 0 0 8px #eef1e8;
        }
        .app-preview-inner { background: #ffffff; border-radius: 22px; padding: 20px; border: 1px solid #e3e6dd; }
        .icon-row { display:flex; gap:12px; flex-wrap:wrap; align-items:center; margin: 8px 0; }
        .legend-dot { width: 14px; height: 14px; border-radius: 999px; display: inline-block; margin-right: 6px; vertical-align: middle; }
        .dot-blue { background:#2e6b35; } .dot-red { background:#c83e3e; }

        .dto5-core-card {
            min-height: 292px;
            height: 292px;
            box-sizing: border-box;
            overflow: visible;
        }
        .dto5-field-block {
            margin: 13px 0 16px;
        }
        .dto5-value {
            font-size: 1.48rem;
        }
        .dto5-note {
            word-break: keep-all;
        }
        .dto5-section-gap {
            height: 34px;
        }
        .dto5-alert-wide {
            margin-top: 18px;
            min-height: 170px;
            height: auto;
            box-sizing: border-box;
        }
        .dto5-alert-grid {
            display: grid;
            grid-template-columns: minmax(170px, .8fr) minmax(0, 2.2fr);
            gap: 22px;
            align-items: start;
        }
        .dto5-alert-title {
            font-size: 1.2rem;
            line-height: 1.45;
            font-weight: 800;
        }
        .dto5-alert-message {
            color: var(--safe-navy);
            font-size: 1.25rem;
            font-weight: 800;
            line-height: 1.45;
            word-break: keep-all;
        }
        .dto5-map-legend {
            font-size: 1rem;
            font-weight: 600;
            color: #344054;
        }
        .mountain-mark {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 18px;
            height: 18px;
            margin-right: 6px;
            color: #2e6b35;
            font-weight: 900;
            vertical-align: middle;
        }
        .infer-save-gap {
            height: 14px;
        }

        /* ── 사이드바 디자인 통일 (Streamlit 1.45.1 고정 전제) ──
           배경은 hero 배너와 같은 진초록 계열, 바탕 위 글씨는 흰색,
           카드류(시점 박스, expander)는 흰 카드로 띄워 대비 확보 */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #2e6b35 0%, #235229 100%);
            border-right: 1px solid #1d4a26;
        }
        [data-testid="stSidebar"] hr {
            border-color: rgba(255, 255, 255, .25);
        }
        [data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"],
        [data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] button {
            color: #ffffff !important;
        }
        /* 진초록 바탕 위 위젯 라벨: 셀렉트박스, 슬라이더, 토글, 라디오 등 (monitor 사이드바 포함)
           expander 흰 카드 내부에는 위젯 라벨이 없다는 전제의 규칙 */
        [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
        [data-testid="stSidebar"] [data-testid="stCheckbox"] p,
        [data-testid="stSidebar"] [data-testid="stRadio"] label p {
            color: #ffffff !important;
        }
        /* 진초록 바탕 위 슬라이더: 핸들 흰색, 트랙 세이지, 값 표기는 흰색 */
        [data-testid="stSidebar"] [data-testid="stSlider"] div[role="slider"] {
            background-color: #ffffff !important;
            border-color: #ffffff !important;
            box-shadow: 0 0 0 1px #dfe6d6 !important;
        }
        [data-testid="stSidebar"] [data-testid="stSlider"] [data-baseweb="slider"] div[style*="background"] {
            background-color: #a3b285 !important;
        }
        [data-testid="stSidebar"] [data-testid="stSliderThumbValue"],
        [data-testid="stSidebar"] [data-testid="stSliderTickBarMin"],
        [data-testid="stSidebar"] [data-testid="stSliderTickBarMax"] {
            color: #ffffff !important;
        }
        /* 진초록 바탕에 직접 놓이는 링크 (실시간 모니터링, GitHub) */
        [data-testid="stSidebar"] .sidebar-nav-monitor a,
        [data-testid="stSidebar"] .project-link {
            color: rgba(255, 255, 255, .94) !important;
        }
        [data-testid="stSidebar"] .sidebar-nav-monitor a:hover,
        [data-testid="stSidebar"] .project-link:hover {
            background: rgba(255, 255, 255, .12);
            border-color: rgba(255, 255, 255, .35);
            color: #ffffff !important;
        }
        /* 시나리오 expander: 흰 카드, 펼친 항목은 진초록 세로 바와 연초록 배경으로 강조 */
        [data-testid="stSidebar"] [data-testid="stExpander"] details {
            background: #ffffff;
            border: 1px solid #e3e6dd;
            border-radius: 10px;
        }
        [data-testid="stSidebar"] [data-testid="stExpander"] details[open] {
            border-color: #c7dfc8;
        }
        [data-testid="stSidebar"] [data-testid="stExpander"] details[open] > summary {
            background: #eef7ef;
            box-shadow: inset 4px 0 0 #2e6b35;
        }

        .sidebar-time-box {
            margin-top: 10px;
            margin-bottom: 16px;
            background: #ffffff;
            border: 1px solid #dfe6d6;
            border-radius: 12px;
            padding: 12px 14px;
        }
        .sidebar-time-label {
            color: #111827;
            font-size: .95rem;
            font-weight: 900;
            margin-bottom: 4px;
        }
        .sidebar-time-value {
            color: #2e6b35;
            font-size: 1rem;
            font-weight: 800;
            line-height: 1.35;
        }
        .sidebar-section-heading {
            margin: 0 0 3px;
            padding-left: 10px;
            border-left: 4px solid #dfe6d6;
            color: #ffffff;
            font-size: 1.12rem;
            font-weight: 900;
            line-height: 1.25;
        }
        .sidebar-section-caption {
            margin: 0 0 8px;
            padding-left: 14px;
            color: rgba(255, 255, 255, .78);
            font-size: .95rem;
            font-weight: 400;
            line-height: 1.45;
        }
        .sidebar-nav {
            display: flex;
            flex-direction: column;
            gap: 6px;
            margin-top: 0;
        }
        .sidebar-nav a {
            display: block;
            padding: 7px 10px;
            border-radius: 10px;
            color: #1f2937 !important;
            text-decoration: none !important;
            font-weight: 700;
            border: 1px solid transparent;
            line-height: 1.25;
        }
        .scenario-sidebar-nav {
            margin-top: 0;
            padding-top: 0;
        }

        /* 사이드바 시나리오 expander 라벨: 긴 제목이 잘리지 않도록 줄바꿈 허용 */
        [data-testid="stSidebar"] details summary p,
        [data-testid="stSidebar"] details summary span {
            white-space: normal !important;
            overflow: visible !important;
            text-overflow: clip !important;
            word-break: keep-all;
            line-height: 1.35;
        }
        [data-testid="stSidebar"] details summary [data-testid="stMarkdownContainer"] p {
            font-size: .95rem;
            font-weight: 700;
        }

        .scenario-sidebar-nav a {
            padding-left: 0.15rem;
        }

        .sidebar-nav a:hover {
            background: #eef7ef;
            border-color: #c7dfc8;
            color: #2e6b35 !important;
        }
        .panel-anchor {
            display: block;
            position: relative;
            top: -72px;
            visibility: hidden;
        }

        /* Streamlit slider accent color */
        [data-testid="stSlider"] div[role="slider"] {
            background-color: #2e6b35 !important;
            border-color: #2e6b35 !important;
            box-shadow: 0 0 0 1px #2e6b35 !important;
        }
        [data-testid="stSlider"] [data-baseweb="slider"] div[style*="background"] {
            background-color: #2e6b35 !important;
        }
        [data-testid="stSlider"] div[style*="rgb(255, 75, 75)"],
        [data-testid="stSlider"] div[style*="#ff4b4b"] {
            background-color: #2e6b35 !important;
            color: #2e6b35 !important;
        }
        body:has(.intro-root) .block-container {
            max-width: 100% !important;
            padding: 0 !important;
        }
        body:has(.intro-root) .main .block-container {
            padding-left: 0 !important;
            padding-right: 0 !important;
        }
        body:has(.intro-root) header[data-testid="stHeader"] {
            background: transparent;
        }
        .intro-link, .intro-link:hover, .intro-link:visited, .intro-link:active {
            color: inherit !important;
            text-decoration: none !important;
        }
        .intro-root {
            position: relative;
            min-height: calc(100vh - 1px);
            overflow: hidden;
            background-color: #16291c;
            color: #ffffff;
            padding: 70px 7.5vw 54px;
        }
        .intro-root::before {
            content: "";
            position: absolute;
            inset: 0;
            background:
                radial-gradient(circle at 72% 22%, rgba(75, 123, 79, .22), transparent 34%),
                linear-gradient(180deg, rgba(255,255,255,.03), rgba(255,255,255,0) 40%);
            pointer-events: none;
        }
        .intro-root::after {
            content: "";
            position: absolute;
            left: 0;
            right: 0;
            bottom: -2px;
            height: 38vh;
            background-image: var(--intro-mountain-url);
            background-repeat: repeat-x;
            background-position: bottom center;
            background-size: auto 100%;
            opacity: .96;
            pointer-events: none;
        }
        .intro-content {
            position: relative;
            z-index: 1;
            width: min(1260px, 100%);
            margin: 0 auto;
            min-height: calc(100vh - 124px);
            display: flex;
            flex-direction: column;
            text-align: left;
        }
        .intro-brand {
            display: grid !important;
            grid-template-columns: 58px minmax(0, auto);
            align-items: center;
            column-gap: 18px;
            width: fit-content;
            margin-bottom: 88px;
        }
        .intro-logo {
            width: 58px;
            height: 58px;
            object-fit: contain;
            border-radius: 999px;
            background: rgba(255,255,255,.94);
            box-shadow: 0 8px 26px rgba(0,0,0,.18);
        }
        .intro-lab-ko {
            color: #f7fff7;
            font-size: 1.12rem;
            font-weight: 900;
            letter-spacing: -.02em;
            margin-bottom: 3px;
        }
        .intro-eyebrow-line {
            color: rgba(255,255,255,.78);
            font-size: .82rem;
            font-weight: 800;
            letter-spacing: .08em;
        }
        .intro-title {
            max-width: 1150px;
            font-size: clamp(3.2rem, 6.3vw, 6.9rem);
            line-height: 1.02;
            font-weight: 900;
            letter-spacing: -.035em;
            margin: 0 0 22px;
            color: #ffffff;
            text-shadow: 0 10px 26px rgba(0,0,0,.18);
        }
        .intro-platform {
            display: flex;
            flex-wrap: wrap;
            align-items: baseline;
            gap: 18px;
            padding-top: 22px;
            border-top: 1px solid rgba(255,255,255,.34);
            font-size: clamp(1.65rem, 2.25vw, 2.55rem);
            font-weight: 800;
            letter-spacing: -.035em;
            color: rgba(255,255,255,.88);
        }
        .intro-platform .green { color: #9cc567; font-weight: 900; }
        .intro-platform .orange { color: #f2952d; font-weight: 900; }
        .intro-desc {
            max-width: 980px;
            margin-top: 30px;
            color: rgba(255,255,255,.80);
            font-size: 1.12rem;
            line-height: 1.75;
            font-weight: 600;
        }
        .intro-desc-line {
            display: block;
            white-space: nowrap;
        }
        .intro-footer {
            margin-top: auto;
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 26px 42px;
            color: rgba(255,255,255,.78);
            font-weight: 700;
            padding-bottom: 18px;
        }
        .intro-footer strong { color: #9cc567; margin-right: 8px; }
        .intro-cta {
            margin-top: 26px;
            display: inline-flex;
            width: fit-content;
            align-items: center;
            justify-content: center;
            gap: 10px;
            padding: 15px 46px;
            border-radius: 999px;
            background: #2e6b35;
            color: #ffffff !important;
            font-weight: 900;
            letter-spacing: .02em;
            box-shadow: 0 12px 28px rgba(0,0,0,.22);
            transition: transform .16s ease, background .16s ease;
        }
        .intro-cta:hover {
            background: #367b3f;
            transform: translateY(-1px);
        }
        @media (max-width: 760px) {
            .intro-root { padding: 54px 7vw 44px; }
            .intro-brand { margin-bottom: 54px; }
            .intro-title { font-size: 3rem; }
            .intro-root::after { height: 30vh; background-size: auto 100%; }
            .intro-desc { font-size: 1rem; }
        }
        /* ── 신규: 프로젝트 링크 (GitHub) — sidebar-nav와 동일한 시각 언어 ── */
        .project-link {
            display: inline-flex;
            align-items: center;
            gap: 9px;
            padding: 8px 11px;
            border-radius: 10px;
            border: 1px solid transparent;
            color: #1f2937 !important;
            text-decoration: none !important;
            font-weight: 700;
            line-height: 1.25;
        }
        .project-link:hover {
            background: #eef7ef;
            border-color: #c7dfc8;
            color: #2e6b35 !important;
        }
        .project-link img {
            width: 20px;
            height: 20px;
            border-radius: 999px;
            display: block;
        }
        .intro-footer .project-link {
            padding: 6px 10px;
            color: rgba(255,255,255,.86) !important;
            font-weight: 700;
        }
        .intro-footer .project-link:hover {
            background: rgba(255,255,255,.10);
            border-color: rgba(255,255,255,.28);
            color: #ffffff !important;
        }

        /* ── 신규: [3] Model Explanation 기여도 분해 바 ── */
        .model-contrib-row { margin: 0 0 14px; }
        .model-contrib-head {
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            margin-bottom: 5px;
        }
        .model-contrib-name {
            color: var(--safe-navy);
            font-size: 1rem;
            font-weight: 800;
        }
        .model-contrib-name span { color: #667085; font-weight: 600; font-size: .95rem; }
        .model-contrib-value { color: #344054; font-size: 1rem; font-weight: 800; }
        .model-contrib-track {
            height: 12px;
            border-radius: 999px;
            background: #f1f0ec;
            border: 1px solid #e3e6dd;
            overflow: hidden;
        }
        .model-contrib-fill {
            height: 100%;
            border-radius: 999px;
            background: linear-gradient(90deg, #2e6b35, #5b8f62);
        }
        .model-contrib-fill.green { background: linear-gradient(90deg, #1f7a5a, #35a37e); }
        .model-contrib-fill.amber { background: linear-gradient(90deg, #ad741b, #d29a3f); }
        .model-contrib-fill.gray { background: linear-gradient(90deg, #98a2b3, #b6bfcc); }

        /* ── 신규: 실시간 모니터링 페이지 ── */
        .monitor-risk-now {
            font-size: 0.72em;
            font-weight: 500;
            color: #5b6472;
            margin-left: 10px;
        }
        .monitor-live-pill {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 6px 12px;
            border-radius: 999px;
            background: #f2fbf7;
            border: 1px solid #cdebdc;
            color: #16734f;
            font-weight: 800;
            font-size: .9rem;
        }
        .monitor-live-pill.paused {
            background: #f2f4f7;
            border-color: #e4e7ec;
            color: #667085;
        }
        .monitor-live-dot {
            width: 9px;
            height: 9px;
            border-radius: 999px;
            background: #1f7a5a;
            animation: monitor-pulse 1.4s ease-in-out infinite;
        }
        .monitor-live-pill.paused .monitor-live-dot {
            background: #98a2b3;
            animation: none;
        }
        @keyframes monitor-pulse {
            0% { box-shadow: 0 0 0 0 rgba(31, 122, 90, .45); }
            70% { box-shadow: 0 0 0 8px rgba(31, 122, 90, 0); }
            100% { box-shadow: 0 0 0 0 rgba(31, 122, 90, 0); }
        }
        .monitor-metric-card {
            min-height: 150px;
            height: 150px;
            box-sizing: border-box;
            overflow: visible;
        }
        .monitor-inject-note {
            color: #667085;
            font-size: 1rem;
            line-height: 1.55;
            word-break: keep-all;
            margin: 6px 0 4px;
        }
        .scenario-card.monitor {
            border-color: #dfe6d6;
        }
        .scenario-card.monitor .scenario-face {
            background: #eef1e8;
        }

        /* ── 신규: 실시간 모니터링 세션 리스트 ── */
        .monitor-session-row {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px 12px;
            border: 1px solid var(--safe-border);
            border-radius: 14px;
            background: #ffffff;
            margin: 4px 0;
        }
        .monitor-session-row.selected {
            background: #f2fbf7;
            border-color: #cdebdc;
        }
        .monitor-session-meta {
            display: flex;
            flex-direction: column;
            min-width: 0;
        }
        .monitor-session-meta b {
            color: var(--safe-navy);
            font-size: 1rem;
            line-height: 1.3;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .monitor-session-meta span {
            color: #667085;
            font-size: .9rem;
            line-height: 1.35;
        }
        .monitor-session-dot {
            flex: 0 0 auto;
            width: 11px;
            height: 11px;
            border-radius: 999px;
        }
        .monitor-session-dot.normal { background: #1f7a5a; }
        .monitor-session-dot.caution { background: #d99a1b; }
        .monitor-session-dot.warning,
        .monitor-session-dot.danger {
            background: #c83e3e;
            animation: monitor-pulse-red 1.4s ease-in-out infinite;
        }
        @keyframes monitor-pulse-red {
            0% { box-shadow: 0 0 0 0 rgba(200, 62, 62, .5); }
            70% { box-shadow: 0 0 0 8px rgba(200, 62, 62, 0); }
            100% { box-shadow: 0 0 0 0 rgba(200, 62, 62, 0); }
        }
        .monitor-session-list {
            display: flex;
            flex-direction: column;
            gap: 3px;
        }
        .monitor-session-item {
            display: flex;
            align-items: center;
            gap: 9px;
            padding: 7px 10px;
            border-radius: 10px;
            border: 1px solid transparent;
            color: #1f2937 !important;
            text-decoration: none !important;
            font-weight: 700;
            line-height: 1.25;
        }
        a.monitor-session-item:hover {
            background: #eef7ef;
            border-color: #c7dfc8;
            color: #2e6b35 !important;
        }
        .monitor-session-item.selected {
            background: #f2fbf7;
            border-color: #cdebdc;
        }
        .monitor-session-id {
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            font-size: .9rem;
        }
        /* 사이드바 배치용 컴팩트 스타일 */
        [data-testid="stSidebar"] .monitor-session-row {
            padding: 8px 10px;
            margin: 3px 0;
            gap: 8px;
        }
        [data-testid="stSidebar"] .monitor-session-meta b {
            font-size: .9rem;
        }
        [data-testid="stSidebar"] .monitor-session-meta span {
            font-size: .8rem;
        }
        [data-testid="stSidebar"] .monitor-session-dot {
            width: 10px;
            height: 10px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def safe_html(text: object) -> str:
    return html.escape("" if text is None else str(text))


def scenario_desc_html(text: str) -> str:
    """시나리오 설명에서 대응 화살표(→) 뒷부분을 줄바꿈해 표시한다."""
    if "→" not in text:
        return safe_html(text)
    before, after = text.split("→", 1)
    return f"{safe_html(before.strip())}<br /><span class='scenario-arrow'>→ {safe_html(after.strip())}</span>"


def card(title: str, body: str, class_name: str = "soft") -> None:
    st.markdown(
        f"""
        <div class="safe-card {class_name}">
            <h4>{safe_html(title)}</h4>
            <div>{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_intro_page() -> None:
    logo_uri = _asset_data_uri("sookmyung_logo.webp", "image/webp")
    mountain_uri = _asset_data_uri("mountain.png", "image/png")
    logo_img = f'<img class="intro-logo" src="{logo_uri}" alt="Sookmyung logo" />' if logo_uri else ""
    mountain_style = f"--intro-mountain-url: url('{mountain_uri}');" if mountain_uri else ""

    # Introduction 화면은 전체 화면 클릭 이동을 사용하지 않습니다.
    # CTA 버튼만 시나리오 선택 화면으로 이동하도록 링크를 분리합니다.
    intro_html = (
        f'<section class="intro-root" style="{mountain_style}">'
        '<div class="intro-content">'
        '<div class="intro-brand">'
        f'{logo_img}'
        '<div class="intro-brand-copy">'
        '<div class="intro-lab-ko">숙명여자대학교 AGI 연구팀</div>'
        '<div class="intro-eyebrow-line">SOOKMYUNG WOMEN\'S UNIVERSITY AGI LAB</div>'
        '</div>'
        '</div>'
        '<h1 class="intro-title">산행안전 AI 시스템 개발 프로젝트</h1>'
        '<div class="intro-platform">'
        '<span class="green">오르다 AI</span>'
        '<span>—</span>'
        '<span>등산 <span class="orange">S·A·F·E</span> 플랫폼</span>'
        '</div>'
        '<p class="intro-desc">'
        '<span class="intro-desc-line">생체 데이터, 위치 데이터, 기상 정보를 기반으로 산행 중 위험 상황을 감지하고</span>'
        '<span class="intro-desc-line">휴식, 하산, 구조 대응을 지원하는 AI 검증 대시보드입니다.</span>'
        '</p>'
        '<a class="intro-link intro-cta" href="?page=scenario" target="_self" aria-label="시나리오 선택 화면으로 이동">산행안전 AI 대시보드</a>'
        '<div class="intro-footer">'
        '<span><strong>CONSORTIUM</strong> 숙명여자대학교 AGI 연구팀 × iNavi Systems Consortium</span>'
        '<span><strong>COPYRIGHT</strong> © 2026 Sookmyung Women’s University AGI Lab. All rights reserved.</span>'
        f'{github_link_html()}'
        '</div>'
        '</div>'
        '</section>'
    )
    st.markdown(intro_html, unsafe_allow_html=True)

def _scenario_paper_card_html(
    *,
    code: str,
    title: str,
    href: str,
    paper_eyebrow: str,
    paper_desc: str,
    paper_meta: str,
    open_label: str,
    pill_label: str,
    pill_class: str,
    extra_class: str = "",
) -> str:
    """표지(코드, 제목, 상태 pill)와 hover 시 덮이는 종이(상세)로 구성된 카드 HTML을 반환한다.

    카드 전체가 링크로 동작하며, 종이 위에 상세 설명과 진행 상태, 열기 문구를 표기한다.
    """
    card_class = f"scenario-card {extra_class}".strip()
    return (
        f'<a class="{card_class}" href="{href}" target="_self" '
        f'aria-label="{safe_html(title)} 화면으로 이동">'
        '<div class="scenario-face">'
        f'<div class="scenario-code">{safe_html(code)}</div>'
        f'<div class="scenario-title">{safe_html(title)}</div>'
        f'<div class="scenario-status"><span class="safe-pill {pill_class}">{safe_html(pill_label)}</span></div>'
        '</div>'
        '<div class="scenario-paper">'
        '<span class="scenario-paper-ribbon"></span>'
        f'<div class="scenario-paper-code">{safe_html(paper_eyebrow)}</div>'
        f'<div class="scenario-paper-desc">{scenario_desc_html(paper_desc)}</div>'
        f'<div class="scenario-paper-meta">{safe_html(paper_meta)}</div>'
        f'<div class="scenario-paper-open">{safe_html(open_label)}</div>'
        '</div>'
        '</a>'
    )


def render_scenario_select_page() -> None:
    # 시나리오 페이지, monitor와 동일한 초록 hero 배너 + 겹치는 흰 요약 카드
    st.markdown(
        (
            '<div class="scenario-hero">'
            '<div class="scenario-hero-eyebrow">SAFE SCENARIOS</div>'
            '<h1 class="scenario-hero-title">시나리오 선택</h1>'
            '</div>'
            '<div class="safe-card scenario-hero-summary">'
            '<div class="safe-muted">'
            '카드에 마우스를 올리면 해당 시나리오 상세 설명 표시'
            '<br />카드를 누르면 해당 시나리오 대시보드로 바로 이동'
            '</div>'
            '</div>'
            '<div style="height:30px;"></div>'
        ),
        unsafe_allow_html=True,
    )

    cards: list[str] = []
    for code, title, desc, demo_ready in SCENARIOS:
        pill_label = "시연 가능" if demo_ready else "준비 중"
        pill_class = "green" if demo_ready else "gray"
        paper_meta = (
            "학습셋 40세션 연동, [1]부터 [7] 패널 시연 가능"
            if demo_ready
            else "골격 화면 진입 가능, 데이터 연동 준비 중"
        )
        cards.append(
            _scenario_paper_card_html(
                code=code,
                title=title,
                href=f"?page=dashboard&scenario={code}",
                paper_eyebrow=f"SCENARIO {code}",
                paper_desc=desc,
                paper_meta=paper_meta,
                open_label="문서 열기 →",
                pill_label=pill_label,
                pill_class=pill_class,
            )
        )
    st.markdown(f'<div class="scenario-grid">{"".join(cards)}</div>', unsafe_allow_html=True)

    # 시나리오 카드와 동일한 시각 언어의 실시간 모니터링 진입 카드 (연세이지 표지)
    monitor_card = _scenario_paper_card_html(
        code="LIVE",
        title="실시간 모니터링",
        href="?page=monitor",
        paper_eyebrow="LIVE MONITOR",
        paper_desc="특정 관찰 대상을 선택해 유입값을 스트리밍으로 관찰 → 이벤트 주입으로 위험 반응 확인",
        paper_meta="벽시계 기준으로 40세션 동시 진행, 재접속 후에도 연속 재생",
        open_label="화면 열기 →",
        pill_label="BETA",
        pill_class="green",
        extra_class="monitor",
    )
    st.markdown(
        (
            '<div style="height:18px;"></div>'
            f'<div class="scenario-grid">{monitor_card}</div>'
        ),
        unsafe_allow_html=True,
    )


def render_pipeline_nav() -> None:
    st.markdown(
        """
        <div class="pipeline-strip">
            <div class="pipeline-step"><span>1</span>DTO-1 Input</div>
            <div class="pipeline-step"><span>2</span>Feature Engineering</div>
            <div class="pipeline-step"><span>3</span>Model Explanation</div>
            <div class="pipeline-step"><span>4</span>What-If Simulating</div>
            <div class="pipeline-step"><span>5</span>Meta Learning 개인화</div>
            <div class="pipeline-step"><span>6</span>DTO-5 Output</div>
            <div class="pipeline-step"><span>7</span>InferenceResult 저장</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _risk_marker_color(score: float) -> str:
    if score < 0.50:
        return "#16734f"
    if score < 0.65:
        return "#8a5900"
    if score < 0.85:
        return "#a83d3d"
    return "#7a1f1f"


def render_risk_gauge(
    score: float,
    secondary_score: float | None = None,
    primary_label: str | None = None,
    secondary_label: str | None = None,
) -> None:
    """위험도 색상 막대. secondary_score를 주면 비교 마커(원본 등)를 함께 표시한다.

    HTML은 빈 줄 없이 한 덩어리로 조립한다. 중간에 빈 줄이 생기면
    마크다운이 HTML 블록을 끊고 뒤를 코드블록으로 렌더링하기 때문.
    """
    score = max(0.0, min(1.0, float(score or 0.0)))
    pct = score * 100
    marker_color = _risk_marker_color(score)
    primary_suffix = f" {primary_label}" if primary_label else ""

    # 이중 마커일 때는 라벨을 2단 레인으로 분리해 겹침을 방지한다.
    #   윗줄(top:0) = 원본(보조), 아랫줄(top:26px) = 주입(주 값, 막대에 더 가깝게)
    # 글씨 크기는 동일하게 두고 보조는 투명도로만 구분한다.
    dual = secondary_score is not None
    labels: list[str] = []
    markers: list[str] = []
    if dual:
        sec = max(0.0, min(1.0, float(secondary_score or 0.0)))
        sec_pct = sec * 100
        sec_color = _risk_marker_color(sec)
        sec_suffix = f" {secondary_label}" if secondary_label else ""
        labels.append(
            f'<div class="risk-marker-label" '
            f'style="left: calc({sec_pct:.1f}%); top: 0; color: {sec_color}; opacity: 0.7;">'
            f'{sec:.4f}{sec_suffix}</div>'
        )
        markers.append(
            f'<div class="risk-marker" '
            f'style="left: calc({sec_pct:.1f}% - 2px); background: {sec_color}; opacity: 0.55;"></div>'
        )
    primary_top = "26px" if dual else "0"
    labels.append(
        f'<div class="risk-marker-label" style="left: calc({pct:.1f}%); top: {primary_top}; color: {marker_color};">'
        f'{score:.4f}{primary_suffix}</div>'
    )
    markers.append(
        f'<div class="risk-marker" style="left: calc({pct:.1f}% - 2px); background: {marker_color};"></div>'
    )

    axis = (
        '<div class="risk-axis">'
        '<span class="risk-label" style="left:25%;">정상</span>'
        '<span class="risk-label" style="left:57.5%;">주의</span>'
        '<span class="risk-label" style="left:75%;">경고</span>'
        '<span class="risk-label" style="left:92.5%;">위험</span>'
        '<span class="risk-tick first" style="left:0%;">0.00</span>'
        '<span class="risk-tick" style="left:50%;">0.50</span>'
        '<span class="risk-tick" style="left:65%;">0.65</span>'
        '<span class="risk-tick" style="left:85%;">0.85</span>'
        '<span class="risk-tick last" style="left:100%;">1.00</span>'
        '</div>'
    )
    wrap_style = ' style="padding-top: 56px;"' if dual else ""
    html = (
        f'<div class="risk-gauge-wrap"{wrap_style}>'
        + "".join(labels)
        + '<div class="risk-gauge">' + "".join(markers) + '</div>'
        + axis
        + '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_panel_selector(default: str = "전체 보기") -> str:
    return st.radio(
        "Panel Navigation",
        PANEL_OPTIONS,
        index=PANEL_OPTIONS.index(default) if default in PANEL_OPTIONS else 0,
        horizontal=True,
        label_visibility="collapsed",
    )