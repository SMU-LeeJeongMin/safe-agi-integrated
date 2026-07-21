# A1 현재 위치와 위험 POI 지도 (공용 지도 골격 호출)

from __future__ import annotations

import streamlit as st

from components.panel_kit import (
    render_soft_notice,
    render_location_map,
)
from scenarios.a1.mapper import A1Context, first_value, nested, row_value, to_float


def render_a1_map(context: A1Context) -> None:
    row = context.row
    user_lat = to_float(first_value(row_value(row, "user_lat", "gps_lat", "lat"), nested(context.dto5, "user_location", "lat")))
    user_lon = to_float(first_value(row_value(row, "user_lon", "gps_lon", "lon"), nested(context.dto5, "user_location", "lon")))
    hazard_lat = to_float(first_value(row_value(row, "hazard_lat"), context.location.get("lat")))
    hazard_lon = to_float(first_value(row_value(row, "hazard_lon"), context.location.get("lon")))

    if None in {user_lat, user_lon, hazard_lat, hazard_lon}:
        render_soft_notice("사용자 위치와 위험 POI 좌표가 연결되면 지도에 표시됩니다.")
        return

    radius = to_float(row_value(row, "danger_radius_m", "hazard_radius_m", "outer_radius_m"))
    render_location_map(
        points=[
            {"lat": user_lat, "lon": user_lon, "label": "현재 위치", "kind": "current"},
            {"lat": hazard_lat, "lon": hazard_lon, "label": "위험 POI", "kind": "hazard"},
        ],
        zoom=14.0,
        legend=[("dot-blue", "현재 위치"), ("dot-red", "위험 POI")],
        circle={"lat": hazard_lat, "lon": hazard_lon, "radius": radius} if radius is not None and radius > 0 else None,
    )
