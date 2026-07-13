# SAFE 산행안전 AI Dashboard

산행 중 위험 상황을 감지하는 S·A·F·E 시나리오(총 9종 예정)의 모델 결과를 검증하고 시연하기 위한 Streamlit 대시보드.
Input(A)과 Model(B)이 만든 외부 산출물을 읽어 화면에 표시하는 역할만 담당하며, Dashboard 내부에서 데이터를 만들어내지 않음.

- 공통 작업 레포: https://github.com/SMU-LeeJeongMin/safe-agi-integrated

## 실행
레포 루트에서 실행.

```bash
pip install -r Dashboard/requirements.txt
streamlit run Dashboard/main.py
```

`streamlit>=1.37`이 필요. (실시간 모니터링의 부분 갱신 기능이 `st.fragment`를 사용)

## 화면 흐름
Intro ──> 시나리오 선택 ──┬──> F1 대시보드 ([1]~[7] 패널)
                          ├──> A1 대시보드 ([1]~[7] 패널, F1과 동일 틀)
                          └──> 실시간 모니터링 (BETA)

- 각 시나리오 대시보드는 [1] DTO-1 Input → [2] Feature Engineering → [3] Model Explanation → [4] What-If → [5] MAML 개인화 → [6] DTO-5 Output → [7] InferenceResult 저장의 7개 패널로 구성.
- 페이지 이동은 `st.session_state["page"]`와 URL 쿼리(`?page=intro|scenario|dashboard|monitor`)로 처리.

## 폴더 구조
Dashboard/
├── main.py                        # 화면 흐름(intro/scenario/dashboard/monitor) + 선택 시나리오 라우팅
├── components/                    # 공용 디자인 골격만 존재 (시나리오 내용 없음)
│   ├── layout.py                  # 전역 CSS / Intro / Scenario Select / GitHub 링크 헬퍼
│   ├── panel_kit.py               # 패널 공용 골격: 패널 헤더, 지표/step/입력/feature/결과/페르소나 카드,
│   │                              #   DTO-5 카드, 기여도 분해, 학습 가중치 근거, 알림/지도/JSON/차트 스타일,
│   │                              #   시나리오 헤더, 저장 결과 — [1]~[7] 전 패널의 골격
│   └── sidebar.py                 # 시점 선택 + 패널·시나리오 내비 + 하단 Links 섹션
├── core/
│   ├── registry.py                # 시나리오별 renderer와 외부 파일 후보 경로 (explanation.json 포함)
│   ├── source_loader.py           # 선택 시나리오 파일만 로드 (mtime 캐시, 9종 대비 상한 18)
│   ├── router.py                  # 선택 시나리오 page.py만 lazy import
│   └── contracts.py               # ScenarioPayload 등 Dashboard 내부 계약
├── scenarios/
│   ├── common.py                  # 뒤로가기, 연결 대기 카드 등 페이지 공통 조각
│   ├── f1/                        # F1 내용: 골격에 넣을 값과 문구, F1 고유 위젯
│   │   ├── page.py                # [1]~[7] 패널 조립
│   │   ├── title_panel.py         # 시나리오 헤더 골격에 F1 문구만 선언
│   │   ├── dto1_input_panel.py    # [1] 입력 카드 골격에 F1 필드만 선언
│   │   ├── feature_engineering_panel.py  # [2]
│   │   ├── model_explanation_panel.py    # [3] F1 계산 단계와 기여도 값
│   │   ├── whatif_panel.py        # [4] F1 슬라이더와 모델 재계산
│   │   ├── personalization_panel.py      # [5]
│   │   ├── dto5_panel.py          # [6] DTO-5 카드 골격에 F1 필드만 선언
│   │   └── inferenceresult_panel.py      # [7] 저장 레코드 정의
│   └── a1/                        # A1 내용: F1과 같은 파일 구성
│       ├── page.py                # [1]~[7] 패널 조립
│       ├── mapper.py              # 외부 필드 → 화면 값 연결만 수행
│       ├── formatting.py          # A1 표기용 포맷 함수
│       ├── a1_map.py              # 현재 위치와 위험 POI 지도 (공용 지도 골격 호출)
│       ├── title_panel.py         # 시나리오 헤더 골격에 A1 문구만 선언
│       ├── dto1_input_panel.py    # [1]
│       ├── feature_engineering_panel.py  # [2]
│       ├── model_explanation_panel.py    # [3]
│       ├── whatif_panel.py        # [4]
│       ├── personalization_panel.py      # [5]
│       ├── dto5_panel.py          # [6]
│       └── inferenceresult_panel.py      # [7]
├── monitor/
│   └── page.py                    # 실시간 모니터링 (BETA): 관찰 대상 선택, 스트림 재생, 이벤트 주입
│                                  #   수신 소스만 CSV 리플레이 → DB 폴링 → REST API 순으로 교체 예정
├── assets/                        # 로고, 인트로 배경, GitHub 아이콘
├── utils/
│   ├── explanation.py             # 규칙 기반 중요도, 판단 근거 문장, 위험 임계값 상수 (실시간 XAI 미사용)
│   └── time_utils.py              # UTC 저장값의 KST 표기 변환
├── requirements.txt
└── README.md


