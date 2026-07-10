"""
Open-Meteo 기상 API 검증 (Phase 3 산출물)
==========================================
7/7 데모용 기상 API 실동작 확인.
- 실시간 조회 + 과거 폭염일 조회 검증
- 폭염일 확정: 2023-08-04 청계산 오후2시 29.2℃

실행: python weather_api_check.py  (네트워크 필요, Colab 권장)
"""
import urllib.request, urllib.parse, json

CHEONGGYE = (37.4212, 127.0421)


def realtime(lat, lon):
    """실시간 기상."""
    p = {"latitude": lat, "longitude": lon,
         "current": "temperature_2m,relative_humidity_2m,weather_code",
         "timezone": "Asia/Seoul"}
    url = f"https://api.open-meteo.com/v1/forecast?{urllib.parse.urlencode(p)}"
    with urllib.request.urlopen(url, timeout=5) as r:
        return json.load(r).get("current", {})


def archive(lat, lon, date, hour=14):
    """과거 폭염일 조회."""
    p = {"latitude": lat, "longitude": lon,
         "start_date": date, "end_date": date,
         "hourly": "temperature_2m,relative_humidity_2m,weather_code",
         "timezone": "Asia/Seoul"}
    url = f"https://archive-api.open-meteo.com/v1/archive?{urllib.parse.urlencode(p)}"
    with urllib.request.urlopen(url, timeout=5) as r:
        h = json.load(r)["hourly"]
    i = h["time"].index(f"{date}T{hour:02d}:00")
    return {"date": date, "temp": h["temperature_2m"][i],
            "humidity": h["relative_humidity_2m"][i],
            "code": h["weather_code"][i]}


if __name__ == "__main__":
    print("[실시간] 청계산:", realtime(*CHEONGGYE))
    print("\n[과거 폭염일 후보]")
    for d in ["2023-08-04", "2024-08-01", "2024-07-25"]:
        print(f"  {archive(*CHEONGGYE, d)}")
    print("\n→ 확정: 2023-08-04 (29.2℃, 흐림, 순수 고온일)")
