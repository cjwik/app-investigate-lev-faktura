# Iteration 3: Matching Supplier Invoices with Clearings

## Overview

This iteration implements the core matching logic to validate that every supplier invoice (receipt on account 2440) has a corresponding clearing voucher (payment via account 1930).

## Implementation Date

Completed: 2026-01-04

## Components Created

### 1. Transaction-Level SIE Parser (`src/transaction_parser.py`)

**Purpose:** Parse SIE files with full transaction-level detail, extracting individual #TRANS lines with account numbers.

**Key Classes:**
- `Transaction`: Represents a single #TRANS line with account, amount, date, description
- `Voucher`: Represents a complete #VER block with all its transactions
  - Methods: `get_transactions_by_account()`, `has_account()`, `get_total_for_account()`, `is_balanced()`

**Why separate from `sie_parser.py`?**
- `sie_parser.py` extracts voucher-level summaries for general reporting
- `transaction_parser.py` provides transaction-level detail needed for matching logic
- This separation allows both use cases without conflicting requirements

### 2. Matching Engine (`src/matcher.py`)

**Purpose:** Implement the matching logic per requirements in [matching-requirements.md](matching-requirements.md).

**Key Classes:**

#### `ReceiptEvent`
Represents a receipt (invoice or credit note):
- Normal invoice: 2440 Kredit (negative)
- Credit note: 2440 Debet (positive) WITHOUT 1930 in voucher

#### `ClearingEvent`
Represents a clearing (payment or refund):
- Payment: 2440 Debet (positive) + 1930 Kredit (negative)
- Refund: 2440 Kredit (negative) + 1930 Debet (positive)

#### `InvoiceCase`
One row in the final report - represents one invoice with its matched clearing.

#### `InvoiceMatcher`
Main matching engine with methods:
- `identify_receipts()` - Finds all receipt events
- `identify_clearings()` - Finds all clearing events
- `find_clearing_for_receipt()` - Matches one receipt with its clearing
- `match_all()` - Complete matching process

**Matching Logic:**
1. Amount must match exactly (absolute value, tolerance < 0.01)
2. Clearing date must be after receipt date
3. Prefer clearings within 1-40 days
4. Accept clearings up to `max_days` (default 120) with note
5. Handle ambiguity (multiple candidates with same criteria)

### 3. Report Generator (`src/report_generator.py`)

**Purpose:** Generate single CSV report with all required columns and review flag.

**Functions:**
- `generate_combined_report()` - Single report with all invoice cases and review flag
- `generate_both_reports()` - Returns path to generated report

**Output Columns:**

**Review Flag:**
- Behöver granskas: "JA" (needs review) or "NEJ" (OK) - First column for easy filtering

**SIE Receipt:**
- Receipt Voucher Id
- Receipt Voucher Date
- Receipt 2440 Amount (signed, Swedish format with comma)
- SIE Supplier (extracted from description)
- SIE Text (full voucher description)

**SIE Clearing:**
- Clearing Voucher Id
- Clearing Voucher Date
- Clearing 2440 Amount (signed, Swedish format with comma)
- Clearing 1930 Amount (signed, Swedish format with comma)

**PDF (placeholder for future):**
- PDF Supplier, Invoice No, PDF Invoice Date, PDF Total Amount, Currency, PDF Filename

**Validation:**
- Status: "OK", "Missing clearing", "Needs review", etc.
- Match Confidence (0-100)
- Comment (explanations, day count, warnings)

**Usage:** Filter by "Behöver granskas" = "JA" in Excel to see only cases that need review

### 4. CLI Command (`src/main.py`)

**New command:** `match`

```bash
python src/main.py match [--year 2024] [--max-days 120]
```

**Options:**
- `--year`: Process specific year (2024 or 2025), default: both
- `--max-days`: Maximum days to search for clearing (default: 120)

**Workflow:**
1. Parse SIE file with transaction-level parser
2. Run matching engine
3. Generate single combined report with review flag
4. Save to `Data/Output/reports/`
5. User can filter by "Behöver granskas" = "JA" in Excel to see cases needing review

