# Iteration 4: Testing & Quality Assurance

**Goal:** Implement comprehensive testing to ensure code quality, catch regressions, and validate functionality.

**Duration:** ~1-2 hours

**Status:** ⏸️ Pending

---

## Overview

This iteration focuses on building a robust test suite that covers:
- Unit tests for individual modules
- Integration tests for CLI commands
- Test fixtures and mocking strategies
- Code coverage reporting
- Continuous testing practices

---

## Why Testing Matters

1. **Catch Bugs Early:** Find issues before they reach production
2. **Prevent Regressions:** Ensure new changes don't break existing functionality
3. **Documentation:** Tests serve as living documentation of expected behavior
4. **Refactoring Confidence:** Make changes with confidence that tests will catch problems
5. **Quality Assurance:** Maintain >80% code coverage for critical paths

---

## Testing Strategy

### Test Pyramid

```
        ┌──────────────┐
        │   E2E Tests  │  (Few - Slow but comprehensive)
        │  Full CLI    │
        └──────────────┘
       ┌────────────────┐
       │ Integration    │  (Some - Test module interaction)
       │     Tests      │
       └────────────────┘
     ┌──────────────────┐
     │   Unit Tests     │  (Many - Fast and focused)
     │  Per Module      │
     └──────────────────┘
```

### Test Types

| Test Type | Purpose | Speed | Coverage |
|-----------|---------|-------|----------|
| **Unit Tests** | Test individual functions/classes in isolation | Fast | Wide |
| **Integration Tests** | Test module interactions | Medium | Moderate |
| **CLI Tests** | Test full command execution | Slow | Narrow |

---

## Test Structure

```
tests/
├── __init__.py
├── conftest.py                  # Shared fixtures
├── test_main.py                 # ✅ CLI command tests (existing)
├── test_config.py               # Configuration tests
├── test_logger.py               # Logging tests
├── test_sie_parser.py           # SIE parsing tests
├── test_file_scanner.py         # Filename scanning tests
├── test_content_extractor.py    # OCR/text extraction tests
├── test_matcher.py              # Matching logic tests
└── fixtures/                    # Test data
    ├── sample.se                # Sample SIE file
    ├── sample_voucher.pdf       # Sample PDF
    └── README.md                # Fixture documentation
```

---

## Testing Tools

### Core Dependencies (Already in requirements.txt)

```txt
pytest>=7.4.0              # Test framework
pytest-cov>=4.1.0          # Coverage reporting
pytest-mock>=3.11.1        # Mocking utilities
```

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_main.py

# Run specific test function
pytest tests/test_main.py::test_cmd_setup_creates_directories

# Run with coverage report
pytest --cov=src --cov-report=html

# Open coverage report
open htmlcov/index.html  # macOS
start htmlcov/index.html  # Windows
```

---

## Test Implementation Plan

### Phase 1: Setup Testing Infrastructure

**Files to create:**
- `tests/conftest.py` - Shared fixtures
- `tests/fixtures/` - Test data directory

**Tasks:**
1. ✅ Create `tests/` directory
2. ✅ Move `test_main.py` to `tests/test_main.py`
3. Create shared fixtures (tmp directories, mock config, sample data)
4. Document fixture usage patterns

### Phase 2: Unit Tests (Per Module)

#### 2.1 Test `src/config.py`

**File:** `tests/test_config.py`

**Test cases:**
- Directory detection (Data/ vs data/)
- Path construction (INPUT_DIR, OUTPUT_DIR, etc.)
- Environment variable overrides
- Invalid configuration handling

```python
def test_config_detects_data_directory(tmp_path):
    """Verify config detects Data/ directory."""
    # Create Data/ directory
    data_dir = tmp_path / "Data"
    data_dir.mkdir()

    # Should use Data/ (capital D)
    assert config.INPUT_DIR == data_dir / "Input"

def test_config_paths_are_pathlib():
    """Ensure all config paths are pathlib.Path objects."""
    assert isinstance(config.INPUT_DIR, Path)
    assert isinstance(config.OUTPUT_DIR, Path)
```

#### 2.2 Test `src/logger.py`

**File:** `tests/test_logger.py`

**Test cases:**
- Logger initialization
- Log file creation
- Log level filtering
- Console vs file output

```python
def test_logger_creates_log_file(tmp_path):
    """Verify logger creates log file in logs/ directory."""
    log_file = tmp_path / "test.log"
    logger = setup_logger(log_file)

    logger.info("Test message")

    assert log_file.exists()
    assert "Test message" in log_file.read_text()
