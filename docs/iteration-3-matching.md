# Iteration 3: Matching

**Goal:** Match verification numbers between SIE and PDF filenames, with optional date/amount verification
**Deliverable:** Comprehensive match report showing matches, discrepancies, and missing PDFs
**Prerequisites:** Iteration 1 (OCR complete) and Iteration 2 (SIE parsing complete)

---

## Success Criteria

✅ All verification numbers matched between SIE and PDFs
✅ Missing PDFs identified and reported
✅ Date discrepancies flagged (±3 days tolerance)
✅ Amount mismatches identified (when extractable from PDFs)
✅ Extra PDFs (no SIE entry) reported
✅ Export comprehensive report to Excel/CSV

---

## Module: src/matcher.py

**Purpose:** Compare SIE entries (truth) with PDF files (reality) and generate discrepancy reports

### Key Functions

#### `match_sie_to_pdfs(sie_data, pdf_folder, year)`
- Read SIE data (verification entries from bookkeeping)
- Scan `Output/Vouchers/{year}/` folder for processed PDFs
- Match verification numbers from SIE to PDF filenames
- Extract verification number from PDF filename pattern: `A{number} - ...`
- Compare dates (allow minor discrepancies ±3 days)
- Extract text from processed PDFs to verify amounts
- Return matching results with file paths

**Parameters:**
```python
sie_data: DataFrame from iteration 2 (sie_parser output)
pdf_folder: Path to processed PDFs (e.g., "data/Output/Vouchers/2024/")
year: Year being processed (2024 or 2025)
```

**Returns:**
```python
DataFrame with columns:
    - verification_number: "A1", "A100"
    - sie_date: datetime(2024, 1, 11)
    - sie_target_amount: 500.00
    - sie_total_amount: 0.00 (validation)
    - pdf_filepath: "data/Output/Vouchers/2024/A100 - ...pdf"
    - pdf_found: True/False
    - pdf_date: datetime(2024, 1, 11) or None
    - pdf_amount: 500.00 or None
    - date_match: True/False/None
    - amount_match: True/False/None
    - discrepancy_type: "missing_pdf", "date_diff", "amount_diff", "extra_pdf", None
    - notes: "Date difference: 2 days" or ""
```

#### `generate_match_report(matches, year)`
- Create comprehensive DataFrame with all matching results
- Separate analysis for:
  - **Matches:** SIE entries with matching PDFs
  - **Missing PDFs:** SIE entries without PDFs
  - **Discrepancies:** Mismatches in dates or amounts
  - **Extra PDFs:** PDFs without corresponding SIE entries
- Export to Excel with multiple sheets
- Export to CSV for further analysis

**Output files:**
- Excel: `data/Output/reports/match_report_{year}_{timestamp}.xlsx`
- CSV: `data/Output/reports/match_report_{year}_{timestamp}.csv`

**Excel sheets:**
1. **Summary** - Overall statistics
2. **Matches** - All successful matches
3. **Missing PDFs** - SIE entries without PDFs
4. **Discrepancies** - Date/amount mismatches
5. **Extra PDFs** - PDFs without SIE entries

---

## Matching Logic

### Primary Match: Verification Number

**Pattern:** `^([A-Z]\d+)\s+-\s+`

**Example:**
```python
filename = "A100 - 2024-11-05 - Ahsell - Faktura.pdf"
verification_id = "A100"  # Extracted via regex
```

**Match criteria:**
- SIE verification_id == PDF verification_id
- Case-sensitive
- Must be exact match

### Secondary Match: Date Proximity

**Tolerance:** ±3 days

**Why tolerance needed:**
- Registration date may differ from transaction date
- Manual entry delays
- Accounting adjustments

**Implementation:**
```python
from datetime import timedelta

def dates_match(sie_date, pdf_date, tolerance_days=3):
    """
    Check if dates are within tolerance.

    Args:
        sie_date: Transaction date from SIE
        pdf_date: Date from PDF filename
        tolerance_days: Days tolerance (default: 3)

    Returns:
        bool: True if dates within tolerance
    """
    if sie_date is None or pdf_date is None:
        return None  # Cannot determine

    diff = abs((sie_date - pdf_date).days)
    return diff <= tolerance_days
```

