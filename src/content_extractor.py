"""
Content extraction module for PDF processing.

This module handles copying PDFs from Input to Output folders,
with OCR processing only when needed (text-first approach).
"""

from __future__ import annotations

import shutil
import time
from pathlib import Path
from typing import Literal

import pdfplumber
from tqdm import tqdm

try:
    import ocrmypdf
except ImportError:
    ocrmypdf = None

from src.logger import get_logger

logger = get_logger(__name__)


def check_pdf_has_text(pdf_path: Path, min_chars: int = 50) -> bool:
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
            # Check first 3 pages only (performance optimization)
            for page in pdf.pages[:3]:
                page_text = page.extract_text()
                if page_text:
                    text += page_text
                if len(text) >= min_chars:
                    return True
            return len(text) >= min_chars
    except Exception as e:
        logger.error(f"Error checking PDF {pdf_path.name}: {e}")
        return False


def process_single_pdf(
    input_path: Path,
    output_path: Path,
    force_ocr: bool = False
) -> dict:
    """
    Process a single PDF: copy if has text, OCR if needed.

    Args:
        input_path: Source PDF path
        output_path: Destination PDF path
        force_ocr: If True, always OCR (skip text check)

    Returns:
        dict with keys: status, processing_time, error
    """
    start_time = time.time()

    try:
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Check if we need OCR
        needs_ocr = force_ocr or not check_pdf_has_text(input_path)

        if needs_ocr:
            # OCR processing required
            if ocrmypdf is None:
                return {
                    'status': 'failed',
                    'processing_time': time.time() - start_time,
                    'error': 'ocrmypdf not installed'
                }

            logger.info(f"OCR processing: {input_path.name}")
            try:
                # Try Swedish first, fallback to English if not available
                try:
                    ocrmypdf.ocr(
                        input_path,
                        output_path,
                        language='swe',  # Swedish language
                        skip_text=True,   # Skip pages that already have text
                        progress_bar=False,
                        quiet=True
                    )
                except Exception as e:
                    if 'language data' in str(e).lower():
                        logger.warning(f"Swedish language not available, using English for {input_path.name}")
                        ocrmypdf.ocr(
                            input_path,
                            output_path,
                            language='eng',  # Fallback to English
                            skip_text=True,
                            progress_bar=False,
                            quiet=True
                        )
                    else:
                        raise
                status: Literal['copied', 'ocr_processed', 'failed'] = 'ocr_processed'
            except Exception as e:
                logger.error(f"OCR failed for {input_path.name}: {e}")
                return {
                    'status': 'failed',
                    'processing_time': time.time() - start_time,
                    'error': str(e)
                }
        else:
            # Simple copy (PDF already has text)
            logger.debug(f"Copying (has text): {input_path.name}")
            shutil.copy2(input_path, output_path)
            status = 'copied'

        processing_time = time.time() - start_time
        return {
            'status': status,
            'processing_time': processing_time,
            'error': None
        }

    except Exception as e:
        logger.error(f"Error processing {input_path.name}: {e}")
        return {
            'status': 'failed',
            'processing_time': time.time() - start_time,
            'error': str(e)
        }


def process_pdf_folder(
    input_folder: Path,
    output_folder: Path,
    year: int,
    limit: int | None = None,
    force_ocr: bool = False
) -> dict:
    """
    Process all PDFs in a folder: copy to output with OCR where needed.

    Args:
        input_folder: Source folder with PDFs
        output_folder: Destination folder
        year: Year for logging/reporting
        limit: Optional limit for testing (e.g., 5 files)
        force_ocr: If True, OCR all files

    Returns:
        dict with processing statistics
    """
    if not input_folder.exists():
        logger.error(f"Input folder not found: {input_folder}")
        return {
            'total': 0,
            'copied': 0,
            'ocr_processed': 0,
            'failed': 0,
            'skipped': 0,
            'processing_time': 0
        }

    # Get list of PDF files
    pdf_files = sorted(input_folder.glob("*.pdf"))

    if limit:
        pdf_files = pdf_files[:limit]
        logger.info(f"Processing limited to {limit} files (testing mode)")

    if not pdf_files:
        logger.warning(f"No PDF files found in {input_folder}")
        return {
            'total': 0,
            'copied': 0,
            'ocr_processed': 0,
            'failed': 0,
            'skipped': 0,
            'processing_time': 0
        }

    # Ensure output folder exists
    output_folder.mkdir(parents=True, exist_ok=True)

    # Statistics
    stats = {
        'total': len(pdf_files),
        'copied': 0,
        'ocr_processed': 0,
        'failed': 0,
        'skipped': 0,
        'processing_time': 0
    }

    start_time = time.time()

    # Process each PDF with progress bar
    logger.info(f"Processing {len(pdf_files)} PDFs from {year}...")

    with tqdm(pdf_files, desc=f"Processing {year} PDFs", unit="file") as pbar:
        for pdf_file in pbar:
            output_path = output_folder / pdf_file.name

            # Skip if already processed
            if output_path.exists():
                logger.debug(f"Skipping (already exists): {pdf_file.name}")
                stats['skipped'] += 1
                pbar.set_postfix({'skipped': stats['skipped']})
                continue

            # Process the PDF
            result = process_single_pdf(pdf_file, output_path, force_ocr)

            if result['status'] == 'copied':
                stats['copied'] += 1
            elif result['status'] == 'ocr_processed':
                stats['ocr_processed'] += 1
            elif result['status'] == 'failed':
                stats['failed'] += 1

            # Update progress bar with current stats
            pbar.set_postfix({
                'copied': stats['copied'],
                'ocr': stats['ocr_processed'],
                'failed': stats['failed']
            })

    stats['processing_time'] = time.time() - start_time

    # Log summary
    logger.info(f"Processing complete for {year}:")
    logger.info(f"  Total: {stats['total']}")
    logger.info(f"  Copied (has text): {stats['copied']}")
    logger.info(f"  OCR processed: {stats['ocr_processed']}")
    logger.info(f"  Failed: {stats['failed']}")
    logger.info(f"  Skipped (already exists): {stats['skipped']}")
    logger.info(f"  Processing time: {stats['processing_time']:.1f}s")

    return stats


def verify_pdf_has_text(pdf_path: Path, show_sample: bool = True) -> bool:
    """
    Verify a PDF has extractable text and optionally show a sample.

    Args:
        pdf_path: Path to PDF file
        show_sample: If True, print text sample

    Returns:
        bool: True if PDF has text
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            for page in pdf.pages[:3]:  # Check first 3 pages
                page_text = page.extract_text()
                if page_text:
                    text += page_text

            has_text = len(text) > 50

            if show_sample and has_text:
                sample = text[:200].replace('\n', ' ')
                print(f"\n{pdf_path.name}:")
                print(f"  Text sample: {sample}...")
                print(f"  Length: {len(text)} characters")

                # Check for Swedish characters
                swedish_chars = set('åäöÅÄÖ')
                found_swedish = swedish_chars & set(text)
                if found_swedish:
                    print(f"  Swedish chars: ✓ ({', '.join(sorted(found_swedish))})")

            return has_text

    except Exception as e:
        logger.error(f"Error verifying PDF {pdf_path.name}: {e}")
        return False
