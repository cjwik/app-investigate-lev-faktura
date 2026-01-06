# Architecture Documentation

This directory contains C4 architecture diagrams for the Wik Invoice Validation System using Structurizr DSL.

## Overview

The Invoice Validation System is a Python CLI application that validates Swedish supplier invoices against SIE (Standard Import/Export) accounting files. It detects:

- **Unpaid invoices** (receipts without clearing payments)
- **Payments without receipts** (payments without matching invoices)
- **Cross-year payments** (2024 invoices paid in 2025)
- **Correction vouchers** (accounting adjustments for incorrectly posted payments)

## Architecture Files

- **[workspace.dsl](workspace.dsl)** - Structurizr DSL file with complete C4 model
  - System Context diagram
  - Container diagram
  - Component diagrams (Matching Engine, CLI Pipeline)
  - Deployment diagram

## Viewing the Architecture

### Option 1: VS Code with C4 DSL Extension (Recommended)

1. **Install the extension**:
   - Open VS Code
   - Go to Extensions (Ctrl+Shift+X / Cmd+Shift+X)
   - Search for "Structurizr"
   - Install **"Structurizr DSL"** by ciarant

2. **Open the diagram**:
   - Open `workspace.dsl` in VS Code
   - Press `Ctrl+Shift+P` (Cmd+Shift+P on Mac)
   - Type "Structurizr: Show Preview"
   - Or click the preview icon in the top right corner

3. **Navigate diagrams**:
   - Use the dropdown in the preview pane to switch between views:
     - **SystemContext** - High-level system context
     - **Containers** - Major subsystems
     - **MatchingEngineComponents** - Core matching logic
     - **CLIComponents** - Complete pipeline flow
     - **Deployment** - Development environment

### Option 2: Structurizr Lite (Docker)

1. **Run Structurizr Lite**:
   ```bash
   docker run -it --rm -p 8080:8080 -v "$(pwd)/docs/architecture:/usr/local/structurizr" structurizr/lite
   ```

2. **Open in browser**:
   - Navigate to http://localhost:8080
   - View diagrams with interactive navigation

### Option 3: Structurizr Cloud (Online)

1. Sign up at https://structurizr.com
2. Create a new workspace
3. Copy contents of `workspace.dsl`
4. Paste into the DSL editor
5. View rendered diagrams

## Architecture Views

### 1. System Context

Shows the Invoice Validation System in relation to:
- **Bookkeeper** (user)
- **Google Drive** (cloud storage for files)
- **Accounting System** (exports SIE files)

### 2. Containers

Five main containers:
- **CLI Application** - Command orchestration (setup, ocr, parse, match, clean)
- **PDF Processor** - OCR processing for invoice PDFs
- **SIE Parser** - Parses Swedish accounting files (CP850 encoding)
- **Matching Engine** - Core business logic for invoice/payment matching
- **Report Generator** - CSV report creation
- **File System Storage** - Input/output data organization

### 3. Component: Matching Engine

Core matching algorithm components:
- **Invoice Matcher** - Main matching class
- **Receipt Identifier** - Finds 2440 Kredit (supplier liabilities created)
- **Clearing Identifier** - Finds 2440 Debet + 1930 (payments clearing liabilities)
- **Correction Identifier** - Detects accounting correction vouchers
- **Matching Orchestrator** - Coordinates multi-step matching workflow
- **Event Models** - Domain objects (ReceiptEvent, ClearingEvent, CorrectionEvent, InvoiceCase)

### 4. Component: CLI Pipeline

Complete processing pipeline:
- **Main Controller** (src/main.py) - Command dispatcher
- **Config Manager** (src/config.py) - Path and settings management
- **Content Extractor** (src/content_extractor.py) - PDF OCR processing
- **Summary Parser** (src/sie_parser.py) - SIE overview
- **Transaction Parser** (src/transaction_parser.py) - SIE transaction detail
- **Invoice Matcher** (src/matcher.py) - Matching logic
- **CSV Generator** (src/report_generator.py) - Report generation

### 5. Deployment

Shows development environment:
- **Python Runtime** (3.11+) on Developer Laptop
- **File System** (local storage)
- **Google Drive Sync Client** (cloud sync)

## Key Architectural Patterns

### 1. Pipeline Architecture
Sequential processing stages:
```
OCR → Parse → Match → Report
```

### 2. Domain-Driven Design
Rich domain models:
- **Voucher** - Complete accounting voucher with transactions
- **Transaction** - Single accounting transaction line
- **ReceiptEvent** - 2440 Kredit event (invoice received)
- **ClearingEvent** - 2440 Debet + 1930 event (invoice paid)
- **CorrectionEvent** - Accounting adjustment without bank transaction
- **InvoiceCase** - Complete invoice validation case

### 3. Command Pattern
CLI commands with clear separation:
- `setup` - Initialize directories
- `ocrclean` - Clean OCR outputs
- `parseclean` - Clean SIE parsing outputs
- `matchclean` - Clean matching reports
- `ocr` - Process PDFs
- `parse` - Parse SIE files
- `match` - Match invoices with payments

### 4. Text-First OCR Strategy
Optimize processing time:
1. Check if PDF has embedded text (pdfplumber)
2. If text exists → simple copy
3. If no text → OCR processing (ocrmypdf)

### 5. Multi-Step Matching Algorithm

