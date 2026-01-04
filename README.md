# OCR Processing and SIE Matching

Find differences between PDF vouchers and vouchers recorded in the bookkeeping system (SIE).

## Setup

1. Create and activate a virtual environment
   - `python -m venv .venv`
   - `.\.venv\Scripts\activate`
2. Install dependencies
   - `pip install -r requirements.txt`
3. Create output folders and verify paths
   - `python src/main.py setup`

## Status

- ✅ Iteration 0 (environment + scaffold) - `setup` command implemented
- ✅ Iteration 1 (OCR processing) - `ocr` and `ocrclean` commands implemented
- ✅ Iteration 2 (SIE parsing) - `parse` and `parseclean` commands implemented
- ✅ Iteration 3 (Matching) - `match` command implemented
- ⏳ Iteration 4 (Full pipeline) - `full` command not implemented yet

## Data layout

- Input is read-only: `Data/Input/`
- All generated output goes to: `Data/Output/`

⚠️ **Important Notes:**
- **SIE files** (`data/Input/SIE/*.se`) are exported from the accounting system and should NOT be modified
- User provides updated SIE exports when new verifications are added to the accounting system
- Preliminary/draft verifications in the accounting system won't appear until exported to SIE

## Commands

### Setup
- `python src/main.py setup` - Create output folders and verify data paths

### OCR Processing
- `python src/main.py ocr --year 2024 --limit 5` - Process PDFs with OCR
- `python src/main.py ocrclean [--year 2024]` - Remove OCR-processed PDFs

### SIE Parsing
- `python src/main.py parse --year 2024` - Parse SIE files and extract verification data
- `python src/main.py parseclean` - Remove all parsed SIE output files

### Matching
- `python src/main.py match [--year 2024] [--max-days 120]` - Match supplier invoices with clearing vouchers
  - Identifies receipt events (2440 Kredit or 2440 Debet without 1930)
  - Finds corresponding clearing events (2440 Debet with 1930)
  - Validates amounts match exactly (absolute value)
  - Generates single report with review flag column "Behöver granskas" (JA = needs review, NEJ = OK)
  - Reports saved to `Data/Output/reports/`
  - Numbers formatted with Swedish decimal separator (comma)
  - Filter by "JA" in Excel to see only cases that need review
- `python src/main.py matchclean` - Remove all matching report files

### Full Pipeline (Not implemented yet)
- `python src/main.py full --year 2024` - Run complete pipeline (OCR → Parse → Match)
