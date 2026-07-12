"""
Phase 3 인터페이스 — Role A가 B/서버(result.py)에 제공하는 진입점.
=================================================================
session_id → 20컬럼 피처표(DataFrame). 지금까지 넘겨온 피처표와 동일 형식.

사용 예 (B / services/result.py):
    from pipeline_api import get_engine, build_features_for_session

    eng = get_engine()                                   # 앱 시작 시 1회
    features_df = build_features_for_session(eng, session_id)   # 요청마다
    # features_df: 20컬럼 DataFrame, 컬럼 순서는 features.schema.COLUMNS 고정
    # → 이 표를 판정 모델(B) 입력으로 사용

주의:
- engine은 read-only. 앱 기동 시 get_engine() 1회 생성해 재사용 권장(요청마다 생성 금지).
- 반환은 순수 피처표. CSV 저장·리포트는 이 함수에 없음(관심사 분리).
"""
import pandas as pd

from features.schema import COLUMNS, validate_columns
from data_adapters.db_adapter import make_engine
from run_features_db import run


def get_engine(**kwargs):
    """read-only 엔진 생성. 앱 시작 시 1회 호출해 재사용."""
    return make_engine(**kwargs)


def build_features_for_session(engine, session_id, *,
                               heatwave_date="2023-08-04", weather_hour=14):
    """
    session_id → 20컬럼 피처표(DataFrame).
    검증된 run() 파이프라인(load→환경보정→baseline→build)을 그대로 사용.
    """
    rows, _report = run(engine, session_id,
                        heatwave_date=heatwave_date, weather_hour=weather_hour)
    df = pd.DataFrame(rows, columns=COLUMNS)
    validate_columns(df)        # 20컬럼·순서 보장 (B에 깨진 표가 안 가게)
    return df


def build_features_with_report(engine, session_id, **kwargs):
    """피처표 + 진단 리포트가 둘 다 필요할 때(검증·디버깅용)."""
    rows, report = run(engine, session_id, **kwargs)
    df = pd.DataFrame(rows, columns=COLUMNS)
    validate_columns(df)
    return df, report


if __name__ == "__main__":
    # 단독 검증: 대표 세션으로 피처표가 나오는지 확인
    eng = get_engine()
    df = build_features_for_session(eng, "97d67527cd4562da24c276c5e571cfc1")
    print(f"피처표 {df.shape[0]}행 × {df.shape[1]}컬럼")
    print("컬럼:", list(df.columns))
    print(df.head(3).to_string())