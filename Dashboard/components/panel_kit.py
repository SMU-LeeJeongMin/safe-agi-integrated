# 패널 공용 골격
# 시나리오마다 반복되는 카드, 헤더, 저장 결과 표시 골격을 한곳에 모음
# 새 시나리오 페이지는 이 골격 함수를 호출하고 내용(문구, 값)만 넣으면 되고,
# 디자인 변경은 이 파일과 layout.py의 CSS만 수정하면 모든 시나리오에 함께 반영

from __future__ import annotations

import html
import json
from typing import Any

import pandas as pd
import streamlit as st
from pathlib import Path

from utils.explanation import to_float


def _safe(text: object) -> str:
    return html.escape("" if text is None else str(text))


# 카드 골격
def metric_card(label: str, value: Any, description: str, card_class: str = "model-metric-card") -> str:
    """라벨, 큰 값, 설명 한 줄로 구성된 지표 카드 HTML을 반환한다."""
    return (
        f'<div class="safe-card soft {card_class}">'
        '<div class="dto1-label-row">'
        f'<span class="dto1-label">{_safe(label)}</span>'
        '</div>'
        f'<div class="dto1-value model-metric-value">{_safe(value)}</div>'
        f'<div class="model-metric-desc">{_safe(description)}</div>'
        '</div>'
    )


def formula_line(label: str, text: Any) -> str:
    """카드 하단의 '라벨: 내용' 한 줄 HTML을 반환한다."""
    text_html = _safe(text).replace("\n", "<br />")
    return (
        '<div class="model-formula-line">'
        f'<span class="model-formula-label">{_safe(label)}</span>'
        f'<span class="model-formula-text">{text_html}</span>'
        '</div>'
    )


def step_card(title: str, summary: str, value: Any, rows: list[tuple[str, Any]]) -> str:
    """[3] 모델 계산 단계에서 쓰는 Step 카드 HTML을 반환한다."""
    rows_html = "".join(formula_line(label, text) for label, text in rows)
    return (
        '<div class="safe-card soft model-step-card">'
        f'<h4>{_safe(title)}</h4>'
        f'<div class="model-step-summary">{_safe(summary)}</div>'
        f'<div class="dto1-value model-step-value">{_safe(value)}</div>'
        f'{rows_html}'
        '</div>'
    )


