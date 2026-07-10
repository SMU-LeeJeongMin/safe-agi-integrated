"""
기상 API 어댑터 (기상청 단기예보/초단기실황)
=============================================
회의 결정: 실제 적용은 기상청 API. 단 실시간 기상 데이터 미보유 상태.
→ API 인터페이스는 정의하되, 데모는 가상 주입(inject) 사용.
→ environment_logs 테이블(temperature/humidity/precipitation/lightning) 대응.

발표 대응: "API 연동 구조는 갖췄고, 데모 값은 가상 주입" 이라고 설명 가능.
"""
import math
from datetime import datetime


class WeatherProvider:
    """기상 데이터 공급자 추상 인터페이스."""
    def get_weather(self, lat, lon, when):
        raise NotImplementedError


class KmaApiProvider(WeatherProvider):
    """
    기상청 단기예보/초단기실황 API 어댑터 (실서비스용).
    현재 API 키·수신경로 미확보 → 호출부만 정의, 데모에선 미사용.
    """
    BASE_URL = ("http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0"
                "/getUltraSrtNcst")

    def __init__(self, service_key=None):
        self.service_key = service_key

    def get_weather(self, lat, lon, when):
        if not self.service_key:
            raise RuntimeError(
                "기상청 API 키 미설정. 데모는 VirtualWeatherProvider 사용.")
        # 실서비스: lat/lon → 기상청 격자(nx,ny) 변환 후 requests 호출
        raise NotImplementedError("실서비스 연동 시 구현")


class OpenMeteoProvider(WeatherProvider):
    """
    Open-Meteo API (7/7 데모용). API 키 불필요, 위경도로 현재 기상 조회.
    실제 프로젝트 적용은 KmaApiProvider(기상청)로 전환 예정.

    ※ 이 작업환경은 외부 네트워크 차단으로 실호출 테스트 불가.
      인터페이스·파싱은 규격대로 구현. 실동작 확인은 실서버/로컬에서.
    """
    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(self, timeout=5):
        self.timeout = timeout

    def get_weather(self, lat, lon, when=None):
        import urllib.request, urllib.parse, json
        params = {
            "latitude": lat, "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,"
                       "wind_speed_10m,precipitation,weather_code",
            "timezone": "Asia/Seoul",
        }
        url = f"{self.BASE_URL}?{urllib.parse.urlencode(params)}"
        try:
            with urllib.request.urlopen(url, timeout=self.timeout) as resp:
                data = json.load(resp)
        except Exception as e:
            raise RuntimeError(f"Open-Meteo 호출 실패: {e}. "
                               f"데모 폴백은 StatVirtualWeatherProvider 사용.")
        cur = data.get("current", {})
        temp = cur.get("temperature_2m")
        hum = cur.get("relative_humidity_2m")
        code = cur.get("weather_code")
        return {
            "temperature": temp,             # ℃
            "humidity": hum,                 # %
            "wind_speed": cur.get("wind_speed_10m"),   # km/h (Open-Meteo 기본)
            "precipitation_mm": cur.get("precipitation", 0.0),
            "weather_code": code,            # WMO 코드
            "lightning_detected": code in (95, 96, 99),   # WMO 뇌우 코드
            "heat_index": heat_index(temp, hum) if temp is not None and hum is not None else temp,
            "source": "open_meteo_api",
            "observed_at": cur.get("time"),
        }


# WMO weather_code 참고 (E계열 시나리오용):
#   0 맑음 / 1-3 대체로맑음~흐림 / 45-48 안개 / 51-67 이슬비~비
#   71-77 눈 / 80-82 소나기 / 95-99 뇌우(낙뢰)


class OpenMeteoArchiveProvider(WeatherProvider):
    """
    Open-Meteo 과거조회 API (절충안: 실 API 연동 + 고온 확보).
    특정 과거 폭염일의 특정 시각 실측 기상을 조회.
    → 실시간과 동일하게 '실제 API 호출'이면서 고온값 확보.

    시연용: 실제 폭염일(예: 작년 8월 최고기온일) 오후 2시 기상을 불러옴.
    ※ 이 작업환경은 외부 네트워크 차단으로 실호출 테스트 불가.
      실동작 확인은 실서버/Colab에서.

    endpoint가 forecast와 다름: /v1/archive + start_date/end_date + hourly.
    """
    BASE_URL = "https://archive-api.open-meteo.com/v1/archive"

    def __init__(self, date="2024-08-01", hour=14, timeout=5):
        self.date = date        # 조회할 과거 폭염일 (YYYY-MM-DD)
        self.hour = hour        # 조회 시각 (한낮 고온)
        self.timeout = timeout

    def get_weather(self, lat, lon, when=None):
        import urllib.request, urllib.parse, json
        params = {
            "latitude": lat, "longitude": lon,
            "start_date": self.date, "end_date": self.date,
            "hourly": "temperature_2m,relative_humidity_2m,"
                      "wind_speed_10m,precipitation,weather_code",
            "timezone": "Asia/Seoul",
        }
        url = f"{self.BASE_URL}?{urllib.parse.urlencode(params)}"
        try:
            with urllib.request.urlopen(url, timeout=self.timeout) as resp:
                data = json.load(resp)
        except Exception as e:
            raise RuntimeError(f"Open-Meteo archive 호출 실패: {e}. "
                               f"폴백은 StatVirtualWeatherProvider 사용.")
        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        # 지정 시각(YYYY-MM-DDTHH:00) 인덱스 찾기
        target = f"{self.date}T{self.hour:02d}:00"
        try:
            i = times.index(target)
        except ValueError:
            i = 0
        temp = hourly.get("temperature_2m", [None])[i]
        hum = hourly.get("relative_humidity_2m", [None])[i]
        code = hourly.get("weather_code", [None])[i]
        return {
            "temperature": temp,
            "humidity": hum,
            "wind_speed": hourly.get("wind_speed_10m", [None])[i],
            "precipitation_mm": hourly.get("precipitation", [0.0])[i],
            "weather_code": code,
            "lightning_detected": code in (95, 96, 99),
            "heat_index": heat_index(temp, hum) if temp is not None and hum is not None else temp,
            "source": "open_meteo_archive",
            "observed_at": target,
        }


