# Technical Reference - SIE Format and Swedish Number Handling

This document contains technical specifications and reference materials used across all iterations.

## SIE File Format Analysis (VERIFIED)

### SIE Format References
Official documentation for the SIE (Standard Import Export) format:
- **Official SIE Website:** https://sie.se/format/
- **SIE Format Specification (PDF):** https://sie.se/wp-content/uploads/2020/05/SIE_filformat_ver_4B_080930.pdf
  - Version: 4B (2008-09-30)
  - Complete technical specification for SIE Type 4 format

### File Header (Confirmed from actual files)
```
#FLAGGA 0
#PROGRAM "Spiris Bokföring & Fakturering" 7.5.0.0
#FORMAT PC8                          ← Character encoding
#GEN 20260104 "Carl-Johan Wik"       ← Generation date and user
#SIETYP 4                             ← SIE Type 4 (Full transactions)
#ORGNR 559064-1337                   ← Organization number
#FNAMN "NC Finance AB"               ← Company name
#RAR 0 20240101 20241231             ← Fiscal year range
#RAR -1 20230101 20231231            ← Previous year
#KPTYP EUBAS97                       ← Chart of accounts type
#VALUTA SEK                          ← Currency
```

### Key Findings
- **SIE Version:** Type 4 (identified by `#SIETYP 4`)
- **Encoding:** PC8 format (IBM Code Page 437/850 for Swedish characters)
- **SIE Type 4 = Full transaction format** with complete voucher entries for analysis

### Account Definitions (#KONTO)
Format: `#KONTO {account_number} "{account_name}"`
- Example: `#KONTO 1930 "Företagskonto/checkkonto/affärskonto (BG)"`
- Example: `#KONTO 2611 "Utgående moms på försäljning inom Sverige, 25%"`

### Verification Entries (#VER) - VERIFIED STRUCTURE
Format: `#VER {series} {number} {date} "{description}" {reg_date}`

**Parameters:**
- **series:** Letter identifying verification series (A, B, C, etc.) - In this file: **"A"**
- **number:** Sequential verification number (1, 2, 3..., 100, 101...)
- **date:** Transaction date in YYYYMMDD format
- **description:** Text description (quoted, Swedish characters)
- **reg_date:** Registration date in YYYYMMDD format

**Actual Examples:**
```
#VER A 2 20240111 "2024-01-11 - Utebetal - KFM,117030239224" 20240117
#VER A 10 20240402 "2024-04-02 - Utebetal - KFM,110357731524" 20240421
#VER A 100 20241105 "2024-11-05 - Ahsell - Faktura - 4795459702" 20241125
```

### Transaction Entries (#TRANS) - VERIFIED STRUCTURE
Format: `#TRANS {account} {object_list} {amount} {date} "{description}"`

**Parameters:**
- **account:** Account number (4 digits typically)
- **object_list:** Cost centers/projects - appears as `{}` (empty) in this file
- **amount:** Decimal amount (positive or negative), format: `300.00` or `-300.00`
- **date:** Transaction date in YYYYMMDD format
- **description:** Text description (quoted)

**Structure with curly braces:**
```
#VER A 2 20240111 "2024-01-11 - Utebetal - KFM,117030239224" 20240117
{
#TRANS 6090 {} 300.00 20240111 "2024-01-11 - Utebetal - KFM,117030239224"
#TRANS 1930 {} -300.00 20240111 "2024-01-11 - Utebetal - KFM,117030239224"
}
```

### Important Parsing Notes
1. **Multi-line structure:** Verifications span multiple lines between `{` and `}`
2. **Balanced entries:** Credits and debits must balance (sum to zero)
3. **PC8 encoding:** Must handle Swedish characters (å, ä, ö) correctly
4. **Date format:** Always YYYYMMDD (8 digits)
5. **Decimal separator:** Period (.) not comma
6. **Verification ID:** Combine series + number (e.g., "A2", "A100")