## 데이터 원칙
- 선택한 시나리오의 외부 산출물만 읽음. 후보 경로와 환경변수는 `core/registry.py`에 정의.
  - Feature: `Input/<ID>/outputs/…csv` (환경변수 `SAFE_DASHBOARD_<ID>_FEATURES`)
  - DTO-5: `Model/<ID>/outputs/…json` 등 (환경변수 `SAFE_DASHBOARD_<ID>_DTO5`)
  - 가중치 설명: `Model/<ID>/outputs/explanation.json` (환경변수 `SAFE_DASHBOARD_<ID>_EXPLANATION`, 선택)
- 파일이 아직 없으면 임의 숫자를 만들지 않고 "데이터 연결 대기" 카드를 표시.

## [3] Model Explanation 구성
패널 흐름: 요약 지표 3개 → Risk_label 등급과 판단 근거(게이지 + 한 줄 요약) → (버튼) 모델 계산 단계 + 기여도 분해 + 학습 가중치 근거. "결과는 위, 계산 과정과 근거 상세는 버튼 안" 구성.

- 판단 근거 문장: `utils/explanation.py`가 규칙 기반으로 생성. 실시간 SHAP/LIME 결합은 시스템 부하 문제로 생략.
- 기여도 분해: e1과 e2는 가중합(가중치 × 항목 점수의 합) 구조이므로 각 항의 곱이 수학적으로 정확한 기여도. 화면 계산만으로 분해하므로 성능 부담이 없음.
- 학습 가중치 근거: 추후 딥러닝으로 가중치를 학습하면, 학습 파이프라인이 1회 export하는 `explanation.json`을 읽어 "왜 이 계수가 나왔는지"를 표시. 무거운 계산은 학습 단계에서 끝내고 대시보드는 파일만 읽음.

기대 스키마:
  ```json
  {
    "trained_at": "2026-07-20T09:00:00+09:00",
    "method": "MAML fine-tuning",
    "summary": "고온 구간 데이터 비중 증가로 env 가중치가 상승",
    "weights": [
      {"name": "생체 (e1)", "weight": 0.52, "prev": 0.55, "reason": "..."}
    ]
  }
  ```

## 실시간 모니터링 (BETA)
특정 관찰 대상(세션/사용자)을 골라 워치 유입값을 분 단위 스트림으로 관찰하고, 이벤트 주입(심박 급상승, SpO2 저하, 이동 정지)으로 모델의 위험 반응을 확인하는 페이지.

모니터링 페이지는 3계층으로 분리되어 있고, 실데이터 전환 시 맨 아래 한 계층만 바뀜.

```text
화면 계층 (유지)        상태 카드, 추이 차트, 알림 로그, 이벤트 주입
갱신 루프 (유지)        st.fragment 폴링, N초마다 최신 시점 요청
데이터 소스 (교체)      1. CSV 리플레이(현재) → 2. safe_db 폴링 → 3. REST API
```

지금은 저장된 CSV를 실시간처럼 흘려보내는 리플레이 방식. 실제 스트림이 없을 때 파이프라인과 화면을 먼저 검증하는 표준적인 개발 방식. 어느 단계로 바뀌어도 화면과 갱신 루프 코드는 그대로이고, `monitor/page.py`에서 "다음 시점 행을 꺼내는" 부분만 "최신 행을 가져오는" 함수로 교체. 이벤트 주입은 F1 확정 공식(`compute_e1_e2`, `judge_fatigue`)을 그대로 호출해 재계산.

## 성능 원칙 (시나리오 9종 확장 대비)
- Intro와 시나리오 선택 화면에서는 패널을 미리 import하지 않음. 시나리오를 선택하면 그 시나리오의 page 모듈과 파일만 로드(`core/router.py`, `core/source_loader.py`).
- 파일 캐시는 mtime 기반이며 `max_entries=18`로 9종 × 소스 2~3개를 감당.
- 실시간 모니터링은 `st.fragment(run_every=…)`로 갱신 영역만 부분 rerun하므로 다른 페이지 성능에 영향이 없음. 차트는 최근 표시 구간만 잘라 그림.
- 새 시나리오 추가 방법: `scenarios/<id>/` 폴더 생성 후 `core/registry.py`에 `ScenarioDefinition`과 파일 후보 경로를 등록.

## 링크
- 사이드바 최하단 Links 섹션과 인트로 footer에 GitHub 링크(SAFE AI Project)가 있음. URL은 `components/layout.py`의 `GITHUB_REPO_URL` 한 곳에서 관리.
