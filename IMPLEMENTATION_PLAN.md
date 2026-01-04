# OCR Processing and SIE Matching Project - Master Plan

**Version:** 2.0 (Split Plan Structure)
**Last Updated:** 2026-01-04

---

## Project Overview

**Main Goal:** Find the differences between PDF vouchers and vouchers recorded in the bookkeeping system.

**The Application:**
1. Parse SIE bookkeeping files to extract verification entries (vouchers from the bookkeeping system)
2. Process PDF vouchers with OCR (Swedish language) to make them searchable
3. Match verification numbers, dates, and amounts between the two systems
4. Generate detailed reports showing:
   - ✅ Matches (vouchers that exist in both systems)
   - ❌ Missing vouchers (exist in bookkeeping but no PDF found)
   - ⚠️ Discrepancies (date mismatches, amount differences)
   - ❓ Extra PDFs (PDF vouchers with no corresponding bookkeeping entry)

---

## Current Folder Structure

```
data/
├── Input/                          (READ-ONLY - Never modified)
│   ├── SIE/
│   │   ├── 20240101-20241231.se   (112 KB)
│   │   └── 20250101-20251231.se   (64 KB)
│   ├── Verifikationer 2024/       (~300+ PDF files)
│   └── Verifikationer 2025/       (~100+ PDF files)
└── Output/                         (All output goes here)
    ├── Vouchers/
    │   ├── 2024/                   (Processed PDFs)
    │   └── 2025/                   (Processed PDFs)
    └── reports/                    (CSV/Excel reports)
```

**Important:** Input folder is READ-ONLY and remains UNTOUCHED. All PDFs are copied to Output/Vouchers/ for processing.

---

## Target Project Structure

```
project-root/
├── .venv/                          # Virtual environment
├── data/
│   ├── Input/                      # (READ-ONLY)
│   └── Output/                     # All output
├── logs/                           # Log files
├── src/
│   ├── __init__.py
│   ├── config.py                   # Configuration
│   ├── logger.py                   # Centralized logging
│   ├── sie_parser.py               # SIE file parser
│   ├── file_scanner.py             # Filename parsing
│   ├── content_extractor.py        # PDF text extraction/OCR
│   ├── matcher.py                  # Matching logic
│   └── main.py                     # CLI interface
├── docs/                           # 📁 Documentation
│   ├── iteration-0-environment-setup.md
│   ├── iteration-1-ocr-processing.md
│   ├── iteration-2-sie-parser.md
│   ├── iteration-3-matching.md
│   └── TECHNICAL_REFERENCE.md
├── requirements.txt
├── .gitignore
├── README.md
├── IMPLEMENTATION_PLAN.md         # ⭐ This file (master coordination)
└── config.example
```

---

## Architecture: Separation of Concerns

### Module Responsibilities

| Module | Responsibility | Speed | Dependencies |
|--------|---------------|-------|--------------|
| **sie_parser.py** | Parse SIE files → "Source of Truth" | Medium | Iteration 0 |
| **file_scanner.py** | Parse filenames (fast, no PDF opening) | Fast | Iteration 0 |
| **content_extractor.py** | Extract text/OCR PDFs | Slow | Iteration 0 |
| **matcher.py** | Compare SIE vs PDFs → Reports | Medium | Iterations 1-2 |

### Benefits

- ✅ **Performance:** Fast filename scanning first; slow content extraction only when needed
- ✅ **Modularity:** Each module has a single, clear responsibility
- ✅ **Testability:** Easy to unit test each module independently
- ✅ **Maintainability:** Changes to OCR logic don't affect filename parsing or matching

---

## Iterative Development Roadmap

**Philosophy:** Build and test one component at a time, verifying each iteration works before moving to the next.

| Iteration | Goal | Deliverable | Time Estimate | Status |
|-----------|------|-------------|---------------|--------|
| **[Iteration 0](docs/iteration-0-environment-setup.md)** | Environment Setup | Virtual env + dependencies | ~15 min | ⏸️ Pending |
| **[Iteration 1](docs/iteration-1-ocr-processing.md)** ⭐ | OCR Processing | Searchable PDFs in Output/ | ~1-2 hours | ⏸️ Pending |
| **[Iteration 2](docs/iteration-2-sie-parser.md)** | SIE Parser | DataFrame with verifications | ~1 hour | ⏸️ Pending |
| **[Iteration 3](docs/iteration-3-matching.md)** | Matching | Match report (Excel/CSV) | ~30-60 min | ⏸️ Pending |
| **Iteration 4** | CLI Polish | User-friendly commands | ~30 min | ⏸️ Optional |

**Total Estimated Time:** ~3-5 hours for core functionality (Iterations 0-3)

---

## Iteration Quick Links

### 📖 Detailed Iteration Plans

- **[Iteration 0: Environment Setup](docs/iteration-0-environment-setup.md)**
  - Virtual environment creation
  - Dependency installation
  - Folder structure setup
  - Configuration modules (config.py, logger.py)

- **[Iteration 1: OCR Processing](docs/iteration-1-ocr-processing.md)** ⭐ START HERE
  - Text-first approach (pdfplumber → OCR)
  - Copy PDFs from Input to Output
  - Swedish language OCR (Tesseract)
  - Modules: file_scanner.py, content_extractor.py

