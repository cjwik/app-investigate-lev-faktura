# Handoff to Codex - Invoice Matching System

## Project Overview

This is a Swedish accounting invoice matching system that processes SIE files (Swedish accounting standard) to match supplier invoices with their corresponding payments.

**Primary Goal**: Match invoice receipts (account 2440) with payment clearings, identify unpaid invoices, and exclude correction vouchers from analysis.

## Current Status: ✅ STABLE & VERIFIED

### Completed Iterations

#### ✅ Iteration 1: OCR Processing
- Extracts supplier invoices from PDF files using Tesseract OCR
- Swedish language processing enabled (`swe` language data installed)
- Outputs structured data to `Data/Output/ocr_results/`
- **Status**: Complete and working

#### ✅ Iteration 2: SIE Parser
- Parses Swedish SIE accounting files
- Extracts vouchers with transaction data
- Handles Swedish accounting accounts:
  - **2440**: Leverantörsskulder (Accounts Payable - supplier debt)
  - **1930**: Företagskonto (Bank account)
- **Status**: Complete and working

#### ✅ Iteration 3: Invoice Matcher
- Matches receipts (negative amounts on 2440) with clearings (positive amounts on 2440)
- Identifies correction vouchers using Swedish keywords "korrigerad" and "Korrigering"
- Generates detailed reports in CSV and text formats
- **Status**: Complete, stable, and verified

#### ✅ Verification System
- **Purpose**: Ensures 2024 results remain constant despite code changes
- **Files**:
  - `tests/expected_2024_results.json` - Ground truth baseline
  - `tests/test_2024_report_verification.py` - 6 comprehensive tests
  - `tests/test_2024_corrections.py` - 2 focused correction tests
- **Status**: ✅ All 8 tests passing

## Critical Bug Fix: Cross-Year Matching

### The Problem
When loading both 2024 and 2025 SIE files for cross-year matching, voucher ID collisions occurred:
- **2024-A53**: Payment to Dahl (legitimate clearing for invoice A49)
- **2025-A53**: VAT refund (part of correction pair with A55)

The old code excluded ALL "A53" vouchers from both years, breaking the A49→A53 match.

### The Solution (IMPLEMENTED & VERIFIED)
Modified `src/matcher.py` to make correction detection **year-aware**:

```python
def identify_correction_vouchers(self, vouchers: List[Voucher], target_year: int = None) -> set[str]:
    """
    Args:
        target_year: If provided, only exclude corrections where BOTH vouchers are from this year.
                    This prevents cross-year voucher ID collisions.
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

**Result**: A49→A53 match now works correctly ✓

## 2024 Ground Truth (VERIFIED & FROZEN)

These values are **constant** and serve as regression tests:

### Correction Voucher Pairs (Always Exclude These 6)
1. **A120 ↔ A131**: Nibe payment (has both 2440 + 1930 accounts)
2. **A143 ↔ A170**: Bauhaus invoice (has 2440 only)
3. **A168 ↔ A169**: Interest income (no 2440 or 1930)

### Expected Results
- **Total Invoice Cases**: 43
- **Paid (OK)**: 37
- **Unpaid (Missing clearing)**: 6
  - A133: -776 SEK (Ahlsell)
  - A136: -309 SEK (Ahlsell)
  - A137: -398 SEK (Ahlsell)
  - A138: -327 SEK (Ahlsell)
  - A149: -296 SEK (Dahl)
  - A163: -223 SEK
- **Needs Review**: 0

### Bookkeeping Totals (Raw SIE Data - Never Changes)
- **Kredit (Receipts)**: 36,225.10 SEK
- **Debet (Clearings)**: 33,896.10 SEK
- **Outstanding Balance**: 2,329.00 SEK

### Critical Matches (Must Always Work)
- **A49 → A53**: 1,906 SEK, cleared 1 day later ✓
- **A110 → A123**: 50 SEK, cleared 1 day later ✓

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
│   │   ├── Fakturor/           # PDF invoices (for future iteration)
│   │   └── SIE/                # Accounting files
│   │       ├── 20240101-20241231.se  # 2024 data (FROZEN)
│   │       └── 20250101-20251231.se  # 2025 data
│   └── Output/
│       ├── ocr_results/        # OCR extracted data
│       └── reports/            # Generated matching reports
└── docs/
    ├── PLANNING.md                      # Original project plan
    ├── VERIFICATION_SYSTEM.md           # How to use verification tests
    ├── CROSS_YEAR_MATCHING_FIX.md      # Documents the A49→A53 fix
    └── HANDOFF_TO_CODEX.md             # This file
```

