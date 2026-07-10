"""
F1 피로 판단 모델 v3 (규격서 정의서 정합)
==========================================
⚠️ 이 파일은 B(모델 담당) 영역. A(성현)는 feature까지.
   e1/e2 산출은 연구원 확정 공식(규격·정의서 근거). MAML 연결 시 대체하되
   입력 feature·출력범위(0~1)·representative=max 규칙은 유지.
   confidence·판정임계는 협의 후 확정 대상.

규격 F1 판정 (정의서 v0.3):
1) 심박 과부하: MaxHR×0.6~0.8, 5분 이상 지속
2) SpO2: 95↑정상 / 90~94 경고 / <90 위험
3) 누적: 90분마다 휴식 권고
결과: 정상 / 휴식 권고 / 즉시 중단

e1/e2는 연구원 확정 공식. confidence·임계는 협의 후 확정 대상.
"""
import sys, os, uuid as uuidlib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .dto5 import build_dto5, f1_alert, make_shelter, risk_level


def _clip(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


# 확정 가중치 (회의 결정, e2 복합): 생체55/이동20/누적15/환경10
W = {"bio": 0.55, "move": 0.20, "accu": 0.15, "env": 0.10}

# 확정 상수 (규격 근거 + 실측 baseline)
K_PERSONAL_STD = 8         # 개인편차 정규화 계수 (hr_z / k)
STEP_BASELINE = 90         # 기준 걸음(1분)
SPEED_BASELINE = 52        # 기준 속도(m/min)
SPO2_REF = 98              # SpO2 저하 기준 상단
SPO2_FLOOR_RANGE = 8       # 98→90에서 0→1
ACCU_REF_MIN = 120         # 누적 정규화(2시간)
HEAT_BASE = 28             # 체감 기준 하단
HEAT_RANGE = 10            # 28→38℃에서 0→1


def compute_e1_e2(f):
    """
    e1_biometric(생체 단독), e2_combined(생체+환경 복합) 산출.
    ── 연구원 확정 공식 (규격·정의서 근거, docs 참조). MAML 연결 시 이 함수 대체,
       단 입력 feature·출력범위(0~1)·representative=max 규칙은 유지. ──

    e1 = 0.5×과부하율 + 0.3×SpO2저하 + 0.2×개인편차
    e2 = 0.55×e1 + 0.20×이동저하 + 0.15×누적 + 0.10×환경
    representative = max(e1, e2)  (schemas에서 처리)
    """
    # ── 공통 정규화 (0~1) ──
    hr_overload = _clip(f["hr_ratio_maxhr"])                    # hr/MaxHR
    spo2 = f.get("spo2_min_pct")
    spo2_drop = _clip((SPO2_REF - spo2) / SPO2_FLOOR_RANGE) if spo2 is not None else 0.0
    hr_z = _clip(f["hr_z_personal"] / K_PERSONAL_STD)          # 개인편차
    step_drop = _clip((STEP_BASELINE - f["steps_1min"]) / STEP_BASELINE)
    speed_drop = _clip((SPEED_BASELINE - f["speed_mean_mpm"]) / SPEED_BASELINE)
    accu = _clip(f["cumulative_min"] / ACCU_REF_MIN)
    hi = f.get("heat_index")
    heat = _clip((hi - HEAT_BASE) / HEAT_RANGE) if hi is not None else 0.0

    # ── e1: 생체 단독 (정의서 F1 3요소: 심박·SpO2·개인baseline) ──
    e1 = _clip(0.5 * hr_overload + 0.3 * spo2_drop + 0.2 * hr_z)

    # ── e2: 생체+환경 복합 (회의 확정 가중치) ──
    move = _clip(0.5 * step_drop + 0.5 * speed_drop)
    env = _clip(0.6 * heat + 0.4 * f["accident_prior"])
    e2 = _clip(W["bio"] * e1 + W["move"] * move + W["accu"] * accu + W["env"] * env)

    return round(e1, 4), round(e2, 4)


def judge_fatigue(f):
    """
    규격 F1 룰 판정 → fatigue_state.
    정의서 v0.3 로직 준수 (5분지속·SpO2등급·90분주기).
    """
    overload = f["hr_overload_5min"]          # MaxHR×0.6~0.8 5분지속
    spo2_g = f["spo2_grade"]                    # 정상/경고/위험
    rest_due = f["rest_due_90min"]

    # 즉시 중단: SpO2 위험 or (과부하 지속 + SpO2 경고)
    if spo2_g == "위험" or (overload and spo2_g == "경고"):
        return "즉시 중단"
    # 휴식 권고: 과부하 5분지속 or SpO2 경고 or 90분 도래
    if overload or spo2_g == "경고" or rest_due:
        return "휴식 권고"
    return "정상"


def infer_f1(f, shelters=None):
    """feature dict → 규격 DTO-5 (F1)."""
    e1, e2 = compute_e1_e2(f)
    state = judge_fatigue(f)

    # 협의 후 확정 대상: 신뢰도 산출 (현 임시식)
    representative = max(e1, e2)
    conf = round(_clip(0.5 + abs(representative - 0.65) * 1.5), 4)

    # nearest_shelter: 정상 아니면 포함 (규격 주4)
    ns = None
    if state != "정상" and shelters is not None:
        from data_adapters.location import nearest_shelter, estimate_walk_min
        raw = nearest_shelter(f["user_lat"], f["user_lon"], shelters)
        if raw:
            # est_min: 등산로 GIS 실측 보행속도(45.9m/min) 기반 (직선거리 아님)
            est = estimate_walk_min(raw["distance_m"])
            ns = make_shelter(raw.get("poi_id"), raw["name"],
                              raw["lat"], raw["lon"], raw["distance_m"], est)

    # alerts: 규격 표55 (휴식권고=lvl1, 즉시중단=lvl2)
    alerts = []
    if state == "휴식 권고":
        alerts.append(f1_alert(1))
    elif state == "즉시 중단":
        alerts.append(f1_alert(2))

    return build_dto5(
        uuid=f["uuid"], ts=f["ts"],
        e1_biometric=e1, e2_combined=e2,
        fatigue_state=state, fatigue_confidence=conf,
        nearest_shelter=ns,
        alerts=alerts,
    )


if __name__ == "__main__":
    from features.build_features import build_feature_table
    from data_adapters.location import load_shelters
    rows, _ = build_feature_table()
    shelters = load_shelters()
    print("=== F1 추론 v3 (규격 판정) ===")
    for r in [rows[3], rows[17], rows[-4], rows[-1]]:
        d = infer_f1(r, shelters)
        print(f"누적{r['cumulative_min']:>3}분 심박{r['hr_mean_bpm']:.0f} "
              f"과부하={r['hr_overload_5min']} SpO2등급={r['spo2_grade']} "
              f"→ {d['fatigue']['state']} (risk {d['risk']['representative']:.2f} {d['risk']['label']})")
        if d["alerts"]:
            print(f"       alert: [{d['alerts'][0]['title']}]")
        if d["fatigue"]["nearest_shelter"]:
            s = d["fatigue"]["nearest_shelter"]
            print(f"       쉼터: {s['name']} {s['distance_m']}m (도달 {s['est_min']}분)")
