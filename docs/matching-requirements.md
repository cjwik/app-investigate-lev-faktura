# Matching Requirements - Supplier Invoice Validation

## Goal

Validate supplier invoice bookkeeping using SIE as the master.

Each supplier invoice or supplier credit note must have:
1. A **receipt posting** on account 2440 (Leverantörsskulder), and
2. A **clearing posting** on account 2440 linked to bank account 1930

Sometimes both steps exist in the same voucher. That is OK.

**No partial payments.**

---

## Inputs

1. One or more SIE files
2. One folder tree with all bookkeeping PDFs (mixed documents)

---

## Scope

- **Only vouchers that include account 2440 are in scope**
- Ignore everything else
- Create one "invoice case" per 2440 receipt line:
  - If one voucher has multiple 2440 lines, treat it as multiple invoices
  - Each case must end up as one row in the final report, even if PDF match fails

---

## SIE Format and Sign Convention

SIE rows use one signed amount:
- **Positive = Debet**
- **Negative = Kredit**

---

## What Counts as Receipt vs Clearing

### Receipt Event (Creates or Reduces Accounts Payable)

- **Normal supplier invoice receipt**: 2440 Kredit (negative amount on 2440 row)
  - Typically paired with expense account (often 4000 series, but can vary) as Debet
  - Example: 2440 Kredit -500.00, 4000 Debet +500.00
- **Supplier credit note receipt**: 2440 Debet (positive amount on 2440 row) **WITHOUT** 1930 in the voucher
  - Key differentiator: NO account 1930 present
  - Example: 2440 Debet +200.00, 4000 Kredit -200.00

### Clearing Event (Settles AP Through Bank 1930)

**Key: Presence of account 1930 in the same voucher**

- **Payment of invoice**: 2440 Debet (positive) + 1930 Kredit (negative) in the same voucher
  - Example: 2440 Debet +500.00, 1930 Kredit -500.00
- **Refund for credit note**: 2440 Kredit (negative) + 1930 Debet (positive) in the same voucher
  - Example: 2440 Kredit -200.00, 1930 Debet +200.00

### Clarification: Receipt vs Clearing Logic

```
If voucher has 2440 line:
  If 2440 is Kredit (negative):
    → Receipt (normal invoice)
  If 2440 is Debet (positive):
    If voucher also has 1930:
      → Clearing (payment/refund)
    Else:
      → Receipt (credit note)
```

---

## Hard Matching Rules on Account 2440

1. **2440 must match exactly**
2. **Receipt 2440 absolute amount must equal clearing 2440 absolute amount**
3. **No differences allowed on 2440**
4. If mismatch, set Status = "Needs review" and explain in Comment
5. **Ignore rounding lines like account 3740** for this rule

---

## Payment Date Window

1. First search for clearing voucher **within 1–40 days after receipt voucher date**
2. If not found, expand search gradually up to a **configurable max (default 120 days)**
3. If found outside 40 days:
   - Mark "OK" or "Needs review" based on preference
   - Write "Late clearing" in Comment with the day count

---

## PDF Handling

**PDFs are not the source of truth for scope. SIE is.**

The app should still try to attach one PDF to each invoice case to extract:
- PDF Supplier
- Invoice number
- Invoice date
- Total amount (signed for credit note)
- Currency
- PDF filename

### PDF Matching Strategy

Invoice number is always in the PDF. Voucher text in SIE often lacks invoice number.

PDF matching must work using:
1. **Exact 2440 amount match** (primary)
2. **Date proximity** (PDF invoice date near receipt voucher date)
3. **Supplier fuzzy match** (optional, low weight)
4. **Filename hints** (optional)

**If PDF match is missing or ambiguous, still output the row. Status reflects this.**

---

## Grouped Vouchers

Handle these cases:

1. **Receipt voucher contains multiple 2440 lines**: Treat as multiple invoices
2. **Clearing voucher contains multiple 2440 lines**: Match per line
3. **If a clearing voucher has one summed 2440 line** that appears to clear multiple invoices:
   - Mark "Ambiguous" or "Needs review"
   - Explain in Comment
4. **If two invoices share the same amount** and both fit the same clearing candidate:
   - Mark "Ambiguous"
   - List candidates in Comment

---

## Same Voucher Case

If one voucher contains both:
- A 2440 receipt line for the invoice, AND
- A clearing pattern against 1930 (payment or refund)

Then:
- Mark "OK"
- Add Comment: "Receipt and clearing in same voucher"

---

## Output

Export CSV or XLSX.

**One row per invoice case (per 2440 receipt line)**, with columns:

### SIE Receipt
- Receipt Voucher Id
- Receipt Voucher Date
- Receipt 2440 Amount (signed)
- SIE Supplier (best-effort from voucher/row text)
- SIE Text (voucher + row text)

