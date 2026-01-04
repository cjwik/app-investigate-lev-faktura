# Iteration 2: SIE Parser

**Goal:** Parse SIE files and extract verification entries
**Deliverable:** DataFrame with all verifications from SIE files
**Prerequisites:** Iteration 0 complete (virtual environment ready)

---

## Success Criteria

✅ All verification entries extracted correctly
✅ Dates parsed properly
✅ Amounts calculated correctly (including target_amount for matching)
✅ Swedish characters (å, ä, ö) handled correctly
✅ Export to CSV for manual inspection

---

## Module: src/sie_parser.py

**Purpose:** Parse SIE files and extract verification entries - this is the "source of truth" from the bookkeeping system

⚠️ **IMPORTANT: SIE File Management**
- **DO NOT modify** SIE files in `data/Input/SIE/`
- SIE files are exported from the accounting system (Spiris Bokföring & Fakturering)
- User will provide updated SIE exports when new verifications are added
- The parser reads what exists in the SIE file - preliminary/draft verifications in the accounting system won't appear until exported

### Key Functions

#### `parse_sie_file(filepath)`
- **Encoding:** Try PC8 encodings in order: `cp437` (primary), `cp850`, `latin-1`, `utf-8`
- **State machine parser** to handle multi-line verification blocks
- Parse `#VER` line to extract: series, number, date, description, reg_date
- Parse `#TRANS` lines within `{...}` blocks
- Calculate total amounts for each verification
- Return structured data (pandas DataFrame)

**Parameters:**
```python
filepath: Path to SIE file (e.g., "data/Input/SIE/20240101-20241231.se")
```

**Returns:**
```python
DataFrame with columns:
    - verification_id: "A1", "A2", "A100"
    - series: "A"
    - number: 1, 2, 100
    - trans_date: datetime(2024, 1, 11)
    - description: "2024-01-11 - Utebetal - KFM..."
    - reg_date: datetime(2024, 1, 17)
    - target_amount: 500.00  # For matching!
    - total_amount: 0.00  # Validation only
    - debit_amount: 500.00
    - credit_amount: 500.00
    - transaction_count: 3
```

#### `extract_verification_data(sie_file)`
- Main entry point for extracting all verifications from a SIE file
- Returns DataFrame with all verification entries
- Logs summary statistics

**Returns DataFrame with columns:**
- `verification_id`: Combined series + number (e.g., "A1", "A2", "A100")
- `series`: Letter (A, B, C, etc.)
- `number`: Integer verification number
- `trans_date`: Transaction date (YYYYMMDD → datetime)
- `description`: Verification description text
- `reg_date`: Registration date (YYYYMMDD → datetime)
- `target_amount`: **Maximum absolute value** from transaction amounts (for matching against PDF receipts)
- `total_amount`: Sum of all transaction amounts (validation only - should be 0 for balanced entries)
- `debit_amount`: Sum of positive amounts
- `credit_amount`: Sum of negative amounts (absolute value)
- `transaction_count`: Number of #TRANS entries

---

## ⚠️ CRITICAL: The "Zero Sum Trap" - Why We Need target_amount

In double-entry bookkeeping, every verification MUST sum to zero (balanced entries). If you try to match the `total_amount` (which is always 0.00) against a PDF receipt showing "500.00 kr", it will NEVER match.

### The Problem

```
SIE Verification A100:
  Debit Cost (Account 6090):  400.00
  Debit VAT (Account 2611):   100.00
  Credit Bank (Account 1930): -500.00
  ─────────────────────────────────
  total_amount (sum):         0.00  ← USELESS for matching!
```

### The Solution

Extract the `target_amount` - the actual receipt/invoice amount - by finding the maximum absolute value from all transactions:

```python
# Algorithm: max(abs(amount) for amount in transaction_amounts)
target_amount = max(abs(400.00), abs(100.00), abs(-500.00))
target_amount = 500.00  ← THIS matches the PDF receipt!
```

### Why This Works

- In most business transactions, one side represents the "invoice/receipt amount" (the number on the paper)
- The other transactions are cost allocations (VAT, cost centers, etc.)
- The largest absolute value is typically the total payment/receipt amount
- This is what appears on the PDF voucher and what we need to match

### Example Matching

```
SIE Data:        target_amount = 500.00
PDF Receipt:     "Totalt: 500,00 kr"
Match:           500.00 == 500.00 ✓ SUCCESS!
```

### Validation

- Keep `total_amount` for validation (must be 0.00 for balanced entries)
- Use `target_amount` for matching against PDF receipts
- If `total_amount` is NOT 0.00, log warning (unbalanced entry - data error)

---

## Parsing Algorithm (State Machine)

