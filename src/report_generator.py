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

        # Determine review flag
        needs_review = "JA" if case.status != "OK" else "NEJ"

        # Handle cases where receipt is missing (payment without invoice)
        if receipt is None:
            # Extract supplier from clearing voucher instead
            sie_supplier = clearing.extract_supplier() if clearing else ""

            row = {
                # Review flag first (most important column)
                "Behöver granskas": needs_review,

                # SIE Receipt (empty for missing receipt cases)
                "Receipt Voucher Id": "",
                "Receipt Voucher Date": "",
                "Receipt 2440 Amount": "",
                "SIE Supplier": sie_supplier,
                "SIE Text": "",

                # SIE Clearing
                "Clearing Voucher Id": clearing.voucher_id if clearing else "",
                "Clearing Voucher Date": clearing.date.strftime("%Y-%m-%d") if clearing else "",
                "Clearing 2440 Amount": f"{clearing.amount_2440:.2f}".replace(".", ",") if clearing else "",
                "Clearing 1930 Amount": f"{clearing.amount_1930:.2f}".replace(".", ",") if clearing else "",

                # PDF (placeholder - to be implemented in future iteration)
                "PDF Supplier": "",
                "Invoice No": clearing.extract_invoice_number() if clearing else "",
                "PDF Invoice Date": "",
                "PDF Total Amount": "",
                "Currency": "SEK",  # Default for Swedish accounting
                "PDF Filename": "",

                # Validation
                "Status": case.status,
                "Match Confidence": case.match_confidence,
                "Comment": case.comment,
            }
        else:
            # Normal case with receipt
            # Extract supplier from voucher description
            sie_supplier = receipt.extract_supplier()

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


def generate_summary_report_with_bookkeeping(cases: List[InvoiceCase], output_path: Path, all_vouchers: List = None) -> None:
    """
    Generates a financial summary report matching bookkeeping totals.

    Args:
        cases: List of InvoiceCase objects to report on
        output_path: Path where the summary CSV will be saved
        all_vouchers: Optional list of all vouchers (including excluded corrections) for reconciliation
    """
    from src.transaction_parser import Voucher

    logger.info(f"Generating summary report for {len(cases)} invoice cases...")

    # Calculate based on actual bookkeeping (all 2440 transactions including corrections)
    if all_vouchers:
        # Calculate total Kredit (receipts) and Debet (clearings) from ALL vouchers
        total_kredit = 0.0  # Receipts (negative on 2440)
        total_debet = 0.0   # Clearings (positive on 2440)

        for voucher in all_vouchers:
            if voucher.has_account("2440"):
                trans_2440_list = voucher.get_transactions_by_account("2440")
                for trans in trans_2440_list:
                    if trans.amount < 0:
                        total_kredit += abs(trans.amount)  # Kredit (receipts)
                    else:
                        total_debet += abs(trans.amount)   # Debet (clearings)

        # Outstanding = Kredit - Debet (in absolute terms)
        outstanding_balance = total_kredit - total_debet
    else:
        # Fallback to cases-based calculation
        total_kredit = sum(abs(c.receipt.amount_2440) for c in cases)
        total_debet = sum(abs(c.clearing.amount_2440) for c in cases if c.clearing)
        outstanding_balance = total_kredit - total_debet

    # Calculate validation statistics from cases (after excluding corrections)
    total_invoices = len(cases)
    paid_cases = [c for c in cases if c.status == "OK"]
    unpaid_cases = [c for c in cases if c.status == "Missing clearing"]
    missing_receipt_cases = [c for c in cases if c.status == "Missing receipt"]
    review_cases = [c for c in cases if c.status == "Needs review"]

    # Create summary rows matching bookkeeping
    summary_rows = [
        {"Category": "Account 2440 - Bookkeeping Totals", "Count": "", "Amount (SEK)": ""},
        {"Category": "Total Kredit (Receipts)", "Count": "", "Amount (SEK)": f"{total_kredit:.2f}".replace(".", ",")},
        {"Category": "Total Debet (Clearings)", "Count": "", "Amount (SEK)": f"{total_debet:.2f}".replace(".", ",")},
        {"Category": "Outstanding Balance (Utg. saldo)", "Count": "", "Amount (SEK)": f"{outstanding_balance:.2f}".replace(".", ",")},
        {"Category": "", "Count": "", "Amount (SEK)": ""},
        {"Category": "Validation Summary (After Excluding Corrections)", "Count": "", "Amount (SEK)": ""},
        {"Category": "Total Invoice Cases", "Count": total_invoices, "Amount (SEK)": ""},
        {"Category": "  - Paid (OK)", "Count": len(paid_cases), "Amount (SEK)": ""},
        {"Category": "  - Unpaid (Missing clearing)", "Count": len(unpaid_cases), "Amount (SEK)": ""},
        {"Category": "  - Payments without receipt", "Count": len(missing_receipt_cases), "Amount (SEK)": ""},
        {"Category": "  - Needs Review", "Count": len(review_cases), "Amount (SEK)": ""},
    ]

    # Create DataFrame and save
    df = pd.DataFrame(summary_rows)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    logger.info(f"Summary report saved to {output_path}")

    # Log summary to console
    logger.info("=" * 60)
    logger.info("Financial Summary - Bookkeeping Reconciliation")
    logger.info("=" * 60)
    logger.info(f"Account 2440 Totals:")
    logger.info(f"  Kredit (Receipts): {total_kredit:,.2f} SEK")
    logger.info(f"  Debet (Clearings): {total_debet:,.2f} SEK")
    logger.info(f"  Outstanding Balance: {outstanding_balance:,.2f} SEK")
    logger.info(f"")
    logger.info(f"Validation Summary:")
    logger.info(f"  Total Cases: {total_invoices}")
    logger.info(f"  Paid (OK): {len(paid_cases)}")
    logger.info(f"  Unpaid (Missing clearing): {len(unpaid_cases)}")
    logger.info(f"  Payments without receipt: {len(missing_receipt_cases)}")
    logger.info(f"  Needs Review: {len(review_cases)}")
    logger.info("=" * 60)


