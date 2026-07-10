# 산행안전 AI 통합 레포
`Input → Model → Dashboard` 흐름을 한 레포에 정리한 통합본

## 폴더 구조
safe-agi-hiking/
├── Input/                 # 원천 데이터 → feature/DTO-5 산출물
│   ├── F1/                # F1 시나리오 입력/feature 파이프라인
│   │   ├── data_adapters/
│   │   ├── features/
│   │   ├── data_raw/
│   │   ├── outputs/       # dashboard가 읽는 CSV/JSON 위치
│   │   ├── run_features.py
│   │   └── export.py
│   ├── A1/                # 추후 추가 시나리오 → 폴더만 미리 생성
│   ├── A2/
│   ├── A5/
│   ├── F2/
│   ├── F3/
│   ├── F4/
│   ├── E1/
│   └── E2/
├── Model/                 # 모델, DTO-5 builder, MAML 개인화
│   ├── f1_model.py
│   ├── dto5.py
│   └── personal_baseline.py
├── Dashboard/             # Streamlit 대시보드
│   ├── main.py
│   ├── components/
│   ├── utils/
│   ├── assets/
│   └── outputs/           # InferenceResult 저장용 로컬 출력
├── requirements.txt
└── README.md

## 실행 방법
공통 requirements에는 Streamlit 대시보드 실행 패키지와 F1 Input 파이프라인 실행에 필요한 `pyshp`가 포함

## 협업 방식 제안
1. `main` 브랜치는 항상 실행 가능한 상태로 유지
2. 각자 작업 브랜치를 나누기
3. 작업 후 Pull Request로 합치기
4. `feat/integration`에서 `Input → Model → Dashboard` 전체 흐름을 먼저 확인한 뒤 `main`에 병합

## 주의 사항
1. Dashboard는 `Input/F1/outputs/`의 산출물을 읽음
2. AI 모델 코드는 `Dashboard/model/`이 아니라 루트의 `Model/`에 둠
3. 향후 다른 시나리오는 `Input/A1`, `Input/A2`처럼 시나리오별 폴더를 추가하고, 대시보드에서 해당 outputs 경로를 연결하는 방식으로 확장