```

#### 2.3 Test `src/sie_parser.py` (Iteration 2)

**File:** `tests/test_sie_parser.py`

**Test cases:**
- Parse valid SIE file
- Extract verifications correctly
- Handle PC8/cp437 encoding
- Calculate target_amount (Zero Sum Trap!)
- Handle malformed SIE files
- Swedish character handling (ÅÄÖ)

```python
def test_sie_parser_extracts_verification():
    """Verify SIE parser extracts verification with correct target_amount."""
    sie_content = """
    #VER A 1 2024-01-15 "Invoice 123"
    {
        #TRANS 1510 {} 500.00
        #TRANS 2641 {} 100.00
        #TRANS 4010 {} -600.00
    }
    """

    verifications = parse_sie(sie_content)

    assert len(verifications) == 1
    assert verifications[0]["ver_no"] == "1"
    assert verifications[0]["date"] == "2024-01-15"
    assert verifications[0]["target_amount"] == 600.00  # NOT 0.00!
```

#### 2.4 Test `src/file_scanner.py` (Iteration 1)

**File:** `tests/test_file_scanner.py`

**Test cases:**
- Parse valid filename patterns
- Extract verification numbers
- Extract dates
- Extract amounts
- Handle invalid filenames
- Swedish number format parsing

```python
def test_file_scanner_parses_filename():
    """Verify filename parser extracts metadata."""
    filename = "Ver 123 2024-03-15 1,234.56kr.pdf"

    metadata = parse_filename(filename)

    assert metadata["ver_no"] == "123"
    assert metadata["date"] == "2024-03-15"
    assert metadata["amount"] == 1234.56
```

#### 2.5 Test `src/content_extractor.py` (Iteration 1)

**File:** `tests/test_content_extractor.py`

**Test cases:**
- Extract text from digital PDF (pdfplumber)
- Fallback to OCR for scanned PDFs
- Handle corrupted PDFs
- Swedish character handling in OCR
- Performance: text extraction preferred

```python
def test_text_extractor_prefers_pdfplumber(sample_pdf):
    """Verify text extractor tries pdfplumber before OCR."""
    with patch("pdfplumber.open") as mock_pdf:
        mock_pdf.return_value.pages[0].extract_text.return_value = "Invoice text"

        text = extract_text(sample_pdf)

        assert text == "Invoice text"
        mock_pdf.assert_called_once()  # Should not call OCR
```

#### 2.6 Test `src/matcher.py` (Iteration 3)

**File:** `tests/test_matcher.py`

**Test cases:**
- Match exact verification number + date + amount
- Match with date tolerance (±3 days)
- Match with amount tolerance (Swedish number formats)
- Detect missing PDFs
- Detect extra PDFs
- Detect date discrepancies
- Detect amount mismatches

```python
def test_matcher_finds_exact_match():
    """Verify matcher identifies exact matches."""
    sie_data = [{"ver_no": "123", "date": "2024-03-15", "target_amount": 500.00}]
    pdf_data = [{"ver_no": "123", "date": "2024-03-15", "amount": 500.00, "path": "ver123.pdf"}]

    matches = match_verifications(sie_data, pdf_data)

    assert len(matches["exact"]) == 1
    assert matches["exact"][0]["ver_no"] == "123"

def test_matcher_detects_date_discrepancy():
    """Verify matcher flags date mismatches within tolerance."""
    sie_data = [{"ver_no": "123", "date": "2024-03-15", "target_amount": 500.00}]
    pdf_data = [{"ver_no": "123", "date": "2024-03-17", "amount": 500.00, "path": "ver123.pdf"}]  # +2 days

    matches = match_verifications(sie_data, pdf_data)

    assert len(matches["date_mismatch"]) == 1
    assert matches["date_mismatch"][0]["date_diff"] == 2
```

### Phase 3: Integration Tests

#### 3.1 Test CLI Commands (Already Exists!)

**File:** `tests/test_main.py` ✅

**Existing test cases:**
- `test_cmd_setup_creates_directories` - Verify setup creates output directories
- `test_cmd_setup_fails_missing_input` - Verify setup fails gracefully

**Additional test cases to add:**
```python
def test_cmd_ocr_processes_pdfs(mock_config, tmp_path):
    """Verify OCR command processes PDFs."""
    # Setup test PDFs
    # Run OCR command
    # Verify output files created
    pass

def test_cmd_parse_extracts_sie_data(mock_config, sample_sie_file):
    """Verify parse command extracts SIE data."""
    # Run parse command
    # Verify DataFrame output
    pass

def test_cmd_match_generates_report(mock_config, tmp_path):
    """Verify match command generates CSV report."""
    # Setup test data
    # Run match command
    # Verify report file exists and contains expected data
    pass