def generate_summary_report(cases: List[InvoiceCase], output_path: Path) -> None:
    """
    Generates a financial summary report showing outstanding balances.

    Args:
        cases: List of InvoiceCase objects to report on
        output_path: Path where the summary CSV will be saved
    """
    logger.info(f"Generating summary report for {len(cases)} invoice cases...")

    # Calculate totals
    total_invoices = len(cases)
    paid_cases = [c for c in cases if c.status == "OK"]
    unpaid_cases = [c for c in cases if c.status == "Missing clearing"]
    review_cases = [c for c in cases if c.status == "Needs review"]

    # Calculate amounts (absolute values for totals)
    total_invoice_amount = sum(abs(c.receipt.amount_2440) for c in cases)
    paid_amount = sum(abs(c.receipt.amount_2440) for c in paid_cases)
    unpaid_amount = sum(abs(c.receipt.amount_2440) for c in unpaid_cases)
    review_amount = sum(abs(c.receipt.amount_2440) for c in review_cases)

    # Create summary rows
    summary_rows = [
        {"Category": "Total Invoices", "Count": total_invoices, "Amount (SEK)": f"{total_invoice_amount:.2f}".replace(".", ",")},
        {"Category": "Paid (OK)", "Count": len(paid_cases), "Amount (SEK)": f"{paid_amount:.2f}".replace(".", ",")},
        {"Category": "Unpaid (Missing clearing)", "Count": len(unpaid_cases), "Amount (SEK)": f"{unpaid_amount:.2f}".replace(".", ",")},
        {"Category": "Needs Review", "Count": len(review_cases), "Amount (SEK)": f"{review_amount:.2f}".replace(".", ",")},
        {"Category": "", "Count": "", "Amount (SEK)": ""},  # Empty row
        {"Category": "Outstanding Balance", "Count": len(unpaid_cases) + len(review_cases), "Amount (SEK)": f"{unpaid_amount + review_amount:.2f}".replace(".", ",")},
    ]

    # Create DataFrame and save
    df = pd.DataFrame(summary_rows)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    logger.info(f"Summary report saved to {output_path}")

    # Log summary to console
    logger.info("=" * 60)
    logger.info("Financial Summary")
    logger.info("=" * 60)
    logger.info(f"Total Invoices: {total_invoices} ({total_invoice_amount:,.2f} SEK)")
    logger.info(f"Paid (OK): {len(paid_cases)} ({paid_amount:,.2f} SEK)")
    logger.info(f"Unpaid: {len(unpaid_cases)} ({unpaid_amount:,.2f} SEK)")
    logger.info(f"Needs Review: {len(review_cases)} ({review_amount:,.2f} SEK)")
    logger.info(f"Outstanding Balance: {len(unpaid_cases) + len(review_cases)} ({unpaid_amount + review_amount:,.2f} SEK)")
    logger.info("=" * 60)


def generate_both_reports(cases: List[InvoiceCase], reports_dir: Path, year: int, all_vouchers: List = None) -> Path:
    """
    Generates the combined validation report with review flag and summary report.

    Args:
        cases: List of InvoiceCase objects
        reports_dir: Directory to save reports
        year: Year for filename
        all_vouchers: Optional list of all vouchers (including excluded corrections) for bookkeeping reconciliation

    Returns:
        Path to the generated report file
    """
    reports_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Combined report with review flag
    combined_path = reports_dir / f"invoice_validation_{year}_{timestamp}.csv"
    generate_combined_report(cases, combined_path)

    # Summary report
    summary_path = reports_dir / f"summary_{year}_{timestamp}.csv"
    generate_summary_report_with_bookkeeping(cases, summary_path, all_vouchers)

    return combined_path