### States

- **OUTSIDE:** Not inside a verification block
- **IN_VER_BLOCK:** Inside `{...}` processing transactions

### Algorithm Steps

```
1. Read file with PC8 encoding (cp437 primary, cp850 fallback)
2. Start in OUTSIDE state
3. When line starts with "#VER":
   - Extract: series, number, date, description, reg_date (using regex)
   - Store VER data temporarily
   - Stay in OUTSIDE state (VER line itself is outside block)
4. When line is "{":
   - Enter IN_VER_BLOCK state
   - Initialize transaction accumulator for this verification
5. While IN_VER_BLOCK state:
   - When line starts with "#TRANS":
     - Parse: account, amount, date, description
     - Accumulate amounts: total_amount, debit_amount, credit_amount
     - Track max absolute value for target_amount calculation
     - Count transaction
   - When line is "}":
     - Calculate target_amount = max(abs(all_transaction_amounts))
     - Validate total_amount ≈ 0.00 (balanced entry check)
     - Save complete verification with all accumulated data
     - Return to OUTSIDE state
     - Reset accumulator
6. Repeat until end of file

CRITICAL: #TRANS lines ONLY belong to the current #VER block
         The {} scope determines which transactions belong to which verification
```

### Example Processing

```
#VER A 2 20240111 "Payment" 20240117    ← Parse VER, store data
{                                        ← Enter block
#TRANS 6090 {} 300.00 20240111 "..."   ← Parse TRANS, add to VER A2
#TRANS 1930 {} -300.00 20240111 "..."  ← Parse TRANS, add to VER A2
}                                        ← Exit block, calculate:
                                           total_amount = 300.00 + (-300.00) = 0.00 ✓
                                           target_amount = max(abs(300), abs(-300)) = 300.00
                                           Save VER A2 complete

#VER A 3 20240115 "Invoice" 20240117    ← New VER, store data
{                                        ← Enter block
#TRANS 1510 {} 500.00 20240115 "..."   ← Parse TRANS, add to VER A3
#TRANS 2611 {} 125.00 20240115 "..."   ← Parse TRANS, add to VER A3 (VAT)
#TRANS 1930 {} -625.00 20240115 "..."  ← Parse TRANS, add to VER A3
}                                        ← Exit block, calculate:
                                           total_amount = 500 + 125 + (-625) = 0.00 ✓
                                           target_amount = max(abs(500), abs(125), abs(-625)) = 625.00
                                           Save VER A3 complete
```

---

## Implementation Details

### Regular Expressions

**VER pattern:**
```python
VER_PATTERN = r'^#VER\s+([A-Z])\s+(\d+)\s+(\d{8})\s+"(.+?)"\s+(\d{8})'
```

**Matches:**
- Group 1: Series letter (A, B, C, etc.)
- Group 2: Verification number
- Group 3: Transaction date (YYYYMMDD)
- Group 4: Description (quoted string)
- Group 5: Registration date (YYYYMMDD)

**TRANS pattern:**
```python
TRANS_PATTERN = r'^#TRANS\s+(\d+)\s+\{\}\s+([-]?\d+\.?\d*)\s+(\d{8})\s+"(.+?)"'
```

**Matches:**
- Group 1: Account number
- Group 2: Amount (signed decimal)
- Group 3: Date (YYYYMMDD)
- Group 4: Description (quoted string)

### Encoding Detection (CRITICAL)

**Encoding priority:**
1. **cp437** (IBM PC Code Page 437 - original PC8 format) ⚠️ TRY THIS FIRST
2. **cp850** (IBM Code Page 850 - Western Europe variant)
3. **latin-1** (ISO 8859-1)
4. **utf-8** (last resort)

**Why critical:**
- Standard utf-8 will **CRASH** on Swedish characters (Ö, Å, Ä) in PC8 format
- Must check `#FORMAT PC8` header in file
- If all encodings fail, log error with filename and raw bytes sample

**Implementation:**
```python
def try_encodings(filepath):
    """Try multiple encodings in order until one works."""
    encodings = ['cp437', 'cp850', 'latin-1', 'utf-8']
    for encoding in encodings:
        try:
            with open(filepath, 'r', encoding=encoding) as f:
                content = f.read()
                # Verify Swedish characters render correctly
                if 'å' in content or 'ä' in content or 'ö' in content:
                    logger.info(f"Successfully read with encoding: {encoding}")
                    return content, encoding
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Could not decode {filepath} with any encoding")
```

### Date Parsing

**SIE dates are in YYYYMMDD format:**
```python
from datetime import datetime

def parse_sie_date(date_str):
    """
    Parse SIE date string to datetime.

    Args:
        date_str: "20240111" (YYYYMMDD)

    Returns:
        datetime(2024, 1, 11)
    """
    return datetime.strptime(date_str, '%Y%m%d')
```

