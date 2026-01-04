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

- Iteration 0 (environment + scaffold) is implemented; `python src/main.py setup` works.
- Iteration 1-3 commands (`ocr`, `parse`, `match`, `full`) are not implemented yet.

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

### Matching (Not implemented yet)
- `python src/main.py match --year 2024` - Match SIE entries with PDF vouchers
- `python src/main.py full --year 2024` - Run full pipeline (OCR → Parse → Match)
