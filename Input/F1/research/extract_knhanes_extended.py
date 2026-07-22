"""
국민건강영양조사(KNHANES) 원자료 → 연령대×성별 확장 baseline 추출
=====================================================================
기존 extract_baseline_knhanes.py 의 골격을 그대로 따르되(같은 연령대 구간,
같은 성별 매핑, 같은 비가중 산술평균 방식), 변수를 확장한다.
- 안정심박 추출과 가중치 방식을 통일하기 위해 복합표본 가중치는 적용하지 않음
  (기존 groupby().mean() 과 동일한 비가중 방식).

입력: HN20~HN24 *_all.sav (SPSS 원시자료)
출력 (Phase 1 분포표 규격, 앞서 확정):
  - dist_summary_knhanes.csv   요약표 (변수×조건 한 행)
  - dist_samples_knhanes.csv   샘플 보존 (부트스트랩·커널밀도용, 조건당 최대 N행)

확장 변수 (0715 전체 범위):
  [연속] 수축기혈압 HE_sbp, 이완기혈압 HE_dbp, BMI HE_BMI, 허리둘레 HE_wc,
         신장 HE_ht, 체중 HE_wt, (참고) 안정심박 HE_mPLS
  [범주-유병률] 고혈압 HE_HP, 당뇨 HE_DM, 이상지질 HE_HCHOL/HE_TG,
         (질환 코드는 코드북 대조 후 확정)
  [활동-설문] 걷기·중강도·고강도·좌식·수면 (변수명 코드북 확정 필요)

주의:
  * 실제 컬럼명·결측코드·질환 있음/없음 코드는 연도별 코드북과 대조 후 확정할 것.
    아래 CONT_VARS / DISEASE_VARS / ACT_VARS 의 변수명과 유효범위는 국건영 표준
    변수명 기준의 초안이며, --probe 로 먼저 실제 존재 여부를 확인하도록 되어 있음.
  * 질환·이상지질 등은 검진·문진 혼재. 값 의미를 코드북에서 반드시 확인.

사용:
  # 1) 먼저 어떤 변수가 실제로 존재하는지 확인 (컬럼명 대조용)
  python extract_knhanes_extended.py <sav디렉토리> --probe

  # 2) 실제 추출
  python extract_knhanes_extended.py <sav디렉토리>
"""
import sys, os
import warnings

warnings.filterwarnings("ignore")

try:
    import pyreadstat
    import pandas as pd
except ImportError:
    print("필요 패키지: pip install pyreadstat pandas")
    raise

# ── 기존 스크립트와 동일 ──────────────────────────────────────────
FILES = {
    "2020": "HN20_all.sav", "2021": "HN21_all.sav", "2022": "HN22_all.sav",
    "2023": "HN23_all.sav", "2024": "HN24_ALL.sav",
}


def age_band(a):
    if a < 20:
        return "10s"
    if a >= 80:
        return "80s"
    return f"{int(a // 10 * 10)}s"


# ── 확장 변수 정의 ────────────────────────────────────────────────
# 연속 변수: (변수명, 단위, 유효최소, 유효최대)  — 유효범위 밖은 결측 처리
CONT_VARS = [
    ("HE_mPLS", "bpm",    30, 200),  # 안정심박 (기존과 동일, 재현·검증용)
    ("HE_sbp",  "mmHg",   60, 250),  # 수축기 혈압
    ("HE_dbp",  "mmHg",   30, 150),  # 이완기 혈압
    ("HE_BMI",  "kg/m2",  10,  60),  # 체질량지수
    ("HE_wc",   "cm",     40, 200),  # 허리둘레
    ("HE_ht",   "cm",    100, 220),  # 신장
    ("HE_wt",   "kg",     20, 200),  # 체중
    ("HE_TG",   "mg/dL",  10, 2000), # 중성지방(실측 수치) — probe에서 연속값 확인
]

