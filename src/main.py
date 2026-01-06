from __future__ import annotations

import argparse
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src import config
from src.logger import get_logger
from src.content_extractor import process_pdf_folder
from src.sie_parser import parse_sie_file
from src.transaction_parser import parse_sie_transactions
from src.matcher import InvoiceMatcher
from src.report_generator import generate_both_reports

logger = get_logger(__name__)


def _ensure_dirs() -> None:
    config.OUTPUT_VOUCHERS_2024.mkdir(parents=True, exist_ok=True)
    config.OUTPUT_VOUCHERS_2025.mkdir(parents=True, exist_ok=True)
    config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    # Ensure the new SIE output directory exists
    config.SIE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def cmd_setup(_: argparse.Namespace) -> int:
    _ensure_dirs()

    missing_inputs = []
    for p in [config.INPUT_DIR, config.SIE_DIR, config.INPUT_VOUCHERS_2024, config.INPUT_VOUCHERS_2025]:
        if not p.exists():
            missing_inputs.append(p)

    logger.info("Base dir: %s", config.BASE_DIR)
    logger.info("Data dir: %s", config.DATA_DIR)
    logger.info("Output dir: %s", config.OUTPUT_DIR)
    logger.info("Logs dir: %s", config.LOGS_DIR)
    logger.info("SIE Output dir: %s", config.SIE_OUTPUT_DIR)

    if missing_inputs:
        for p in missing_inputs:
            logger.error("Missing expected input path: %s", p)
        return 2

    logger.info("Setup OK")
    return 0


def cmd_ocrclean(args: argparse.Namespace) -> int:
    """Remove all OCR-processed PDFs from output folders."""
    years = [args.year] if args.year else [2024, 2025]
    total_removed = 0
    for year in years:
        output_folder = config.OUTPUT_VOUCHERS_2024 if year == 2024 else config.OUTPUT_VOUCHERS_2025
        if not output_folder.exists():
            logger.info(f"Output folder does not exist: {output_folder}")
            continue
        pdf_files = list(output_folder.glob("*.pdf"))
        if not pdf_files:
            logger.info(f"No PDFs to remove in {year}")
            continue
        logger.info(f"Removing {len(pdf_files)} PDFs from {year}...")
        for pdf_file in pdf_files:
            try:
                pdf_file.unlink()
                total_removed += 1
            except Exception as e:
                logger.error(f"Failed to remove {pdf_file.name}: {e}")
    logger.info(f"OCR clean complete: {total_removed} files removed")
    return 0


def cmd_parseclean(args: argparse.Namespace) -> int:
    """Remove all parsed SIE output files."""
    if not config.SIE_OUTPUT_DIR.exists():
        logger.info(f"SIE output folder does not exist: {config.SIE_OUTPUT_DIR}")
        return 0

    # Find all CSV and TXT files in SIE output directory
    csv_files = list(config.SIE_OUTPUT_DIR.glob("sie_data_*.csv"))
    txt_files = list(config.SIE_OUTPUT_DIR.glob("sie_summary_*.txt"))
    all_files = csv_files + txt_files

    if not all_files:
        logger.info("No parsed SIE files to remove")
        return 0

    logger.info(f"Removing {len(all_files)} parsed SIE files ({len(csv_files)} CSV, {len(txt_files)} TXT)...")
    total_removed = 0
    for file in all_files:
        try:
            file.unlink()
            total_removed += 1
            logger.debug(f"Removed: {file.name}")
        except Exception as e:
            logger.error(f"Failed to remove {file.name}: {e}")

    logger.info(f"Parse clean complete: {total_removed} files removed")
    return 0


def cmd_matchclean(args: argparse.Namespace) -> int:
    """Remove all matching report files."""
    if not config.REPORTS_DIR.exists():
        logger.info(f"Reports folder does not exist: {config.REPORTS_DIR}")
        return 0

    # Find all CSV files in reports directory (validation and any old exception files)
    validation_files = list(config.REPORTS_DIR.glob("invoice_validation_*.csv"))
    exception_files = list(config.REPORTS_DIR.glob("invoice_exceptions_*.csv"))
    summary_files = list(config.REPORTS_DIR.glob("summary_*.csv"))
    report_files = validation_files + exception_files + summary_files

    if not report_files:
        logger.info("No report files to remove")
        return 0

    logger.info(f"Removing {len(report_files)} report files...")
    total_removed = 0
    for file in report_files:
        try:
            file.unlink()
            total_removed += 1
            logger.debug(f"Removed: {file.name}")
        except Exception as e:
            logger.error(f"Failed to remove {file.name}: {e}")

    logger.info(f"Match clean complete: {total_removed} files removed")
    return 0


