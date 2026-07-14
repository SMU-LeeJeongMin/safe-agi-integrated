"""
실 safe_db read 어댑터 (Phase 2 신규)
=====================================
기존 biometric.py(삼성헬스 zip 입력) → 실 DB read 입력으로 교체.

2층 구조 유지:
  [DB read] → (이 모듈: db_adapter) → [표준 중간형식] → (build_features) → [20컬럼]

표준 중간형식(build_from_series 입력 규격, 삼성헬스 어댑터와 동일):
  hr_series   : [(datetime, hr_bpm)]
  spo2_series : [(datetime, spo2_pct)]
  step_series : [(datetime, steps)]
  gps_series  : [(datetime, lat, lon, alt)]   # alt는 None
  session_meta: dict (uuid, age_group, gender, hr_rest 실측, t_end 등)

Phase 1 발견 → Phase 2 반영 사항
- interval == 시점 데이터: HR/SpO2/step 모두 start_time == end_time.
  구간가중 평균 대신 시점값으로 취급(resample_1min이 시점값 단순평균 처리).
- SpO2 0건 세션 정상: spo2_series=[] → spo2_min_pct=null → grade='미측정'.
- hiking_sessions.end_time null 가능: cumulative_min은 activity 마지막 ts로 계산.
- GPS 속도 컬럼 없음: activity_samples.gps_lat/lon → build_features가 haversine/분 계산.
- users.age_group/gender null 정상: PERSONA 상수 fallback.
- session_biometric_summary.hr_rest 있으면 개인 baseline 실측 우선.
- ts는 timestamp without time zone (UTC/KST 미확정): naive 그대로 반환, 시간대 판단은 상위 레이어.

매핑표 (Phase 1 확정):
  DTO-1 개념        실 테이블                        컬럼
  ----------------  -------------------------------  -----------------------------
  uuid/세션          hiking_sessions                  session_id
  heart_rates       heart_rate_intervals             start_time, value_bpm
  blood_oxygens     spo2_intervals                   start_time, value_pct
  steps             step_intervals                   start_time, value_steps
  samples.gps       activity_samples                 ts, gps_lat, gps_lon
  x_profile         users                            age_group, gender
  개인 baseline      session_biometric_summary        hr_rest, hr_mean, hr_max
  세션 시간          hiking_sessions                  start_time, end_time
"""
from datetime import datetime
from sqlalchemy import create_engine, text
from features.baseline_reference import get_baseline


def _as_dt(v):
    """
    ts / start_time 컬럼을 datetime으로 정규화.
    실 DB(psycopg2)는 timestamp without time zone → datetime 반환하지만,
    드라이버/문자열 저장 경우를 대비해 방어적으로 파싱. tz 정보는 부여하지 않음
    (UTC/KST 미확정 — naive 유지, 시간대 판단은 상위 레이어).
    """
    if v is None or isinstance(v, datetime):
        return v
    s = str(v).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s[:26] if "." in s else s[:19], fmt)
        except ValueError:
            continue
    return None


# ── 접속 (read-only 전용). 접속정보는 .env(환경변수)에서 로드. ──────────────
# 필요한 키: SAFE_DB_HOST / PORT / NAME / USER / PASSWORD (.env.example 참고)
# read-only 보장: SELECT만 발행하며, 세션을 default_transaction_read_only로 강제.
def make_engine(url=None, *, host=None, port=None,
                db=None, user=None, pw=None):
    # 접속정보는 코드에 하드코딩하지 않고 .env(환경변수)에서 읽는다.
    # (GitHub 노출 방지. .env는 .gitignore로 커밋 차단)
    import os
    from dotenv import load_dotenv
    load_dotenv()  # 프로젝트 루트의 .env 로드

    host = host or os.environ.get("SAFE_DB_HOST")
    port = port or os.environ.get("SAFE_DB_PORT", "5432")
    db   = db   or os.environ.get("SAFE_DB_NAME", "safe_db")
    user = user or os.environ.get("SAFE_DB_USER")
    pw   = pw   or os.environ.get("SAFE_DB_PASSWORD")

    if url is None:
        if not all([host, user, pw]):
            raise RuntimeError(
                "DB 접속정보 없음. 프로젝트 루트에 .env를 만들고 "
                "SAFE_DB_HOST/USER/PASSWORD를 설정하세요 (.env.example 참고).")
        url = f"postgresql+psycopg2://{user}:{pw}@{host}:{port}/{db}"

    # 라이브 무변경 방어: 커넥션마다 read-only 트랜잭션 강제
    eng = create_engine(url, connect_args={"options": "-c default_transaction_read_only=on"})
    return eng


