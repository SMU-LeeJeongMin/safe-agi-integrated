"""
실측 집계 엔진 (계층 1)
========================
원천 시계열 → 1분 feature. 실서비스/데모 공용 경로.
우회 없이 실제 집계·보간·GPS속도·UTC변환 수행.
"""
from datetime import datetime, timedelta, timezone
import math

KST = timezone(timedelta(hours=9))
UTC = timezone.utc


def to_utc(dt):
    """naive/KST datetime → UTC aware."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=KST)          # 원천은 KST(UTC+0900)
    return dt.astimezone(UTC)


def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1); dl = math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(a))


def _floor_min(dt):
    """분 단위 내림 (초 절삭)."""
    return dt.replace(second=0, microsecond=0)


def resample_1min(series, agg="mean"):
    """
    [(datetime, value)] → {분버킷datetime: 집계값}.
    agg: mean(가중평균 대신 단순평균) / min / max / sum
    """
    buckets = {}
    for dt, v in series:
        if v is None:
            continue
        key = _floor_min(dt)
        buckets.setdefault(key, []).append(v)
    out = {}
    for k, vs in buckets.items():
        if agg == "mean":
            out[k] = sum(vs) / len(vs)
        elif agg == "min":
            out[k] = min(vs)
        elif agg == "max":
            out[k] = max(vs)
        elif agg == "sum":
            out[k] = sum(vs)
    return out


def interpolate_minute(bucket, minute_keys):
    """
    분버킷 dict를 연속 분(minute_keys)으로 채움.
    빈 분은 앞뒤 값 시간가중 선형보간. 반환: (값dict, 보간된분set)
    """
    filled, interp = {}, set()
    known = sorted(bucket.keys())
    if not known:
        return filled, interp
    for m in minute_keys:
        if m in bucket:
            filled[m] = bucket[m]
            continue
        # 앞뒤 known 찾기
        prev = [k for k in known if k <= m]
        nxt = [k for k in known if k >= m]
        if prev and nxt:
            a, b = prev[-1], nxt[0]
            if a == b:
                filled[m] = bucket[a]
            else:
                span = (b - a).total_seconds()
                w = (m - a).total_seconds() / span
                filled[m] = bucket[a] * (1 - w) + bucket[b] * w
            interp.add(m)
        elif prev:                    # 뒤가 없음 → 마지막값 유지
            filled[m] = bucket[prev[-1]]; interp.add(m)
        elif nxt:                     # 앞이 없음 → 첫값 유지
            filled[m] = bucket[nxt[0]]; interp.add(m)
    return filled, interp


def gps_speed_1min(gps, minute_keys):
    """
    GPS [(datetime,lat,lon,alt)] → {분: (대표lat, 대표lon, 분당이동m, 속도mpm)}.
    각 분 버킷 내 좌표들의 누적 이동거리로 분당 이동량 실계산.
    """
    buckets = {}
    for dt, lat, lon, *_ in gps:
        buckets.setdefault(_floor_min(dt), []).append((dt, lat, lon))
    out = {}
    for m in minute_keys:
        pts = sorted(buckets.get(m, []))
        if not pts:
            out[m] = None
            continue
        # 분내 누적 이동거리 (GPS 노이즈 클리핑)
        # 실데이터 검증서 발견: 산속 워치 GPS가 위성 재획득 순간 좌표 점프(최대 400m/초).
        # 사람 보행 최대 ~8m/s → 초당 이동이 이를 넘으면 노이즈로 보고 해당 구간 제외.
        dist = 0.0
        for i in range(len(pts) - 1):
            seg = haversine_m(pts[i][1], pts[i][2], pts[i+1][1], pts[i+1][2])
            dt_sec = (pts[i+1][0] - pts[i][0]).total_seconds()
            if dt_sec <= 0:
                continue
            if seg / dt_sec > 8.0:      # 8m/s 초과 = 비현실적 점프 → 제외
                continue
            dist += seg
        dist = min(dist, 120.0)          # 이중 방어: 분당 120m 상한 클리핑
        rep_lat = sum(p[1] for p in pts) / len(pts)
        rep_lon = sum(p[2] for p in pts) / len(pts)
        out[m] = (round(rep_lat, 6), round(rep_lon, 6),
                  round(dist, 1), round(dist, 1))   # 1분이므로 이동량=분당속도
    return out


def sustained_overload(minute_rows, ratio_key, lo=0.60, hi=0.80, minutes=5):
    """
    시간 기반 5분 지속 판정. minute_rows: [(ts, {..ratio..})] 시간순.
    각 행에 hr_overload_5min bool 부여 반환.
    """
    flags = []
    streak_start = None
    for ts, r in minute_rows:
        val = r[ratio_key]
        if val >= lo:                     # 과부하 진입: 하한(0.6) 이상 (심박↑=위험↑, 단조)
            if streak_start is None:      # hi(0.80)는 스키마상 밴드 상단 '표기'용 — 판정엔 미사용
                streak_start = ts
            elapsed = (ts - streak_start).total_seconds() / 60
            flags.append(elapsed >= minutes)
        else:
            streak_start = None
            flags.append(False)
    return flags


if __name__ == "__main__":
    # 자가검증: 8분 간격 심박 → 1분 보간
    base = datetime(2025, 8, 21, 14, 0, tzinfo=KST)
    series = [(base + timedelta(minutes=i), 80 + i) for i in range(0, 20, 8)]
    bucket = resample_1min(series)
    keys = [_floor_min(base) + timedelta(minutes=i) for i in range(0, 17)]
    filled, interp = interpolate_minute(bucket, keys)
    print(f"원천 {len(series)}점 → 1분 {len(filled)}개, 보간 {len(interp)}개")
    print(f"  예: {keys[0].strftime('%H:%M')}={filled[keys[0]]:.1f}, "
          f"{keys[4].strftime('%H:%M')}={filled[keys[4]]:.1f}(보간)")
    print(f"UTC 변환: {base} → {to_utc(base)}")