**Date extraction from PDF:**
1. **From filename:** `\d{4}-\d{2}-\d{2}` pattern
2. **From content:** Look for common Swedish date formats

### Tertiary Match: Amount Comparison

**⚠️ CRITICAL: Use target_amount from SIE (NOT total_amount which is always 0.00)**

```
SIE data:                    PDF amounts:
  target_amount: 500.00        "500,00 kr"
  total_amount: 0.00 (ignored) "500.00 SEK"

Comparison: sie_target_amount == pdf_amount ± 0.01

Why: In double-entry bookkeeping, verifications sum to zero.
     target_amount = max(abs(all_transactions)) gives us the receipt amount.
```

**Tolerance:** ±0.01 (1 öre) for rounding differences

**Implementation:**
```python
def amounts_match(sie_amount, pdf_amount, tolerance=0.01):
    """
    Check if amounts match within tolerance.

    Args:
        sie_amount: target_amount from SIE
        pdf_amount: Amount extracted from PDF
        tolerance: Tolerance in SEK (default: 0.01)

    Returns:
        bool: True if amounts within tolerance
    """
    if sie_amount is None or pdf_amount is None:
        return None  # Cannot determine

    diff = abs(sie_amount - pdf_amount)
    return diff <= tolerance
```

---

## Amount Extraction from PDFs

### Swedish Number Parsing

**See [TECHNICAL_REFERENCE.md](TECHNICAL_REFERENCE.md) for complete implementation**

**Quick reference:**
```python
from src.matcher import parse_swedish_amount

# Extract amount from PDF text
text = extract_text_from_pdf(pdf_path)
amount = parse_swedish_amount(text)

# Examples that work:
"1 234,56 kr"       → 1234.56
"1.234,56 kr"       → 1234.56
"1234,56 kr"        → 1234.56
"1234.56 SEK"       → 1234.56
"Totalt: 1 234,56"  → 1234.56
```

**⚠️ Regex Safety:** Uses `[ \t\xa0]` NOT `\s` to avoid matching newlines

### Multiple Amounts Strategy

If multiple amounts found in PDF:

**Option 1: Use largest amount** (recommended)
```python
amounts = [100.00, 25.00, 125.00]  # Cost, VAT, Total
target = max(amounts)  # 125.00 (likely the total)
```

**Option 2: Use labeled amount**
```python
# Look for "Totalt:", "Summa", "Total" labels
# These are more likely to be the invoice total
```

**Option 3: Sum all amounts** (if clear cost breakdown)
```python
# Only if PDF clearly shows: Cost + VAT = Total
# And you want to match against cost+VAT
```

---

## Discrepancy Types

### 1. Missing PDF
- **Condition:** SIE entry exists, but no matching PDF found
- **Severity:** HIGH
- **Action:** Manual investigation required
- **Report note:** "PDF not found for verification {id}"

### 2. Date Difference
- **Condition:** PDF found, but date differs by > 3 days
- **Severity:** MEDIUM
- **Action:** Review for data entry errors
- **Report note:** "Date difference: {days} days"

### 3. Amount Difference
- **Condition:** PDF found, but amount differs by > 0.01
- **Severity:** MEDIUM
- **Action:** Review for calculation errors
- **Report note:** "Amount difference: SIE={sie_amt}, PDF={pdf_amt}"

### 4. Extra PDF
- **Condition:** PDF exists, but no matching SIE entry
- **Severity:** MEDIUM
- **Action:** Missing from bookkeeping or misnamed PDF
- **Report note:** "No SIE entry found for {verification_id}"

### 5. Match (Perfect)
- **Condition:** All criteria match
- **Severity:** NONE
- **Action:** None required
- **Report note:** "" (empty)

---

## Output Files (Iteration 3)

### Excel Report

**File:** `data/Output/reports/match_report_{year}_{timestamp}.xlsx`

**Sheet 1: Summary**
```
=== MATCHING SUMMARY ===
Year: 2024
Generated: 2026-01-04 17:00:00

Total SIE entries: 150
Total PDFs found: 148

MATCHES:
  Perfect matches: 140 (93%)
  Date mismatches: 5 (3%)
  Amount mismatches: 3 (2%)

DISCREPANCIES:
  Missing PDFs: 2 (1%)
  Extra PDFs: 0 (0%)
```

