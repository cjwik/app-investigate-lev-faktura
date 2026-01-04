# src/report_generator.py

"""
Report generator for supplier invoice validation.

Creates CSV/Excel output with all required columns per the matching requirements.
Each row represents one invoice case (one 2440 receipt line).
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import List

import pandas as pd

from src.matcher import InvoiceCase

logger = logging.getLogger(__name__)


def generate_report(cases: List[InvoiceCase], output_path: Path) -> None:
    """
    Generates a CSV report from invoice cases.

    Args:
        cases: List of InvoiceCase objects to report on
        output_path: Path where the CSV file will be saved
    """
    logger.info(f"Generating report for {len(cases)} invoice cases...")

    rows = []
    for case in cases:
        receipt = case.receipt
        clearing = case.clearing

        # Extract supplier from voucher description
        sie_supplier = receipt.extract_supplier()

        # Build row data (using Swedish number format: comma as decimal separator)
        row = {
            # SIE Receipt
            "Receipt Voucher Id": receipt.voucher_id,
            "Receipt Voucher Date": receipt.date.strftime("%Y-%m-%d"),
            "Receipt 2440 Amount": f"{receipt.amount_2440:.2f}".replace(".", ","),
            "SIE Supplier": sie_supplier,
            "SIE Text": receipt.description,

            # SIE Clearing
            "Clearing Voucher Id": clearing.voucher_id if clearing else "",
            "Clearing Voucher Date": clearing.date.strftime("%Y-%m-%d") if clearing else "",
            "Clearing 2440 Amount": f"{clearing.amount_2440:.2f}".replace(".", ",") if clearing else "",
            "Clearing 1930 Amount": f"{clearing.amount_1930:.2f}".replace(".", ",") if clearing else "",

            # PDF (placeholder - to be implemented in future iteration)
            "PDF Supplier": "",
            "Invoice No": "",
            "PDF Invoice Date": "",
            "PDF Total Amount": "",
            "Currency": "SEK",  # Default for Swedish accounting
            "PDF Filename": "",

            # Validation
            "Status": case.status,
            "Match Confidence": case.match_confidence,
            "Comment": case.comment,
        }
        rows.append(row)

    # Create DataFrame
    df = pd.DataFrame(rows)

    # Save to CSV
    df.to_csv(output_path, index=False, encoding="utf-8-sig")  # utf-8-sig for Excel compatibility
    logger.info(f"Report saved to {output_path}")

    # Log statistics
    logger.info(f"Total rows: {len(df)}")
    logger.info(f"Status breakdown:")
    for status, count in df["Status"].value_counts().items():
        logger.info(f"  - {status}: {count}")


def generate_exceptions_report(cases: List[InvoiceCase], output_path: Path) -> None:
    """
    Generates an exceptions report (non-OK statuses only).

    Args:
        cases: List of InvoiceCase objects to report on
        output_path: Path where the exceptions CSV will be saved
    """
    # Filter to non-OK cases
    exception_cases = [c for c in cases if c.status != "OK"]

    logger.info(f"Generating exceptions report for {len(exception_cases)} cases...")

    if not exception_cases:
        logger.info("No exceptions found - all cases are OK")
        return

    rows = []
    for case in exception_cases:
        receipt = case.receipt
        clearing = case.clearing

        sie_supplier = receipt.extract_supplier()

        row = {
            # SIE Receipt
            "Receipt Voucher Id": receipt.voucher_id,
            "Receipt Voucher Date": receipt.date.strftime("%Y-%m-%d"),
            "Receipt 2440 Amount": f"{receipt.amount_2440:.2f}".replace(".", ","),
            "SIE Supplier": sie_supplier,
            "SIE Text": receipt.description,

            # SIE Clearing
            "Clearing Voucher Id": clearing.voucher_id if clearing else "",
            "Clearing Voucher Date": clearing.date.strftime("%Y-%m-%d") if clearing else "",
            "Clearing 2440 Amount": f"{clearing.amount_2440:.2f}".replace(".", ",") if clearing else "",
            "Clearing 1930 Amount": f"{clearing.amount_1930:.2f}".replace(".", ",") if clearing else "",

            # PDF (placeholder)
            "PDF Supplier": "",
            "Invoice No": "",
            "PDF Invoice Date": "",
            "PDF Total Amount": "",
            "Currency": "SEK",
            "PDF Filename": "",

            # Validation
            "Status": case.status,
            "Match Confidence": case.match_confidence,
            "Comment": case.comment,
        }
        rows.append(row)

    df = pd.DataFrame(rows)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    logger.info(f"Exceptions report saved to {output_path}")
    logger.info(f"Exception types:")
    for status, count in df["Status"].value_counts().items():
        logger.info(f"  - {status}: {count}")


def generate_combined_report(cases: List[InvoiceCase], output_path: Path) -> None:
    """
    Generates a single combined report with review flag column.

    Args:
        cases: List of InvoiceCase objects to report on
        output_path: Path where the CSV file will be saved
    """
    logger.info(f"Generating combined report for {len(cases)} invoice cases...")

    rows = []
    for case in cases:
        receipt = case.receipt
        clearing = case.clearing

        # Extract supplier from voucher description
        sie_supplier = receipt.extract_supplier()

        # Determine review flag
        needs_review = "JA" if case.status != "OK" else "NEJ"

        # Build row data (using Swedish number format: comma as decimal separator)
        row = {
            # Review flag first (most important column)
            "Behöver granskas": needs_review,

            # SIE Receipt
            "Receipt Voucher Id": receipt.voucher_id,
            "Receipt Voucher Date": receipt.date.strftime("%Y-%m-%d"),
            "Receipt 2440 Amount": f"{receipt.amount_2440:.2f}".replace(".", ","),
            "SIE Supplier": sie_supplier,
            "SIE Text": receipt.description,

            # SIE Clearing
            "Clearing Voucher Id": clearing.voucher_id if clearing else "",
            "Clearing Voucher Date": clearing.date.strftime("%Y-%m-%d") if clearing else "",
            "Clearing 2440 Amount": f"{clearing.amount_2440:.2f}".replace(".", ",") if clearing else "",
            "Clearing 1930 Amount": f"{clearing.amount_1930:.2f}".replace(".", ",") if clearing else "",

            # PDF (placeholder - to be implemented in future iteration)
            "PDF Supplier": "",
            "Invoice No": "",
            "PDF Invoice Date": "",
            "PDF Total Amount": "",
            "Currency": "SEK",  # Default for Swedish accounting
            "PDF Filename": "",

            # Validation
            "Status": case.status,
            "Match Confidence": case.match_confidence,
            "Comment": case.comment,
        }
        rows.append(row)

    # Create DataFrame
    df = pd.DataFrame(rows)

    # Save to CSV
    df.to_csv(output_path, index=False, encoding="utf-8-sig")  # utf-8-sig for Excel compatibility
    logger.info(f"Combined report saved to {output_path}")

    # Log statistics
    logger.info(f"Total rows: {len(df)}")
    logger.info(f"Needs review: {(df['Behöver granskas'] == 'JA').sum()}")
    logger.info(f"Status breakdown:")
    for status, count in df["Status"].value_counts().items():
        logger.info(f"  - {status}: {count}")


def generate_both_reports(cases: List[InvoiceCase], reports_dir: Path, year: int) -> Path:
    """
    Generates the combined validation report with review flag.

    Args:
        cases: List of InvoiceCase objects
        reports_dir: Directory to save reports
        year: Year for filename

    Returns:
        Path to the generated report file
    """
    reports_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Combined report with review flag
    combined_path = reports_dir / f"invoice_validation_{year}_{timestamp}.csv"
    generate_combined_report(cases, combined_path)

    return combined_path