# 시나리오 대시보드 상단 헤더 골격
def render_scenario_header(eyebrow: str, title: str, summary_html: str, notice_html: str | None = None) -> None:
    """eyebrow, 제목, 시나리오 요약 카드, (선택) 안내 박스를 렌더링한다.

    summary_html과 notice_html은 <br/> 등을 포함할 수 있어 이스케이프하지 않는다.
    호출하는 쪽에서 신뢰할 수 있는 문자열만 넘겨야 한다.
    """
    # 초록 배너(제목) + 배너에 걸쳐 올라오는 흰색 요약 카드
    st.markdown(
        (
            '<div class="scenario-hero">'
            f'<div class="scenario-hero-eyebrow">{_safe(eyebrow)}</div>'
            f'<h1 class="scenario-hero-title">{_safe(title)}</h1>'
            '</div>'
            '<div class="safe-card scenario-hero-summary">'
            f'<div class="safe-muted">{summary_html}</div>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )

    if notice_html:
        st.markdown(
            (
                '<div style="height:22px;"></div>'
                '<div style="background:#eef5ff; border-radius:10px; padding:18px 20px;'
                ' color:#1f3b5d; line-height:1.65; font-size:1.02rem;">'
                f'{notice_html}'
                '</div>'
            ),
            unsafe_allow_html=True,
        )


# [7] 저장 결과 표시 골격
def render_saved_records(
    saved_df: pd.DataFrame,
    summary_columns: list[str],
    file_prefix: str,
    records: list[dict] | None = None,
    source_caption: str | None = None,
) -> None:
    """저장된 InferenceResult 요약 표, 전체 컬럼 expander, 다운로드 expander를 렌더링한다.

    records를 넘기면 JSON 다운로드 버튼도 함께 표시한다.
    source_caption은 saved_df에 source 컬럼이 두 종류 이상일 때만 표시한다.
    """
    st.markdown("#### 저장된 InferenceResult 요약")
    existing = [column for column in summary_columns if column in saved_df.columns]
    st.dataframe(saved_df[existing], use_container_width=True, hide_index=True)

    if source_caption and "source" in saved_df.columns and saved_df["source"].nunique() > 1:
        st.caption(source_caption)

    with st.expander("전체 저장 컬럼 보기"):
        st.dataframe(saved_df, use_container_width=True, hide_index=True)

    with st.expander("결과 다운로드"):
        st.download_button(
            label=f"{file_prefix}.csv 다운로드",
            data=saved_df.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"{file_prefix}.csv",
            mime="text/csv",
        )
        if records is not None:
            st.download_button(
                label=f"{file_prefix}.json 다운로드",
                data=json.dumps(records, ensure_ascii=False, indent=2),
                file_name=f"{file_prefix}.json",
                mime="application/json",
            )


# 패널 헤더와 [1] Input 골격
def render_panel_banner(number: int, title: str, description: str) -> None:
    """번호 + 사선 초록 배너형 패널 제목. 제목은 크게, 설명은 작게 배너 안에 표시한다."""
    st.markdown(
        (
            '<div class="panel-banner">'
            f'<div class="panel-banner-num">{number:02d}</div>'
            '<div class="panel-banner-body">'
            f'<div class="panel-banner-title">{_safe(title)}</div>'
            f'<div class="panel-banner-desc">{_safe(description)}</div>'
            '</div>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


def render_subsection(title: str, tooltip: str | None = None) -> None:
    """panel 내부 소제목. 제목 배너와 같은 사다리꼴 모티프의 얇은 리본을
    글씨 아래에 깐다. tooltip이 있으면 제목 오른쪽에 (i) 아이콘으로 표시한다."""
    indent_class = ""
    tooltip_html = ""
    if tooltip:
        tooltip_html = (
            '<span class="dto1-tooltip" aria-label="설명 보기" style="margin-left:8px;">i'
            f'<span class="dto1-tooltip-text">{_safe(tooltip)}</span>'
            '</span>'
        )
    st.markdown(
        f'<div class="panel-subsection{indent_class}"><span>{_safe(title)}</span>{tooltip_html}</div>',
        unsafe_allow_html=True,
    )


def render_soft_notice(text: str) -> None:
    """연한 초록 안내 박스. 파란 st.info 대체용 공통 디자인."""
    st.markdown(
        (
            '<div class="soft-notice">'
            f'{_safe(text)}'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


def render_panel_header(title: str, description: str) -> None:
    """패널 제목(st.header)과 회색 설명 한 줄을 렌더링한다."""
    st.header(title)
    st.markdown(
        f'<div class="panel-description">{description}</div>',
        unsafe_allow_html=True,
    )


def metric_block(label: str, value: Any, note: str | None = None, nowrap: bool = False) -> str:
    """[1] Input 카드 내부의 '라벨 + 값(+ 물음표 툴팁)' 한 블록 HTML을 반환한다.

    nowrap=True면 툴팁 문구를 줄바꿈 없이 한 줄로 표시한다."""
    nowrap_class = " dto1-tooltip-nowrap" if nowrap else ""
    tooltip_html = (
        f'<span class="dto1-tooltip{nowrap_class}" aria-label="설명 보기">i'
        f'<span class="dto1-tooltip-text">{_safe(note)}</span>'
        '</span>'
        if note
        else ""
    )
    return (
        '<div class="dto1-metric-block">'
        '<div class="dto1-label-row">'
        f'<span class="dto1-label">{_safe(label)}</span>'
        f'{tooltip_html}'
        '</div>'
        f'<div class="dto1-value">{_safe(value)}</div>'
        '</div>'
    )


def info_card(kind: str, title: str, body_html: str, extra_class: str = "dto1-card") -> str:
    """색상 종류(kind)와 제목, 본문 HTML로 구성된 카드 HTML을 반환한다."""
    return (
        f'<div class="safe-card {kind} {extra_class}">'
        f'<h4>{_safe(title)}</h4>'
        f'{body_html}'
        '</div>'
    )


def render_time_card(time_text: str) -> None:
    """[1] Input 상단의 '현재 시점' 카드를 렌더링한다."""
    st.markdown(
        (
            '<div class="safe-card soft dto1-time-card">'
            '<b>현재 시점</b>'
            f'<span class="dto1-time-value">{_safe(time_text)}</span>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def server_icon_b64() -> str:
    """진한 초록으로 재채색한 서버 아이콘(base64)."""
    import base64
    path = Path(__file__).resolve().parent.parent / "assets" / "server_green.png"
    return base64.b64encode(path.read_bytes()).decode("ascii")


@st.cache_data(show_spinner=False)
def _watch_icon_b64() -> str:
    """진한 초록으로 재채색한 워치 아이콘(base64)."""
    import base64
    path = Path(__file__).resolve().parent.parent / "assets" / "watch_green.png"
    return base64.b64encode(path.read_bytes()).decode("ascii")


# 말풍선 배경색 (연한 세이지 그린 팔레트, 제목 배너의 진초록과 구분)
BUBBLE_COLORS = ["#a3b285"]  # [2] 패널 연한 초록으로 통일 ([1] 말풍선, [6] 꽃잎 공용)


def render_input_bubbles(bubbles: list[tuple[str, list[tuple]]], time_text: str | None = None) -> None:
    """[1] Input 데이터를 말풍선 4개 + 중앙 워치 아이콘 구도로 렌더링한다.

    bubbles: (말풍선 제목, 블록 목록) 목록. 블록은 metric_block과 동일 형식.
    말풍선 꼬리는 아래 중앙의 워치를 향하고, time_text가 있으면
    워치 아래 "현재 시점 / 날짜 / 시각" 세 줄로 표시한다.
    """
    bubble_html = "".join(
        (
            f'<div class="dto1-bubble" style="--bubble:{BUBBLE_COLORS[i % len(BUBBLE_COLORS)]};">'
            f'<div class="dto1-bubble-title">{_safe(title)}</div>'
            + "".join(metric_block(*block) for block in blocks)
            + '</div>'
        )
        for i, (title, blocks) in enumerate(bubbles)
    )
    time_html = ""
    if time_text:
        parts = str(time_text).split(" ")
        date_part = parts[0] if parts else str(time_text)
        clock_part = " ".join(parts[1:]) if len(parts) > 1 else ""
        time_html = (
            '<div class="dto1-watch-time">'
            '<div class="time-label">현재 시점</div>'
            f'<div class="time-value">{_safe(date_part)}</div>'
            f'<div class="time-value">{_safe(clock_part)}</div>'
            '</div>'
        )
    st.markdown(
        (
            f'<div class="dto1-bubble-row">{bubble_html}</div>'
            '<div class="dto1-watch">'
            f'<img src="data:image/png;base64,{_watch_icon_b64()}" alt="워치" />'
            '</div>'
            f'{time_html}'
        ),
        unsafe_allow_html=True,
    )


def render_input_cards(cards: list[tuple[str, str, list[tuple]]]) -> None:
    """[1] Input의 카드 행을 렌더링한다.

    cards: (색상 kind, 카드 제목, 블록 목록) 목록.
    블록은 (라벨, 값) 또는 (라벨, 값, 툴팁 설명) 튜플.
    """
    columns = st.columns(len(cards))
    for column, (kind, title, blocks) in zip(columns, cards):
        body = "".join(metric_block(*block) for block in blocks)
        with column:
            st.markdown(info_card(kind, title, body), unsafe_allow_html=True)


def render_detail_expander(
    rows: list[dict] | None,
    title: str = "원본 입력 상세 보기",
    empty_text: str | None = None,
) -> None:
    """[1] Input 하단의 원본 상세 expander를 렌더링한다."""
    st.markdown('<div class="dto1-expander-gap"></div>', unsafe_allow_html=True)
    with st.expander(title):
        if not rows:
            st.caption(empty_text or "연결된 원본 입력이 없습니다.")
        else:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# [6] DTO-5 골격
def _dto5_label(label: str, tooltip: str | None, wide: bool) -> str:
    if not tooltip:
        return f'<div class="dto1-label">{_safe(label)}</div>'
    wide_class = " dto1-tooltip-wide" if wide else ""
    return (
        '<div class="dto1-label-row">'
        f'<span class="dto1-label">{_safe(label)}</span>'
        f'<span class="dto1-tooltip{wide_class}">i'
        f'<span class="dto1-tooltip-text">{tooltip}</span>'
        '</span>'
        '</div>'
    )


def dto5_card(title: str, blocks: list[dict], class_name: str = "soft") -> str:
    """[6] DTO-5 핵심 필드 카드 HTML을 반환한다.

    blocks 항목: {"label", "value", "note"(선택), "tooltip"(선택, HTML 허용), "wide"(선택)}
    """
    body = []
    for block in blocks:
        note = block.get("note")
        body.append(
            '<div class="dto5-field-block">'
            f'{_dto5_label(block["label"], block.get("tooltip"), bool(block.get("wide")))}'
            f'<div class="dto1-value dto5-value">{_safe(block["value"])}</div>'
            + (f'<div class="dto1-note dto5-note">{_safe(note)}</div>' if note else "")
            + '</div>'
        )
    return (
        f'<div class="safe-card {class_name} dto5-core-card">'
        f'<h4>{_safe(title)}</h4>'
        f'{"".join(body)}'
        '</div>'
    )


def alert_wide_card(title: str, message: str) -> str:
    """[6] 하단의 가로형 Alerts 카드 HTML을 반환한다."""
    return (
        '<div class="safe-card green dto5-alert-wide">'
        '<h4>Alerts</h4>'
        '<div class="dto5-alert-grid">'
        '<div>'
        '<div class="dto1-label">알림 제목</div>'
        f'<div class="dto1-value dto5-alert-title">{_safe(title)}</div>'
        '</div>'
        '<div>'
        '<div class="dto1-label">알림 문구</div>'
        f'<div class="dto5-alert-message">{_safe(message)}</div>'
        '</div>'
        '</div>'
        '</div>'
    )


def render_json_expander(data: Any, title: str = "DTO-5 JSON 상세 보기", empty_text: str | None = None) -> None:
    """DTO-5 원본 JSON expander를 렌더링한다."""
    with st.expander(title):
        if data:
            st.json(data)
        else:
            st.caption(empty_text or "DTO-5 파일이 연결되면 공식 JSON을 그대로 표시합니다.")


def render_location_map(
    points: list[dict],
    zoom: float,
    legend: list[tuple[str, str]] | None = None,
    circle: dict | None = None,
    height: int | None = None,
) -> None:
    """현재 위치와 대상 지점을 표시하는 공용 지도.

    points: {"lat", "lon", "label", "kind"} 목록. kind가 "current"면 파란 점, 아니면 붉은 점.
    legend: (legend-dot CSS 클래스, 문구) 목록. 예: [("dot-blue", "현재 위치"), ("dot-red", "추천 쉼터")]
    circle: {"lat", "lon", "radius"}를 주면 대상 주변에 반경 원을 함께 그린다.
    """
    map_df = pd.DataFrame(points)

    if legend:
        def _legend_marker(dot_class: str) -> str:
            # "icon:<색상>:<문자>" 형식이면 색 문자를 마커로 사용 (예: "icon:#1f7a5a:▲")
            if dot_class.startswith("icon:"):
                _, color, char = dot_class.split(":", 2)
                return (
                    f'<span style="color:{color}; font-weight:800; margin-right:6px; '
                    f'font-size:1rem; line-height:1;">{_safe(char)}</span>'
                )
            return f'<span class="legend-dot {dot_class}"></span>'

        legend_html = "".join(
            f'<span>{_legend_marker(dot_class)}{_safe(text)}</span>'
            for dot_class, text in legend
        )
        st.markdown(
            f'<div class="icon-row dto5-map-legend">{legend_html}</div>',
            unsafe_allow_html=True,
        )

    try:
        import pydeck as pdk

        scatter_df = map_df.copy()
        scatter_df["color"] = scatter_df["kind"].apply(
            lambda kind: [36, 84, 166, 215] if kind == "current" else [200, 62, 62, 225]
        )
        scatter_df["size"] = scatter_df["kind"].apply(lambda kind: 75 if kind == "current" else 92)

        text_df = map_df.copy()
        text_df["lat"] = text_df["lat"] + 0.00018

        layers = [
            pdk.Layer(
                "ScatterplotLayer",
                data=scatter_df,
                get_position="[lon, lat]",
                get_radius="size",
                get_fill_color="color",
                pickable=True,
            ),
            pdk.Layer(
                "TextLayer",
                data=text_df,
                get_position="[lon, lat]",
                get_text="label",
                get_size=15,
                get_color=[20, 35, 63, 255],
                get_text_anchor="middle",
                get_alignment_baseline="bottom",
            ),
        ]

        if circle is not None and to_float_or_none(circle.get("radius")) and float(circle["radius"]) > 0:
            radius_df = pd.DataFrame([circle])
            layers.insert(
                0,
                pdk.Layer(
                    "ScatterplotLayer",
                    data=radius_df,
                    get_position="[lon, lat]",
                    get_radius="radius",
                    get_fill_color=[200, 62, 62, 35],
                    get_line_color=[200, 62, 62, 150],
                    stroked=True,
                ),
            )

        view_state = pdk.ViewState(
            latitude=sum(p["lat"] for p in points) / len(points),
            longitude=sum(p["lon"] for p in points) / len(points),
            zoom=zoom,
            pitch=0,
        )
        st.pydeck_chart(
            pdk.Deck(
                map_style=None,
                initial_view_state=view_state,
                layers=layers,
                tooltip={"text": "{label}"},
            ),
            use_container_width=True,
            height=height if height else None,
        )
    except Exception:
        fallback = pd.DataFrame(
            [
                {
                    "lat": p["lat"],
                    "lon": p["lon"],
                    "color": "#2454a6" if p.get("kind") == "current" else "#c83e3e",
                    "size": 40 if p.get("kind") == "current" else 48,
                }
                for p in points
            ]
        )
        st.map(fallback, latitude="lat", longitude="lon", color="color", size="size", height=height)


def to_float_or_none(value: Any):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result


def _clip01(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


# 가중치(계수) 설명
def _contrib_bar(name: str, weight: float, value: float, contribution: float, share: float, color: str) -> str:
    width = _clip01(share) * 100
    return (
        '<div class="model-contrib-row">'
        '<div class="model-contrib-head">'
        f'<span class="model-contrib-name">{_safe(name)} <span>가중치 {weight:.2f} × 항목 점수 {value:.3f}</span></span>'
        f'<span class="model-contrib-value">{contribution:.4f} ({share * 100:.0f}%)</span>'
        '</div>'
        '<div class="model-contrib-track">'
        f'<div class="model-contrib-fill {color}" style="width:{width:.1f}%;"></div>'
        '</div>'
        '</div>'
    )


def render_contribution_section_header() -> None:
    """기여도 분해 섹션 제목과 쉬운 설명. F1 외 시나리오에서도 동일하게 사용한다."""
    st.markdown("#### 기여도 분해와 학습 가중치 근거")
    st.markdown(
        (
            '<div class="panel-description">'
            '막대는 위험 점수를 구성하는 각 항목이 이번 시점에 차지한 몫으로, 몫이 큰 항목일수록 판단에 크게 기여한 신호입니다.'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


def render_contribution_card(
    title: str,
    description: str,
    items: list[tuple[str, float, float, str]],
    bottom_label: str | None = None,
    bottom_text: str | None = None,
    waiting_text: str | None = None,
) -> None:
    """가중합 기여도 분해 카드.

    items: (항목 이름, 가중치 w, 항목 점수 x, 막대 색상) 목록. 비어 있으면 waiting_text를 표시한다.
    bottom_label, bottom_text: 카드 하단 한 줄 안내 (예: 가중치 출처, 학습 가중치 근거).
    """
    if items:
        contributions = [(name, weight, value, weight * value, color) for name, weight, value, color in items]
        total = sum(c for _, _, _, c, _ in contributions) or 1.0
        body = "".join(
            _contrib_bar(name, weight, value, contribution, contribution / total, color)
            for name, weight, value, contribution, color in contributions
        )
    else:
        body = f'<div class="safe-muted">{_safe(waiting_text or "가중치 공식이 확정되면 항목별 기여도 막대가 표시됩니다.")}</div>'

    bottom_html = formula_line(bottom_label, bottom_text) if bottom_label and bottom_text else ""

    st.markdown(
        (
            '<div class="safe-card soft">'
            f'<h4>{_safe(title)}</h4>'
            f'<div class="model-metric-desc" style="margin:2px 0 18px;">{_safe(description)}</div>'
            f'{body}'
            f'{bottom_html}'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


OFFLINE_EXPLANATION_NOTE = (
    "추후 딥러닝으로 가중치를 학습하면, 학습 시점에 만들어지는 explanation.json을 읽어 "
    "이 자리에 학습 근거를 표시합니다. 무거운 계산은 학습 단계에서 미리 끝내므로 대시보드 속도에는 영향이 없습니다."
)


def render_offline_weight_explanation(explanation: dict[str, Any] | None, scenario_id: str = "F1") -> None:
    """학습 가중치 근거 카드. 산출물이 없으면 연결 대기 틀만 표시한다."""
    if not explanation:
        st.markdown(
            (
                '<div class="safe-card soft">'
                '<h4>학습 가중치 근거 — 연결 대기</h4>'
                '<div class="safe-muted">'
                '가중치를 딥러닝으로 학습한 뒤에는 "왜 이 계수가 나왔는지"를 이 카드에서 보여줍니다.<br/>'
                '기대 형식: <b>trained_at, method, summary, weights[]</b> '
                '(항목별 name, weight, prev, reason)'
                '</div>'
                '</div>'
            ),
            unsafe_allow_html=True,
        )
        return

    trained_at = _safe(explanation.get("trained_at", "-"))
    method = _safe(explanation.get("method", "-"))
    summary = _safe(explanation.get("summary", ""))
    weights = explanation.get("weights") or explanation.get("rationale") or []

    items_html = ""
    for item in weights:
        if not isinstance(item, dict):
            continue
        name = _safe(item.get("name", "-"))
        weight = to_float(item.get("weight"))
        prev = item.get("prev")
        prev_text = f" (기존 {to_float(prev):.2f} → 학습 {weight:.2f})" if prev is not None else f" (학습 {weight:.2f})"
        reason = _safe(item.get("reason", ""))
        items_html += (
            '<div class="model-importance-item">'
            f'<div class="model-importance-title">{name}<span>{prev_text}</span></div>'
            f'<div class="model-importance-reason">{reason}</div>'
            '</div>'
        )

    st.markdown(
        (
            '<div class="safe-card soft">'
            '<h4>학습 가중치 근거</h4>'
            '<div class="model-metric-desc" style="margin:2px 0 18px;">'
            f'학습 시점 {trained_at}, 방법 {method}. 학습 파이프라인이 내보낸 explanation.json 내용을 표시합니다.'
            '</div>'
            f'{items_html}'
            + (f'<div class="model-formula-line"><span class="model-formula-label">요약</span>'
               f'<span class="model-formula-text">{summary}</span></div>' if summary else '')
            + '</div>'
        ),
        unsafe_allow_html=True,
    )


# [2] Feature 카드, [4] What-If 결과 카드, [5] MAML 페르소나 카드 골격
def feature_card(field: str, title: str, value: Any, tooltip: str, box_label: str, box_text: str) -> str:
    """[2] Feature 카드 HTML. 상단은 feature 이름/제목/값, 하단 박스는 공식이나 출처 한 줄."""
    return (
        '<div class="safe-card soft feature-card">'
        f'<h4>{_safe(field)}</h4>'
        '<div class="feature-metric-block">'
        '<div class="dto1-label-row">'
        f'<span class="dto1-label">{_safe(title)}</span>'
        '<span class="dto1-tooltip">i'
        f'<span class="dto1-tooltip-text">{_safe(tooltip)}</span>'
        '</span>'
        '</div>'
        f'<div class="dto1-value">{_safe(value)}</div>'
        '</div>'
        '<div class="feature-formula-box">'
        '<div class="feature-formula-row">'
        f'<span class="feature-formula-label">{_safe(box_label)}</span>'
        f'<span class="feature-formula-text">{_safe(box_text)}</span>'
        '</div>'
        '</div>'
        '</div>'
    )


def style_feature_fig(fig):
    """[2] 시계열 차트의 공통 스타일(초록 라인, 글자 크기)을 적용한다."""
    safe_green = "#2e6b35"
    fig.update_traces(
        line=dict(color=safe_green, width=3),
        marker=dict(color=safe_green, size=7),
    )
    fig.update_layout(
        font=dict(size=16),
        title_font=dict(size=20),
        legend_font=dict(size=15),
        margin=dict(l=20, r=20, t=58, b=34),
    )
    fig.update_xaxes(title_font=dict(size=16), tickfont=dict(size=14))
    fig.update_yaxes(title_font=dict(size=16), tickfont=dict(size=14))
    return fig


def result_card(title: str, value_text: str, rows: list[tuple[str, Any]], class_name: str = "soft") -> str:
    """[4] What-If 결과 카드 HTML. 큰 값 하나와 '라벨: 값' 줄 목록으로 구성된다."""
    muted = "<br/>".join(f'{_safe(label)}: <b>{_safe(value)}</b>' for label, value in rows)
    return (
        f'<div class="safe-card {class_name}">'
        f'<h4>{_safe(title)}</h4>'
        f'<div class="big">{_safe(value_text)}</div>'
        f'<div class="safe-muted">{muted}</div>'
        '</div>'
    )


def risk_tone(label: str) -> str:
    """위험 라벨 문자열을 페르소나/필 색상 클래스(normal, caution, warning, danger)로 변환한다."""
    normalized = str(label).strip()
    if normalized == "정상":
        return "normal"
    if normalized == "주의":
        return "caution"
    if normalized == "경고":
        return "warning"
    if normalized in {"위험", "긴급"}:
        return "danger"
    return "neutral"


def persona_card(
    title: str,
    subtitle: str,
    metrics: list[tuple[str, Any]],
    risk_pill_class: str,
    risk_pill_text: str,
    state_pill_text: str,
    interpretation: str,
    tone: str,
) -> str:
    """[5] MAML 페르소나 카드 HTML.

    metrics: (라벨 HTML, 값) 목록. 라벨에는 툴팁 HTML을 넣을 수 있어 이스케이프하지 않는다.
    """
    metric_html = "".join(
        f'<div><span>{label_html}</span><b>{_safe(value)}</b></div>' for label_html, value in metrics
    )
    return (
        f'<div class="maml-persona-card {tone}">'
        f'<div class="maml-persona-title">{_safe(title)}</div>'
        f'<div class="maml-persona-subtitle">{_safe(subtitle)}</div>'
        '<div class="maml-divider"></div>'
        f'<div class="maml-metric-row">{metric_html}</div>'
        '<div class="maml-result-row">'
        f'<span class="maml-risk-pill {risk_pill_class}">{_safe(risk_pill_text)}</span>'
        f'<span class="maml-state-pill">{_safe(state_pill_text)}</span>'
        '</div>'
        f'<div class="maml-interpretation">{_safe(interpretation)}</div>'
        '</div>'
    )


# 공용 버튼 문구
WHATIF_RERUN_LABEL = "변경값으로 다시 분석하기"
INFERENCE_SAVE_LABEL = "현재 시점 InferenceResult 저장"


def model_detail_button_label(scenario_id: str) -> str:
    return f"선택 시점의 {scenario_id} 모델 결과 상세 보기"