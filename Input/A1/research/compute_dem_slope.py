"""
DEM(Copernicus GLO-30) → 경사(slope) 계산 + A1 급경사 구간 통계
=====================================================================
목적: A1(급경사·추락) 시나리오의 핵심 입력인 '경사도'를 DEM 고도 격자에서 계산.
      가상 세션이 "이 구간 경사 몇 도"를 정박할 근거, 급경사 위험구간 산출.

입력: dem_sudogwon.tif (Copernicus DEM, EPSG:4326 위경도, 고도 m)
출력:
      slope_sudogwon.tif           경사 래스터 (도 단위)
      dist_summary_dem_slope.csv   경사 분포 요약 (다른 데이터셋과 동일 규격)
      steep_zone_stats.csv         급경사 구간 비율 (경사 등급별 픽셀 비율)

경사 계산 원리:
  DEM 좌표가 도(degree) 단위이므로, 경사를 정확히 구하려면 격자 간격을
  미터로 환산해야 한다.
    - 위도 방향 1도 ≈ 111,320 m (일정)
    - 경도 방향 1도 ≈ 111,320 × cos(위도) m (위도에 따라 달라짐)
  각 픽셀에서 x·y 방향 고도 기울기(gradient)를 미터 기준으로 구하고,
    slope = arctan( sqrt(dz/dx^2 + dz/dy^2) ) 를 도(°)로 변환.
  (표준 Horn 방식의 단순화 버전. numpy.gradient 사용.)

경사 등급 (A1 급경사 판정 참고용, 등산 맥락):
    완경사   < 15°
    중경사   15~30°
    급경사   30~45°
    매우급경사 ≥ 45°

사용:
  source demenv/bin/activate
  python compute_dem_slope.py dem_sudogwon.tif
"""
import sys, os
import numpy as np
import rasterio

DEG_TO_M = 111320.0  # 위도 1도의 미터 환산

# 경사 등급 경계(도)
GRADE_BINS = [0, 15, 30, 45, 90]
GRADE_NAMES = ["gentle(<15)", "moderate(15-30)", "steep(30-45)", "very_steep(>=45)"]
MAX_SAMPLES = 20000


def main(dem_path):
    src = rasterio.open(dem_path)
    dem = src.read(1).astype(float)
    nodata = src.nodata
    if nodata is not None:
        dem[dem == nodata] = np.nan
    dem[dem < -1000] = np.nan  # 이상 저값 제거

    # 격자 간격(도) → 미터
    lon_res_deg, lat_res_deg = abs(src.res[0]), abs(src.res[1])
    # 대상 영역 중앙 위도로 경도 환산 (영역이 넓지 않아 중앙값이면 충분)
    center_lat = (src.bounds.top + src.bounds.bottom) / 2.0
    dx = lon_res_deg * DEG_TO_M * np.cos(np.radians(center_lat))  # 경도 방향 픽셀폭(m)
    dy = lat_res_deg * DEG_TO_M                                   # 위도 방향 픽셀높이(m)

    # 고도 기울기 (미터 기준)
    dz_dy, dz_dx = np.gradient(dem, dy, dx)
    slope_rad = np.arctan(np.sqrt(dz_dx ** 2 + dz_dy ** 2))
    slope_deg = np.degrees(slope_rad)

    # 경사 래스터 저장
    prof = src.profile.copy()
    prof.update(dtype="float32", count=1, nodata=np.nan)
    out_tif = os.path.join(os.path.dirname(dem_path) or ".", "slope_sudogwon.tif")
    with rasterio.open(out_tif, "w", **prof) as dst:
        dst.write(slope_deg.astype("float32"), 1)

    # 유효 경사값만
    s = slope_deg[np.isfinite(slope_deg)]

    # 경사 분포 요약 (다른 데이터셋과 동일 규격)
    import pandas as pd
    summ = [{
        "dataset": "DEM_Copernicus", "variable": "slope_deg",
        "condition_key": "region", "condition_value": "sudogwon",
        "n": int(s.size),
        "mean": round(float(s.mean()), 2), "std": round(float(s.std()), 2),
        "min": round(float(s.min()), 2),
        "p05": round(float(np.percentile(s, 5)), 2),
        "p25": round(float(np.percentile(s, 25)), 2),
        "p50": round(float(np.percentile(s, 50)), 2),
        "p75": round(float(np.percentile(s, 75)), 2),
        "p95": round(float(np.percentile(s, 95)), 2),
        "max": round(float(s.max()), 2),
        "missing_rate": round(float(np.isnan(slope_deg).mean()), 4),
        "unit": "degree", "layer": "DERIVED_DEM",
        "license": "Copernicus DEM(free)",
    }]
    pd.DataFrame(summ).to_csv(
        os.path.join(os.path.dirname(dem_path) or ".", "dist_summary_dem_slope.csv"),
        index=False, encoding="utf-8-sig")

    # 급경사 등급별 비율
    counts, _ = np.histogram(s, bins=GRADE_BINS)
    total = counts.sum()
    grade_rows = []
    for name, c in zip(GRADE_NAMES, counts):
        grade_rows.append({
            "dataset": "DEM_Copernicus", "region": "sudogwon",
            "slope_grade": name, "pixel_count": int(c),
            "ratio": round(float(c / total), 4) if total else None,
        })
    pd.DataFrame(grade_rows).to_csv(
        os.path.join(os.path.dirname(dem_path) or ".", "steep_zone_stats.csv"),
        index=False, encoding="utf-8-sig")

    # 콘솔 요약
    print(f"경사 래스터 저장: {out_tif}")
    print(f"경사(도): 평균 {s.mean():.1f}, 중앙 {np.median(s):.1f}, "
          f"p95 {np.percentile(s,95):.1f}, 최대 {s.max():.1f}")
    print("\n[경사 등급별 비율]")
    for name, c in zip(GRADE_NAMES, counts):
        print(f"  {name:18s} {c/total*100:5.1f}%  ({c}px)")
    # 고도-경사 관계 참고
    steep_mask = slope_deg >= 30
    if np.isfinite(dem[steep_mask]).any():
        print(f"\n급경사(>=30도) 지점 평균 고도: "
              f"{np.nanmean(dem[steep_mask]):.0f}m "
              f"(전체 평균 {np.nanmean(dem):.0f}m)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용: python compute_dem_slope.py <dem.tif>")
        sys.exit(1)
    main(sys.argv[1])
