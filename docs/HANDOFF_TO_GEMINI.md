# Handoff Instructions for Gemini AI

## Project Overview

This is a Swedish accounting invoice matching system that processes SIE files (Swedish accounting standard) to match supplier invoices (receipts on account 2440) with their corresponding payments (clearings).

**Primary Goal**: Match invoice receipts with payment clearings, identify unpaid invoices, and exclude correction vouchers from analysis.

## Current Status - COMPLETED WORK

### ✅ Iteration 1: OCR Processing (COMPLETE)
- Extracts supplier invoices from PDF files using Tesseract OCR
- Swedish language processing enabled
- Outputs structured data for matching

### ✅ Iteration 2: SIE Parser (COMPLETE)
- Parses Swedish SIE accounting files
- Extracts vouchers with transaction data
- Handles account 2440 (Leverantörsskulder/Accounts Payable)
- Handles account 1930 (Företagskonto/Bank account)

### ✅ Iteration 3: Invoice Matcher (COMPLETE)
- Matches receipts (negative amounts on 2440) with clearings (positive amounts on 2440)
- Identifies correction vouchers using Swedish keywords "korrigerad" and "Korrigering"
- **CRITICAL FIX APPLIED**: Year-aware correction detection to prevent cross-year voucher ID collisions
- Generates detailed reports in CSV and text formats

### ✅ Verification System (COMPLETE)
- **Baseline File**: `tests/expected_2024_results.json` - Contains ground truth for 2024 matching
- **Comprehensive Tests**: `tests/test_2024_report_verification.py` - 6 automated tests
- **Correction Tests**: `tests/test_2024_corrections.py` - 2 focused tests on known correction pairs
- **All 8 tests passing** ✓

## CRITICAL BUG FIX - MUST UNDERSTAND

### Problem: Cross-Year Voucher ID Collision
When processing 2024 invoices with cross-year matching (loading both 2024 and 2025 SIE files), voucher **A49** was incorrectly excluded.

**Root Cause**:
- 2024-A53: Payment to Dahl (legitimate clearing for A49)
- 2025-A53: VAT refund (part of correction pair with A55)
- Old code excluded ALL "A53" vouchers from both years

**Solution Applied**:
Modified `src/matcher.py` - `identify_correction_vouchers()` method to accept `target_year` parameter:

```python
def identify_correction_vouchers(self, vouchers: List[Voucher], target_year: int = None) -> set[str]:
    """
    Args:
        target_year: If provided, only exclude corrections where BOTH vouchers are from this year.
                    This prevents cross-year voucher ID collisions (e.g., 2024-A53 vs 2025-A53)
    """
    # Only process vouchers from the target year
    if target_year and voucher.date.year != target_year:
        continue

    # Only exclude if BOTH vouchers in the pair are from the same year
    if ref_voucher and (not target_year or ref_voucher.date.year == target_year):
        exclude_ids.add(voucher.voucher_id)
        exclude_ids.add(referenced_id)
```

**Key Principle**: Correction vouchers can only occur within the same year.

## Known Ground Truth for 2024 (NEVER CHANGE)

### Correction Voucher Pairs (Always Exclude These 6):
1. **A120 ↔ A131**: Nibe payment (has both 2440 + 1930 accounts)
2. **A143 ↔ A170**: Bauhaus invoice (has 2440 only)
3. **A168 ↔ A169**: Interest income (no 2440 or 1930)

### Expected Results for 2024:
- **Total Invoice Cases**: 43
- **Paid (OK)**: 37
- **Unpaid**: 6 (A133, A136, A137, A138, A149, A163)
- **Needs Review**: 0
- **Bookkeeping Totals**: Kredit 36,225.10 SEK, Debet 33,896.10 SEK, Outstanding 2,329.00 SEK

### Critical Matches That Must Work:
- **A49 → A53**: Receipt 1,906 SEK matched with clearing 1 day later ✓
- **A110 → A123**: Receipt 50 SEK matched with clearing 1 day later ✓

