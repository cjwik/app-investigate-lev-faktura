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

## Commands (planned)

- `python src/main.py setup`
- `python src/main.py ocr --year 2024 --limit 5`
- `python src/main.py parse --year 2024`
- `python src/main.py match --year 2024`
- `python src/main.py full --year 2024`
