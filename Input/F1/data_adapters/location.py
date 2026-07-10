"""
위치 데이터 어댑터
==================
1) 운동 세션 GPS: exercise location_data JSON (lat/lon/altitude, epoch ms)
2) POI 안전쉼터·응급시설: 03 shapefile (nearest_shelter 산출용)
"""
import os, json, math
from datetime import datetime
from .common import get_zip


def load_session_gps(z, session_json_path):
    """세션 location JSON(전체 경로 또는 부분문자열) → [(datetime, lat, lon, alt)]."""
    for n in z.namelist():
        if "__MACOSX" in n or not n.endswith(".json"):
            continue
        if n == session_json_path or session_json_path in n:
            j = json.loads(z.open(n).read().decode("utf-8", errors="replace"))
            out = []
            for item in j:
                if not isinstance(item, dict):
                    continue
                lat = item.get("latitude"); lon = item.get("longitude")
                if lat is None or lon is None:
                    continue
                ts = item.get("start_time")
                dt = datetime.fromtimestamp(ts / 1000) if ts else None
                out.append((dt, float(lat), float(lon), item.get("altitude")))
            out.sort(key=lambda x: (x[0] is None, x[0] or datetime.min))
            return out
    return []


def find_any_summer_gps(z):
    """여름 등산 세션 GPS 하나를 자동 선택(청계산권 좌표 우선)."""
    locs = [n for n in z.namelist()
            if "location_data" in n and n.endswith(".json") and "__MACOSX" not in n]
    best = None
    for n in locs:
        try:
            j = json.loads(z.open(n).read().decode("utf-8", errors="replace"))
        except Exception:
            continue
        pts = [(it.get("latitude"), it.get("longitude"), it.get("altitude"),
                it.get("start_time")) for it in j if isinstance(it, dict)
               and it.get("latitude")]
        if len(pts) < 50:
            continue
        # 여름 판정
        ts = next((p[3] for p in pts if p[3]), None)
        if not ts:
            continue
        month = datetime.fromtimestamp(ts / 1000).month
        alts = [p[2] for p in pts if p[2] is not None]
        alt_gain = (max(alts) - min(alts)) if alts else 0
        # 여름 + 고도변화 큰(등산성) 세션 우선
        score = (month in (6, 7, 8)) * 1000 + alt_gain
        if best is None or score > best[0]:
            best = (score, n, len(pts), month, alt_gain)
    return best


# ---------- POI 쉼터 ----------
# 휴식지점 카테고리 (우선순위: 낮을수록 우선). 규격 표27 기반.
REST_POI_PRIORITY = {
    "300200": (1, "쉼터"),
    "300700": (2, "매점/휴게소"),
    "300900": (2, "탐방지원센터"),
    "300300": (3, "약수터"),
    "600100": (3, "전망대"),
    "300100": (4, "화장실"),
    "600000": (4, "봉우리/명소"),
    "200200": (4, "계곡"),
}
_SAFETY_CODES = set(REST_POI_PRIORITY.keys())


def load_shelters(mountain_name=None):
    """
    03 POI shapefile에서 안전쉼터+응급시설 반환.
    [(name, cate_cd, lon, lat, mntn)]. mountain_name 지정 시 필터.
    """
    import shapefile
    base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "data_raw", "extracted")
    top = os.path.join(base, os.listdir(base)[0])
    p03 = os.path.join(top, [d for d in os.listdir(top) if d.startswith("03_")][0])
    poidir = os.path.join(p03, "poi")
    shps = []
    for dp, _, files in os.walk(poidir):
        for fn in files:
            if fn.endswith(".shp"):
                shps.append(os.path.join(dp, fn))
    out = []
    for shp in shps:
        try:
            r = shapefile.Reader(shp, encoding="utf-8")
        except Exception:
            continue
        flds = [f[0] for f in r.fields[1:]]
        ix = {f: i for i, f in enumerate(flds)}
        for rec in r.records():
            cd = str(rec[ix["CATE_CD"]]).strip()
            if cd not in _SAFETY_CODES:
                continue
            mntn = rec[ix["MNTN_NM"]]
            if mountain_name and mountain_name not in str(mntn):
                continue
            out.append((rec[ix["POI_NM"]], cd,
                        float(rec[ix["XCRD"]]), float(rec[ix["YCRD"]]), mntn))
    return out