def cmd_ocr(args: argparse.Namespace) -> int:
    """Process PDFs: copy to output with OCR where needed."""
    _ensure_dirs()
    years = [args.year] if args.year else [2024, 2025]
    limit = args.limit if hasattr(args, 'limit') else None
    overall_stats = {'total': 0, 'copied': 0, 'ocr_processed': 0, 'failed': 0, 'skipped': 0, 'processing_time': 0}
    for year in years:
        input_folder = config.INPUT_VOUCHERS_2024 if year == 2024 else config.INPUT_VOUCHERS_2025
        output_folder = config.OUTPUT_VOUCHERS_2024 if year == 2024 else config.OUTPUT_VOUCHERS_2025
        logger.info(f"Processing year {year}...")
        stats = process_pdf_folder(input_folder, output_folder, year, limit=limit)
        for key in overall_stats:
            overall_stats[key] += stats.get(key, 0)
    logger.info("=" * 60)
    logger.info("OCR Processing Complete")
    logger.info("=" * 60)
    logger.info(f"Total files: {overall_stats['total']}")
    logger.info(f"Copied (already had text): {overall_stats['copied']}")
    logger.info(f"OCR processed (image PDFs): {overall_stats['ocr_processed']}")
    logger.info(f"Failed: {overall_stats['failed']}")
    logger.info(f"Skipped (already processed): {overall_stats['skipped']}")
    logger.info(f"Total time: {overall_stats['processing_time']:.1f}s")
    if overall_stats['failed'] > 0:
        logger.warning(f"{overall_stats['failed']} files failed processing")
        return 1
    return 0