### Regular Expressions for SIE Parsing
- **VER pattern:** `^#VER\s+([A-Z])\s+(\d+)\s+(\d{8})\s+"(.+?)"\s+(\d{8})`
- **TRANS pattern:** `^#TRANS\s+(\d+)\s+\{\}\s+([-]?\d+\.?\d*)\s+(\d{8})\s+"(.+?)"`

### Encoding Detection (CRITICAL)
- **Primary: cp437** (IBM PC Code Page 437 - original PC8 format) ⚠️ MUST USE THIS
- **Fallback: cp850** (IBM Code Page 850 - Western Europe variant)
- **Last resort:** latin-1, utf-8
- **Why critical:** Standard utf-8 will CRASH on Swedish characters (Ö, Å, Ä) in PC8 format
- **Verification:** Check #FORMAT PC8 header in file
- **Error handling:** If all encodings fail, log error with filename and raw bytes sample

---

## PDF Filename Pattern Analysis
- **Format:** `A{number} - {date} - {description}.pdf`
- **Example:** `A1 - 2024-08-06 - Aktiekapital insättning.pdf`
- **Example:** `A100 - 2024-11-05 - Ahsell - Faktura - 4795459702.pdf`
- **Verification number:** Matches SIE entries (A1, A2, A100, etc.)
- **Parsing regex:** `^([A-Z]\d+)\s+-\s+` for verification number
- **Date regex:** `\d{4}-\d{2}-\d{2}` for date extraction

---

## Swedish Number Formats and Parsing

### Swedish Number Format Rules
- **Thousand separator:** Space (␣) or dot (.) - e.g., "1 234,56" or "1.234,56"
- **Decimal separator:** Comma (,) - e.g., "1234,56"
- **International format:** Also common - dot (.) as decimal - e.g., "1234.56"
- **Currency:** "kr" or "SEK" suffix

### Regex Patterns for Swedish Numbers

**⚠️ CRITICAL: Use `[ \t\xa0]` NOT `\s` for thousand separators**
- `\s` matches newlines and could join numbers across line breaks
- `[ \t\xa0]` matches only: space, tab, non-breaking space (safe for PDFs)

```python
# Pattern 1: Swedish with thousand separators (space or dot)
r'(\d{1,3}(?:[. \t\xa0]\d{3})*),(\d{2})[ \t\xa0]*(?:kr|SEK)'
# Matches: "1 234,56 kr", "1.234,56 kr"
# Safe: Won't match across line breaks

# Pattern 2: Swedish without thousand separator
r'(\d+),(\d{2})[ \t\xa0]*(?:kr|SEK)'
# Matches: "1234,56 kr"

# Pattern 3: International format
r'(\d{1,3}(?:,\d{3})*)\.(\d{2})[ \t\xa0]*(?:kr|SEK)'
# Matches: "1,234.56 kr", "1234.56 SEK"

# Pattern 4: Simple number with labels
r'(?:Totalt|Summa|Total|Belopp):[ \t\xa0]*(\d{1,3}(?:[., \t\xa0]\d{3})*[.,]\d{2})'
# Matches: "Totalt: 1 234,56", "Summa 1234.56"
# Safe: Won't accidentally join "1234" on one line with "56" on next line
```

### Parsing Strategy
1. Try each pattern in order (most specific first)
2. Clean matched number: Remove spaces/dots/commas from thousand separators
3. Identify decimal separator (comma vs dot based on pattern)
4. Convert to float: `1234.56` (standardized format)
5. If multiple amounts found: Use largest or sum (configurable)

### Edge Cases to Handle
- VAT inclusive vs exclusive amounts (multiple amounts in same PDF)
- Negative amounts (credits/returns): "-1234,56 kr"
- Amounts without decimals: "1234 kr" (treat as 1234.00)
- Multiple currencies in same PDF (ignore non-SEK/kr amounts)

