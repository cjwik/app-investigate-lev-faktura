# Iteration 0: Environment Setup

**Goal:** Get Python environment ready
**Deliverable:** Working virtual environment with dependencies installed
**Prerequisites:** None - this is the foundation

---

## Files to Create

1. `.venv/` (virtual environment directory)
2. `requirements.txt`
3. `.gitignore`
4. `logs/` (log files directory)
5. `src/__init__.py`
6. `src/config.py`
7. `src/logger.py`

---

## Step-by-Step Actions

### 1. Create Virtual Environment
```bash
python -m venv .venv
```

### 2. Activate Virtual Environment
**Windows:**
```bash
.venv\Scripts\activate
```

**Linux/Mac:**
```bash
source .venv/bin/activate
```

### 3. Create requirements.txt
```txt
ocrmypdf>=15.0.0
pdfplumber>=0.10.0
pandas>=2.0.0
openpyxl>=3.1.0
python-dotenv>=1.0.0
tqdm>=4.66.0
```

**Dependencies explained:**
- `ocrmypdf` - OCR processing with Tesseract
- `pdfplumber` - Fast PDF text extraction
- `pandas` - Data analysis and DataFrame manipulation
- `openpyxl` - Excel file export (.xlsx)
- `python-dotenv` - Configuration management
- `tqdm` - Progress bars for batch processing

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Create Output Folders
```bash
mkdir -p data/Output/Vouchers/2024
mkdir -p data/Output/Vouchers/2025
mkdir -p data/Output/reports
mkdir -p logs
```

---

## Module: src/logger.py

**Purpose:** Centralized logging setup for all modules

**Features:**
- Configure Python's logging module
- Multiple log handlers:
  - Console output (INFO level)
  - Main log file: `logs/ocr_processing.log` (DEBUG level)
  - Error log file: `logs/ocr_errors.log` (ERROR level only)
- Timestamp format: `YYYY-MM-DD HH:MM:SS`
- Automatic log rotation (when files get too large)

**Functions to implement:**
```python
def setup_logger(name, log_file, level=logging.INFO):
    """
    Create logger instance with file and console handlers.

    Args:
        name: Logger name (typically __name__)
        log_file: Path to log file
        level: Logging level (INFO, DEBUG, ERROR)

    Returns:
        logging.Logger instance
    """
    pass

def get_logger(module_name):
    """
    Get logger for specific module.

    Args:
        module_name: Module name (typically __name__)

    Returns:
        logging.Logger instance
    """
    pass

def log_processing_summary(stats):
    """
    Write processing summary to report file.

    Args:
        stats: Dictionary with processing statistics
    """
    pass
```

**Implementation Notes:**
- Use `logging.handlers.RotatingFileHandler` for log rotation
- Max file size: 10MB before rotation
- Keep 5 backup files
- Format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`

---

## Module: src/config.py

**Purpose:** Configuration settings for all paths and options

**Configuration structure:**
```python
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"

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
OCR_LANGUAGE = 'swe'  # Swedish
OCR_SKIP_EXISTING = True
OCR_TIMEOUT = 300  # 5 minutes per file

# Matching settings
DATE_TOLERANCE_DAYS = 3
AMOUNT_TOLERANCE = 0.01  # ±1 öre
```

**Important:**
- All paths use `pathlib.Path` for cross-platform compatibility
- Input paths are READ-ONLY - never modify source data
- All output goes to `data/Output/`

---

## Module: src/__init__.py

**Purpose:** Python package marker

**Content:**
```python
"""
OCR Processing and SIE Matching Project
"""
__version__ = "0.1.0"
```

---

## File: .gitignore

**Purpose:** Git ignore rules for Python projects

**Content:**
```
# Virtual environment
.venv/
venv/
ENV/

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python

# IDE
.idea/
.vscode/
*.swp
*.swo
*~

# Project specific
data/Output/
logs/
*.log

# Environment variables
.env
.env.local

# OS
.DS_Store
Thumbs.db
```

---

## Verification Steps

After completing Iteration 0, verify:

1. **Virtual environment active:**
   ```bash
   which python  # Should show .venv/Scripts/python (Windows) or .venv/bin/python (Linux/Mac)
   ```

2. **Dependencies installed:**
   ```bash
   pip list
   # Should show: ocrmypdf, pdfplumber, pandas, openpyxl, python-dotenv, tqdm
   ```

3. **Folders created:**
   ```bash
   ls data/Output/Vouchers/
   # Should show: 2024/ 2025/

   ls data/Output/
   # Should show: Vouchers/ reports/

   ls logs/
   # Should exist (may be empty)
   ```

4. **Python can import modules:**
   ```python
   from src import config, logger
   print(config.BASE_DIR)  # Should print project root path
   ```

---

## Success Criteria

✅ Virtual environment created and activated
✅ All dependencies installed successfully
✅ Output folder structure created
✅ Logs folder created
✅ `src/__init__.py` exists
✅ `src/config.py` with all path configurations
✅ `src/logger.py` with logging utilities
✅ `.gitignore` with Python project rules

**Time Estimate:** ~15 minutes

---

## Next Step

➡️ **Iteration 1:** OCR Processing ([iteration-1-ocr-processing.md](iteration-1-ocr-processing.md))