def cmd_parse(args: argparse.Namespace) -> int:
    """Parse SIE files and extract verification data."""
    _ensure_dirs()
    years = [args.year] if args.year else [2024, 2025]
    start_time = time.time()

    for year in years:
        logger.info(f"Parsing SIE file for year {year}...")
        sie_file = next(config.SIE_DIR.glob(f"{year}*.se"), None)

        if not sie_file:
            logger.error(f"No SIE file found for year {year} in {config.SIE_DIR}")
            continue

        df = parse_sie_file(sie_file)

        if df.empty:
            logger.warning(f"Parsing resulted in an empty DataFrame for {sie_file.name}. No output will be generated.")
            continue

        # Save the output to the new directory
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = config.SIE_OUTPUT_DIR / f"sie_data_{year}_{ts}.csv"
        summary_path = config.SIE_OUTPUT_DIR / f"sie_summary_{year}_{ts}.txt"

        # Save CSV
        df.to_csv(csv_path, index=False, date_format='%Y-%m-%d')
        logger.info(f"Successfully saved parsed data to {csv_path}")

        # Generate and save summary report
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(f"SIE Parsing Summary\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"=== FILE: {sie_file.name} ===\n")
            f.write(f"Total verifications: {len(df)}\n")
            f.write(f"Date range: {df['trans_date'].min().date()} to {df['trans_date'].max().date()}\n\n")
            
            unbalanced = df[abs(df['total_amount']) > 0.01]
            f.write(f"=== VALIDATION ===\n")
            f.write(f"Balanced entries: {len(df) - len(unbalanced)}/{len(df)}\n")
            f.write(f"Unbalanced entries: {len(unbalanced)}\n\n")

            f.write(f"=== AMOUNTS ===\n")
            f.write(f"Min target_amount: {df['target_amount'].min():.2f} kr\n")
            f.write(f"Max target_amount: {df['target_amount'].max():.2f} kr\n")
            f.write(f"Average target_amount: {df['target_amount'].mean():.2f} kr\n\n")

            f.write(f"=== SERIES ===\n")
            for series, count in df['series'].value_counts().items():
                f.write(f"Series {series}: {count} verifications\n")
        
        logger.info(f"Successfully saved summary to {summary_path}")

    total_time = time.time() - start_time
    logger.info(f"SIE parsing finished in {total_time:.2f}s")
    return 0


def cmd_match(args: argparse.Namespace) -> int:
    """Match supplier invoices with clearing vouchers."""
    _ensure_dirs()
    years = [args.year] if args.year else [2024, 2025]
    max_days = args.max_days if hasattr(args, 'max_days') else 120
    start_time = time.time()

    # Track closing balances for each year to use as opening balance for next year
    closing_balances = {}

    for year in years:
        logger.info(f"Processing matching for year {year}...")
        sie_file = next(config.SIE_DIR.glob(f"{year}*.se"), None)

        if not sie_file:
            logger.error(f"No SIE file found for year {year} in {config.SIE_DIR}")
            continue

        # Parse SIE file with transaction-level detail
        vouchers = parse_sie_transactions(sie_file)

        if not vouchers:
            logger.warning(f"No vouchers parsed from {sie_file.name}")
            continue

        # For cross-year matching: also load next year's data for clearings
        # This allows 2024 invoices to find 2025 payments
        all_vouchers_for_matching = list(vouchers)
        next_year = year + 1
        next_year_sie = next(config.SIE_DIR.glob(f"{next_year}*.se"), None)

        if next_year_sie:
            logger.info(f"Loading {next_year} data for cross-year matching...")
            next_year_vouchers = parse_sie_transactions(next_year_sie)
            if next_year_vouchers:
                all_vouchers_for_matching.extend(next_year_vouchers)
                logger.info(f"Added {len(next_year_vouchers)} vouchers from {next_year} for cross-year clearing detection")

        # Also load previous year's data for cross-year clearing detection
        # This allows 2025 clearings to match 2024 receipts
        prev_year = year - 1
        prev_year_sie = next(config.SIE_DIR.glob(f"{prev_year}*.se"), None)

        prev_year_vouchers = None
        if prev_year_sie:
            logger.info(f"Loading {prev_year} data for cross-year clearing detection...")
            prev_year_vouchers = parse_sie_transactions(prev_year_sie)
            if prev_year_vouchers:
                all_vouchers_for_matching.extend(prev_year_vouchers)
                logger.info(f"Added {len(prev_year_vouchers)} vouchers from {prev_year} for cross-year clearing detection")

        # Calculate previous year's closing balance if not already cached
        prev_year_closing_balance = None
        if prev_year not in closing_balances and prev_year_vouchers:
            # Calculate closing balance from previous year's vouchers
            prev_kredit = 0.0
            prev_debet = 0.0
            for voucher in prev_year_vouchers:
                if voucher.has_account("2440"):
                    trans_2440_list = voucher.get_transactions_by_account("2440")
                    for trans in trans_2440_list:
                        if trans.amount < 0:
                            prev_kredit += abs(trans.amount)
                        else:
                            prev_debet += abs(trans.amount)
            prev_year_closing_balance = prev_kredit - prev_debet
            closing_balances[prev_year] = prev_year_closing_balance
            logger.info(f"Calculated {prev_year} closing balance: {prev_year_closing_balance:,.2f} SEK")
        elif prev_year in closing_balances:
            prev_year_closing_balance = closing_balances[prev_year]

        # Perform matching with current year receipts and all available clearings
        matcher = InvoiceMatcher(max_days=max_days)
        cases = matcher.match_all(all_vouchers_for_matching, receipt_year=year)

        if not cases:
            logger.warning(f"No invoice cases generated for {year}")
            continue

        # Generate report (pass only current year vouchers for bookkeeping reconciliation)
        report_path = generate_both_reports(cases, config.REPORTS_DIR, year, all_vouchers=vouchers, prev_year_closing_balance=prev_year_closing_balance)
        logger.info(f"Report generated: {report_path.name}")

        # Calculate and store current year's closing balance for next iteration
        curr_kredit = 0.0
        curr_debet = 0.0
        for voucher in vouchers:
            if voucher.has_account("2440"):
                trans_2440_list = voucher.get_transactions_by_account("2440")
                for trans in trans_2440_list:
                    if trans.amount < 0:
                        curr_kredit += abs(trans.amount)
                    else:
                        curr_debet += abs(trans.amount)
        closing_balances[year] = (prev_year_closing_balance or 0.0) + (curr_kredit - curr_debet)

    total_time = time.time() - start_time
    logger.info(f"Matching finished in {total_time:.2f}s")
    return 0


def cmd_not_implemented(args: argparse.Namespace) -> int:
    logger.error("%s not implemented yet (see docs/)", args.command)
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="investigationlevfaktura")
    sub = parser.add_subparsers(dest="command", required=True)

    setup = sub.add_parser("setup", help="Create output folders and verify data paths")
    setup.set_defaults(func=cmd_setup)

    ocrclean = sub.add_parser("ocrclean", help="Remove all OCR-processed PDFs from output folders")
    ocrclean.add_argument("--year", type=int, choices=[2024, 2025], help="Clean specific year (default: both)")
    ocrclean.set_defaults(func=cmd_ocrclean)

    parseclean = sub.add_parser("parseclean", help="Remove all parsed SIE output files")
    parseclean.set_defaults(func=cmd_parseclean)

    matchclean = sub.add_parser("matchclean", help="Remove all matching report files")
    matchclean.set_defaults(func=cmd_matchclean)

    ocr = sub.add_parser("ocr", help="Copy PDFs to output with OCR where needed")
    ocr.add_argument("--year", type=int, choices=[2024, 2025], help="Process specific year (default: both)")
    ocr.add_argument("--limit", type=int, help="Limit number of files for testing (e.g., 5)")
    ocr.set_defaults(func=cmd_ocr)

    # Add the new parse command
    parse_cmd = sub.add_parser("parse", help="Parse SIE files and extract verification data")
    parse_cmd.add_argument("--year", type=int, choices=[2024, 2025], help="Process specific year (default: both)")
    parse_cmd.set_defaults(func=cmd_parse)

    # Add the match command
    match_cmd = sub.add_parser("match", help="Match supplier invoices with clearing vouchers")
    match_cmd.add_argument("--year", type=int, choices=[2024, 2025], help="Process specific year (default: both)")
    match_cmd.add_argument("--max-days", type=int, default=120, help="Maximum days to search for clearing (default: 120)")
    match_cmd.set_defaults(func=cmd_match)

    for name in ["full"]:
        p = sub.add_parser(name, help="Not implemented yet (see docs/)")
        p.set_defaults(func=cmd_not_implemented)

    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
