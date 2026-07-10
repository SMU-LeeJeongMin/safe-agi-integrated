# 대시보드에서 사용하는 파일 경로를 관리하는 파일

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent

# F1 입력/feature 파이프라인 산출물 위치
# Dashboard/data 폴더가 아니라 Input/F1/outputs를 읽습니다.
INPUT_F1_OUTPUT_DIR = REPO_ROOT / "Input" / "F1" / "outputs"

FEATURE_PATH = INPUT_F1_OUTPUT_DIR / "fatigue_minute_features.csv"
DTO5_PATH = INPUT_F1_OUTPUT_DIR / "dto5_sequence.json"
REPORT_PATH = INPUT_F1_OUTPUT_DIR / "validation_report.json"

# Dashboard에서 사용자가 저장하는 InferenceResult 로컬 출력 위치
DASHBOARD_OUTPUT_DIR = BASE_DIR / "outputs"
DASHBOARD_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
INFERENCE_SAVE_PATH = DASHBOARD_OUTPUT_DIR / "inference_results_demo.csv"
