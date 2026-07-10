"""
DTO-5 스키마 v3 (규격서 DTO_v1.2 정합)
=======================================
5블록 통합 JSON: course_recommendation / risk / fatigue / descent_warning / alerts[]
F1 시나리오는 fatigue + alerts[] 사용.

규격 확정값 (docs/spec_reconciliation_v3.md):
- risk.representative = max(e1_biometric, e2_combined)
- fatigue.state ∈ {정상, 휴식 권고, 즉시 중단}
- nearest_shelter: poi_id/name/lat/lon/distance_m/est_min (cate_cd 없음)
- level 기준: 정상<0.5 / 주의0.50~0.64 / 경고0.65~0.84 / 위험0.85~1.0
"""
from dataclasses import dataclass, field
from typing import Optional
import datetime


# 규격 주3: risk.level 색상 기준
def risk_level(representative):
    """대표 위험도 → (level_int, label)."""
    if representative >= 0.85:
        return 3, "위험"
    if representative >= 0.65:
        return 2, "경고"
    if representative >= 0.50:
        return 1, "주의"
    return 0, "정상"


# F1 alert 문구 (규격 표55, 그대로 사용)
F1_ALERTS = {
    1: {"title": "잠시 쉬어가세요",
        "message": "심박과 피로 신호가 평소보다 높습니다. 가까운 쉼터에서 5분 이상 휴식하세요."},
    2: {"title": "즉시 휴식이 필요해요",
        "message": "피로 누적이 한계치에 도달했습니다. 가장 가까운 쉼터로 이동해 충분히 회복한 뒤 산행을 이어가세요."},
}


def build_dto5(*, uuid, ts, e1_biometric, e2_combined,
               fatigue_state, fatigue_confidence, nearest_shelter=None,
               descent_required=False, descent_reason=None,
               remaining_daylight_min=None, course_recommendation=None,
               alerts=None):
    """
    규격 정합 DTO-5 JSON 생성.
    F1에서 채우는 값 위주, 나머지 블록은 규격 기본값.
    """
    representative = round(max(e1_biometric, e2_combined), 4)
    lvl, label = risk_level(representative)
    return {
        "uuid": uuid,
        "ts": ts.isoformat() if hasattr(ts, "isoformat") else ts,
        "course_recommendation": course_recommendation,   # F-4용, F1은 null
        "risk": {
            "e1_biometric": round(e1_biometric, 4),
            "e2_combined": round(e2_combined, 4),
            "representative": representative,
            "level": lvl,
            "label": label,
        },
        "fatigue": {
            "state": fatigue_state,                # 정상|휴식 권고|즉시 중단
            "confidence": round(fatigue_confidence, 4),
            "nearest_shelter": nearest_shelter,    # 정상이면 null
        },
        "descent_warning": {
            "required": descent_required,
            "reason": descent_reason,              # null|일몰임박|기상급변
            "remaining_daylight_min": remaining_daylight_min,
        },
        "alerts": alerts or [],
    }


def f1_alert(level):
    """F1 alert 객체 생성 (규격 표55 문구)."""
    a = F1_ALERTS.get(level)
    if not a:
        return None
    return {"type": "F1", "level": level,
            "title": a["title"], "message": a["message"]}


def make_shelter(poi_id, name, lat, lon, distance_m, est_min):
    """nearest_shelter 블록 (규격 정합: est_min 포함, cate_cd 없음)."""
    return {"poi_id": poi_id, "name": name, "lat": lat, "lon": lon,
            "distance_m": int(distance_m), "est_min": int(est_min)}


if __name__ == "__main__":
    d = build_dto5(
        uuid="sess_demo_f1", ts=datetime.datetime(2025, 8, 21, 6, 27),
        e1_biometric=0.80, e2_combined=0.72,
        fatigue_state="휴식 권고", fatigue_confidence=0.76,
        nearest_shelter=make_shelter(10001, "깔딱고개쉼터", 37.6617, 126.9879, 197, 3),
        alerts=[f1_alert(1)],
    )
    import json
    print(json.dumps(d, ensure_ascii=False, indent=2))
