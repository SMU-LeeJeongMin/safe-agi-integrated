"""
삼성헬스 CSV 공용 로더
======================
삼성헬스 export 3층 구조 처리: L0=메타, L1=헤더, L2~=데이터.
zip 내부에서 직접 읽으며, 파일명 부분매치로 소스를 찾는다.
"""
import os, zipfile, csv
from datetime import datetime

# 느어아웅 zip 경로 자동 탐색
def _find_zip():
    base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "data_raw", "extracted")
    top = os.path.join(base, os.listdir(base)[0])
    p05 = os.path.join(top, [d for d in os.listdir(top) if d.startswith("05_")][0])
    return os.path.join(p05, [f for f in os.listdir(p05)
                              if "1988" in f and f.endswith(".zip")][0])

_ZIP_PATH = None
def get_zip():
    global _ZIP_PATH
    if _ZIP_PATH is None:
        _ZIP_PATH = _find_zip()
    return zipfile.ZipFile(_ZIP_PATH)


def find_csv(z, key):
    """파일명 부분매치로 CSV 경로 반환."""
    for n in z.namelist():
        if "__MACOSX" in n:
            continue
        if key in os.path.basename(n) and n.endswith(".csv"):
            return n
    return None


def load_csv(z, key):
    """(header, rows) 반환. L1=헤더, L2~=데이터."""
    path = find_csv(z, key)
    if not path:
        raise FileNotFoundError(f"소스 없음: {key}")
    raw = z.open(path).read().decode("utf-8-sig", errors="replace").splitlines()
    header = raw[1].split(",")
    rows = list(csv.reader(raw[2:]))
    return header, rows


def col_index(header, *candidates):
    """정확매치 우선, 없으면 부분매치로 컬럼 인덱스 반환."""
    idx = {h: i for i, h in enumerate(header)}
    for c in candidates:
        for h in header:
            if h.strip() == c:
                return idx[h]
    for c in candidates:
        for h in header:
            if c in h:
                return idx[h]
    return None


def parse_dt(s):
    """'YYYY-MM-DD HH:MM:SS...' → datetime (naive, KST 기준)."""
    if not s or len(s) < 19:
        return None
    try:
        return datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None