def haversine_m(lat1, lon1, lat2, lon2):
    """두 좌표 간 거리(m)."""
    R = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1); dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def nearest_shelter(lat, lon, shelters, max_detour_m=200):
    """
    가장 가까운 휴식지점 → dict.
    우선순위 규칙: 최근접을 기본으로 하되, max_detour_m 이내에 더 높은 우선순위
    (쉼터 등)가 있으면 그것을 선택 (약수터보다 쉼터가 조금 멀어도 쉼터 안내).
    """
    if not shelters:
        return None
    scored = []
    for s in shelters:
        name, cd, x, y, mntn = s
        d = haversine_m(lat, lon, y, x)
        # cd가 CATE_CD(300200 등)면 REST_POI_PRIORITY, 청계산 키워드면 CHEONGGYE
        if cd in REST_POI_PRIORITY:
            pri, label = REST_POI_PRIORITY[cd]
        elif cd in CHEONGGYE_REST_KW:
            pri, label = CHEONGGYE_REST_KW[cd], cd
        else:
            pri, label = 9, "기타"
        scored.append((d, pri, label, s))
    scored.sort(key=lambda t: t[0])            # 거리순
    nearest_d = scored[0][0]
    # 최근접 반경 + max_detour 안에서 우선순위 최상 선택
    within = [t for t in scored if t[0] <= nearest_d + max_detour_m]
    best = min(within, key=lambda t: (t[1], t[0]))   # 우선순위→거리
    d, pri, label, s = best
    return {"poi_id": None, "name": s[0], "cate_cd": s[1],
            "poi_type": label, "distance_m": int(d), "lat": s[3], "lon": s[2]}


if __name__ == "__main__":
    z = get_zip()
    best = find_any_summer_gps(z)
    print("자동선택 여름 GPS 세션:", best)
    if best:
        gps = load_session_gps(z, best[1])
        print(f"  GPS {len(gps)}점, 시작 {gps[0][1]:.5f},{gps[0][2]:.5f}, 고도 {gps[0][3]}")
    sh = load_shelters()
    print(f"쉼터 총 {len(sh)}개")
    if best and gps:
        ns = nearest_shelter(gps[0][1], gps[0][2], sh)
        print(f"  시작점 최근접 쉼터: {ns}")


# ── est_min: GIS FLINK 실측 보행속도 기반 (경사 보정 추정) ──
# 근거: 01 GIS FLINK 2,579구간 실측 보행속도 평균 45.9 m/min (2.8km/h)
#       평지 4km/h가 아닌 등산로 실측값 사용.
TRAIL_WALK_MPM = 45.9      # 등산로 실측 평균 보행속도 (m/min)


def estimate_walk_min(distance_m, walk_mpm=TRAIL_WALK_MPM):
    """
    도달 예상시간(분) = 거리 / 등산로 실측 보행속도.
    경사 보정 추정치 (직선거리 기반, FLINK 경로탐색은 실서비스 전환 시).
    """
    return max(round(distance_m / walk_mpm), 1)


# ── 청계산 POI 전용 로더 (업로드 파일, 특수 처리) ──
# 주의: 이 파일은 CATE_CD 비어있음 → POI_NM 기반 분류.
#       dbf XCRD/YCRD 필드명 뒤바뀜 → shape geometry 사용.
CHEONGGYE_REST_KW = {
    "쉼터": 1, "전망휴게": 2, "휴게": 2, "약수": 3,
    "전망": 3, "화장실": 4, "정상": 4, "봉": 4, "계곡": 4, "벤치": 4,
}


def load_cheonggye_rest(shp_path):
    """
    청계산 POI에서 휴식지점 로드 (이름 기반, geometry 좌표).
    반환: [(name, cate_label, lon, lat, priority)]
    """
    import shapefile
    r = shapefile.Reader(shp_path, encoding="utf-8")
    recs = r.records()
    flds = [f[0] for f in r.fields[1:]]
    ix = {f: i for i, f in enumerate(flds)}
    out = []
    for i, sh in enumerate(r.shapes()):
        if not sh.points:
            continue
        lon, lat = sh.points[0]          # geometry는 (경도,위도) 정상
        nm = str(recs[i][ix["POI_NM"]])
        for kw, pri in CHEONGGYE_REST_KW.items():
            if kw in nm:
                out.append((nm, kw, lon, lat, pri))
                break
    return out
