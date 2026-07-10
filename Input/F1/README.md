# F1 Input Pipeline

이 폴더는 F1 시나리오의 원천 입력을 1분 단위 feature 및 DTO-5 시퀀스로 변환하는 Input 파트입니다.
모델 코드는 루트 `Model/` 폴더를 공통으로 사용합니다.

# 산행 AI — F1(피로/휴식권고) 파이프라인 (수정본 전체)

처음에 주신 코드 전체를 실제 임포트 구조에 맞춰 패키지로 재구성한 묶음입니다.
전체 파이썬 모듈은 임포트 검증을 통과합니다(아래 "검증" 참고).

## 폴더 구조
```
.
├── data_adapters/          # 원천 데이터 어댑터 (구 phase5)
│   ├── common.py           # 삼성헬스 zip 로더 (get_zip, load_csv, col_index, parse_dt)
│   ├── biometric.py        # 심박/SpO2/피부온도  [수정]
│   ├── location.py         # GPS/쉼터/최근접 계산 [수정]
│   ├── weather.py          # 기상 provider/heat_index [수정]
│   └── accident.py         # accident_prior 산출 [수정]
├── features/               # 피처 엔지니어링 (구 phase6 + phase7)
│   ├── resample.py         # 1분 리샘플/보간/GPS속도/과부하판정 (구 phase6.py) [수정]
│   ├── schema.py           # 컬럼 스키마/spo2_grade (구 phase7) [수정]
│   ├── build_features.py   # 분단위 피처 테이블 생성 (구 phase7) [수정]
│   └── hr_pattern.py       # 심박 노이즈/변동성 (구 phase7)
├── ├── export.py               # 전체 러너 (피처표→모델→DTO-5→쉼터). 구 phase8; ROOT 경로 1단계 조정
├── run_features.py          # 피처표까지만 만드는 러너 (input→피처표). export.py의 앞부분과 동일 로직
├── research/               # 독립 실증 스크립트 (구 phase3)
├── data_raw/               # ⚠️ 원천 데이터 (미포함 — 아래 참고)
└── (참고) fatigue_minute_features.csv / dto5_sequence.json / validation_report.json  ← 수정 前 기존 출력
```

## 실행에 필요한 원천 데이터 (⚠️ 이 zip에 없음)
코드가 `data_raw/`에서 아래를 읽습니다:
1. **삼성헬스 export zip** — common.py::_find_zip() 이 `data_raw/extracted/<폴더>/05_*/` 안의 `*1988*.zip` 을 자동 탐색.
2. **산악사고 현황 CSV** — accident.py 가 `data_raw/현황데이터_필수선택_최종.csv` 를 읽음.
3. 쉼터 shapefile 등(location.py) — 사용 시 필요.

## 실행 방법
```bash
python export.py                 # 피처→F1추론→dto5_sequence.json/*.csv/validation_report.json
python -m features.build_features
# 모델/DTO-5 코드는 루트 Model/ 폴더를 사용합니다.
```

## 이번에 고친 것
값 관련 확정(실측 검증):
- accident.py — accident_prior 합산(덧셈), 실측 CSV로 0.31 확인.
- features/resample.py — 과부하 "0.6 이상" 유지(밴드 아님), 이상구간 휴식권고 정상 발동.

크래시 방어(출력 불변): location 정렬 None, biometric/weather 컬럼누락, biometric 빈데이터, export 빈세그먼트 NaN, dto5 alerts None 제거.
안전 표기(출력 불변): schema spo2 None→"미측정", build_features HR 0.0 결측오인 수정.
수정 없음: common, hr_pattern, f1_model, research/*.

## 검증
- 14개 모듈 py_compile 통과.
- 루트에서 12개 모듈 import 성공(순환참조/경로 문제 없음).
- **실측 재실행 완료 (POI 포함, 전체 파이프라인)**: 느어아웅 zip + 현황 CSV + 청계산 POI(poi_1961)로
  `python export.py` 전체 실행 → `outputs/` 재생성.
  결과: 116행×20컬럼, 상태분포 정상44/휴식72, alert 72, F1 검증(이상구간 휴식권고) 통과,
  nearest_shelter 채워짐(name="쉼터", 337m, 7분, 72건) = 원본 출력과 완전 일치.
- 청계산 POI shapefile(poi_1961.shp/.shx/.dbf/.cpg/.prj)은 data_raw/ 에 포함됨.