### SIE Clearing
- Clearing Voucher Id
- Clearing Voucher Date
- Clearing 2440 Amount (signed)
- Clearing 1930 Amount (signed)

### PDF (if found)
- PDF Supplier
- Invoice No
- Invoice Date
- PDF Total Amount (signed)
- Currency
- PDF Filename

### Validation
- **Status**: OK, Missing clearing, Missing PDF, Ambiguous, Needs review
- **Match Confidence** (0–100)
- **Comment** (all differences and reasons)

### Additional Output
- Also export an **exceptions file filtered to non-OK** statuses

---

## Determinism and Audit

1. **Log candidates and scores** per invoice case
2. **Persist manual overrides** in JSON:
   - Key: receipt voucher id + receipt 2440 amount
   - Value: chosen PDF file (hash) and chosen clearing voucher id

---

## Acceptance Criteria

For each 2440 receipt line:

1. App produces **one report row**
2. Row is **"OK" only if**:
   - A clearing voucher exists with correct 1930 pattern (payment or refund)
   - 2440 amounts match exactly (absolute value)
   - Clearing date is after receipt date
3. **Missing PDF is allowed** but must be explicit
4. **Missing clearing is the critical error to surface**

---

## Key Insights

- **SIE is the source of truth** for what needs to be validated
- **Account 2440 (Leverantörsskulder)** is the master filter
- **PDFs are supplementary** - used for enrichment (invoice number, supplier name, etc.)
- **Every 2440 receipt line must have a matching clearing voucher** to be marked "OK"
- **Amounts on 2440 must match exactly** between receipt and clearing

---

## Implementation Clarifications (from Q&A)

### Data Loading Strategy
- **Load entire SIE file** with full transaction-level detail into memory
- Work with individual #TRANS lines, not just voucher summaries
- This provides flexibility for analyzing multiple accounts (2440, 1930, etc.)

### PDF Amount Matching
- **Exact match required** on absolute values initially
- Compare: `abs(sie_2440_amount) == abs(pdf_amount)`
- Example: SIE 2440 = -500.00, PDF = "500,00 kr" → Match ✓
- May loosen tolerance later based on OCR accuracy

### Expense Account Variation
- Receipt vouchers typically pair 2440 with expense accounts (4000 series)
- **Expense account can vary** - not always 4000
- The matching logic focuses on 2440 and 1930, ignoring other accounts

---

## Test Cases

### Test Case 1: Perfect Match - A110 → A123 (2024)

**A110 - Receipt (2024-11-05)**
```
#VER A 110 20241105 "Leverantörsfaktura - 2024-11-05 - Dahl - Faktura-123963966"
{
  #TRANS 2440 {} -50.00      ← Receipt (Kredit) - Creates payable
  #TRANS 2641 {} 10.04       ← VAT
  #TRANS 4000 {} 40.14       ← Expense
  #TRANS 3740 {} -0.18       ← Rounding (IGNORE for matching)
}
```

**A123 - Clearing (2024-11-06)**
```
#VER A 123 20241106 "LeveransKonto - 2024-11-06 - Dahl - Faktura-123963966"
{
  #TRANS 1930 {} -50.00      ← Bank payment (Kredit)
  #TRANS 2440 {} 50.00       ← Clears payable (Debet)
}
```

**Expected Output Row:**

| Column | Value |
|--------|-------|
| **Receipt Voucher Id** | A110 |
| **Receipt Voucher Date** | 2024-11-05 |
| **Receipt 2440 Amount** | -50.00 |
| **SIE Supplier** | Dahl |
| **SIE Text** | Leverantörsfaktura - 2024-11-05 - Dahl - Faktura-123963966 |
| **Clearing Voucher Id** | A123 |
| **Clearing Voucher Date** | 2024-11-06 |
| **Clearing 2440 Amount** | 50.00 |
| **Clearing 1930 Amount** | -50.00 |
| **PDF Supplier** | (to be matched) |
| **Invoice No** | 123963966 |
| **PDF Invoice Date** | (to be matched) |
| **PDF Total Amount** | (to be matched) |
| **Currency** | SEK |
| **PDF Filename** | (to be matched) |
| **Status** | OK |
| **Match Confidence** | 100 |
| **Comment** | Clearing found 1 day after receipt |

**Validation:**
- ✅ Receipt identified: 2440 Kredit (-50.00) without 1930
- ✅ Clearing identified: 2440 Debet (+50.00) with 1930 Kredit (-50.00)
- ✅ Amounts match exactly: abs(-50.00) == abs(50.00)
- ✅ Clearing date after receipt: 2024-11-06 > 2024-11-05
- ✅ Date difference: 1 day (within 1-40 day window)
- ✅ 1930 pattern present: -50.00 Kredit (payment)
- ✅ Invoice number extracted: 123963966
- ✅ Supplier extracted: Dahl
- ✅ Rounding line (3740) ignored in matching logic