```

#### 3.2 Test Full Pipeline (E2E)

**File:** `tests/test_integration.py`

**Test case:**
```python
def test_full_pipeline_end_to_end(tmp_path):
    """Verify full OCR → Parse → Match pipeline works."""
    # Setup: Create sample SIE file + PDFs in tmp_path
    # Run: python src/main.py full --year 2024
    # Assert: Reports generated with expected matches
    pass
```

### Phase 4: Test Fixtures

#### 4.1 Create `tests/conftest.py`

**Shared fixtures:**

```python
import pytest
from pathlib import Path
from unittest.mock import patch

@pytest.fixture
def tmp_data_dir(tmp_path):
    """Create temporary data directory structure."""
    input_dir = tmp_path / "Input"
    input_dir.mkdir()

    (input_dir / "SIE").mkdir()
    (input_dir / "Verifikationer 2024").mkdir()
    (input_dir / "Verifikationer 2025").mkdir()

    return tmp_path

@pytest.fixture
def mock_config(tmp_data_dir):
    """Mock config module with temporary paths."""
    with patch("src.config") as mock:
        mock.INPUT_DIR = tmp_data_dir / "Input"
        mock.SIE_DIR = mock.INPUT_DIR / "SIE"
        mock.INPUT_VOUCHERS_2024 = mock.INPUT_DIR / "Verifikationer 2024"
        mock.INPUT_VOUCHERS_2025 = mock.INPUT_DIR / "Verifikationer 2025"
        mock.OUTPUT_DIR = tmp_data_dir / "Output"
        mock.OUTPUT_VOUCHERS_2024 = mock.OUTPUT_DIR / "Vouchers" / "2024"
        mock.OUTPUT_VOUCHERS_2025 = mock.OUTPUT_DIR / "Vouchers" / "2025"
        mock.REPORTS_DIR = mock.OUTPUT_DIR / "reports"
        mock.LOGS_DIR = tmp_data_dir / "logs"
        yield mock

@pytest.fixture
def sample_sie_file(tmp_path):
    """Create sample SIE file for testing."""
    sie_path = tmp_path / "sample.se"
    sie_path.write_text("""
#FLAGGA 0
#FORMAT PC8
#VER A 1 2024-01-15 "Invoice 123"
{
    #TRANS 1510 {} 500.00
    #TRANS 2641 {} 100.00
    #TRANS 4010 {} -600.00
}
    """.strip(), encoding="cp437")
    return sie_path

@pytest.fixture
def sample_pdf(tmp_path):
    """Create sample PDF for testing."""
    # Use reportlab or copy from fixtures/
    pdf_path = tmp_path / "ver123.pdf"
    # TODO: Create minimal PDF with text
    return pdf_path
```

#### 4.2 Create Test Fixtures Directory

```bash
tests/fixtures/
├── README.md           # Document fixture files
├── sample.se           # Minimal SIE file
├── sample_digital.pdf  # PDF with extractable text
├── sample_scanned.pdf  # PDF requiring OCR
└── sample_swedish.pdf  # PDF with ÅÄÖ characters
```

---

## Code Coverage Goals

| Module | Target Coverage | Priority |
|--------|----------------|----------|
| `src/config.py` | 90%+ | High |
| `src/logger.py` | 80%+ | Medium |
| `src/sie_parser.py` | 95%+ | Critical |
| `src/file_scanner.py` | 95%+ | Critical |
| `src/content_extractor.py` | 85%+ | High |
| `src/matcher.py` | 95%+ | Critical |
| `src/main.py` | 70%+ | Medium |
| **Overall** | **85%+** | - |

---

## Testing Best Practices

### 1. Use Descriptive Test Names

```python
# ✅ GOOD: Clearly states what is being tested
def test_sie_parser_handles_swedish_characters():
    pass

# ❌ BAD: Vague, unclear intent
def test_parser():
    pass
```

### 2. Follow AAA Pattern (Arrange-Act-Assert)

```python
def test_matcher_finds_exact_match():
    # Arrange - Setup test data
    sie_data = [{"ver_no": "123", "date": "2024-03-15", "target_amount": 500.00}]
    pdf_data = [{"ver_no": "123", "date": "2024-03-15", "amount": 500.00}]

    # Act - Execute the function under test
    matches = match_verifications(sie_data, pdf_data)

    # Assert - Verify expected outcome
    assert len(matches["exact"]) == 1
```

### 3. Test Edge Cases

```python
def test_file_scanner_handles_malformed_filename():
    """Test scanner gracefully handles invalid filenames."""
    invalid_names = [
        "no-verification-number.pdf",
        "Ver ABC 2024-01-15.pdf",  # Non-numeric ver_no
        "Ver 123 invalid-date.pdf",
        "Ver 123 2024-01-15 no-amount.pdf",
    ]

    for filename in invalid_names:
        metadata = parse_filename(filename)
        assert metadata is None or metadata["ver_no"] is None
