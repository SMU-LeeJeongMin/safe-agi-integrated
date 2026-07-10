# F1 산행 안전 AI — Feature Engineering (Input → 피처표)

워치 생체 데이터·GPS·기상·산악사고 통계를 입력받아, **1분 단위 20컬럼 피처표**를 생성하는 모듈입니다.
전체 F1 파이프라인의 **01 Input → 02 Feature Engineering** 단계를 담당하며,
산출물(`fatigue_minute_features.csv`)은 이후 판정 모델·대시보드의 입력으로 사용됩니다.

## 하는 일

원천 센서 데이터는 구간 형태로, 데이터별 주기가 달라 그대로는 "현재 종합 상태"를 산출할 수 없습니다.
이 모듈은 모든 입력을 **1분 격자에 정렬**해 모델이 바로 쓸 수 있는 피처표로 가공합니다.

집계 엔진 5단계:

1. **1분 리샘플** — 심박(평균)·SpO2(최솟값)·걸음(합계)을 1분 대표값으로 집계
2. **시간 가중 보간** — 8~10분 간격 심박 사이의 빈 1분을 앞뒤 값의 시간비율로 채움 (`missing_flags` 표시)
3. **GPS 속도 실계산** — 위경도 좌표의 실제 거리로 분당 이동량(m/min) 산출
4. **과부하 5분 판정** — 심박이 위험 구간에 5분 연속 머물렀는지 판단 (`hr_overload_5min`)
5. **UTC 변환** — 한국시간(KST)을 UTC로 변환해 저장

## 프로젝트 구조

```
.
├── run_features.py          # 진입점: input → 피처표 CSV
├── data_adapters/           # 01 Input 어댑터
│   ├── common.py            # 삼성헬스 export zip 로더
│   ├── biometric.py         # 심박 / SpO2 / 피부온도 + 개인 baseline
│   ├── weather.py           # 기상 provider(Open-Meteo) + heat_index
│   ├── accident.py          # 산악사고 통계 → accident_prior
│   └── location.py          # GPS 로드
├── features/                # 02 Feature Engineering
│   ├── resample.py          # 1분 리샘플·보간·GPS속도·과부하5분·UTC
│   ├── schema.py            # 20컬럼 스키마 정의 + 검증
│   ├── build_features.py    # 피처표 생성 (build_feature_table)
│   └── hr_pattern.py        # 실측 심박 변동성 반영
├── data_raw/                # 입력 데이터 (아래 참고)
└── outputs/                 # 결과물 (fatigue_minute_features.csv)
```

## 요구 사항

- Python 3.10+
- 의존성: `pandas`

```bash
pip install pandas
```

## 데이터 준비

`data_raw/` 아래에 다음을 배치합니다.

| 경로 | 내용 |
|------|------|
| `data_raw/extracted/<사용자>/05_*/삼성헬스_export.zip` | 워치 데이터 (심박·SpO2·걸음·GPS·운동세션) |
| `data_raw/현황데이터_필수선택_최종.csv` | 산악사고 통계 (accident_prior 근거) |

기상 데이터는 실행 시 Open-Meteo API로 조회하며, 실패 시 통계 기반 값으로 대체합니다.

## 실행

```bash
python run_features.py
#  → outputs/fatigue_minute_features.csv  (116행 × 20컬럼)
```

## 출력: 피처표 20컬럼

| 분류 | 컬럼 |
|------|------|
| 식별·위치 | `uuid`, `ts`, `user_lat`, `user_lon` |
| 심박 | `hr_mean_bpm`, `hr_max_bpm`, `hr_ratio_maxhr`, `hr_overload_5min`, `hr_z_personal` |
| 산소 | `spo2_min_pct`, `spo2_grade` |
| 이동·누적 | `steps_1min`, `speed_mean_mpm`, `cumulative_min`, `rest_due_90min` |
| 환경·프로필·결측 | `heat_index`, `accident_prior`, `age_group`, `gender`, `missing_flags` |

**GIVEN** (입력에서 그대로/정적 참조): uuid, ts, 위경도, 평균 심박, 최소 SpO2, 걸음 수, 연령대, 성별, accident_prior, 결측 표시
**DERIVED** (집계 엔진 계산): 최대심박 대비 비율, 과부하 5분 여부, 개인 기준 편차, SpO2 등급, 평균 속도, 누적 시간, 90분 휴식 필요 여부, heat_index

## 참고

- 페르소나 기준값: 안정시 심박 58bpm·표준편차 13.6 (국민건강영양조사 60대 남성, n=398), 최대심박 155 (Fox 220−65).
- SpO2·연령대·성별은 60대 실측 부족으로 가상 보정, 체온은 미측정 대신 heat_index로 대체합니다.
- 산출된 피처표는 판정 모델(e1/e2)·DTO-5·대시보드 단계의 입력으로 연결됩니다.
