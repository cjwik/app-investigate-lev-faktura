# Invoice Matching Rules - Complete Reference

This document defines the exact rules the system uses to validate and match supplier invoices.

---

## 1. Receipt Voucher (Invoice Received)

### Standardized Title Format
```
Leverantörsfaktura - Mottagen - [Supplier] - [Invoice#]
```

**Example:**
```
Leverantörsfaktura - Mottagen - Centro - 3677881
```

### Required Account Structure

| Account | Name | Type | Amount | Required |
|---------|------|------|--------|----------|
| **2440** | Leverantörsskulder (Accounts Payable) | **Kredit** | **Negative** | ✅ YES |
| 4000-4999 | Expense accounts | Debet | Positive | Optional |
| 2641 | VAT | Debet | Positive | Optional |
| **1930** | Bank account | - | - | ❌ NO (if present, it's a payment) |

### Accounting Logic

```
2440 Kredit (negative) = Debt INCREASES
Example: -1,420 SEK means we OWE supplier 1,420 SEK

#VER A30 20250121
  {
    #TRANS 2440 {} -1420.00    ← NEGATIVE (Kredit) = Receipt
    #TRANS 4000 {} 1136.00      ← Expense
    #TRANS 2641 {} 284.00       ← VAT
  }
```

### Validation Rules (Code: matcher.py lines 232-240)

```python
# Receipt identification:
if trans_2440.amount < 0:  # ← NEGATIVE = Kredit = Receipt
    receipt = ReceiptEvent(
        voucher=voucher,
        amount_2440=trans_2440.amount,  # e.g., -1420.00
        trans_2440=trans_2440,
        is_credit_note=False
    )
```

✅ **Valid Receipt Checks:**
1. Title: "Leverantörsfaktura - Mottagen - [Supplier] - [Invoice#]"
2. Account 2440 exists
3. Amount on 2440 is **NEGATIVE** (Kredit)
4. NO account 1930 (otherwise it's a payment, not receipt)
5. Supplier extracted from field 3
6. Invoice number extracted from field 4

---

## 2. Payment Voucher (Invoice Paid)

### Standardized Title Format
```
Leverantörsfaktura - Betalat - [Supplier] - [Invoice#] [optional info]
```

**Example:**
```
Leverantörsfaktura - Betalat - Centro - 3677881
Leverantörsfaktura - Betalat - Ahsell - 4962010809 (korrigerad med verifikation A532)
```

### Required Account Structure

| Account | Name | Type | Amount | Required |
|---------|------|------|--------|----------|
| **2440** | Leverantörsskulder (Accounts Payable) | **Debet** | **Positive** | ✅ YES |
| **1930** | Företagskonto (Bank account) | **Kredit** | **Negative** | ✅ YES |

**BOTH accounts MUST exist in the same voucher**

### Accounting Logic

```
2440 Debet (positive) = Debt DECREASES (we're paying it off)
1930 Kredit (negative) = Money LEAVES bank account

Example: Paying 1,420 SEK invoice

#VER A71 20250210
  {
    #TRANS 2440 {} 1420.00     ← POSITIVE (Debet) = Debt decreases
    #TRANS 1930 {} -1420.00    ← NEGATIVE (Kredit) = Money leaves bank
  }

Amounts MUST match: abs(2440) = abs(1930)
```

### Validation Rules (Code: matcher.py lines 272-293)

```python
# Clearing identification:
# Must have BOTH 2440 and 1930
if not (voucher.has_account("2440") and voucher.has_account("1930")):
    continue  # ← Not a valid clearing

for trans_2440 in trans_2440_list:
    for trans_1930 in trans_1930_list:
        clearing = ClearingEvent(
            voucher=voucher,
            amount_2440=trans_2440.amount,   # e.g., +1420.00 (Debet)
            amount_1930=trans_1930.amount,   # e.g., -1420.00 (Kredit)
            trans_2440=trans_2440,
            trans_1930=trans_1930
        )
```

✅ **Valid Payment Checks:**
1. Title: "Leverantörsfaktura - Betalat - [Supplier] - [Invoice#]"
2. Account 2440 exists with **POSITIVE** amount (Debet)
3. Account 1930 exists with **NEGATIVE** amount (Kredit)
4. BOTH accounts in same voucher
5. abs(2440) = abs(1930) (amounts match)
6. Supplier extracted from field 3
7. Invoice number extracted from field 4

---

## 3. Matching Receipt to Payment

When the system matches a receipt voucher to its payment voucher, it validates:

### Priority Sorting (Code: matcher.py lines 375-379)

```python
# Sort candidates by (highest priority first):
# 1. Both supplier AND invoice# match (both_match=True)
# 2. Invoice# match only (invoice_match=True)
# 3. Days difference (closest date first)
candidates_with_info.sort(key=lambda x: (not x[4], not x[2], x[1]))
```

**Matching Priority:**
1. 🥇 **Full Match**: Supplier AND Invoice# both match
2. 🥈 **Invoice# Match**: Invoice# matches, supplier differs
3. 🥉 **Date Proximity**: Closest payment date after receipt

### Required Conditions (ALL must be true)

| Condition | Rule | Code Location |
|-----------|------|---------------|
| **Amount Match** | abs(receipt.2440) = abs(payment.2440) | matcher.py:327-330 |
| **Date Sequence** | Payment date ≥ Receipt date | matcher.py:336-339 |
| **Not Used** | Each payment can only match ONE receipt | matcher.py:345-349 |
| **Date Window** | Payment within max_days (default: 120) | matcher.py:374-377 |

### Match Quality Indicators (Code: matcher.py lines 393-409)

```python
if both_match:
    comment += " ✓ FULL MATCH (supplier + invoice#)"

elif invoice_match and not supplier_match:
    comment += " ⚠ WARNING: Invoice# matches but SUPPLIER MISMATCH"
    comment += f" (Receipt: {receipt_sup} vs Clearing: {clearing_sup})"
    comment += " - CHECK SIE FILE"

elif supplier_match and not invoice_match:
    comment += " ⚠ WARNING: Supplier matches but INVOICE# MISMATCH"
    comment += f" (Receipt: {receipt_inv} vs Clearing: {clearing_inv})"
    comment += " - CHECK SIE FILE"

elif not invoice_match and not supplier_match:
    comment += " ⚠ WARNING: NO MATCH - Possible old format or needs SIE file correction"
```

### Report Indicators Explained

| Indicator | Meaning | Action Required |
|-----------|---------|-----------------|
| ✓ FULL MATCH (supplier + invoice#) | Perfect match, SIE file correctly formatted | None - all good ✅ |
| ⚠ SUPPLIER MISMATCH | Invoice# correct but supplier name differs | Fix supplier field in SIE file |
| ⚠ INVOICE# MISMATCH | Supplier correct but invoice# differs | Fix invoice# field in SIE file |
| ⚠ NO MATCH | Neither matches, likely old format | Update to standardized format |

---

## 4. Special Cases

### 4.1 Same-Voucher Payment

**Scenario:** Receipt and payment in the SAME voucher (immediate payment)

**Standardized Title Format:**
```
Leverantörsfaktura - MottagenBetalat - [Supplier] - [Invoice#]
```

**Example:**
```
Leverantörsfaktura - MottagenBetalat - Ahsell - 7058996807
```

**Account Structure:**
```
#VER A83 20241015
  {
    #TRANS 2440 {} -239.00    ← Receipt (Kredit)
    #TRANS 4000 {} 191.00     ← Expense
    #TRANS 2641 {} 48.00      ← VAT
    #TRANS 2440 {} 239.00     ← Clearing (Debet)
    #TRANS 1930 {} -239.00    ← Bank payment (Kredit)
  }
```

**System Behavior:**
- Creates BOTH a receipt event (2440 Kredit) AND a clearing event (2440 Debet + 1930 Kredit)
- Matches them together (same voucher)
- Status: "Receipt and clearing in same voucher"
- Should use "MottagenBetalat" in title to indicate combined receipt+payment

**Code:** matcher.py lines 437-440

---

### 4.2 Self-Canceling Vouchers (EXCLUDED)

**Scenario:** Invoice + Credit note in same voucher, NO payment

**Account Structure:**
```
#VER A111 20250228
  {
    #TRANS 2440 {} -2636.00   ← Invoice (Kredit)
    #TRANS 4000 {} 2109.00    ← Expense
    #TRANS 2641 {} 527.00     ← VAT
    #TRANS 2440 {} 2636.00    ← Credit note (Debet, NO 1930)
    #TRANS 4000 {} -2109.00   ← Reverse expense
    #TRANS 2641 {} -527.00    ← Reverse VAT
  }
```

**Validation:** Sum of 2440 ≈ 0 AND no 1930 account

**System Behavior:**
- Detects: `sum(2440) ≈ 0` and `no account 1930`
- **EXCLUDES from matching** (not a real invoice to track)
- Logged as: "Excluding self-canceling voucher without payment"

**Code:** matcher.py lines 217-225

---

### 4.3 Correction Vouchers (EXCLUDED)

**Scenario:** Accounting corrections that cancel each other out

**Title Keywords:**
- "korrigerad" = This voucher was corrected by another
- "Korrigering" = This voucher corrects another

**Examples:**
```
A5: Leverantörsfaktura - Betalat - Ahsell - 4962010809 (korrigerad med verifikation A532)
A532: Korrigering av ver.nr. A5
```

**System Behavior:**
- Detects correction keywords + voucher reference (e.g., "A532")
- **EXCLUDES BOTH vouchers** (A5 and A532) from matching
- Year-aware: Only excludes if both vouchers from same year (prevents cross-year ID collisions)

**Code:** matcher.py lines 127-190

---

### 4.4 Credit Notes (Credit Invoices)

**Scenario:** Refund or credit from supplier

**Standardized Title Format:**
```
Leverantörskreditfaktura - Mottagen - [Supplier] - [Invoice#]
```

**Example:**
```
Leverantörskreditfaktura - Mottagen - Dahl - 125195371
```

**Account Structure:**
```
#VER A186 20250415
  {
    #TRANS 2440 {} 500.00     ← POSITIVE Debet (but NO 1930)
    #TRANS 4000 {} -400.00    ← Reverse expense
    #TRANS 2641 {} -100.00    ← Reverse VAT
  }
```

**Key Difference:** 2440 Debet (positive) but **NO 1930** account

**Validation:**
- First word: "Leverantörskreditfaktura" (instead of "Leverantörsfaktura")
- Second word: "Mottagen" (receipt of credit)
- Third word: Supplier name
- Fourth word: Credit invoice number
- Account 2440: Debet (positive) - reduces our debt
- NO account 1930 (no bank transaction at receipt time)

**System Behavior:**
- Identified as **credit note receipt** (not a payment)
- Matched with clearing like normal invoices
- Supplier and invoice number extracted using same rules as regular invoices
- Flag: `is_credit_note=True`

**Clearing Format:**
When the credit is applied/cleared, it should follow:
```
Leverantörskreditfaktura - Betalat - [Supplier] - [Invoice#]
```
With account structure:
- 2440 Kredit (negative) - reverses the credit
- 1930 Debet (positive) - money comes into bank OR applied against another invoice

**Code:** matcher.py lines 241-249

---

## 5. Complete Validation Checklist

### For Receipt Vouchers

- [ ] Title format: `Leverantörsfaktura - Mottagen - [Supplier] - [Invoice#]`
- [ ] Account 2440 exists
- [ ] Account 2440 amount is **NEGATIVE** (Kredit)
- [ ] Account 1930 does **NOT** exist
- [ ] Supplier name in field 3
- [ ] Invoice number in field 4 (digits only, before any parentheses)
- [ ] Not a self-canceling voucher (sum of 2440 ≠ 0)
- [ ] Not a correction voucher (no "korrigerad" or "Korrigering" in title)

### For Payment Vouchers

- [ ] Title format: `Leverantörsfaktura - Betalat - [Supplier] - [Invoice#]`
- [ ] Account 2440 exists
- [ ] Account 2440 amount is **POSITIVE** (Debet)
- [ ] Account 1930 exists
- [ ] Account 1930 amount is **NEGATIVE** (Kredit)
- [ ] abs(2440) = abs(1930)
- [ ] Supplier name in field 3 (must match receipt)
- [ ] Invoice number in field 4 (must match receipt)
- [ ] Not a correction voucher (or correction info in parentheses at end)

### For Receipt → Payment Matching

- [ ] Amounts match: abs(receipt.2440) = abs(payment.2440)
- [ ] Payment date ≥ Receipt date
- [ ] Payment not already used by another receipt
- [ ] Payment within date window (≤ max_days)
- [ ] Supplier names match (case-insensitive)
- [ ] Invoice numbers match (exact)

---

## 6. Quick Reference Table

| Voucher Type | 2440 | 1930 | Title |
|--------------|------|------|-------|
| **Receipt (Invoice)** | Kredit (negative) | NONE | Leverantörsfaktura - Mottagen - [Supplier] - [Invoice#] |
| **Payment (Clearing)** | Debet (positive) | Kredit (negative) | Leverantörsfaktura - Betalat - [Supplier] - [Invoice#] |
| **Same-Voucher Payment** | Both Kredit + Debet | Kredit (negative) | Leverantörsfaktura - MottagenBetalat - [Supplier] - [Invoice#] |
| **Credit Invoice Receipt** | Debet (positive) | NONE | Leverantörskreditfaktura - Mottagen - [Supplier] - [Invoice#] |
| **Credit Invoice Clearing** | Kredit (negative) | Debet (positive) | Leverantörskreditfaktura - Betalat - [Supplier] - [Invoice#] |
| **Self-Canceling** | Sum ≈ 0 | NONE | (any) - EXCLUDED |
| **Correction** | (any) | (any) | Contains "korrigerad" or "Korrigering" - EXCLUDED |

---

## 7. Example: Perfect Match Flow

### Step 1: Receipt Voucher (A129)
```
Title: Leverantörsfaktura - Mottagen - Centro - 3677881
Date: 2025-03-08

#VER A129 20250308
  {
    #TRANS 2440 {} -163.00    ← Receipt (Kredit) ✓
    #TRANS 4000 {} 130.40     ← Expense
    #TRANS 2641 {} 32.60      ← VAT
  }
```

**Extracted:**
- Supplier: "Centro"
- Invoice#: "3677881"
- Amount: -163.00 SEK

---

### Step 2: Payment Voucher (A137)
```
Title: Leverantörsfaktura - Betalat - Centro - 3677881
Date: 2025-03-11

#VER A137 20250311
  {
    #TRANS 2440 {} 163.00     ← Clearing (Debet) ✓
    #TRANS 1930 {} -163.00    ← Bank (Kredit) ✓
  }
```

**Extracted:**
- Supplier: "Centro"
- Invoice#: "3677881"
- Amount: +163.00 SEK

---

### Step 3: Matching Result

✅ **All Checks Pass:**
- Amount match: abs(-163.00) = abs(+163.00) ✓
- Date sequence: 2025-03-11 ≥ 2025-03-08 ✓
- Supplier match: "Centro" = "Centro" ✓
- Invoice# match: "3677881" = "3677881" ✓
- Not used: First time matching this payment ✓
- Within window: 3 days (≤ 120 days) ✓

**Report Line:**
```csv
NEJ,A129,2025-03-08,"-163,00",Centro,"Leverantörsfaktura - Mottagen - Centro - 3677881",A137,2025-03-11,"163,00","-163,00",,,,,SEK,,OK,100,Clearing found 3 days after receipt ✓ FULL MATCH (supplier + invoice#)
```

---

## 8. Example: Mismatch Warning

### Receipt Voucher (A42)
```
Title: Leverantörsfaktura - Mottagen - Elektroskandia - 31641715
Supplier: "Elektroskandia"
Invoice#: "31641715"
```

### Payment Voucher (A66) - OLD FORMAT
```
Title: Leverantörsfaktura - 2025-02-10 - Betalat - Elektroskandia - 31641715
Supplier: ? (can't extract, wrong format)
Invoice#: "31641715"
```

**Matching Result:**
```csv
⚠ WARNING: Invoice# matches but SUPPLIER MISMATCH (Receipt: Elektroskandia vs Clearing: ?) - CHECK SIE FILE
```

**Action:** Update A66 title to standardized format:
```
Leverantörsfaktura - Betalat - Elektroskandia - 31641715
```

---

**Document Version:** 1.0
**Created:** 2026-01-05
**Author:** Claude Sonnet 4.5 (via Claude Code)