class VirtualWeatherProvider(WeatherProvider):
    """
    데모용 가상 기상 주입 (회의 확정: 여름 28℃/습도 70%).
    """
    def __init__(self, temp_c=28.0, humidity=70.0,
                 precipitation_mm=0.0, lightning=False):
        self.temp_c = temp_c
        self.humidity = humidity
        self.precipitation_mm = precipitation_mm
        self.lightning = lightning

    def get_weather(self, lat, lon, when):
        return {
            "temperature": self.temp_c,
            "humidity": self.humidity,
            "precipitation_mm": self.precipitation_mm,
            "lightning_detected": self.lightning,
            "heat_index": heat_index(self.temp_c, self.humidity),
            "source": "virtual_injection",
        }


def heat_index(temp_c, humidity):
    """체감온도(℃). NWS heat index (고온용), 저온은 기온 그대로."""
    if temp_c < 20:
        return round(temp_c, 1)
    t = temp_c * 9 / 5 + 32
    r = humidity
    hi = (-42.379 + 2.04901523 * t + 10.14333127 * r
          - 0.22475541 * t * r - 0.00683783 * t * t
          - 0.05481717 * r * r + 0.00122874 * t * t * r
          + 0.00085282 * t * r * r - 0.00000199 * t * t * r * r)
    return round((hi - 32) * 5 / 9, 1)


def load_exercise_weather(z):
    """운동세션 실측 날씨 [(datetime, temp, humidity, heat_index)] — 발표 실증근거."""
    from .common import load_csv, col_index, parse_dt
    hdr, rows = load_csv(z, "exercise.weather")
    i_st = col_index(hdr, "start_time")
    i_t = col_index(hdr, "temperature")
    i_h = col_index(hdr, "humidity")
    out = []
    if i_st is None or i_t is None or i_h is None:   # 필수 컬럼 누락 시 방어
        return out
    for r in rows:
        if len(r) <= max(i_st, i_t, i_h):
            continue
        dt = parse_dt(r[i_st])
        if not dt:
            continue
        try:
            temp = float(r[i_t]); hum = float(r[i_h])
        except (ValueError, IndexError):
            continue
        out.append((dt, temp, hum, heat_index(temp, hum)))
    out.sort()
    return out


if __name__ == "__main__":
    vp = VirtualWeatherProvider()
    print("가상 기상(데모):", vp.get_weather(37.65, 126.98, datetime.now()))
    from .common import get_zip
    w = load_exercise_weather(get_zip())
    summer = [x for x in w if x[0].month in (6, 7, 8)]
    print(f"실측 여름 날씨 {len(summer)}건, 예: {summer[0] if summer else None}")


# ── 통계 기반 가상 기상 생성기 (04 현황데이터 실측 분포 근거) ──
# 근거: 산악사고 33,380건의 여름 시간대별 기상 실측 (data_adapters/accident 소스)
# 실측 평균(여름): 8시 23℃/82%, 12시 27.5℃/63%, 14시 28.5℃/59%, 16시 28℃/61%
SUMMER_HOURLY = {   # 시: (기온평균, 기온표준편차, 습도평균, 풍속평균)
    8:  (23.2, 3.5, 82, 1.2),
    10: (26.0, 3.5, 69, 1.7),
    12: (27.5, 3.5, 63, 2.1),
    14: (28.5, 3.9, 59, 2.4),
    16: (28.1, 4.3, 61, 2.5),
}


class StatVirtualWeatherProvider(WeatherProvider):
    """
    실측 분포 기반 가상 기상 (04 현황데이터 여름 시간대별 통계).
    VirtualWeatherProvider(고정값)보다 현실적. 시각에 따라 기온·습도 변동.
    """
    def __init__(self, season="summer"):
        self.season = season

    def get_weather(self, lat, lon, when):
        hour = when.hour if hasattr(when, "hour") else 14
        # 가장 가까운 기준 시각의 통계 사용
        ref = min(SUMMER_HOURLY.keys(), key=lambda h: abs(h - hour))
        ta, ta_std, hm, ws = SUMMER_HOURLY[ref]
        return {
            "temperature": ta,
            "temperature_std": ta_std,      # 불확실성 표기
            "humidity": hm,
            "wind_speed": ws,
            "precipitation_mm": 0.0,
            "lightning_detected": False,
            "heat_index": heat_index(ta, hm),
            "source": "stat_virtual(accident_history_summer)",
            "basis": "산악사고 33,380건 여름 시간대별 실측 분포",
        }