### Helper Function for Swedish Number Parsing
```python
def parse_swedish_amount(text):
    """
    Extract amount from Swedish text using multiple regex patterns.
    Returns: float or None

    Handles:
    - Swedish format: "1 234,56 kr" or "1.234,56 kr"
    - Simple Swedish: "1234,56 kr"
    - International: "1234.56 kr"
    - With labels: "Totalt: 1 234,56"

    CRITICAL: Uses [ \t\xa0] instead of \s to avoid matching newlines
    """
    patterns = [
        # Pattern 1: Swedish with thousand separators (space or dot)
        # SAFE: [ \t\xa0] won't match newlines
        (r'(\d{1,3}(?:[. \t\xa0]\d{3})*),(\d{2})[ \t\xa0]*(?:kr|SEK)', 'swedish'),

        # Pattern 2: Swedish without thousand separator
        (r'(\d+),(\d{2})[ \t\xa0]*(?:kr|SEK)', 'swedish'),

        # Pattern 3: International format
        (r'(\d{1,3}(?:,\d{3})*)\.(\d{2})[ \t\xa0]*(?:kr|SEK)', 'international'),

        # Pattern 4: With labels
        # SAFE: [ \t\xa0] prevents matching across line breaks
        (r'(?:Totalt|Summa|Total|Belopp):[ \t\xa0]*(\d{1,3}(?:[., \t\xa0]\d{3})*[.,]\d{2})', 'auto'),
    ]

    for pattern, format_type in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            if format_type == 'swedish':
                # Remove thousand separators (space, tab, nbsp, or dot), comma is decimal
                amount_str = match.group(0)
                amount_str = re.sub(r'[ \t\xa0.](?=\d{3})', '', amount_str)  # Remove thousand sep
                amount_str = amount_str.replace(',', '.')  # Comma to dot
            elif format_type == 'international':
                # Remove thousand separators (comma)
                amount_str = match.group(0)
                amount_str = re.sub(r',(?=\d{3})', '', amount_str)

            # Extract just the number
            number_match = re.search(r'([\d.]+)', amount_str)
            if number_match:
                return float(number_match.group(1))

    return None  # No amount found
```

### Test Cases for Swedish Number Parsing
```python
# Should all parse to 1234.56
test_cases = [
    "1 234,56 kr",           # Swedish with space separator
    "1.234,56 kr",           # Swedish with dot separator
    "1234,56 kr",            # Swedish without separator
    "1234.56 SEK",           # International format
    "Totalt: 1 234,56",      # With label (Swedish)
    "Summa 1234.56",         # With label (International)
    "Belopp: 1.234,56 kr",   # With label (Swedish dot separator)
]

# Edge cases
edge_cases = [
    ("-1234,56 kr", -1234.56),       # Negative amount
    ("1234 kr", 1234.00),            # No decimals
    ("Total 50,00 + VAT 12,50", 50.00),  # Multiple amounts (pick first)
]
```

---

## Performance Considerations

### OCR Processing
- **Text-first approach:** Use pdfplumber to check for embedded text before OCR
- **Expected split:** 70-90% simple copy, 10-30% OCR needed
- **Skip processed files:** Check output folder to avoid reprocessing
- **Batch processing:** Use progress bars (tqdm)
- **Error recovery:** Log failures, continue processing
- **Swedish language:** Use `--language swe` with ocrmypdf when OCR needed

### SIE Parsing
- **State machine:** Handle multi-line verification blocks
- **Encoding order:** cp437 → cp850 → latin-1 → utf-8
- **Respect scope:** #TRANS lines ONLY belong to their enclosing #VER block
- **Validation:** Sum transaction amounts (should balance to zero)
- **Signed amounts:** Handle Debits (+) and Credits (-)

### Matching
- **Primary match:** Verification number (A1, A2, etc.)
- **Secondary match:** Date proximity (±3 days tolerance)
- **Tertiary match:** Amount comparison with tolerance (±0.01)
- **Filename parsing:** Fast regex extraction of verification ID and date
- **Amount extraction:** Use safe regex patterns with `[ \t\xa0]` not `\s`
