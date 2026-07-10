"""
input → 피처표 러너
====================
원천 입력(삼성헬스 zip·현황 CSV·기상)을 1분 단위 20컬럼 피처표로 변환해 저장.
(발표자료 01 Input → 02 Feature Engineering 단계. 모델/DTO-5 이후는 미포함.)
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd
from features.schema import COLUMNS, validate_columns
from features.build_features import build_feature_table

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "outputs")
os.makedirs(OUT, exist_ok=True)


def main():
    rows, meta = build_feature_table()
    df = pd.DataFrame(rows, columns=COLUMNS)
    validate_columns(df)                       # 20컬럼 스키마 검증
    path = os.path.join(OUT, "fatigue_minute_features.csv")
    df.to_csv(path, index=False)
    print(f"피처표 생성 완료: {len(df)}행 × {len(df.columns)}컬럼")
    print(f"저장: {path}")
    return path


if __name__ == "__main__":
    main()