# ── 세션 신호 read ───────────────────────────────────────────────────────
def load_session(engine, session_id):
    """
    session_id 하나의 모든 신호를 표준 중간형식으로 반환.
    반환: (hr_series, spo2_series, step_series, gps_series, session_meta)
    """
    with engine.connect() as conn:
        meta = _load_meta(conn, session_id)
        hr = _load_hr(conn, session_id)
        spo2 = _load_spo2(conn, session_id)
        step = _load_step(conn, session_id)
        gps = _load_gps(conn, session_id)
        # end_time이 null이면 activity 마지막 ts로 세션 종료 시각 확정
        if meta.get("end_time") is None and gps:
            meta["end_time"] = gps[-1][0]
        elif meta.get("end_time") is None and hr:
            meta["end_time"] = hr[-1][0]
    return hr, spo2, step, gps, meta


def _load_meta(conn, sid):
    row = conn.execute(text("""
        SELECT s.session_id, s.user_id, s.start_time, s.end_time,
               u.age_group, u.gender,
               b.hr_rest, b.hr_mean, b.hr_max, b.spo2_mean, b.steps_total
        FROM hiking_sessions s
        LEFT JOIN users u ON u.user_id = s.user_id
        LEFT JOIN session_biometric_summary b ON b.session_id = s.session_id
        WHERE s.session_id = :sid
    """), {"sid": sid}).mappings().first()
    if row is None:
        raise ValueError(f"세션 없음: {sid}")
    d = dict(row)
    d["start_time"] = _as_dt(d.get("start_time"))
    d["end_time"] = _as_dt(d.get("end_time"))
    return d


def _load_hr(conn, sid):
    """heart_rate_intervals → [(ts, bpm)]. 시점값(start==end) 취급."""
    rows = conn.execute(text("""
        SELECT start_time, value_bpm FROM heart_rate_intervals
        WHERE session_id = :sid AND value_bpm > 0
        ORDER BY start_time
    """), {"sid": sid}).all()
    return [(_as_dt(r[0]), float(r[1])) for r in rows]


def _load_spo2(conn, sid):
    """spo2_intervals → [(ts, pct)]. 0건이면 [] (정상 케이스)."""
    rows = conn.execute(text("""
        SELECT start_time, value_pct FROM spo2_intervals
        WHERE session_id = :sid AND value_pct > 0
        ORDER BY start_time
    """), {"sid": sid}).all()
    return [(_as_dt(r[0]), float(r[1])) for r in rows]


def _load_step(conn, sid):
    """step_intervals → [(ts, steps)]. 시점값 취급."""
    rows = conn.execute(text("""
        SELECT start_time, value_steps FROM step_intervals
        WHERE session_id = :sid
        ORDER BY start_time
    """), {"sid": sid}).all()
    return [(_as_dt(r[0]), float(r[1])) for r in rows]


def _load_gps(conn, sid):
    """
    activity_samples → [(ts, lat, lon, None)].
    속도 컬럼 없음 → build_features의 gps_speed_1min이 haversine/분으로 산출.
    gps_lat/lon null 샘플은 제외(가속도만 있고 위치 없는 실내/터널 구간).
    """
    rows = conn.execute(text("""
        SELECT ts, gps_lat, gps_lon FROM activity_samples
        WHERE session_id = :sid AND gps_lat IS NOT NULL AND gps_lon IS NOT NULL
        ORDER BY ts
    """), {"sid": sid}).all()
    return [(_as_dt(r[0]), float(r[1]), float(r[2]), None) for r in rows]


def resolve_baseline(session_meta, persona=None):
    """
    개인 baseline 결정:
      1) session_biometric_summary.hr_rest 실측 있으면 우선 사용
      2) 없으면 get_baseline(age_band, gender)로 국건영 연령대별 기준
         (프로필 null이면 성인 전체통계 fallback)
    반환: dict(resting_hr, hr_std, max_hr, is_fallback, source)
    """
    age = session_meta.get("age_group")
    gender = session_meta.get("gender")
    ref = get_baseline(age, gender)

    hr_rest = session_meta.get("hr_rest")
    if hr_rest is not None and hr_rest > 0:
        return {
            "resting_hr": float(hr_rest), "hr_std": ref["resting_std"],
            "max_hr": ref["max_hr"], "is_fallback": ref["is_fallback"],
            "source": "session_biometric_summary.hr_rest(실측)",
        }
    return {
        "resting_hr": ref["resting_hr"], "hr_std": ref["resting_std"],
        "max_hr": ref["max_hr"], "is_fallback": ref["is_fallback"],
        "source": ref["resting_source"],
    }


def resolve_profile(session_meta, persona=None):
    """age_group/gender를 null 그대로 반환 (PERSONA 대체 안 함)."""
    return session_meta.get("age_group"), session_meta.get("gender")
