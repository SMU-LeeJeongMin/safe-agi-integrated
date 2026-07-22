# -*- coding: utf-8 -*-
"""
identity_origin.py — 비식별 ID + 컬럼별 label_origin 매핑 (Phase 2)
====================================================================
두 개의 독립된 축을 다룬다.

[축 1] 비식별 ID — "누구인가"
  - person_id : 동일 인물 = 동일 ID (재추적 가능). 실명·생년월일 등 식별정보
    없이 페르소나 특성 해시로 생성.
  - session_id: 세션마다 고유 (person_id + 상황/반복 조합).
  - 한 세션 = 한 사람 (person_id 하나). 한 사람은 여러 세션을 가질 수 있다
    (같은 사람의 정상/주의/경고/위험 세션 = 같은 person_id, 다른 session_id).

[축 2] label_origin — "각 값이 어디서 왔나" (컬럼별)
  - 사람(person_id)과 무관한 별개 축. 한 세션 안에서도 컬럼마다 출처가 다르다.
  - 실측이 쌓여도 외부 데이터(국건영·PAMAP2·Non-EEG)가 정박점으로 남으므로,
    세션 단위 단일 표기가 아니라 컬럼별 매핑이 필요하다.

origin 5분류:
  - MEASURED          : 실측 상수 (실제 기상·사고통계)
  - EXTERNAL_ANCHORED : 외부 실측 데이터 정박 합성 (국건영·Non-EEG·PAMAP2 근거)
  - SCENARIO_VIRTUAL  : 순수 합성/시나리오값 (근거 없는 시나리오 주입분)
  - PROJECT_DERIVED   : 규칙 오라클 파생 정답 (y)
  - STRUCTURAL        : 구조·식별자·시간 인덱스
"""
import hashlib


# ── 축 2: 컬럼별 label_origin 매핑 ──────────────────────────
COLUMN_ORIGIN = {
    # 실측 상수
    "heat_index": "MEASURED",
    "accident_prior": "MEASURED",
    # 외부 데이터 정박 합성
    "hr_mean_bpm": "EXTERNAL_ANCHORED",       # 국건영 절대값+변동, PAMAP2 범위
    "hr_ratio_maxhr": "EXTERNAL_ANCHORED",    # 국건영 MaxHR(Fox)
    "hr_z_personal": "EXTERNAL_ANCHORED",     # 국건영 rest_hr/std
    "spo2_min_pct": "EXTERNAL_ANCHORED",      # Non-EEG 정상분포
    # 순수 합성/시나리오
    "steps_1min": "SCENARIO_VIRTUAL",
    "speed_mean_mpm": "SCENARIO_VIRTUAL",
    # 규칙 파생 정답
    "y_e1": "PROJECT_DERIVED",
    "y_e2": "PROJECT_DERIVED",
    "y_risk_level": "PROJECT_DERIVED",
    "y_fatigue_state": "PROJECT_DERIVED",
    # 구조·식별자
    "cumulative_min": "STRUCTURAL",
    "minute_idx": "STRUCTURAL",
    "person_id": "STRUCTURAL",
    "session_id": "STRUCTURAL",
    "situation": "STRUCTURAL",
    "acute_anomaly_flag": "STRUCTURAL",
}


def origin_of(column):
    """컬럼명 → label_origin. 미등록 컬럼은 UNKNOWN."""
    return COLUMN_ORIGIN.get(column, "UNKNOWN")


def origin_manifest():
    """origin별 컬럼 목록 (검증·발표용 역인덱스)."""
    inv = {}
    for col, org in COLUMN_ORIGIN.items():
        inv.setdefault(org, []).append(col)
    return inv


# ── 축 1: 비식별 ID ─────────────────────────────────────────
def make_person_id(persona):
    """
    동일 인물 = 동일 ID. 페르소나 특성(연령대·성별·안정심박·체력·BMI)의
    해시로 생성 — 실명·생년월일 등 식별정보 미사용(비식별).

    같은 특성의 페르소나는 같은 person_id 를 갖는다(재현·재추적 가능).
    persona 는 PersonaMeta 또는 name/age/rest_hr/fitness 속성 보유 객체.
    """
    parts = [
        getattr(persona, "age_band", str(getattr(persona, "age", ""))),
        getattr(persona, "gender", ""),
        f"{getattr(persona, 'rest_hr', 0):.1f}",
        f"{getattr(persona, 'fitness', 0):.3f}",
        f"{getattr(persona, 'bmi', 0):.1f}",
    ]
    key = "|".join(str(p) for p in parts)
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()[:8]
    return f"P-{h}"


def make_session_id(person_id, situation, rep=0):
    """
    세션 고유 ID = person_id + 상황 + 반복번호.
    같은 사람의 다른 상황/반복 세션을 구분하되, person_id 로 묶어 재추적 가능.
    """
    return f"{person_id}-{situation}-{rep:02d}"


if __name__ == "__main__":
    # 비식별 ID: 같은 특성이면 같은 person_id
    class P:
        age_band = "60s"; gender = "M"; rest_hr = 58.0
        fitness = 0.95; bmi = 24.4; age = 65; name = "kn001"
    p = P()
    pid = make_person_id(p)
    print("person_id:", pid)
    print("정상 세션:", make_session_id(pid, "정상"))
    print("위험 세션:", make_session_id(pid, "위험"))
    print("→ 같은 person_id 로 묶여 동일 인물 재추적 가능")
    print()
    # 재현성: 같은 특성 → 같은 ID
    print("재현성 확인:", make_person_id(P()) == pid)
    print()
    # origin 매니페스트
    print("=== label_origin 매니페스트 ===")
    for org, cols in origin_manifest().items():
        print(f"  {org}: {len(cols)}개")