## How to Run

### Generate 2024 Report
```bash
python src/main.py match --year 2024
```

### Verify Results (CRITICAL - ALWAYS RUN AFTER CODE CHANGES)
```bash
# Run all verification tests
python -m pytest tests/test_2024_report_verification.py -v

# Run just correction tests (fast check)
python -m pytest tests/test_2024_corrections.py -v

# Run all tests
python -m pytest tests/ -v
```

**Expected**: All 8 tests should pass ✓

### Clean Old Reports
```bash
python src/main.py matchclean --year 2024
```

## Swedish Accounting Terminology

| Swedish Term | English | Account | Meaning |
|--------------|---------|---------|---------|
| SIE | Swedish accounting file format | - | Standard file format |
| Verifikation | Voucher | - | Transaction record |
| Leverantörsskulder | Accounts Payable | 2440 | Supplier debt |
| Företagskonto | Bank account | 1930 | Company bank |
| Kredit | Credit | - | Negative on 2440 = debt increases |
| Debet | Debit | - | Positive on 2440 = debt decreases |
| Korrigerad | Corrected | - | Marks incorrect voucher |
| Korrigering | Correction | - | The correcting voucher |
| Utg. saldo | Outstanding balance | - | Unpaid amount |

## Recent History: Gemini Breaking Changes (RESOLVED)

### What Happened
Gemini introduced "Direct Payment" logic that created false positive matches by matching invoices (account 2440) with vouchers that only had bank payments (account 1930) but NO account 2440.

### Impact
- All 6 unpaid invoices were incorrectly marked as paid
- Tests failed: Expected 37 paid/6 unpaid, got 43 paid/0 unpaid
- Verification system caught it immediately ✓

### Resolution
- Reverted all Gemini changes to `src/matcher.py`
- Removed Gemini's test files (based on flawed logic)
- System restored to stable state
- All tests passing ✓

### Lesson Learned
**NEVER match invoices with vouchers that lack account 2440.** If a voucher only has 1930 (bank) without 2440, it's a direct purchase, NOT a clearing of an existing invoice.

## Critical Rules for Codex

### ✅ DO:
1. **Always run verification tests** after ANY code changes to matcher.py or transaction_parser.py
2. **Preserve the year-aware correction detection** - this is critical for cross-year matching
3. **Only match when proper accounting entries exist**:
   - Receipt MUST have: 2440 Kredit (negative)
   - Clearing MUST have: 2440 Debet (positive) + 1930 Kredit (negative)
4. **Read documentation** before making changes:
   - [docs/PLANNING.md](PLANNING.md) - Original vision
   - [docs/VERIFICATION_SYSTEM.md](VERIFICATION_SYSTEM.md) - Test system
   - [docs/CROSS_YEAR_MATCHING_FIX.md](CROSS_YEAR_MATCHING_FIX.md) - Critical bug fix
5. **Use the verification files** as regression tests

