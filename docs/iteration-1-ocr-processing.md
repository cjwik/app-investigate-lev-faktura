# Iteration 1: OCR Processing ⭐ START HERE

**Goal:** Copy all PDFs from Input to Output and ensure they have searchable text (OCR only if needed)
**Deliverable:** All PDFs copied to `data/Output/Vouchers/{year}/` with searchable text
**Prerequisites:** Iteration 0 complete (virtual environment, dependencies installed)

---

## Success Criteria

✅ All PDFs copied from Input to Output folders
✅ Can read text from all PDFs (original text or OCR'd)
✅ Swedish characters (å, ä, ö) display correctly
✅ Input folder remains UNTOUCHED (read-only)
✅ PDFs that already have text are copied without OCR (faster)
✅ PDFs that are images-only get OCR processing when copied

---

## Smart Processing Strategy (Text-First Approach)

**⚡ CRITICAL PERFORMANCE OPTIMIZATION:**

```
┌─────────────────────────────────────────────────────────────┐
│ TEXT-FIRST APPROACH                                         │
│                                                             │
│ 1. Try pdfplumber text extraction first (fast & accurate)  │
│ 2. Only use Tesseract OCR if text extraction fails         │
│                                                             │
│ Why: Most accounting PDFs are "born digital" (not scanned) │
│ Result: 100x speed improvement for majority of files       │
└─────────────────────────────────────────────────────────────┘
```

### Processing Flow

1. **Text extraction attempt:** Use pdfplumber to check if PDF has embedded text
2. **If successful (has text):** Copy PDF to Output folder as-is - **NO OCR NEEDED** (100x faster!)
   - Most modern invoices/receipts from accounting software are born-digital PDFs
   - Simple file copy operation takes milliseconds vs. minutes for OCR
3. **If failed (image-only):** Process with Tesseract OCR and save to Output folder
   - Scanned paper receipts, photos of receipts
   - Heavy processing but necessary for image-only PDFs
4. **Logging:** Track which PDFs were copied vs. OCR'd to show time savings

### Expected Results

- **70-90%** of PDFs will be copied without OCR - assuming modern digital invoicing
- **10-30%** will require OCR - older scanned receipts
- Total processing time reduced from **hours to minutes** for majority of files
- Input folder remains **completely untouched**

---

## Module: src/file_scanner.py (Iteration 1A)

**Purpose:** Lightweight module to scan PDF folders and extract metadata from filenames (NO OCR, just filename parsing)

### Key Functions

#### `scan_pdf_folder(folder_path, year)`
- Scan folder for PDF files
- Parse verification number from filename (e.g., "A100" from "A100 - 2024-11-05 - Description.pdf")
- Parse date from filename (e.g., "2024-11-05")
- Return DataFrame with: filepath, verification_id, filename_date, filename
- Very fast - just file listing and regex parsing

**Returns:**
```python
DataFrame([
    {'filepath': Path('A1 - 2024-08-06 - Aktiekapital.pdf'),
     'verification_id': 'A1',
     'filename_date': datetime(2024, 8, 6),
     'filename': 'A1 - 2024-08-06 - Aktiekapital.pdf'},
    ...
])
```

#### `parse_verification_from_filename(filename)`
- Extract verification number using regex: `^([A-Z]\d+)\s+-\s+`
- Return verification_id (e.g., "A100") or None

**Example:**
```python
parse_verification_from_filename("A100 - 2024-11-05 - Description.pdf")
# Returns: "A100"
```

#### `parse_date_from_filename(filename)`
- Extract date using regex: `\d{4}-\d{2}-\d{2}`
- Return date as datetime or None

**Example:**
```python
parse_date_from_filename("A100 - 2024-11-05 - Description.pdf")
# Returns: datetime(2024, 11, 5)
```

---

## Module: src/content_extractor.py (Iteration 1B)

**Purpose:** Copy PDFs from Input to Output, with OCR only if needed (Input folder remains UNTOUCHED)

### Key Functions

#### `check_pdf_has_text(pdf_path)`
- Use pdfplumber to extract text from PDF
- Return True if PDF has extractable text (>50 characters)
- Return False if PDF is image-only
- Quick check to avoid unnecessary OCR

**Implementation:**
```python
import pdfplumber

def check_pdf_has_text(pdf_path, min_chars=50):
    """
    Check if PDF has embedded text using pdfplumber.

    Args:
        pdf_path: Path to PDF file
        min_chars: Minimum characters to consider "has text"

    Returns:
        bool: True if PDF has text, False if image-only
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            for page in pdf.pages[:3]:  # Check first 3 pages only
                text += page.extract_text() or ""
                if len(text) >= min_chars:
                    return True
            return len(text) >= min_chars
    except Exception as e:
        logger.error(f"Error checking PDF {pdf_path}: {e}")
        return False
```

#### `process_single_pdf(input_path, output_path, force_ocr=False)`
- First check if PDF already has text using `check_pdf_has_text()`
- If has text and not force_ocr: Copy file to output (faster!)
- If no text or force_ocr: Process with ocrmypdf using Swedish language `--language swe`
- Return status: "copied" or "ocr_processed" or "failed"
- Log any errors

**Returns:**
```python
{
    'status': 'copied' | 'ocr_processed' | 'failed',
    'processing_time': 0.15,  # seconds
    'text_sample': "First 100 chars of extracted text...",
    'error': None | "Error message"
}
```

#### `verify_pdf_has_text(pdf_path)`
- Use pdfplumber to extract text from PDF
- Print sample of extracted text for verification
- Used for final validation

**Example:**
```python
verify_pdf_has_text("data/Output/Vouchers/2024/A1 - ...pdf")
# Prints:
# Text sample: "Aktiekapital insättning NC Finance AB..."
# Swedish chars: ✓ (å, ä, ö detected)
# Length: 1234 characters
```

#### `process_pdf_folder(input_folder, output_folder, year, limit=None)`
- Read PDFs from input folder (e.g., `data/Input/Verifikationer 2024/`)
- For each PDF: check text, then copy or OCR
- Save to output folder (e.g., `data/Output/Vouchers/2024/`)
- Keep same filename as original
- **Input folder is READ-ONLY - never modified**
- **limit parameter:** Process only first N files for testing (e.g., limit=5)
- Skip files already in output (to avoid reprocessing)
- Progress bar for batch processing (tqdm)
- Error logging for failed files

**Parameters:**
```python
input_folder: Path to source PDFs (e.g., "data/Input/Verifikationer 2024/")
output_folder: Path to destination (e.g., "data/Output/Vouchers/2024/")
year: Year for logging/reporting (2024 or 2025)
limit: Optional limit for testing (e.g., 5 files)
```

**Returns:**
```python
{
    'total': 300,
    'copied': 215,  # PDFs that already had text
    'ocr_processed': 82,  # PDFs that needed OCR
    'failed': 3,  # PDFs that couldn't be processed
    'processing_time': 2730.5,  # seconds
    'time_saved': 2100.0  # seconds saved by skipping OCR
}
```

#### `batch_process(year=None, limit=None)`
- Process specific year or both (2024, 2025)
- Return statistics with breakdown:
  - `copied`: PDFs that already had text
  - `ocr_processed`: PDFs that needed OCR
  - `failed`: PDFs that couldn't be processed
- Show time saved by skipping OCR on text-ready PDFs

**Example:**
```python
stats = batch_process(year=2024, limit=5)
# Processes first 5 PDFs from 2024 for testing
```

---

## Testing Strategy

**Iteration 1 Testing Approach:**

1. **Test with 1 PDF that has text** (should copy)
   ```bash
   python src/main.py ocr --year 2024 --limit 1
   ```
   - Verify: Processing time <1 second
   - Verify: Status = "copied"
   - Verify: Text can be extracted from output PDF

2. **Test with 1 PDF that's image-only** (should OCR)
   - Manually create/find a scanned PDF
   - Process it
   - Verify: Status = "ocr_processed"
   - Verify: Processing time 30-60 seconds
   - Verify: Text can be extracted after OCR

3. **Verify both can be read and text extracted**
   ```python
   from src.content_extractor import verify_pdf_has_text
   verify_pdf_has_text("data/Output/Vouchers/2024/A1 - ...pdf")
   verify_pdf_has_text("data/Output/Vouchers/2024/A2 - ...pdf")
   ```

4. **Verify Input folder is unchanged**
   ```bash
   # Check file count hasn't changed
   ls "data/Input/Verifikationer 2024/" | wc -l
   # Should be same as before processing
   ```

5. **Test with 5 PDFs** (mix of text and images)
   ```bash
   python src/main.py ocr --year 2024 --limit 5
   ```
   - Review report: `data/Output/reports/ocr_report_{timestamp}.txt`
   - Verify statistics look reasonable

6. **Process all PDFs for one year**
   ```bash
   python src/main.py ocr --year 2024
   ```
   - Monitor progress bar
   - Review final report
   - Check logs for errors

7. **Finally process both years**
   ```bash
   python src/main.py ocr
   ```

---

## Output Reports (Iteration 1)

### Log Files

**Main log:** `logs/ocr_processing.log` - All operations logged with timestamps
```
2026-01-04 12:34:56 - INFO - Processing: A1 - 2024-08-06 - Aktiekapital insättning.pdf
2026-01-04 12:34:57 - INFO - Action: copied (already has text)
2026-01-04 12:34:57 - INFO - Text sample: "Aktiekapital insättning NC Finance AB..."
2026-01-04 12:35:10 - INFO - Processing: A2 - 2024-08-20 - Bauhaus - Kvitto.pdf
2026-01-04 12:35:45 - INFO - Action: ocr_processed (image-only PDF)
2026-01-04 12:35:45 - INFO - OCR time: 35.2s
```

**Error log:** `logs/ocr_errors.log` - Failed files with error details
```
2026-01-04 12:35:45 - ERROR - Failed to process: A99 - corrupted.pdf
2026-01-04 12:35:45 - ERROR - Error details: Invalid PDF structure
```

### Processing Report

**File:** `data/Output/reports/ocr_report_{timestamp}.txt`

**Content:**
```
OCR Processing Report
Generated: 2026-01-04 15:30:45

=== SUMMARY ===
Total PDFs Processed: 450
- Copied (already had text): 320 (71%)
- OCR Processed (image-only): 125 (28%)
- Failed: 5 (1%)

Processing Time: 45 minutes 30 seconds
Time Saved (by skipping OCR): ~35 minutes

=== 2024 FILES ===
Total: 300 files
Copied: 215, OCR'd: 82, Failed: 3

=== 2025 FILES ===
Total: 150 files
Copied: 105, OCR'd: 43, Failed: 2

=== FAILED FILES ===
1. A99 - corrupted.pdf - Error: Invalid PDF structure
2. A150 - encrypted.pdf - Error: PDF is password protected
3. A200 - damaged.pdf - Error: Cannot read PDF
4. A250 - large.pdf - Error: Timeout after 5 minutes
5. A300 - format.pdf - Error: Unsupported PDF version

=== VERIFICATION SAMPLES ===
Sample 1: A1 - 2024-08-06 - Aktiekapital insättning.pdf
Text: "Aktiekapital insättning NC Finance AB Org.nr: 559064-1337..."
Swedish chars: ✓ (å, ä, ö detected)
Amounts found: ✓ (50,000 kr)

Sample 2: A100 - 2024-11-05 - Ahsell - Faktura.pdf
Text: "Ahlsell Sverige AB Faktura 4795459702..."
Swedish chars: ✓
Amounts found: ✓ (1,234.56 kr)
```

### Processing Data (CSV)

**File:** `data/Output/reports/ocr_results_{timestamp}.csv`

**Columns:**
```csv
filename,year,action,processing_time_sec,text_length,has_swedish_chars,error
A1 - 2024-08-06 - Aktiekapital.pdf,2024,copied,0.15,1234,True,
A2 - 2024-08-20 - Bauhaus.pdf,2024,ocr_processed,35.2,856,True,
A99 - corrupted.pdf,2024,failed,0.01,0,False,Invalid PDF structure
```

---

## Important Notes

### Tesseract Installation (Windows)

**ocrmypdf requires Tesseract to be installed separately:**

1. Download Tesseract for Windows:
   - https://github.com/UB-Mannheim/tesseract/wiki
   - Choose latest installer (e.g., tesseract-ocr-w64-setup-5.3.0.exe)

2. Install Tesseract:
   - Default installation path: `C:\Program Files\Tesseract-OCR\`
   - **Important:** Check "Add to PATH" during installation

3. Install Swedish language pack:
   - Download `swe.traineddata` from: https://github.com/tesseract-ocr/tessdata
   - Copy to: `C:\Program Files\Tesseract-OCR\tessdata\`

4. Verify installation:
   ```bash
   tesseract --version
   tesseract --list-langs  # Should show "swe" in the list
   ```

### Input Folder Protection

**CRITICAL: Input folder is READ-ONLY**

The implementation MUST ensure:
- No files are modified in `data/Input/`
- No files are deleted from `data/Input/`
- No files are moved from `data/Input/`
- All processing happens on COPIES in `data/Output/`

**Verification:**
```python
# Before processing
input_files_before = list(INPUT_VOUCHERS_2024.glob("*.pdf"))

# After processing
input_files_after = list(INPUT_VOUCHERS_2024.glob("*.pdf"))

assert input_files_before == input_files_after, "Input folder was modified!"
```

---

## CLI Commands (main.py)

### Available Commands for Iteration 1

```bash
# Check environment setup
python src/main.py setup

# Process 2024 PDFs
python src/main.py ocr --year 2024

# Process 2025 PDFs
python src/main.py ocr --year 2025

# Process both years
python src/main.py ocr

# Test with only 5 files
python src/main.py ocr --year 2024 --limit 5

# Force OCR even if PDF has text (for testing)
python src/main.py ocr --year 2024 --limit 5 --force-ocr
```

---

## Success Criteria (Final Checklist)

✅ All PDFs from Input copied to Output folders
✅ Text-first strategy implemented (check for text before OCR)
✅ Swedish language OCR working (`--language swe`)
✅ Progress bars showing during batch processing
✅ Comprehensive logging (main log + error log)
✅ Processing report generated with statistics
✅ Input folder remains completely untouched
✅ Failed PDFs logged with error details
✅ CLI commands work as expected

**Time Estimate:** ~1-2 hours (depending on PDF count and mix of text/image files)

---

## Next Step

➡️ **Iteration 2:** SIE Parser ([iteration-2-sie-parser.md](iteration-2-sie-parser.md))

## Reference

📖 **Technical Reference:** See [TECHNICAL_REFERENCE.md](TECHNICAL_REFERENCE.md) for:
- PDF filename pattern details
- Swedish number parsing (for future iterations)
- Performance considerations
