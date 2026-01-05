# Cross-Year Matching Fix

## Problem
When processing 2024 invoices with cross-year matching enabled (loading both 2024 and 2025 SIE files), voucher **A49** (2024-10-14, payment to Dahl for 1,906 SEK) was incorrectly excluded and not matched with its clearing voucher **A53** (2024-10-15).

### Root Cause
The issue was caused by a **voucher ID collision** between different years:
- **2024-A53**: Payment to Dahl (dated 2024-10-15) - legitimate clearing voucher
- **2025-A53**: VAT refund from Skatteverket (dated 2025-02-03) - part of a correction pair with A55

When both years' data were loaded for cross-year matching, the correction detection logic found that 2025-A53 was marked as corrected, and excluded ALL vouchers with ID "A53" from both years, including the legitimate 2024-A53 payment.

## Solution
Modified the correction voucher detection to be **year-aware**:

### Code Changes

#### 1. Updated `identify_correction_vouchers()` in [src/matcher.py](src/matcher.py:127)

Added `target_year` parameter to filter corrections by year:

```python
def identify_correction_vouchers(self, vouchers: List[Voucher], target_year: int = None) -> set[str]:
    """
    Args:
        vouchers: List of all vouchers to search
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

#### 2. Updated `match_all()` in [src/matcher.py](src/matcher.py:371)

Pass the `receipt_year` to correction detection:

```python
# Step 0: Identify and exclude correction vouchers (only from the target year to avoid cross-year ID collisions)
exclude_ids = self.identify_correction_vouchers(vouchers, target_year=receipt_year)
```

### 3. Created Verification Tests in [tests/test_2024_corrections.py](tests/test_2024_corrections.py)

Added automated tests to ensure the known 2024 correction pairs remain constant:

```python
# Expected correction pairs for 2024 (will not change)
EXPECTED_2024_CORRECTIONS = {
    'A120', 'A131',  # Nibe payment (has 2440 + 1930)
    'A143', 'A170',  # Bauhaus invoice (has 2440 only)
    'A168', 'A169',  # Interest income (no 2440 or 1930)
}
```

These tests will fail if code changes accidentally alter the correction detection logic.

## Results

### Before Fix
- **A49** status: "Missing clearing"
- **Outstanding invoices**: 7 (including A49)
- **2025-A53** incorrectly excluded **2024-A53**

### After Fix
- **A49** → **A53**: Correctly matched ✓
- **A49** status: "OK"
- **Comment**: "Clearing found 1 day after receipt"
- **Outstanding invoices**: 6 (A133, A136, A137, A138, A149, A163)

### Verification
```bash
# Run verification tests
python -m pytest tests/test_2024_corrections.py -v

# Results
✓ test_2024_correction_vouchers_unchanged PASSED
✓ test_2024_correction_pairs_details PASSED
```

### Summary Report (2024)
```
Account 2440 - Bookkeeping Totals
  Kredit (Receipts): 36,225.10 SEK
  Debet (Clearings): 33,896.10 SEK
  Outstanding Balance: 2,329.00 SEK

Validation Summary (After Excluding Corrections)
  Total Invoice Cases: 43
  - Paid (OK): 37
  - Unpaid (Missing clearing): 6
  - Needs Review: 0
```

All numbers match the bookkeeping system exactly ✓

## Key Principle

**Correction vouchers can only occur within the same year.**

When processing year X:
- Only exclude correction pairs where BOTH vouchers are from year X
- Load vouchers from year X+1 for cross-year clearing detection, but don't apply their corrections to year X
- This prevents voucher ID collisions between different years (e.g., A53 appears in both 2024 and 2025)

## Testing

Run the verification test after any code changes:
```bash
python -m pytest tests/test_2024_corrections.py
```

This ensures the known 2024 correction pairs (A120/A131, A143/A170, A168/A169) remain correctly detected.