## Test Results

### Test Case: A110 → A123 (2024)

**Input:**
- A110 (Receipt): 2440 Kredit -50.00, dated 2024-11-05, Dahl invoice 123963966
- A123 (Clearing): 2440 Debet +50.00, 1930 Kredit -50.00, dated 2024-11-06

**Expected Output:** (from [matching-requirements.md](matching-requirements.md))
- Status: OK
- Match Confidence: 100
- Comment: "Clearing found 1 day after receipt"

**Actual Output:**
```csv
Receipt Voucher Id: A110
Receipt Voucher Date: 2024-11-05
Receipt 2440 Amount: -50.00
SIE Supplier: Dahl
SIE Text: Leverantörsfaktura - 2024-11-05 - Dahl - Faktura-123963966
Clearing Voucher Id: A123
Clearing Voucher Date: 2024-11-06
Clearing 2440 Amount: 50.00
Clearing 1930 Amount: -50.00
Status: OK
Match Confidence: 100
Comment: Clearing found 1 day after receipt
```

**Result:** ✅ Perfect match - all criteria validated

### Statistics (2024 Data)

**After Correction Voucher Exclusion (2026-01-05):**
- Total verifications: 165
- Correction voucher pairs excluded: **3 pairs (6 vouchers)**: A120/A131, A143/A168, A169/A170
- Invoice cases identified: **43** (after excluding 3 correction receipts)
- Status breakdown:
  - OK: **37** (86.0%)
  - Missing clearing: **6** (14.0%)
- Same-voucher payments: **7 cases** (A38, A39, A40, A83, A89, A94)

**Features Implemented:**
1. **VER_PATTERN regex** - Handles both quoted and unquoted descriptions (fixed A47)
2. **identify_receipts() logic** - Processes each 2440 transaction individually (fixed A83 and same-voucher cases)
3. **Correction voucher detection** - Automatically excludes accounting corrections that cancel each other out (keywords: "korrigerad", "Korrigering")

### Statistics (2025 Data)

- Total verifications: 510
- Invoice cases identified: 113
- Status breakdown:
  - OK: 92 (81.4%)
  - Missing clearing: 21 (18.6%)
- Processing time: ~0.07s

## Correction Voucher Handling

The matcher automatically detects and excludes correction voucher pairs that represent accounting corrections rather than actual supplier invoices.

### Detection Pattern

Correction vouchers are identified by keywords in the description:
- **"korrigerad"** (corrected) - The incorrect voucher that was corrected
- **"Korrigering"** (correction) - The correction voucher that fixes the error

Both vouchers in the pair are excluded from the validation report.

### Example: A120 ↔ A131

**A120** (Incorrect - later corrected):
```
Description: "...Nibe - Faktura - DSTP100041480... (korrigerad med verifikation A131...)"
Transactions:
  #TRANS 1930 {} -5352.00    ← Bank (Kredit)
  #TRANS 2440 {} 5352.00     ← Clears AP (Debet) - but was incorrect
```

**A131** (Correction - reverses A120):
```
Description: "Korrigering av ver.nr. A120, LeveransKonto - 2024-11-06 - Nibe..."
Transactions:
  #TRANS 1930 {} 5352.00     ← Bank (Debet) - reverses payment
  #TRANS 2440 {} -5352.00    ← Creates AP (Kredit) - reverses clearing
```

**Result**: Both A120 and A131 excluded from report - they cancel each other out.

### 2024 Data

3 correction pairs identified and excluded:
- **A120 ↔ A131**: Nibe invoice (5352.00 SEK)
- **A143 ↔ A168**: Unknown (796.10 SEK)
- **A169 ↔ A170**: Unknown (796.10 SEK credit note)

This improved the match rate from 82.6% to 86.0% by removing false negatives.

## Known Limitations

### 1. PDF Matching Not Implemented
All PDF-related columns are currently empty placeholders. PDF matching will be implemented in a future iteration.

### 2. Supplier Extraction is Best-Effort
The `extract_supplier()` method uses heuristics to parse supplier names from voucher descriptions. It works for common patterns but may fail on unusual formats.