- **[Iteration 2: SIE Parser](docs/iteration-2-sie-parser.md)**
  - Parse SIE Type 4 files
  - Handle PC8 encoding (cp437)
  - **CRITICAL:** Zero Sum Trap - extract target_amount for matching
  - Module: sie_parser.py

- **[Iteration 3: Matching](docs/iteration-3-matching.md)**
  - Match verification numbers
  - Compare dates (±3 days tolerance)
  - Compare amounts (Swedish number parsing)
  - Generate comprehensive reports
  - Module: matcher.py

### 📚 Technical References

- **[Technical Reference](docs/TECHNICAL_REFERENCE.md)**
  - SIE file format specification
  - Swedish number formats and regex patterns
  - Encoding details (PC8/cp437)
  - Performance considerations

---

## Critical Technical Notes

### ⚠️ The Zero Sum Trap (Iteration 2)

In double-entry bookkeeping, all SIE verifications sum to zero. We MUST extract `target_amount` (not `total_amount`) for matching:

```python
# ❌ WRONG: total_amount is always 0.00 (won't match PDF receipts)
total_amount = sum(transaction_amounts)  # 400 + 100 + (-500) = 0.00

# ✅ CORRECT: target_amount is the actual receipt amount
target_amount = max(abs(amt) for amt in transaction_amounts)  # 500.00
```

**See:** [iteration-2-sie-parser.md](docs/iteration-2-sie-parser.md#-critical-the-zero-sum-trap---why-we-need-target_amount)

### ⚡ Text-First OCR Strategy (Iteration 1)

Most modern accounting PDFs are "born digital" (not scanned):

1. Try pdfplumber text extraction first (fast & accurate)
2. Only use Tesseract OCR if text extraction fails

**Expected result:** 70-90% of files are simple copies → hours saved

**See:** [iteration-1-ocr-processing.md](docs/iteration-1-ocr-processing.md#smart-processing-strategy-text-first-approach)

### 🔒 Regex Safety for Swedish Numbers (Iteration 3)

**Use `[ \t\xa0]` NOT `\s` for thousand separators:**

- `\s` matches newlines → could join "1234" on one line with "56" on next line
- `[ \t\xa0]` matches only: space, tab, non-breaking space (safe!)

**See:** [TECHNICAL_REFERENCE.md](docs/TECHNICAL_REFERENCE.md#regex-patterns-for-swedish-numbers)

---

## Success Criteria (Overall Project)

✅ Virtual environment created and activated
✅ All dependencies installed
✅ OCR processes PDFs from Input folders to Output folders
✅ SIE parser extracts all verification entries correctly (with target_amount)
✅ Matcher generates reports showing:
  - Found matches
  - Missing PDFs
  - Date discrepancies
  - Amount mismatches
✅ CLI interface provides clear feedback and progress
✅ Comprehensive error handling and logging
✅ Documentation complete with setup and usage instructions

---

## CLI Commands Overview

### Iteration 0: Setup
```bash
python src/main.py setup
```

### Iteration 1: OCR Processing
```bash
# Test with 5 files
python src/main.py ocr --year 2024 --limit 5

# Process all 2024 PDFs
python src/main.py ocr --year 2024

# Process both years
python src/main.py ocr
```

### Iteration 2: SIE Parsing
```bash
# Parse 2024 SIE file
python src/main.py parse --year 2024

# Parse both years
python src/main.py parse
```

### Iteration 3: Matching
```bash
# Match 2024 data
python src/main.py match --year 2024

# Run full pipeline (OCR → Parse → Match)
python src/main.py full --year 2024
```

---

## Getting Started

### 1. Start with Iteration 0
Read and complete: **[docs/iteration-0-environment-setup.md](docs/iteration-0-environment-setup.md)**

### 2. Proceed to Iteration 1
Read and complete: **[docs/iteration-1-ocr-processing.md](docs/iteration-1-ocr-processing.md)**

### 3. Continue sequentially
Follow the iteration order (0 → 1 → 2 → 3)

---

## Project Status

**Current Iteration:** Planning Complete ✅
**Next Action:** Begin [Iteration 0: Environment Setup](docs/iteration-0-environment-setup.md)

---

## Document Change Log

- **v2.0 (2026-01-04):** Split into modular plan structure
- **v1.0 (2026-01-04):** Initial monolithic plan (867 lines)

---

## Quick Reference Links

| Document | Purpose | When to Read |
|----------|---------|--------------|
| [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) | Master coordination (this file) | First, for overview |
| [iteration-0-environment-setup.md](docs/iteration-0-environment-setup.md) | Setup virtual environment | Before starting |
| [iteration-1-ocr-processing.md](docs/iteration-1-ocr-processing.md) | OCR processing details | During Iteration 1 |
| [iteration-2-sie-parser.md](docs/iteration-2-sie-parser.md) | SIE parsing details | During Iteration 2 |
| [iteration-3-matching.md](docs/iteration-3-matching.md) | Matching logic details | During Iteration 3 |
| [TECHNICAL_REFERENCE.md](docs/TECHNICAL_REFERENCE.md) | Technical specs | As needed |

---

**Ready to start?** → [docs/iteration-0-environment-setup.md](docs/iteration-0-environment-setup.md)
