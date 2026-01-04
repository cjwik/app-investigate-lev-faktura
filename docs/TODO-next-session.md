# TODO: Next Session (2026-01-05)

## Current Status (End of 2026-01-04)

### Completed Today ✅
1. Fixed VER_PATTERN regex to handle both quoted and unquoted descriptions
2. Fixed identify_receipts() to process each 2440 transaction individually (same-voucher payments)
3. Added Test Case 2 (A47 - single-word description) to matching-requirements.md
4. Added Test Case 3 (A83 - same-voucher payment) to matching-requirements.md
5. Updated statistics in iteration-3-matching.md

### Current State
- **Iteration 3 (Matching)**: ✅ Complete and tested
- **2024 Results**: 46 cases identified, 38 OK (82.6%), 8 missing clearing
- **2025 Results**: Not yet re-run with bug fixes

## Tasks for Next Session

### Priority 1: Verify 2025 Data
- [ ] Run `python src/main.py match --year 2025` with bug fixes
- [ ] Compare statistics with previous run (was 113 cases, 92 OK, 21 missing)
- [ ] Verify same-voucher payments are now correctly identified in 2025 data
- [ ] Update iteration-3-matching.md with 2025 statistics

### Priority 2: Review Missing Clearing Cases
- [ ] Open latest 2024 report: `Data/Output/reports/invoice_validation_2024_*.csv`
- [ ] Filter by "Behöver granskas" = "JA" to see 8 missing clearing cases
- [ ] Review each case with user to determine:
  - Are these legitimate unpaid invoices?
  - Are there clearing vouchers we're not detecting?
  - Should we adjust max_days parameter?

### Priority 3: Next Iteration Planning
Based on [iteration-3-matching.md](iteration-3-matching.md) "Next Steps" section:

**Option A: Iteration 4 - PDF Matching**
- Extract invoice data from OCR-processed PDFs
- Match PDFs to receipts by absolute amount + date proximity
- Populate PDF columns in report (supplier, invoice number, date, amount)

**Option B: Manual Override System**
- JSON persistence for manual corrections
- UI/workflow for reviewing ambiguous cases
- Candidate logging for audit trail

**Option C: Full Pipeline Command**
- Implement `full` command: OCR → Parse → Match in one step
- Progress reporting
- Error recovery

**User Decision Needed**: Which iteration to prioritize?

## Files Modified Today
- `src/transaction_parser.py` - VER_PATTERN regex fix (line 25)
- `src/matcher.py` - identify_receipts() logic fix (lines 127-150)
- `docs/matching-requirements.md` - Added Test Case 2 and 3
- `docs/iteration-3-matching.md` - Updated statistics

## Known Issues
None - all bugs found today have been fixed and tested.

## Questions for User
1. Should we review the 8 missing clearing cases in 2024?
2. Which iteration should we start next? (PDF matching, manual overrides, or full pipeline)
3. Are there any specific vouchers in 2025 we should verify?