### ❌ DON'T:
1. **NEVER match invoices with vouchers lacking account 2440** (Gemini's mistake)
2. **NEVER "infer" or "simulate" accounting entries** that don't exist
3. **NEVER modify expected_2024_results.json** without user approval
4. **NEVER remove the target_year parameter** from identify_correction_vouchers()
5. **NEVER assume voucher IDs are unique across years** (e.g., A53 exists in both 2024 and 2025)
6. **NEVER skip running tests** after code changes

## Testing Philosophy

### Hard Constraints (NEVER Change)
- Bookkeeping totals: 36,225.10 / 33,896.10 / 2,329.00
- Correction pairs: A120↔A131, A143↔A170, A168↔A169
- Number of vouchers in SIE file

### May Change (With Justification & User Approval)
- Matching results (if algorithm genuinely improves)
- Outstanding invoice list (if better clearings are found)
- Status classifications (if validation rules change)

**If tests fail**:
1. Verify the code change is actually correct
2. Manually review the new report
3. Only update expected_2024_results.json if change is intentional AND correct
4. Document the reason in git commit message

## Next Steps - Future Work

### Iteration 4: PDF-to-SIE Matching (NOT STARTED)
**Goal**: Match OCR-extracted invoices from PDFs with SIE voucher entries

**Challenges**:
1. **Fuzzy Matching**: Supplier names differ between PDF and SIE
   - PDF: "Ahlsell Sverige AB"
   - SIE: "Ahlsell"
   - Solution: Use fuzzy string matching (e.g., `fuzzywuzzy` or `rapidfuzz`)

2. **Amount Matching**: May need tolerance for rounding
   - PDF: 1,905.75 SEK
   - SIE: 1,906.00 SEK
   - Solution: Allow ±1 SEK or ±0.5% tolerance

3. **Date Matching**: Invoice date vs voucher date may differ
   - Invoice date: 2024-10-10
   - Voucher date: 2024-10-14 (registered 4 days later)
   - Solution: Match within date range (e.g., ±30 days)

**Strategy**:
- Read OCR results from `Data/Output/ocr_results/`
- Match against existing SIE voucher cases
- Enrich the report with: Invoice Number, PDF Date, PDF Amount
- Flag discrepancies for review

### Iteration 5: Web Interface (NOT STARTED)
**Goal**: Create a web UI for uploading files and viewing results

**Technology Suggestions**:
- Backend: Flask or FastAPI (Python)
- Frontend: Simple HTML/CSS/JS or React
- Features:
  - Upload SIE files
  - Upload PDF invoices
  - View matching results in table format
  - Download reports (CSV/Excel)
  - Filter by status (Paid/Unpaid/Review)
  - Highlight critical matches and outstanding invoices

## Key Files to Review

Before starting work, read these:

1. **[docs/PLANNING.md](PLANNING.md)** - Original project vision, all iterations planned
2. **[docs/VERIFICATION_SYSTEM.md](VERIFICATION_SYSTEM.md)** - How to use tests
3. **[docs/CROSS_YEAR_MATCHING_FIX.md](CROSS_YEAR_MATCHING_FIX.md)** - Critical bug fix explanation
4. **[src/matcher.py](../src/matcher.py)** - Core logic (lines 127-170, 370-373 are critical)
5. **[tests/expected_2024_results.json](../tests/expected_2024_results.json)** - Ground truth

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

# 6. If results changed unexpectedly, investigate and revert
# 7. If results changed as expected, update expected_2024_results.json (with user approval)
# 8. Re-run tests to ensure they pass
python -m pytest tests/ -v

# 9. Commit with descriptive message
git add .
git commit -m "feat: [description] - [reason for baseline change if any]"
```

## Quick Reference Commands

```bash
# Run matching for 2024
python src/main.py match --year 2024

# Clean old 2024 reports
python src/main.py matchclean --year 2024

# Run all verification tests (ALWAYS DO THIS AFTER CODE CHANGES)
python -m pytest tests/ -v

# Run only correction tests (fast check)
python -m pytest tests/test_2024_corrections.py -v

# View latest report summary
cat Data/Output/reports/summary_2024_*.csv

# Check outstanding invoices
grep "Missing clearing" Data/Output/reports/invoice_validation_2024_*.csv
```

## Success Criteria

You'll know everything is working correctly if:

✅ All 8 verification tests pass
✅ A49 → A53 match is working (status: "OK")
✅ 6 outstanding invoices: A133, A136, A137, A138, A149, A163
✅ 6 correction vouchers excluded: A120, A131, A143, A168, A169, A170
✅ Bookkeeping totals match: 36,225.10 / 33,896.10 / 2,329.00
✅ 43 total cases: 37 paid, 6 unpaid, 0 review

## Current System State

### Last Verified: 2026-01-05

| Aspect | Status | Details |
|--------|--------|---------|
| Code | ✅ STABLE | Gemini changes reverted, year-aware fix in place |
| Tests | ✅ 8/8 PASSING | All verification tests green |
| 2024 Data | ✅ VERIFIED | 37 paid, 6 unpaid (correct) |
| Documentation | ✅ CLEAN | Handoff docs removed, only essentials remain |
| Reports | ✅ FRESH | Clean report generated 2026-01-05 13:00:34 |

### Git Status
```
Branch: main
Commits ahead: 10 (ready to push if needed)
Working directory: clean
Latest commit: "chore: Clean up documentation after reverting Gemini breaking changes"
```

## Final Notes

This project has a **solid foundation** with a robust verification system. The most critical aspect is understanding the **year-aware correction detection** fix - without it, cross-year matching breaks.

The verification system is your safety net:
- It caught Gemini's breaking changes immediately
- It ensures 2024 results stay constant
- It gives you confidence to make changes

**Focus on Iteration 4 next** (PDF-to-SIE matching), as Iterations 1-3 are complete and verified.

Good luck! Trust the tests - they're there to help you.

---

**Document Version**: 1.0
**Created**: 2026-01-05
**Last System Verification**: 2026-01-05 13:00:34 (All tests passing ✅)
**Author**: Claude Sonnet 4.5 (via Claude Code)
