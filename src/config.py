from __future__ import annotations

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


def _pick_data_dir(base_dir: Path) -> Path:
    data_dir = base_dir / "Data"
    if data_dir.exists():
        return data_dir
    return base_dir / "data"


DATA_DIR = _pick_data_dir(BASE_DIR)

# Input paths (READ-ONLY)
INPUT_DIR = DATA_DIR / "Input"
SIE_DIR = INPUT_DIR / "SIE"
INPUT_VOUCHERS_2024 = INPUT_DIR / "Verifikationer 2024"
INPUT_VOUCHERS_2025 = INPUT_DIR / "Verifikationer 2025"

# Output paths
OUTPUT_DIR = DATA_DIR / "Output"
OUTPUT_VOUCHERS_DIR = OUTPUT_DIR / "Vouchers"
OUTPUT_VOUCHERS_2024 = OUTPUT_VOUCHERS_DIR / "2024"
OUTPUT_VOUCHERS_2025 = OUTPUT_VOUCHERS_DIR / "2025"
REPORTS_DIR = OUTPUT_DIR / "reports"

# Log paths
LOGS_DIR = BASE_DIR / "logs"
MAIN_LOG = LOGS_DIR / "ocr_processing.log"
ERROR_LOG = LOGS_DIR / "ocr_errors.log"

# OCR settings
OCR_LANGUAGE = "swe"
OCR_SKIP_EXISTING = True
OCR_TIMEOUT = 300  # seconds

# Matching settings
DATE_TOLERANCE_DAYS = 3
AMOUNT_TOLERANCE = 0.01

