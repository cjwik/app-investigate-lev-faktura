from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src import config
from src.logger import get_logger
from src.content_extractor import process_pdf_folder


logger = get_logger(__name__)


def _ensure_dirs() -> None:
    config.OUTPUT_VOUCHERS_2024.mkdir(parents=True, exist_ok=True)
    config.OUTPUT_VOUCHERS_2025.mkdir(parents=True, exist_ok=True)
    config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    config.LOGS_DIR.mkdir(parents=True, exist_ok=True)


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
        if year == 2024:
            output_folder = config.OUTPUT_VOUCHERS_2024
        elif year == 2025:
            output_folder = config.OUTPUT_VOUCHERS_2025
        else:
            logger.error(f"Invalid year: {year}")
            continue

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


def cmd_ocr(args: argparse.Namespace) -> int:
    """Process PDFs: copy to output with OCR where needed."""
    _ensure_dirs()

    years = [args.year] if args.year else [2024, 2025]
    limit = args.limit if hasattr(args, 'limit') else None

    overall_stats = {
        'total': 0,
        'copied': 0,
        'ocr_processed': 0,
        'failed': 0,
        'skipped': 0,
        'processing_time': 0
    }

    for year in years:
        if year == 2024:
            input_folder = config.INPUT_VOUCHERS_2024
            output_folder = config.OUTPUT_VOUCHERS_2024
        elif year == 2025:
            input_folder = config.INPUT_VOUCHERS_2025
            output_folder = config.OUTPUT_VOUCHERS_2025
        else:
            logger.error(f"Invalid year: {year}")
            continue

        logger.info(f"Processing year {year}...")
        stats = process_pdf_folder(input_folder, output_folder, year, limit=limit)

        # Aggregate stats
        for key in overall_stats:
            overall_stats[key] += stats.get(key, 0)

    # Final summary
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

    ocr = sub.add_parser("ocr", help="Copy PDFs to output with OCR where needed")
    ocr.add_argument("--year", type=int, choices=[2024, 2025], help="Process specific year (default: both)")
    ocr.add_argument("--limit", type=int, help="Limit number of files for testing (e.g., 5)")
    ocr.set_defaults(func=cmd_ocr)

    for name in ["parse", "match", "full"]:
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
