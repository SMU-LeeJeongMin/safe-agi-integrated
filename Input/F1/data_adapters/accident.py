"""
사고 사전확률 어댑터 (04 현황데이터)
====================================
여름철·탈진성 사고 비율을 0~1 스칼라로 산출 → accident_prior.
"""
import os, csv


def _path():
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "data_raw", "현황데이터_필수선택_최종.csv")


def accident_prior_summer():
    """
    여름(6~8월) 사고 중 탈진/실신/온열 관련 비율을 accident_prior로 반환.
    반환: dict(summer_ratio, fatigue_ratio, prior, n_total, n_summer)
    """
    p = _path()
    with open(p, encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    n = len(rows)
    # 컬럼명 확인
    month_col = "신고월"
    cause_col = "사고원인코드명_사고종별"
    summer = [r for r in rows if _is_summer(r.get(month_col))]
    fatigue_kw = ["탈진", "실신", "온열", "고체온", "피로", "심장", "호흡"]
    fatigue = [r for r in summer
               if any(k in str(r.get(cause_col, "")) for k in fatigue_kw)]
    summer_ratio = len(summer) / n if n else 0
    fatigue_ratio = len(fatigue) / len(summer) if summer else 0
    # accident_prior: 여름 비중 + 탈진성 비중을 0~1로 클램프(합산 스케일)
    prior = round(min(summer_ratio + fatigue_ratio, 1.0), 3)
    return {"summer_ratio": round(summer_ratio, 3),
            "fatigue_ratio": round(fatigue_ratio, 3),
            "prior": prior, "n_total": n, "n_summer": len(summer),
            "n_fatigue": len(fatigue)}


def _is_summer(m):
    try:
        return int(float(m)) in (6, 7, 8)
    except (ValueError, TypeError):
        return False


if __name__ == "__main__":
    print(accident_prior_summer())
