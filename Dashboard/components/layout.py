# 공통 레이아웃 및 스타일 컴포넌트

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
    "[5] MAML 개인화 Panel",
    "[6] DTO-5 Output Panel",
    "[7] InferenceResult 저장 Panel",
]

SCENARIOS = [
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


def _asset_data_uri(filename: str, mime: str) -> str:
    """Return a base64 data URI for Streamlit HTML/CSS assets."""
    path = ASSET_DIR / filename
    if not path.exists():
        return ""
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def inject_global_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --safe-navy: #10233f;
            --safe-blue: #2454a6;
            --safe-sky: #eef5ff;
            --safe-green: #1f7a5a;
            --safe-red: #c83e3e;
            --safe-amber: #ad741b;
            --safe-gray: #667085;
            --safe-border: #d9e2f2;
            --safe-card: #ffffff;
        }
        .block-container { padding-top: 3.4rem; max-width: 1320px; }
        .main .block-container { font-size: 1.06rem; }
        .main .block-container p, .main .block-container li { font-size: 1.06rem; line-height: 1.65; }
        .main .block-container div[data-testid="stMarkdownContainer"] { font-size: 1.06rem; }
        h1 { font-size: 2.75rem !important; letter-spacing: -0.035em; }
        h2, h3 { letter-spacing: -0.025em; }
        [data-testid="stMetricValue"] { font-size: 2.25rem; }
        [data-testid="stMetricLabel"] { font-size: 1.04rem; }
        .safe-hero {
            border: 1px solid var(--safe-border);
            border-radius: 28px;
            padding: 42px 44px;
            background: linear-gradient(135deg, #f6f9ff 0%, #ffffff 46%, #eff7f1 100%);
            box-shadow: 0 18px 48px rgba(16, 35, 63, 0.12);
            margin-bottom: 22px;
        }
        .safe-eyebrow { color: var(--safe-blue); font-weight: 800; letter-spacing: .08em; font-size: .9rem; }
        .safe-title { color: var(--safe-navy); font-size: 3.35rem; line-height: 1.08; font-weight: 900; margin: 10px 0 12px; letter-spacing: -0.05em; }
        .safe-subtitle { color: #344054; font-size: 1.26rem; line-height: 1.65; max-width: 880px; }
        .safe-card {
            border: 1px solid var(--safe-border);
            border-radius: 20px;
            padding: 20px 22px;
            background: var(--safe-card);
            box-shadow: 0 8px 24px rgba(16, 35, 63, 0.06);
            height: 100%;
        }
        .safe-card.soft { background: #f8fbff; }
        .safe-card.green { background: #f2fbf7; border-color: #cdebdc; }
        .safe-card.amber { background: #fff8ec; border-color: #f1d19a; }
        .safe-card.red { background: #fff3f3; border-color: #efc0c0; }
        .safe-card h3, .safe-card h4 { margin-top: 0; color: var(--safe-navy); }
        .safe-card h3 { font-size: 1.55rem; }
        .safe-card h4 { font-size: 1.22rem; }
        .safe-card .big { font-size: 2.05rem; font-weight: 900; color: var(--safe-navy); }

        .panel-description {
            color: #98a2b3;
            font-size: 1.00rem;
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
            font-weight: 950;
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
            background: #eef2f7;
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
            font-size: .92rem;
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
            font-size: .96rem;
            font-weight: 500;
            margin-bottom: 3px;
        }
        .feature-formula-text {
            display: block;
            color: #475467;
            font-size: .98rem;
            line-height: 1.45;
            font-weight: 500;
            word-break: keep-all;
        }
        .dto1-value {
            color: var(--safe-navy);
            font-size: 1.72rem;
            font-weight: 950;
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
            padding: 6px 11px; border-radius: 999px; background: #eef5ff;
            border: 1px solid #d3e1fb; color: #163a70; font-weight: 800; font-size: .86rem;
        }
        .safe-pill.gray { background: #f2f4f7; border-color: #e4e7ec; color: #667085; }
        .safe-pill.green { background: #eaf8f0; border-color: #c7ead5; color: #16734f; }
        .safe-pill.amber { background: #fff4db; border-color: #f3d28b; color: #8a5900; }
        .scenario-card {
            border: 1px solid var(--safe-border);
            border-radius: 20px;
            padding: 18px 18px 16px;
            background: #ffffff;
            height: 190px;
            box-sizing: border-box;
            display: flex;
            flex-direction: column;
            box-shadow: 0 8px 22px rgba(16,35,63,.06);
        }
        .scenario-card.disabled { opacity: .55; background: #f7f8fa; }
        .scenario-code { font-size: .9rem; color: var(--safe-blue); font-weight: 900; }
        .scenario-title { font-size: 1.12rem; font-weight: 900; color: var(--safe-navy); margin: 4px 0 8px; min-height: 30px; }
        .scenario-desc { color: #475467; line-height: 1.52; font-size: .95rem; word-break: keep-all; }
        .scenario-arrow { display: inline-block; margin-top: 4px; }
        .scenario-status { margin-top: auto; padding-top: 12px; }
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
            font-weight: 800; font-size: .86rem; color: var(--safe-navy);
        }
        .pipeline-step span { display: block; color: var(--safe-gray); font-size: .76rem; font-weight: 700; margin-bottom: 3px; }
        .risk-gauge-wrap { position: relative; margin: 22px 0 20px; padding-top: 30px; }
        .risk-gauge {
            position: relative;
            height: 34px;
            border-radius: 999px;
            overflow: hidden;
            border: 1px solid #cfd8e8;
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
            font-size: 1.08rem;
            font-weight: 950;
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
            font-size: 1.08rem;
            font-weight: 600;
            white-space: nowrap;
        }
        .risk-axis .risk-tick {
            position: absolute;
            top: 24px;
            transform: translateX(-50%);
            color: #667085;
            font-size: 1.02rem;
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
            font-size: 1.22rem;
            font-weight: 850;
            line-height: 1.45;
        }
        .model-importance-title span {
            color: #475467;
            font-weight: 650;
        }
        .model-importance-reason {
            color: #667085;
            font-size: 1.08rem;
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
            font-size: 1.02rem;
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
            font-size: .96rem;
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
            font-size: 1.14rem;
            font-weight: 900;
        }
        .main [data-testid="stSlider"] label,
        .main [data-testid="stSlider"] label p {
            font-size: 1.08rem !important;
            color: var(--safe-navy) !important;
            font-weight: 650 !important;
        }
        .main [data-testid="stSlider"] [data-testid="stTickBarMin"],
        .main [data-testid="stSlider"] [data-testid="stTickBarMax"] {
            font-size: 1.02rem !important;
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
            font-size: 1.04rem;
            line-height: 1.65;
            word-break: keep-all;
        }
        .maml-current-box {
            border: 1px solid #d9e2f2;
            border-radius: 18px;
            background: rgba(255,255,255,.78);
            padding: 18px 20px;
        }
        .maml-current-box span {
            display: block;
            color: #667085;
            font-size: .98rem;
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
            font-size: 1.22rem;
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
            font-weight: 950;
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
        .maml-persona-card.neutral { background: #f8fbff; }
        .maml-persona-card.low { background: #fff8ec; border-color: #f1d19a; }
        .maml-persona-card.high { background: #f2fbf7; border-color: #cdebdc; }
        .maml-persona-title {
            color: var(--safe-navy);
            font-size: 1.25rem;
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
            font-size: .92rem;
            font-weight: 850;
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
            border-radius: 28px; border: 1px solid #cfd8e8; background: #f9fbff; padding: 22px;
            box-shadow: inset 0 0 0 8px #eef3fb;
        }
        .app-preview-inner { background: #ffffff; border-radius: 22px; padding: 20px; border: 1px solid #e4eaf5; }
        .icon-row { display:flex; gap:12px; flex-wrap:wrap; align-items:center; margin: 8px 0; }
        .legend-dot { width: 14px; height: 14px; border-radius: 999px; display: inline-block; margin-right: 6px; vertical-align: middle; }
        .dot-blue { background:#2454a6; } .dot-red { background:#c83e3e; }

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
            font-size: 1.28rem;
            line-height: 1.45;
            font-weight: 850;
        }
        .dto5-alert-message {
            color: var(--safe-navy);
            font-size: 1.28rem;
            font-weight: 850;
            line-height: 1.45;
            word-break: keep-all;
        }
        .dto5-map-legend {
            font-size: 1.02rem;
            font-weight: 650;
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
            font-weight: 950;
            vertical-align: middle;
        }
        .infer-save-gap {
            height: 14px;
        }

        .sidebar-time-box {
            margin-top: 10px;
            margin-bottom: 16px;
        }
        .sidebar-time-label {
            color: #111827;
            font-size: .94rem;
            font-weight: 900;
            margin-bottom: 4px;
        }
        .sidebar-time-value {
            color: #1f2937;
            font-size: .98rem;
            font-weight: 700;
            line-height: 1.35;
        }
        .sidebar-section-heading {
            margin: 0 0 3px;
            color: #111827;
            font-size: 1.1rem;
            font-weight: 900;
            line-height: 1.25;
        }
        .sidebar-section-caption {
            margin: 0 0 8px;
            color: #31333f;
            font-size: .94rem;
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
            font-weight: 750;
            border: 1px solid transparent;
            line-height: 1.25;
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
            font-weight: 950;
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
        .intro-platform .green { color: #9cc567; font-weight: 950; }
        .intro-platform .orange { color: #f2952d; font-weight: 950; }
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
            font-weight: 950;
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
        </style>
        """,
        unsafe_allow_html=True,
    )


def safe_html(text: object) -> str:
    return html.escape("" if text is None else str(text))


def scenario_desc_html(text: str) -> str:
    """Render scenario descriptions with the action arrow on a new line."""
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
        '</div>'
        '</div>'
        '</section>'
    )
    st.markdown(intro_html, unsafe_allow_html=True)

def render_scenario_select_page() -> None:
    st.markdown("<div class='safe-eyebrow'>SAFE SCENARIOS</div>", unsafe_allow_html=True)
    st.title("시나리오 선택")

    for start in range(0, len(SCENARIOS), 3):
        cols = st.columns(3)
        for col, (code, title, desc, enabled) in zip(cols, SCENARIOS[start:start + 3]):
            with col:
                status = "시연 가능" if enabled else "준비 중"
                pill_class = "green" if enabled else "gray"
                disabled_class = "" if enabled else "disabled"
                st.markdown(
                    f"""
                    <div class="scenario-card {disabled_class}">
                        <div class="scenario-code">{safe_html(code)}</div>
                        <div class="scenario-title">{safe_html(title)}</div>
                        <div class="scenario-desc">{scenario_desc_html(desc)}</div>
                        <div class="scenario-status"><span class="safe-pill {pill_class}">{safe_html(status)}</span></div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if enabled:
                    if st.button("F1 대시보드 열기", key=f"open_{code}", use_container_width=True, type="primary"):
                        st.session_state["selected_scenario"] = code
                        st.session_state["page"] = "dashboard"
                        st.rerun()
                else:
                    st.button("준비 중", key=f"disabled_{code}", disabled=True, use_container_width=True)


def render_pipeline_nav() -> None:
    st.markdown(
        """
        <div class="pipeline-strip">
            <div class="pipeline-step"><span>1</span>DTO-1 Input</div>
            <div class="pipeline-step"><span>2</span>Feature Engineering</div>
            <div class="pipeline-step"><span>3</span>Model Explanation</div>
            <div class="pipeline-step"><span>4</span>What-If Simulating</div>
            <div class="pipeline-step"><span>5</span>MAML 개인화</div>
            <div class="pipeline-step"><span>6</span>DTO-5 Output</div>
            <div class="pipeline-step"><span>7</span>InferenceResult 저장</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_risk_gauge(score: float) -> None:
    score = max(0.0, min(1.0, float(score or 0.0)))
    pct = score * 100
    if score < 0.50:
        marker_color = "#16734f"
    elif score < 0.65:
        marker_color = "#8a5900"
    elif score < 0.85:
        marker_color = "#a83d3d"
    else:
        marker_color = "#7a1f1f"
    st.markdown(
        f"""
        <div class="risk-gauge-wrap">
            <div class="risk-marker-label" style="left: calc({pct:.1f}%); color: {marker_color};">{score:.4f}</div>
            <div class="risk-gauge">
                <div class="risk-marker" style="left: calc({pct:.1f}% - 2px); background: {marker_color};"></div>
            </div>
            <div class="risk-axis">
                <span class="risk-label" style="left:25%;">정상</span>
                <span class="risk-label" style="left:57.5%;">주의</span>
                <span class="risk-label" style="left:75%;">경고</span>
                <span class="risk-label" style="left:92.5%;">위험</span>
                <span class="risk-tick first" style="left:0%;">0.00</span>
                <span class="risk-tick" style="left:50%;">0.50</span>
                <span class="risk-tick" style="left:65%;">0.65</span>
                <span class="risk-tick" style="left:85%;">0.85</span>
                <span class="risk-tick last" style="left:100%;">1.00</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_panel_selector(default: str = "전체 보기") -> str:
    return st.radio(
        "Panel Navigation",
        PANEL_OPTIONS,
        index=PANEL_OPTIONS.index(default) if default in PANEL_OPTIONS else 0,
        horizontal=True,
        label_visibility="collapsed",
    )
