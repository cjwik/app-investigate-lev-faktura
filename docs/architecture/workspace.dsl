workspace "Wik Invoice Validation System" "C4 Architecture for Swedish supplier invoice validation and reconciliation" {

    model {
        # People
        bookkeeper = person "Bookkeeper" "Small business owner who needs to validate supplier invoices against accounting records"

        # External Systems
        googleDrive = softwareSystem "Google Drive" "Cloud storage for accounting documents and SIE files" "External System"
        accountingSystem = softwareSystem "Accounting System" "Swedish accounting system that exports SIE format files" "External System"

        # Main System
        invoiceValidation = softwareSystem "Invoice Validation System" "Validates supplier invoices against SIE accounting data, detects unpaid invoices and payments without receipts" {

            # CLI Container
            cli = container "CLI Application" "Command-line interface for processing pipeline" "Python" {
                mainController = component "Main Controller" "Orchestrates workflow commands (setup, ocr, parse, match, clean)" "src/main.py"
                configManager = component "Config Manager" "Manages file paths and system settings" "src/config.py"
                logger = component "Logger" "Centralized logging for all operations" "src/logger.py"
            }

            # PDF Processing Container
            pdfProcessor = container "PDF Processor" "Extracts text from invoice PDFs with OCR fallback" "Python + OCRmyPDF" {
                contentExtractor = component "Content Extractor" "Checks PDF text and applies OCR when needed" "src/content_extractor.py"
                pdfPlumberEngine = component "PDFPlumber Engine" "Extracts embedded text from PDFs" "pdfplumber library"
                ocrEngine = component "OCR Engine" "Performs OCR on image-only PDFs" "ocrmypdf library"
            }

            # SIE Parsing Container
            sieParser = container "SIE Parser" "Parses Swedish SIE accounting files" "Python + Pandas" {
                summaryParser = component "Summary Parser" "Extracts voucher summaries for overview" "src/sie_parser.py"
                transactionParser = component "Transaction Parser" "Extracts transaction-level detail for matching" "src/transaction_parser.py"
                encodingHandler = component "Encoding Handler" "Handles CP850/CP437 Swedish character encoding" "Built into parsers"
                voucherModel = component "Voucher Model" "Domain model for vouchers and transactions" "Voucher, Transaction classes"
            }

            # Matching Engine Container
            matchingEngine = container "Matching Engine" "Matches invoices with payments using account 2440 and 1930" "Python" {
                invoiceMatcher = component "Invoice Matcher" "Core matching algorithm" "src/matcher.py::InvoiceMatcher"
                receiptIdentifier = component "Receipt Identifier" "Identifies 2440 Kredit (receipts)" "identify_receipts()"
                clearingIdentifier = component "Clearing Identifier" "Identifies 2440 Debet + 1930 (payments)" "identify_clearings()"
                correctionIdentifier = component "Correction Identifier" "Detects accounting correction vouchers" "identify_corrections()"
                matchingOrchestrator = component "Matching Orchestrator" "Coordinates matching workflow" "match_all()"
                eventModels = component "Event Models" "ReceiptEvent, ClearingEvent, CorrectionEvent, InvoiceCase" "dataclasses"
            }

            # Report Generator Container
            reportGenerator = container "Report Generator" "Generates CSV validation reports" "Python + Pandas" {
                csvGenerator = component "CSV Generator" "Creates validation and summary reports" "src/report_generator.py"
                summaryCalculator = component "Summary Calculator" "Calculates totals and statistics" "generate_both_reports()"
            }

            # Data Storage Container
            dataStorage = container "File System Storage" "Stores input data, processed files, and reports" "File System" {
                inputVouchers = component "Input Vouchers" "Original PDF vouchers by year" "Data/Input/Verifikationer"
                sieFiles = component "SIE Files" "Accounting export files" "Data/Input/SIE"
                processedPdfs = component "Processed PDFs" "OCR-processed PDFs" "Data/Output/Vouchers"
                parsedSie = component "Parsed SIE" "CSV exports of SIE data" "Data/Output/SIE"
                reports = component "Reports" "Validation and summary reports" "Data/Output/reports"
                logs = component "Logs" "Processing and error logs" "logs/"
            }
        }

        # Relationships - User interactions
        bookkeeper -> cli "Runs commands via CLI" "Command line"
        bookkeeper -> googleDrive "Uploads/downloads accounting documents" "HTTPS"
        accountingSystem -> googleDrive "Exports SIE files" "HTTPS"

        # Relationships - System to External
        cli -> googleDrive "Reads input files from synced folder" "File I/O"
        reportGenerator -> googleDrive "Writes reports to synced folder" "File I/O"

        # Relationships - Between Containers
        cli -> pdfProcessor "Initiates OCR processing" "Function call"
        cli -> sieParser "Initiates SIE parsing" "Function call"
        cli -> matchingEngine "Initiates matching" "Function call"
        cli -> reportGenerator "Generates reports" "Function call"
        cli -> dataStorage "Manages directories" "File I/O"

        pdfProcessor -> dataStorage "Reads input PDFs, writes processed PDFs" "File I/O"
        sieParser -> dataStorage "Reads SIE files, writes parsed CSV" "File I/O"
        matchingEngine -> sieParser "Uses parsed vouchers" "In-memory objects"
        reportGenerator -> dataStorage "Writes CSV reports" "File I/O"
        reportGenerator -> matchingEngine "Uses InvoiceCase results" "In-memory objects"

        # Relationships - Component Level (CLI)
        mainController -> configManager "Gets file paths and settings" "Import"
        mainController -> logger "Logs operations" "Function call"
        mainController -> contentExtractor "Executes OCR command" "Function call"
        mainController -> summaryParser "Executes parse command" "Function call"
        mainController -> transactionParser "Executes match command (loads vouchers)" "Function call"
        mainController -> invoiceMatcher "Executes match command (matching)" "Function call"
        mainController -> csvGenerator "Executes match command (reporting)" "Function call"

        # Relationships - Component Level (PDF Processor)
        contentExtractor -> pdfPlumberEngine "Checks for embedded text" "Library call"
        contentExtractor -> ocrEngine "Performs OCR when needed" "Library call"
        contentExtractor -> inputVouchers "Reads input PDFs" "File I/O"
        contentExtractor -> processedPdfs "Writes processed PDFs" "File I/O"

        # Relationships - Component Level (SIE Parser)
        summaryParser -> encodingHandler "Decodes CP850/CP437" "Built-in"
        summaryParser -> sieFiles "Reads SIE files" "File I/O"
        summaryParser -> parsedSie "Writes CSV summaries" "File I/O"
        transactionParser -> encodingHandler "Decodes CP850/CP437" "Built-in"
        transactionParser -> sieFiles "Reads SIE files" "File I/O"
        transactionParser -> voucherModel "Creates Voucher objects" "Object instantiation"

        # Relationships - Component Level (Matching Engine)
        matchingOrchestrator -> correctionIdentifier "Step 0: Detect corrections" "Function call"
        matchingOrchestrator -> receiptIdentifier "Step 1: Identify receipts (2440 Kredit)" "Function call"
        matchingOrchestrator -> clearingIdentifier "Step 1: Identify clearings (2440 Debet + 1930)" "Function call"
        matchingOrchestrator -> correctionIdentifier "Step 1.5: Identify correction events" "Function call"
        matchingOrchestrator -> eventModels "Creates InvoiceCase objects" "Object instantiation"
        receiptIdentifier -> voucherModel "Analyzes voucher transactions" "Method call"
        clearingIdentifier -> voucherModel "Analyzes voucher transactions" "Method call"
        correctionIdentifier -> voucherModel "Analyzes voucher transactions" "Method call"
        receiptIdentifier -> eventModels "Creates ReceiptEvent" "Object instantiation"
        clearingIdentifier -> eventModels "Creates ClearingEvent" "Object instantiation"
        correctionIdentifier -> eventModels "Creates CorrectionEvent" "Object instantiation"

        # Relationships - Component Level (Report Generator)
        csvGenerator -> summaryCalculator "Generates both validation and summary" "Function call"
        csvGenerator -> eventModels "Reads InvoiceCase data" "Object access"
        csvGenerator -> reports "Writes CSV files" "File I/O"

        # Deployment - Development Environment
        deploymentEnvironment "Development" {
            deploymentNode "Developer Laptop" "" "Windows/Mac/Linux" {
                deploymentNode "Python Runtime" "" "Python 3.11+" {
                    cliInstance = containerInstance cli
                    pdfProcessorInstance = containerInstance pdfProcessor
                    sieParserInstance = containerInstance sieParser
                    matchingEngineInstance = containerInstance matchingEngine
                    reportGeneratorInstance = containerInstance reportGenerator
                }
                deploymentNode "File System" "" "NTFS/ext4/APFS" {
                    dataStorageInstance = containerInstance dataStorage
                }
            }
            deploymentNode "Google Drive" "" "Cloud" {
                googleDriveSync = infrastructureNode "Google Drive Sync Client" "" "Desktop client"
            }
        }
    }

    views {
        # System Context View
        systemContext invoiceValidation "SystemContext" {
            include *
            autoLayout lr
        }

        # Container View
        container invoiceValidation "Containers" {
            include *
            autoLayout lr
        }

        # Component View - Matching Engine (Core Business Logic)
        component matchingEngine "MatchingEngineComponents" {
            include *
            autoLayout tb
        }

        # Component View - Complete Pipeline
        component cli "CLIComponents" {
            include *
            include mainController configManager logger contentExtractor summaryParser transactionParser invoiceMatcher csvGenerator
            autoLayout lr
        }

        # Deployment View
        deployment invoiceValidation "Development" "Deployment" {
            include *
            autoLayout lr
        }

        # Styling
        styles {
            element "Software System" {
                background #1168bd
                color #ffffff
            }
            element "External System" {
                background #999999
                color #ffffff
            }
            element "Person" {
                shape person
                background #08427b
                color #ffffff
            }
            element "Container" {
                background #438dd5
                color #ffffff
            }
            element "Component" {
                background #85bbf0
                color #000000
            }
            element "Infrastructure Node" {
                background #cccccc
                color #000000
            }
        }

        # Themes
        theme default
    }
}