## Project Structure

```
Wik - InvestigationLevFaktura/
├── src/
│   ├── main.py                 # CLI entry point
│   ├── ocr_processor.py        # Iteration 1: PDF → text extraction
│   ├── transaction_parser.py   # Iteration 2: SIE file parser
│   └── matcher.py              # Iteration 3: Invoice matching (YEAR-AWARE)
├── tests/
│   ├── expected_2024_results.json           # Ground truth baseline
│   ├── test_2024_report_verification.py     # 6 comprehensive tests
│   └── test_2024_corrections.py             # 2 correction pair tests
├── Data/
│   ├── Input/
│   │   ├── Fakturor/           # PDF invoices
│   │   └── SIE/                # Accounting files (20240101-20241231.se, 20250101-20251231.se)
│   └── Output/
│       └── reports/            # Generated CSV and TXT reports
└── docs/
    ├── PLANNING.md             # Original project plan
    ├── VERIFICATION_SYSTEM.md  # How to use verification tests
    ├── CROSS_YEAR_MATCHING_FIX.md  # Documents the A49→A53 fix
    └── HANDOFF_TO_GEMINI.md    # This file
```

## How to Run

### Generate 2024 Report
```bash
python src/main.py match --year 2024
```

### Verify Results (ALWAYS RUN AFTER CODE CHANGES)
```bash
# Run all verification tests
python -m pytest tests/test_2024_report_verification.py -v

# Run just correction tests
python -m pytest tests/test_2024_corrections.py -v

# Run all tests
python -m pytest tests/ -v
```

**Expected Output**: All 8 tests should pass ✓

## Swedish Accounting Terms

- **SIE**: Swedish accounting file format standard
- **Verifikation**: Voucher (transaction record)
- **Konto 2440**: Leverantörsskulder (Accounts Payable - supplier debt)
- **Konto 1930**: Företagskonto (Bank account)
- **Kredit** (negative on 2440): Invoice receipt (debt increases)
- **Debet** (positive on 2440): Payment clearing (debt decreases)
- **Korrigerad**: Corrected (marks the incorrect voucher)
- **Korrigering**: Correction (the voucher that corrects it)
- **Utg. saldo**: Outstanding balance

## Next Steps - FUTURE WORK

### Iteration 4: PDF-to-SIE Matching (NOT STARTED)
**Goal**: Match OCR-extracted invoices from PDFs with SIE voucher entries

**Challenges**:
1. **Fuzzy Matching**: Supplier names may differ between PDF and SIE
   - PDF: "Ahlsell Sverige AB"
   - SIE: "Ahlsell"

2. **Amount Matching**: May need tolerance for rounding differences
   - PDF: 1,905.75 SEK
   - SIE: 1,906.00 SEK (rounded)

3. **Date Matching**: Invoice date vs voucher date may differ
   - Invoice date: 2024-10-10
   - Voucher date: 2024-10-14 (registered 4 days later)

**Strategy Suggestion**:
- Use fuzzy string matching (e.g., `fuzzywuzzy` library) for supplier names
- Allow configurable amount tolerance (e.g., ±1 SEK or ±0.5%)
- Match within date range (e.g., voucher within 30 days of invoice)

### Iteration 5: Web Interface (NOT STARTED)
**Goal**: Create a web UI for uploading files and viewing results

**Technology Suggestions**:
- **Backend**: Flask or FastAPI (Python)
- **Frontend**: Simple HTML/CSS/JavaScript or React
- **Features**:
  - Upload SIE files
  - Upload PDF invoices
  - View matching results in table format
  - Download reports
  - Filter by status (Paid/Unpaid/Review)

## Important Rules for Gemini

### ✅ DO:
1. **Always run verification tests** after any code changes to matcher.py or transaction_parser.py
2. **Preserve the year-aware correction detection** - this fix is critical
3. **Use the verification files** as regression tests
4. **Read the documentation files** in `docs/` folder before making changes
5. **Follow Swedish accounting conventions** (Kredit/Debet on account 2440)