**Sheet 2: Matches** (140 rows)
```
verification_id | sie_date   | sie_target_amount | pdf_found | pdf_date   | pdf_amount | date_match | amount_match | notes
A1              | 2024-08-06 | 50000.00          | True      | 2024-08-06 | 50000.00   | True       | True         |
A2              | 2024-01-11 | 300.00            | True      | 2024-01-11 | 300.00     | True       | True         |
```

**Sheet 3: Missing PDFs** (2 rows)
```
verification_id | sie_date   | sie_target_amount | notes
A99             | 2024-05-15 | 1234.56           | PDF not found
A150            | 2024-08-20 | 567.89            | PDF not found
```

**Sheet 4: Discrepancies** (8 rows)
```
verification_id | sie_date   | pdf_date   | sie_target_amount | pdf_amount | discrepancy_type | notes
A25             | 2024-02-10 | 2024-02-15 | 500.00            | 500.00     | date_diff        | Date difference: 5 days
A50             | 2024-03-20 | 2024-03-20 | 1000.00           | 1001.00    | amount_diff      | Amount difference: 1.00
```

**Sheet 5: Extra PDFs** (0 rows)
```
pdf_filename                          | verification_id | notes
A999 - 2024-12-31 - Unknown.pdf       | A999            | No SIE entry found
```

### CSV Report

**File:** `data/Output/reports/match_report_{year}_{timestamp}.csv`

Same structure as Excel, but single flat file with all data.

---

## CLI Commands (main.py)

### Available Commands for Iteration 3

```bash
# Match 2024 data
python src/main.py match --year 2024

# Match 2025 data
python src/main.py match --year 2025

# Match both years
python src/main.py match

# Run full pipeline (OCR → Parse → Match)
python src/main.py full --year 2024
```

---

## Testing Strategy

### Test 1: Perfect Match
```python
# SIE entry: A1, 2024-08-06, 50000.00
# PDF: A1 - 2024-08-06 - Aktiekapital.pdf with "50 000,00 kr"
# Expected: Perfect match
```

### Test 2: Date Mismatch (within tolerance)
```python
# SIE entry: A2, 2024-01-11, 300.00
# PDF: A2 - 2024-01-13 - Payment.pdf  (2 days difference)
# Expected: Match with warning
```

### Test 3: Date Mismatch (outside tolerance)
```python
# SIE entry: A3, 2024-01-11, 500.00
# PDF: A3 - 2024-01-20 - Payment.pdf  (9 days difference)
# Expected: Discrepancy flagged
```

### Test 4: Amount Mismatch
```python
# SIE entry: A4, 2024-02-15, 1000.00
# PDF: A4 - 2024-02-15 - Invoice.pdf with "1001,00 kr"
# Expected: Discrepancy flagged (amount_diff)
```

### Test 5: Missing PDF
```python
# SIE entry: A99, 2024-05-15, 1234.56
# PDF: (not found)
# Expected: Missing PDF report
```

### Test 6: Extra PDF
```python
# SIE entry: (not found)
# PDF: A999 - 2024-12-31 - Unknown.pdf
# Expected: Extra PDF report
```

---

## Success Criteria (Final Checklist)

✅ Primary matching (verification number) works
✅ Date matching with ±3 days tolerance works
✅ Amount extraction from Swedish PDFs works
✅ Safe regex patterns used (no newline matching)
✅ target_amount used for matching (not total_amount)
✅ Excel report generated with multiple sheets
✅ CSV report generated
✅ All discrepancy types identified correctly
✅ Summary statistics accurate

**Time Estimate:** ~30 minutes - 1 hour

---

## Next Step

✅ **Project Complete!** All iterations finished.

Optional enhancements:
- Add GUI interface
- Email notifications for discrepancies
- Automatic PDF downloads from cloud storage
- Integration with accounting software API

## Reference

📖 **Technical Reference:** See [TECHNICAL_REFERENCE.md](TECHNICAL_REFERENCE.md) for:
- Swedish number parsing details
- Regex patterns (safe, no `\s`)
- Helper function implementation
- Test cases
- Performance considerations

📖 **Iteration 2:** See [iteration-2-sie-parser.md](iteration-2-sie-parser.md) for:
- Zero Sum Trap explanation
- Why we use target_amount for matching
