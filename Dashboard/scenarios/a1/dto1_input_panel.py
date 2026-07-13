# [1] DTO-1 Input Panel

from __future__ import annotations

from components.panel_kit import (
    render_detail_expander,
    render_input_cards,
    render_panel_header,
    render_time_card,
)
from scenarios.a1.mapper import A1Context, first_value, nested, row_value
from scenarios.a1.formatting import _fmt, _fmt_bool, _text
from utils.explanation import format_id
from utils.time_utils import format_kst, format_utc


def render_dto1_input_panel(context: A1Context) -> None:
    row = context.row
    render_panel_header(
        "[1] DTO-1 Input Panel",
        "사용자 위치, 워치 입력, 지형, 위험 POI가 모델에 들어가기 전 어떤 값으로 전달되었는지 확인하는 panel",
    )
    render_time_card(format_kst(row_value(row, "ts", "timestamp")) if row else "데이터 연결 대기")

    user_lat = first_value(row_value(row, "user_lat", "gps_lat", "lat"), nested(context.dto5, "user_location", "lat"))
    user_lon = first_value(row_value(row, "user_lon", "gps_lon", "lon"), nested(context.dto5, "user_location", "lon"))
    hazard_type = first_value(row_value(row, "hazard_type"), context.location.get("hazard_type"), context.alert.get("hazard_type"))
    hazard_poi_id = first_value(row_value(row, "hazard_poi_id", "poi_id"), context.location.get("poi_id"))
    distance = row_value(row, "dist_to_hazard_m", "distance_to_hazard_m")
    uuid_display, uuid_tooltip = format_id(_text(row_value(row, "uuid", "session_id")))
    uuid_block = ("세션 ID", uuid_display, uuid_tooltip) if uuid_tooltip else ("세션 ID", uuid_display)

    render_input_cards(
        [
            (
                "soft",
                "사용자 정보",
                [
                    uuid_block,
                    ("연령대", _text(row_value(row, "age_group"))),
                    ("성별", _text(row_value(row, "gender"))),
                ],
            ),
            (
                "amber",
                "현재 위치",
                [
                    ("위도", _fmt(user_lat, 6)),
                    ("경도", _fmt(user_lon, 6)),
                    ("고도", _fmt(row_value(row, "altitude_m"), 1, " m")),
                ],
            ),
            (
                "red",
                "위험 POI",
                [
                    ("위험 유형", _text(hazard_type), "Input/DTO-3의 위험 POI 유형"),
                    ("위험 POI ID", _text(hazard_poi_id)),
                    ("위험 지점 거리", _fmt(distance, 1, " m"), "Input 파이프라인이 산출한 최근접 위험 POI 거리"),
                ],
            ),
            (
                "green",
                "지형 및 보조 입력",
                [
                    ("경사도", _fmt(row_value(row, "slope_deg"), 1, "°")),
                    ("지정로 이탈", _fmt(row_value(row, "off_trail_dist_m"), 1, " m")),
                    ("접근 중", _fmt_bool(row_value(row, "approaching_flag"), "접근", "멀어짐")),
                    ("평균 심박수", _fmt(row_value(row, "hr_mean_bpm"), 1, " bpm"), "A1 공간 판단의 보조 입력"),
                ],
            ),
        ]
    )

    detail_rows = None
    if row:
        detail_rows = []
        for key, value in row.items():
            if key in {"ts", "timestamp"}:
                value = f"KST {format_kst(value)} / UTC {format_utc(value)}"
            detail_rows.append({"항목": str(key), "값": _text(value)})
    render_detail_expander(detail_rows, empty_text="A1 Feature 파일이 연결되면 원본 입력이 표시됩니다.")