---

### Test Case 2: Single-Word Description - A47 → A50 (2024)

**Issue Found:** VER_PATTERN regex initially required quotes, but single-word descriptions have no quotes in SIE format.

**A47 - Receipt (2024-10-14)**
```
#VER A 47 20241014 Leverantörsfaktura 20241014
{
  #TRANS 2440 {} -261.00     ← Receipt (Kredit) - Creates payable
  #TRANS 2641 {} 52.35       ← VAT
  #TRANS 4000 {} 208.65      ← Expense
}
```
**Note:** Description "Leverantörsfaktura" is a single word → **no quotes** in SIE file

**A50 - Clearing (2024-10-15)**
```
#VER A 50 20241015 "LeveransKonto - Payment"
{
  #TRANS 1930 {} -261.00     ← Bank payment (Kredit)
  #TRANS 2440 {} 261.00      ← Clears payable (Debet)
}
```

**Expected Output Row:**

| Column | Value |
|--------|-------|
| **Receipt Voucher Id** | A47 |
| **Receipt Voucher Date** | 2024-10-14 |
| **Receipt 2440 Amount** | -261.00 |
| **SIE Supplier** | (empty - single word description) |
| **SIE Text** | Leverantörsfaktura 20241014 |
| **Clearing Voucher Id** | A50 |
| **Clearing Voucher Date** | 2024-10-15 |
| **Clearing 2440 Amount** | 261.00 |
| **Clearing 1930 Amount** | -261.00 |
| **Status** | OK |
| **Match Confidence** | 100 |
| **Comment** | Clearing found 1 day after receipt |

**Validation:**
- ✅ VER_PATTERN handles both quoted and unquoted descriptions
- ✅ Pattern: `r'^#VER\s+([A-Za-z0-9]+)\s+([^\s]+)\s+(\d{8})\s+(.*?)(?:\s*\{)?$'`
- ✅ Single-word descriptions (no quotes) parsed correctly
- ✅ Multi-word descriptions (with quotes) still work

**SIE Quoting Pattern:**
- Single-word descriptions: **no quotes** (e.g., `Leverantörsfaktura`)
- Multi-word descriptions: **with quotes** (e.g., `"Leverantörsfaktura - 2024-11-05 - Dahl"`)

---

### Test Case 3: Same-Voucher Payment - A83 (2024)

**Issue Found:** identify_receipts() initially skipped entire voucher if it had account 1930, preventing same-voucher receipt+clearing detection.

**A83 - Receipt AND Clearing in Same Voucher (2024-10-24)**
```
#VER A 83 20241024 "LeveransKonto - 2024-10-24 - Ahsell- Faktura - Kvitto - 4767488200"
{
  #TRANS 1930 {} -148.00     ← Bank payment (Kredit)
  #TRANS 2440 {} 148.00      ← Clearing - reduces payable (Debet)
  #TRANS 2440 {} -148.00     ← Receipt - creates payable (Kredit)
  #TRANS 2641 {} 29.61       ← VAT
  #TRANS 4000 {} 118.39      ← Expense
}
```
**Note:** Voucher has **TWO 2440 lines** - one receipt (Kredit -148.00) and one clearing (Debet +148.00)

**Expected Output Row:**

| Column | Value |
|--------|-------|
| **Receipt Voucher Id** | A83 |
| **Receipt Voucher Date** | 2024-10-24 |
| **Receipt 2440 Amount** | -148.00 |
| **SIE Supplier** | Ahsell |
| **SIE Text** | LeveransKonto - 2024-10-24 - Ahsell- Faktura - Kvitto - 4767488200 |
| **Clearing Voucher Id** | A83 |
| **Clearing Voucher Date** | 2024-10-24 |
| **Clearing 2440 Amount** | 148.00 |
| **Clearing 1930 Amount** | -148.00 |
| **Status** | OK |
| **Match Confidence** | 100 |
| **Comment** | Receipt and clearing in same voucher |

**Validation:**
- ✅ Receipt identified: 2440 Kredit (-148.00) even though voucher has 1930
- ✅ Clearing identified: 2440 Debet (+148.00) with 1930 Kredit (-148.00)
- ✅ Logic processes each 2440 transaction individually
- ✅ Same voucher ID for both receipt and clearing
- ✅ Matched correctly as same-voucher payment

**Fix Applied:**
- Modified `identify_receipts()` to check each 2440 transaction individually
- **OLD:** Skipped entire voucher if it had account 1930
- **NEW:** Process each 2440 line - Kredit (negative) is always receipt, regardless of 1930

**Use Case:**
- Cash purchases paid immediately
- Direct bank payments at point of purchase
- Credit card transactions where expense and payment occur simultaneously