### Amount Handling

**Amounts in SIE use period as decimal separator:**
```python
amount_str = "300.00"   # Debit
amount_str = "-300.00"  # Credit

amount = float(amount_str)  # Direct conversion works
```

**Calculate target_amount:**
```python
transaction_amounts = [400.00, 100.00, -500.00]
target_amount = max(abs(amt) for amt in transaction_amounts)
# Result: 500.00
```

---

## Output Files (Iteration 2)

### CSV Export

**File:** `data/Output/SIE/sie_data_{timestamp}.csv`

**Columns:**
```csv
verification_id,series,number,trans_date,description,reg_date,target_amount,total_amount,debit_amount,credit_amount,transaction_count
A1,A,1,2024-08-06,"Aktiekapital insättning",2024-08-06,50000.00,0.00,50000.00,50000.00,2
A2,A,2,2024-01-11,"Utebetal - KFM",2024-01-17,300.00,0.00,300.00,300.00,2
A100,A,100,2024-11-05,"Ahsell - Faktura",2024-11-25,625.00,0.00,625.00,625.00,3
```

### Summary Report

**File:** `data/Output/SIE/sie_summary_{timestamp}.txt`

**Content:**
```
SIE Parsing Summary
Generated: 2026-01-04 16:00:00

=== FILE: 20240101-20241231.se ===
Encoding: cp437 (PC8)
Total verifications: 150
Date range: 2024-01-11 to 2024-12-28

=== VALIDATION ===
Balanced entries: 150/150 (100%)
Unbalanced entries: 0
Swedish characters: ✓ Found (å, ä, ö)

=== AMOUNTS ===
Min target_amount: 50.00 kr
Max target_amount: 50,000.00 kr
Average target_amount: 1,234.56 kr

=== SERIES ===
Series A: 150 verifications

=== SAMPLE ENTRIES ===
A1: 2024-08-06, target=50000.00, desc="Aktiekapital insättning"
A2: 2024-01-11, target=300.00, desc="Utebetal - KFM"
A100: 2024-11-05, target=625.00, desc="Ahsell - Faktura"
```

---

## Testing Strategy

### Unit Tests

**Test 1: Single verification parsing**
```python
test_sie = """
#VER A 1 20240101 "Test" 20240101
{
#TRANS 1930 {} 100.00 20240101 "Debit"
#TRANS 2440 {} -100.00 20240101 "Credit"
}
"""
result = parse_sie_file(test_sie)
assert result['target_amount'][0] == 100.00
assert result['total_amount'][0] == 0.00
```

**Test 2: Encoding detection**
```python
# Test with Swedish characters
test_sie_swedish = """
#VER A 1 20240101 "Köp från leverantör" 20240101
"""
# Should work with cp437/cp850
```

**Test 3: Zero sum trap**
```python
# Verify target_amount is NOT zero
result = parse_sie_file(actual_sie_file)
assert all(result['total_amount'] == 0.00)  # All balanced
assert all(result['target_amount'] > 0.00)  # All have target amounts
```

### Integration Test

```bash
python src/main.py parse --year 2024
```

**Expected output:**
- CSV file created in `data/Output/SIE/`
- Summary report with statistics
- Log file showing all verifications processed

---

## CLI Commands (main.py)

### Available Commands for Iteration 2

```bash
# Parse 2024 SIE file
python src/main.py parse --year 2024

# Parse 2025 SIE file
python src/main.py parse --year 2025

# Parse both years
python src/main.py parse
```

---

## Success Criteria (Final Checklist)

✅ SIE files parsed successfully with cp437 encoding
✅ All verification entries extracted
✅ target_amount calculated correctly (NOT zero)
✅ total_amount validated (should be 0.00 for all entries)
✅ Swedish characters (å, ä, ö) rendered correctly
✅ Dates parsed correctly
✅ CSV export created
✅ Summary report generated
✅ Unbalanced entries logged as warnings

**Time Estimate:** ~1 hour

---

## Next Step

➡️ **Iteration 3:** Matching ([iteration-3-matching.md](iteration-3-matching.md))

## Reference

📖 **Official SIE Specification:**
   - [SIE File Format Version 4B (PDF)](https://sie.se/wp-content/uploads/2020/05/SIE_filformat_ver_4B_080930.pdf)

📖 **Technical Reference:** See [TECHNICAL_REFERENCE.md](TECHNICAL_REFERENCE.md) for:
- Complete SIE file format specification
- Encoding details
- Regular expressions
- Performance considerations