# 질환(범주) 변수 — 이용지침서(제9기)로 코딩 확정.
# "유병=있음" 으로 볼 코드는 연도에 따라 다를 수 있어 (변수, {연도: [있음코드]}) 형태.
# 기본(default)은 연도 명시가 없을 때 적용.
#
# HE_HP(고혈압 유병여부):
#   2020~2021 → 3범주: 1정상 / 2고혈압전단계 / 3고혈압      → 있음 = [3]
#   2022~2024 → 4범주: 1정상 / 2주의혈압 / 3고혈압전단계 / 4고혈압 → 있음 = [4]
#   ※ "유병(고혈압)"은 최고 범주(실제 고혈압)만. 전단계는 유병에서 제외해 통일.
# HE_DM_HbA1c(당뇨 유병여부, 당화혈색소 반영): 1정상 / 2전단계 / 3당뇨 → 있음 = [3]
# HE_HCHOL(고콜레스테롤혈증): 0없음 / 1있음 → 있음 = [1]  (probe 확인)
DISEASE_VARS = [
    ("HE_HP", {"2020": [3], "2021": [3],
               "2022": [4], "2023": [4], "2024": [4],
               "default": [4]}),
    ("HE_DM_HbA1c", {"default": [3]}),  # 당뇨 유병(당화혈색소 반영): 1정상/2전단계/3당뇨 → 있음=[3]
    ("HE_HCHOL", {"default": [1]}),
]

# 활동(설문) 변수 — probe에서 존재 확인된 것만. 대부분 범주(실천여부/일수).
# 값 의미는 유병률과 달리 "분포"로 보기 애매하므로, 여기서는 존재하는 것만
# 범주별 빈도(비율)로 남기고, 필요시 코드북 대조 후 확장.
ACT_VARS = [
    "pa_aerobic",  # 유산소 신체활동 실천 (probe: 전 연도 존재)
    "BE3_31",      # 걷기 관련 (probe: 전 연도 존재, 연도별 의미 확인 필요)
]

MAX_SAMPLES_PER_CELL = 5000  # 조건당 샘플 보존 상한


def _find(base_dir, fname):
    for root, _, files in os.walk(base_dir):
        for f in files:
            if f.lower() == fname.lower():
                return os.path.join(root, f)
    return None


def load_all(base_dir, wanted_cols):
    """존재하는 컬럼만 골라 연도별로 읽어 합친다."""
    frames = []
    for yr, fname in FILES.items():
        path = _find(base_dir, fname)
        if not path:
            print(f"[skip] {fname} 없음")
            continue
        # 먼저 메타에서 이 파일이 가진 컬럼 확인
        _, meta = pyreadstat.read_sav(path, metadataonly=True)
        have = [c for c in wanted_cols if c in meta.column_names]
        missing = [c for c in wanted_cols if c not in meta.column_names]
        if missing:
            print(f"[{yr}] 없는 변수: {missing}")
        df, _ = pyreadstat.read_sav(path, usecols=have)
        df["_year"] = yr
        frames.append(df)
    if not frames:
        raise SystemExit("sav 파일을 찾지 못했습니다.")
    return pd.concat(frames, ignore_index=True)


def probe(base_dir):
    """실제 컬럼 존재 여부·고유값을 찍어 코드북 대조를 돕는다."""
    all_wanted = ["age", "sex"] + [v[0] for v in CONT_VARS] \
        + [v[0] for v in DISEASE_VARS] + ACT_VARS
    for yr, fname in FILES.items():
        path = _find(base_dir, fname)
        if not path:
            print(f"[skip] {fname} 없음")
            continue
        _, meta = pyreadstat.read_sav(path, metadataonly=True)
        cols = set(meta.column_names)
        print(f"\n=== {yr} ({fname}) : 전체 {len(cols)}개 컬럼 ===")
        for c in all_wanted:
            print(f"  {c:12s} {'OK' if c in cols else '없음'}")
        # 질환 변수 고유값 확인 (있음/없음 코드 파악)
        dis_have = [v[0] for v in DISEASE_VARS if v[0] in cols]
        if dis_have:
            df, _ = pyreadstat.read_sav(path, usecols=dis_have)
            for c in dis_have:
                vc = df[c].value_counts(dropna=False).head(10)
                print(f"  [{c}] 고유값: {dict(vc)}")