### ❌ DON'T:
1. **NEVER change the correction detection** without understanding the cross-year collision issue
2. **NEVER modify expected_2024_results.json** unless you've verified the change is correct
3. **NEVER remove the target_year parameter** from `identify_correction_vouchers()`
4. **NEVER assume voucher IDs are unique across years** (e.g., A53 exists in both 2024 and 2025)
5. **NEVER skip running tests** after code changes

## Testing Philosophy

### What Should NEVER Change (Hard Constraints):
- Bookkeeping totals (raw SIE data): 36,225.10 Kredit, 33,896.10 Debet
- Correction pairs: A120↔A131, A143↔A170, A168↔A169
- Number of vouchers in SIE file

### What MAY Change (With Justification):
- Matching results (if algorithm improves)
- Outstanding invoice list (if better clearings are found)
- Status classifications (if validation rules change)

**If tests fail**:
1. First, verify the code change is correct
2. Manually review the new report
3. Update expected_2024_results.json ONLY if the change is intentional and correct
4. Document the reason in git commit message

## Key Files to Review

Before continuing work, read these files:

1. **[docs/PLANNING.md](../docs/PLANNING.md)** - Original project vision and iterations
2. **[docs/VERIFICATION_SYSTEM.md](../docs/VERIFICATION_SYSTEM.md)** - How to use verification tests
3. **[docs/CROSS_YEAR_MATCHING_FIX.md](../docs/CROSS_YEAR_MATCHING_FIX.md)** - Critical bug fix explanation
4. **[src/matcher.py](../src/matcher.py)** - Core matching logic (lines 127-170, 370-373 are critical)
5. **[tests/expected_2024_results.json](../tests/expected_2024_results.json)** - Ground truth baseline

## Example Workflow for New Features

```bash
# 1. Read relevant documentation
# 2. Make code changes
# 3. ALWAYS run verification tests
python -m pytest tests/ -v

# 4. Generate new report to manually verify
python src/main.py match --year 2024

# 5. Check the report
cat Data/Output/reports/summary_2024_*.csv

# 6. If results changed unexpectedly, investigate
# 7. If results changed as expected, update expected_2024_results.json
# 8. Re-run tests to ensure they pass
python -m pytest tests/ -v

# 9. Commit with descriptive message
git add .
git commit -m "feat: [description of change] - Updated baseline because [reason]"
```

## Contact Points

- **Original Developer**: Claude Sonnet 4.5 (via VSCode extension)
- **Verification System Created**: 2026-01-05
- **Last Test Run**: All 8 tests passing ✓
- **Git Branch**: main

## Quick Reference Commands

```bash
# Run matching for 2024
python src/main.py match --year 2024

# Run all verification tests
python -m pytest tests/ -v

# Run only correction tests (fast check)
python -m pytest tests/test_2024_corrections.py -v

# Check test coverage (if installed)
python -m pytest tests/ --cov=src --cov-report=term

# View latest report
ls -lt Data/Output/reports/ | head -5
```

## Success Criteria

You'll know you're on the right track if:

✅ All 8 verification tests pass
✅ A49 → A53 match is working (status: "OK")
✅ 6 outstanding invoices: A133, A136, A137, A138, A149, A163
✅ 6 correction vouchers excluded: A120, A131, A143, A168, A169, A170
✅ Bookkeeping totals match: 36,225.10 / 33,896.10 / 2,329.00

## Final Notes

This project is well-structured with a solid foundation. The verification system ensures you can make changes confidently without breaking existing functionality. The most critical part is understanding the **year-aware correction detection** fix - without it, cross-year matching breaks.

Focus on Iteration 4 (PDF-to-SIE matching) next, as Iterations 1-3 are complete and verified.

Good luck! The tests are your safety net - use them.

---

**Document Version**: 1.0
**Created**: 2026-01-05
**Last Verified**: 2026-01-05 (All tests passing)