```

### 4. Mock External Dependencies

```python
@patch("src.content_extractor.tesseract_ocr")
def test_ocr_fallback(mock_tesseract):
    """Test OCR fallback when text extraction fails."""
    mock_tesseract.return_value = "OCR extracted text"

    # Simulate pdfplumber failure
    with patch("pdfplumber.open", side_effect=Exception("PDF error")):
        text = extract_text("sample.pdf")

    assert text == "OCR extracted text"
    mock_tesseract.assert_called_once()
```

### 5. Use Fixtures for Reusable Test Data

```python
@pytest.fixture
def sample_verifications():
    """Reusable SIE verification data."""
    return [
        {"ver_no": "1", "date": "2024-01-15", "target_amount": 500.00},
        {"ver_no": "2", "date": "2024-01-16", "target_amount": 1200.00},
        {"ver_no": "3", "date": "2024-01-17", "target_amount": 750.00},
    ]

def test_matcher_with_sample_data(sample_verifications):
    """Test matcher using fixture data."""
    # Use sample_verifications in test
    pass
```

---

## Running Tests in CI/CD

### GitHub Actions Example

Create `.github/workflows/test.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt

    - name: Run tests with coverage
      run: |
        pytest --cov=src --cov-report=xml --cov-report=term

    - name: Upload coverage reports
      uses: codecov/codecov-action@v3
      with:
        files: ./coverage.xml
```

---

## Success Criteria

By the end of Iteration 4, you should have:

✅ Test directory structure created (`tests/` with `__init__.py`)
✅ `tests/conftest.py` with shared fixtures
✅ Unit tests for all modules (config, logger, sie_parser, file_scanner, content_extractor, matcher)
✅ Integration tests for CLI commands (setup, ocr, parse, match)
✅ Test fixtures directory with sample data
✅ All tests passing (`pytest` exits with 0)
✅ Code coverage >85% for critical modules
✅ Coverage report generated (`pytest --cov=src --cov-report=html`)
✅ Documentation of test patterns and best practices

---

## Next Steps

After completing this iteration:

1. **Run tests regularly** during development
2. **Add tests** when fixing bugs (regression tests)
3. **Update tests** when changing functionality
4. **Review coverage** to identify untested code paths
5. **Move to Iteration 5** (CLI Polish) if desired

---

## Common Testing Scenarios

### Scenario 1: Testing File Operations

```python
def test_copy_pdf_preserves_content(tmp_path):
    """Verify PDF copying doesn't corrupt files."""
    source = tmp_path / "source.pdf"
    dest = tmp_path / "dest.pdf"

    # Create source PDF
    source.write_bytes(b"PDF content")

    # Copy file
    copy_pdf(source, dest)

    # Verify
    assert dest.exists()
    assert dest.read_bytes() == source.read_bytes()
```

### Scenario 2: Testing Date Parsing

```python
@pytest.mark.parametrize("date_str,expected", [
    ("2024-01-15", datetime(2024, 1, 15)),
    ("2024/01/15", datetime(2024, 1, 15)),
    ("15-01-2024", datetime(2024, 1, 15)),
])
def test_date_parser_handles_formats(date_str, expected):
    """Test various date format parsing."""
    result = parse_date(date_str)
    assert result == expected
```

### Scenario 3: Testing Swedish Number Parsing

```python
@pytest.mark.parametrize("text,expected", [
    ("1 234,56 kr", 1234.56),
    ("1234.56", 1234.56),
    ("1.234,56", 1234.56),
    ("5,00 kr", 5.00),
])
def test_swedish_number_parser(text, expected):
    """Test Swedish number format parsing."""
    result = parse_swedish_number(text)
    assert result == expected
```

---

## Troubleshooting

### Issue: Tests can't import `src` modules

**Solution:** Ensure `pytest` is run from project root:
```bash
# Run from project root (where src/ is located)
pytest
```

Or add `src/` to Python path in `conftest.py`:
```python
import sys
from pathlib import Path

# Add src/ to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
```

### Issue: File permission errors on Windows

**Solution:** Use `tmp_path` fixture (automatically cleaned up):
```python
def test_with_temp_files(tmp_path):
    test_file = tmp_path / "test.pdf"
    # pytest automatically cleans up tmp_path
```

### Issue: Mock not working as expected

**Solution:** Ensure correct import path:
```python
# ❌ BAD: Mock where it's defined
@patch("unittest.mock.MagicMock")

# ✅ GOOD: Mock where it's used
@patch("src.main.config")  # Mock config as imported in src.main
```

---

**Ready to implement tests?** Start with Phase 1 (Setup) and work through each module systematically.

**Next:** [Iteration 5: CLI Polish](iteration-5-cli-polish.md) (Optional)