def main(base_dir):
    wanted = ["age", "sex"] + [v[0] for v in CONT_VARS] \
        + [v[0] for v in DISEASE_VARS] + [c for c in ACT_VARS]
    d = load_all(base_dir, wanted)

    # 공통 전처리 (기존과 동일)
    d = d.dropna(subset=["age", "sex"])
    d["age_band"] = d["age"].apply(age_band)
    d["gender"] = d["sex"].map({1.0: "M", 2.0: "F"})
    d = d.dropna(subset=["gender"])

    summary_rows = []
    sample_rows = []

    # ── 연속 변수: 연령대×성별 분포 요약 + 샘플 보존 ──
    present_cont = [v for v in CONT_VARS if v[0] in d.columns]
    for var, unit, lo, hi in present_cont:
        sub = d[["age_band", "gender", var]].copy()
        sub[var] = pd.to_numeric(sub[var], errors="coerce")
        sub = sub[(sub[var] >= lo) & (sub[var] <= hi)].dropna(subset=[var])
        for (ab, g), grp in sub.groupby(["age_band", "gender"]):
            v = grp[var]
            summary_rows.append({
                "dataset": "KNHANES", "variable": var,
                "condition_key": "age_band|gender",
                "condition_value": f"{ab}|{g}",
                "n": len(v),
                "mean": round(v.mean(), 2), "std": round(v.std(), 2),
                "min": round(v.min(), 2),
                "p05": round(v.quantile(.05), 2), "p25": round(v.quantile(.25), 2),
                "p50": round(v.quantile(.50), 2), "p75": round(v.quantile(.75), 2),
                "p95": round(v.quantile(.95), 2),
                "max": round(v.max(), 2),
                "missing_rate": None,
                "unit": unit, "layer": "SURVEY",
                "license": "KNHANES(공식공개)",
            })
            # 샘플 보존 (조건당 상한)
            keep = v.sample(min(len(v), MAX_SAMPLES_PER_CELL), random_state=42)
            for x in keep:
                sample_rows.append({
                    "dataset": "KNHANES", "variable": var,
                    "condition_key": "age_band|gender",
                    "condition_value": f"{ab}|{g}", "value": x,
                })

    # ── 질환 변수: 연령대×성별 유병률 (연도별 코드 차이 반영) ──
    present_dis = [v for v in DISEASE_VARS if v[0] in d.columns]
    for var, code_map in present_dis:
        sub = d[["age_band", "gender", "_year", var]].dropna(subset=[var])
        # 각 행을 그 행의 연도에 해당하는 '있음 코드'로 판정
        def _is_pos(row):
            codes = code_map.get(str(row["_year"]), code_map.get("default", []))
            return row[var] in codes
        sub = sub.copy()
        sub["_pos"] = sub.apply(_is_pos, axis=1)
        for (ab, g), grp in sub.groupby(["age_band", "gender"]):
            n = len(grp)
            pos = int(grp["_pos"].sum())
            summary_rows.append({
                "dataset": "KNHANES", "variable": var,
                "condition_key": "age_band|gender",
                "condition_value": f"{ab}|{g}",
                "n": n,
                "mean": round(pos / n, 4) if n else None,  # 유병률
                "std": None, "min": None, "p05": None, "p25": None,
                "p50": None, "p75": None, "p95": None, "max": None,
                "missing_rate": None,
                "unit": "prevalence", "layer": "SURVEY",
                "license": "KNHANES(공식공개)",
            })

    # ── 저장 ──
    summ = pd.DataFrame(summary_rows)
    samp = pd.DataFrame(sample_rows)
    out_summ = os.path.join(base_dir, "dist_summary_knhanes.csv")
    out_samp = os.path.join(base_dir, "dist_samples_knhanes.csv")
    summ.to_csv(out_summ, index=False, encoding="utf-8-sig")
    samp.to_csv(out_samp, index=False, encoding="utf-8-sig")

    print(f"\n요약표 저장: {out_summ}  ({len(summ)}행)")
    print(f"샘플 저장 : {out_samp}  ({len(samp)}행)")
    print("\n[연속변수 미리보기]")
    print(summ[summ.unit != "prevalence"].head(20).to_string(index=False))
    if (summ.unit == "prevalence").any():
        print("\n[유병률 미리보기]")
        print(summ[summ.unit == "prevalence"].head(20).to_string(index=False))

    # 안정심박 재현 검증 (기존 값과 비교)
    if "HE_mPLS" in d.columns:
        chk = summ[(summ.variable == "HE_mPLS") &
                   (summ.condition_value == "60s|M")]
        if len(chk):
            print(f"\n[검증] 60s|M 안정심박 mean={chk.iloc[0]['mean']} "
                  f"(기존 baseline_hr_reference.csv: 58.4, n=396)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용: python extract_knhanes_extended.py <sav디렉토리> [--probe]")
        sys.exit(1)
    base = sys.argv[1]
    if "--probe" in sys.argv:
        probe(base)
    else:
        main(base)