The matching engine uses a sophisticated multi-step process:

```
Step 0: Identify correction vouchers (exclude from normal processing)
Step 1: Identify receipts (2440 Kredit) and clearings (2440 Debet + 1930)
Step 1.5: Identify correction events (2025 corrections for 2024 errors)
Step 2: Match receipts with clearings (by amount, date, supplier, invoice#)
Step 2.5: Match receipts with corrections (cross-year correction handling)
Step 3: Identify unmatched clearings (payments without receipts)
```

**Matching criteria** (in order of preference):
1. **Exact match**: Amount + Supplier + Invoice# + Date within tolerance
2. **Supplier + Invoice# match**: Amount + Supplier + Invoice#
3. **Amount + Supplier match**: Amount + Supplier name
4. **Amount-only match**: Amount within tolerance

**Special handling**:
- Cross-year payments (2024 invoices paid in 2025)
- Correction vouchers (2025 corrections clearing 2024 liabilities)
- Same-voucher payments (receipt and payment in single voucher)
- Multiple 1930 transactions per voucher (best-match selection)

## Data Flow

### OCR Flow
```
Input PDFs → pdfplumber (text check) → [if no text] → ocrmypdf (OCR) → Output PDFs
```

### Parse Flow
```
SIE File (CP850) → Encoding Handler → Transaction Parser → Voucher Objects → Parsed CSV
```

### Match Flow
```
Voucher Objects → Receipt Identifier → ReceiptEvent[]
                → Clearing Identifier → ClearingEvent[]
                → Correction Identifier → CorrectionEvent[]
                → Matching Orchestrator → InvoiceCase[]
                → CSV Generator → Validation Report
```

## File Structure Mapping

```
src/
├── main.py              → CLI Container → Main Controller
├── config.py            → CLI Container → Config Manager
├── logger.py            → CLI Container → Logger
├── content_extractor.py → PDF Processor Container → Content Extractor
├── sie_parser.py        → SIE Parser Container → Summary Parser
├── transaction_parser.py→ SIE Parser Container → Transaction Parser, Voucher Model
├── matcher.py           → Matching Engine Container → All components
└── report_generator.py  → Report Generator Container → CSV Generator

Data/
├── Input/
│   ├── SIE/                    → SIE Files component
│   ├── Verifikationer 2024/    → Input Vouchers component
│   └── Verifikationer 2025/    → Input Vouchers component
└── Output/
    ├── Vouchers/               → Processed PDFs component
    ├── SIE/                    → Parsed SIE component
    └── reports/                → Reports component

logs/                           → Logs component
```

## Technology Stack

- **Language**: Python 3.11+
- **CLI Framework**: argparse
- **PDF Processing**: pdfplumber, ocrmypdf
- **Data Processing**: pandas
- **SIE Parsing**: Custom state machine parser (CP850/CP437 encoding)
- **Logging**: Python logging module
- **File I/O**: pathlib
- **External Storage**: Google Drive (file sync)

## Design Decisions

### Why CP850 encoding for SIE files?
Swedish accounting systems use PC8 format (CP850/CP437) for proper handling of Swedish characters (å, ä, ö). The parser tries CP850 first, then falls back to CP437, latin-1, and utf-8.

### Why transaction-level parsing?
The matching algorithm needs access to individual #TRANS lines to identify:
- Account 2440 transactions (supplier liabilities)
- Account 1930 transactions (bank payments)
- Transaction amounts and dates
- Multiple transactions per voucher

A summary-level parser would lose this critical detail.

### Why separate Receipt and Clearing events?
Swedish double-entry bookkeeping creates two separate vouchers:
1. **Receipt** voucher (invoice received): 2440 Kredit (liability created)
2. **Payment** voucher (invoice paid): 2440 Debet (liability cleared) + 1930 Kredit (bank payment)

The system must identify and match these separately.

### Why correction vouchers?
When 2024 payments were incorrectly posted (bypassing account 2440), the 2024 fiscal year was already locked. Correction vouchers in 2025 Q1 clear the 2024 liabilities without creating new bank transactions. The system detects these by pattern matching in voucher descriptions.

### Why best-match selection for multiple 1930 transactions?
Some vouchers have multiple bank transactions (e.g., partial payments, refunds). The system selects the best matching 1930 transaction per 2440 transaction by preferring exact amount matches, preventing duplicate clearing events.

## Future Enhancements

Potential architectural changes:
- Add database layer for persistent storage (SQLite/PostgreSQL)
- Add web UI container (Flask/FastAPI)
- Add API container for external integrations
- Add PDF content extraction component (invoice data parsing)
- Add reconciliation component (compare PDF vs SIE data)
- Add notification component (email alerts for exceptions)

## References

- [C4 Model](https://c4model.com/) - Architecture diagram standard
- [Structurizr](https://structurizr.com/) - Diagram tooling
- [SIE Format](https://sie.se/) - Swedish accounting file format
- [Double-entry bookkeeping](https://en.wikipedia.org/wiki/Double-entry_bookkeeping) - Accounting principle

## Maintenance

When updating the architecture:

1. **Code changes** → Update `workspace.dsl` components and relationships
2. **New modules** → Add new components to relevant containers
3. **Data flow changes** → Update component relationships
4. **Deployment changes** → Update deployment diagram

Keep diagrams in sync with code to maintain documentation value.