**Current logic:**
- Split description by dashes (`-`)
- Filter out: first part (type), numeric-only parts (dates/invoice numbers), very short parts
- Skip parts starting with "Faktura", "Invoice", "Fatura"
- Return first valid candidate

**Known to work for:**
- "Leverantörsfaktura - 2024-11-05 - Dahl - Faktura-123963966" → "Dahl" ✅
- "Leverantörsfaktura - Ahlsell - Faktura - 4836029506" → "Ahlsell" ✅

### 3. Grouped Vouchers with Multiple 2440 Lines
Currently creates one clearing event per 2440 line in clearing voucher. If a clearing voucher has one summed 2440 line clearing multiple invoices, this will be flagged in comments but not automatically resolved.

### 4. Ambiguity Detection
When multiple clearing candidates exist with same criteria (amount + date), the first is chosen with a warning comment. Manual review recommended for these cases.

## Adherence to Requirements

Implemented features from [matching-requirements.md](matching-requirements.md):

### ✅ Implemented
- [x] SIE as source of truth
- [x] Account 2440 as master filter
- [x] Transaction-level parsing
- [x] Receipt identification (2440 Kredit or 2440 Debet without 1930)
- [x] Clearing identification (2440 + 1930 pattern)
- [x] Exact amount matching (absolute value)
- [x] Date window validation (1-40 days optimal, up to configurable max)
- [x] Same voucher case handling
- [x] Full report generation (CSV)
- [x] Exceptions report generation (non-OK only)
- [x] All required output columns
- [x] Status determination (OK, Missing clearing, Needs review)
- [x] Match confidence scoring (0-100)
- [x] Comment generation with explanations

### ⏳ Not Yet Implemented
- [ ] PDF matching by amount and date
- [ ] PDF data extraction (supplier, invoice number, date, amount)
- [ ] Manual override persistence (JSON)
- [ ] Detailed candidate logging
- [ ] Grouped voucher advanced handling (summed clearings)
- [ ] Ambiguity resolution UI/workflow

## Files Modified

- `src/main.py` - Added `cmd_match()` function and CLI parser entry
- `README.md` - Updated status and command documentation

## Files Created

- `src/transaction_parser.py` - Transaction-level SIE parser (219 lines)
- `src/matcher.py` - Matching engine with receipt/clearing logic (271 lines)
- `src/report_generator.py` - CSV report generation (133 lines)
- `docs/iteration-3-matching.md` - This documentation

## Next Steps

Potential improvements for future iterations:

1. **PDF Matching (Iteration 4)**
   - Extract invoice data from OCR-processed PDFs
   - Match PDFs to receipts by absolute amount + date proximity
   - Populate PDF columns in report

2. **Manual Override System**
   - JSON persistence for manual corrections
   - UI/workflow for reviewing ambiguous cases
   - Candidate logging for audit trail

3. **Enhanced Supplier Extraction**
   - Machine learning approach for better supplier name extraction
   - Supplier name normalization (Ahlsell vs Ahsell)
   - Supplier database/lookup

4. **Grouped Voucher Handling**
   - Detect summed clearing vouchers
   - Algorithm to split grouped payments to individual invoices
   - Enhanced ambiguity resolution

5. **Full Pipeline Command**
   - Implement `full` command: OCR → Parse → Match in one step
   - Progress reporting
   - Error recovery

## Lessons Learned

1. **Encoding matters:** SIE files use cp850 (Western European) for Swedish characters (å, ä, ö)
2. **Double-entry bookkeeping:** Must work with signed amounts, not just absolute values
3. **Heuristics vs precision:** Supplier extraction uses heuristics; PDF matching will provide exact invoice numbers
4. **Test cases are essential:** A110 → A123 provided concrete validation of matching logic
5. **Separation of concerns:** Transaction parser separate from voucher-summary parser allows both use cases

## References

- [matching-requirements.md](matching-requirements.md) - Complete matching specifications
- [iteration-2-sie-parser.md](iteration-2-sie-parser.md) - SIE parsing background
- SIE file format documentation (external)
