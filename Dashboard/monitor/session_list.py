# 사이드바 산행 세션 리스트
# 세션별 현재 수신 시점의 위험 등급 dot과 필터, 정렬, 관찰 전환 링크를 담당한다.

from __future__ import annotations

from urllib.parse import quote

import streamlit as st

from components.layout import safe_html
from monitor.session_registry import SessionEntry, session_snapshot
from monitor.state import _get_state


GRADE_ORDER = ["정상", "주의", "경고", "위험"]
GRADE_DOT_CLASS = {"정상": "normal", "주의": "caution", "경고": "warning", "위험": "danger"}
GRADE_DOT_COLOR = {"normal": "#1f7a5a", "caution": "#d99a1b", "warning": "#c83e3e", "danger": "#c83e3e"}


def _render_session_list(entries: list[SessionEntry], selected_key: str | None) -> str | None:
    """사이드바 세션 리스트: 필터, 정렬, 세션별 위험 dot과 관찰 선택.

    dot 색은 각 세션의 현재 수신 시점(pos) 위험 등급 기준이며,
    경고 및 위험 세션은 붉은 pulse로 강조해 관제 화면에서 바로 골라낼 수 있게 한다.
    st.sidebar 컨텍스트 안에서 호출된다.
    """
    st.markdown(
        """
        <div class="sidebar-section-heading">산행 세션</div>
        <div class="sidebar-section-caption">세션별 현재 수신 시점의 위험 등급<br/>목록에서 사용자를 누르면 해당 세션으로 전환</div>
        """,
        unsafe_allow_html=True,
    )

    if not entries:
        st.markdown(
            '<div class="sidebar-section-caption">표시할 세션이 없습니다. '
            'Input 산출물이 연결되면 목록이 채워집니다.</div>',
            unsafe_allow_html=True,
        )
        return None

    snapshots: list[tuple[SessionEntry, dict]] = []
    for entry in entries:
        pos = int(_get_state(entry.scenario_id, entry.session_id, "pos", 0))
        snapshots.append((entry, session_snapshot(entry, pos)))

    age_options = sorted({snap["age_group"] for _, snap in snapshots})
    grade_filter = st.multiselect("등급 필터", GRADE_ORDER, default=[], key="monitor_grade_filter",
                                  placeholder="전체 등급")
    age_filter = st.multiselect("연령대 필터", age_options, default=[], key="monitor_age_filter",
                                placeholder="전체 연령대")
    sort_desc = st.toggle("위험도 내림차순 정렬", value=True, key="monitor_sort_desc")

    visible = [
        (entry, snap)
        for entry, snap in snapshots
        if (not grade_filter or snap["grade"] in grade_filter)
        and (not age_filter or snap["age_group"] in age_filter)
    ]
    if sort_desc:
        visible.sort(key=lambda pair: pair[1]["representative"], reverse=True)

    if not visible:
        st.markdown(
            '<div class="panel-description">필터 조건에 맞는 세션이 없습니다.</div>',
            unsafe_allow_html=True,
        )
        return selected_key

    visible_keys = {entry.key for entry, _ in visible}
    if selected_key not in visible_keys:
        selected_key = visible[0][0].key

    with st.expander(f"사용자 목록 ({len(visible)})", expanded=True):
        rows: list[str] = []
        for entry, snap in visible:
            dot_class = GRADE_DOT_CLASS.get(snap["grade"], "normal")
            # 인라인 스타일로 크기와 색을 보장한다 (CSS 로드 전에도 dot이 보이도록).
            # pulse 애니메이션은 layout.py의 클래스 CSS가 담당한다.
            dot_color = GRADE_DOT_COLOR.get(dot_class, "#1f7a5a")
            dot_html = (
                f'<span class="monitor-session-dot {dot_class}" '
                f'style="display:inline-block; flex:0 0 auto; width:10px; height:10px; '
                f'border-radius:999px; background:{dot_color}; margin-right:9px;"></span>'
            )
            shown_id = entry.session_id if len(entry.session_id) <= 16 else entry.session_id[:15] + "…"
            id_html = (
                f'<span class="monitor-session-id" title="{safe_html(entry.session_id)}">'
                f'{safe_html(shown_id)}</span>'
            )
            if entry.key == selected_key:
                # 관찰 중 배지: CSS 미적용 환경에서도 보이도록 인라인 스타일로 처리
                badge_html = (
                    '<span class="monitor-session-badge" '
                    'style="display:inline-block; flex:0 0 auto; margin-left:8px; padding:2px 8px; '
                    'border-radius:999px; background:#eaf8f0; border:1px solid #c7ead5; '
                    'color:#16734f; font-size:.74rem; font-weight:800; white-space:nowrap;">관찰 중</span>'
                )
                rows.append(
                    '<div class="monitor-session-item selected" '
                    f'style="display:flex; align-items:center; padding:6px 2px;">{dot_html}{id_html}{badge_html}</div>'
                )
            else:
                href = f"?page=monitor&session={quote(entry.key)}"
                rows.append(
                    f'<a class="monitor-session-item" href="{href}" target="_self" '
                    f'style="display:flex; align-items:center; padding:6px 2px;">{dot_html}{id_html}</a>'
                )
        st.markdown(
            '<div class="monitor-session-list" style="margin-bottom:6px;">' + "".join(rows) + "</div>",
            unsafe_allow_html=True,
        )
    return selected_key