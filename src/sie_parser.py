# src/sie_parser.py

"""
Parses SIE (Standard Import/Export) accounting files, specifically type 4.

This module is responsible for reading SIE files, handling their specific PC8
encoding (cp437), and extracting verification (voucher) data into a structured
pandas DataFrame.

Key functionalities:
- State machine parser to process multi-line verification blocks.
- Regular expressions to parse #VER and #TRANS lines.
- Correctly calculates 'target_amount' for matching against PDF invoices,
  avoiding the "Zero Sum Trap" of double-entry bookkeeping.
"""

import logging
import re
from datetime import datetime
from pathlib import Path
import pandas as pd

# Configure logging
logger = logging.getLogger(__name__)

# REGEX explanation from docs/iteration-2-sie-parser.md
# VER_PATTERN: Captures Series, Number, Date, and Description from a #VER line.
# Adjusted to handle various quoting and spacing scenarios.
VER_PATTERN = re.compile(r'^#VER\s+([A-Za-z0-9]+)\s+(?:"?([^"]*)"?)\s+(\d{8})\s+"(.*)"')
# TRANS_PATTERN: Captures Account, Amount, Date, and Description from a #TRANS line.
TRANS_PATTERN = re.compile(r'^#TRANS\s+(\d+)\s+\{.*?\}\s+([-]?\d+\.?\d*)\s*(\d{8})?\s*(?:"?(.*?)"?)?$')


def _try_read_file(filepath: Path) -> str:
    """Tries to read the file with different encodings.

    Priority order for PC8 format:
    1. cp850 (OEM 850 - Western European) - RECOMMENDED for Swedish å,ä,ö
    2. cp437 (OEM 437 - US)
    3. latin-1 (ISO 8859-1)
    4. utf-8
    """
    encodings = ['cp850', 'cp437', 'latin-1', 'utf-8']
    for encoding in encodings:
        try:
            with open(filepath, 'r', encoding=encoding) as f:
                content = f.read()
            logger.info(f"Successfully read {filepath.name} with encoding: {encoding}")
            return content
        except UnicodeDecodeError:
            logger.debug(f"Failed to decode {filepath.name} with {encoding}")

    raise ValueError(f"Could not decode {filepath} with any of the attempted encodings.")

def parse_sie_file(filepath: Path) -> pd.DataFrame:
    """
    Parses a SIE file and extracts verification data into a pandas DataFrame.

    This function implements a state machine to read through the file line by
    line, correctly associating #TRANS lines with their parent #VER block.

    Args:
        filepath: The path to the SIE file.

    Returns:
        A pandas DataFrame containing structured verification data,
        or an empty DataFrame if parsing fails or the file is empty.
    """
    logger.info(f"Starting parsing of SIE file: {filepath.name}")
    
    try:
        content = _try_read_file(filepath)
    except ValueError as e:
        logger.error(e)
        return pd.DataFrame()

    verifications = []
    current_ver_data = None
    in_ver_block = False

    lines = content.splitlines()
    for i, line in enumerate(lines):
        line = line.strip()

        # Fix for VER lines that might be malformed
        if line.startswith("#VER"):
            # If the line doesn't end with a quote, it might be a multi-line description.
            # This is a simple heuristic. A more robust parser would handle this better.
            if not line.endswith('"') and (i + 1) < len(lines):
                 line += lines[i+1].strip()
            
            ver_match = VER_PATTERN.match(line)
            if ver_match:
                # If we have a pending verification, process it before starting a new one.
                if current_ver_data and current_ver_data['transactions']:
                    # This case can happen if a { block is missing.
                    # Process the old one before starting anew.
                    pass # Or log a warning

                # Store the extracted verification data
                try:
                    ver_num_str = ver_match.group(2).strip('"')
                    ver_num = int(ver_num_str) if ver_num_str else 0

                    current_ver_data = {
                        'series': ver_match.group(1),
                        'number': ver_num,
                        'trans_date': datetime.strptime(ver_match.group(3), '%Y%m%d').date(),
                        'description': ver_match.group(4).strip('"'),
                        'transactions': []
                    }
                except (ValueError, IndexError) as e:
                    logger.warning(f"Could not parse #VER line: {line}. Error: {e}")
                    current_ver_data = None
        
        elif line.startswith("{") and current_ver_data:
            in_ver_block = True
        
        elif line.startswith("}") and in_ver_block:
            # End of a verification block, process it
            if current_ver_data and current_ver_data['transactions']:
                trans = current_ver_data['transactions']
                
                total_amount = sum(t['amount'] for t in trans)
                # CRITICAL: Calculate target_amount as per docs
                target_amount = max(abs(t['amount']) for t in trans) if trans else 0.0
                debit_amount = sum(t['amount'] for t in trans if t['amount'] > 0)
                credit_amount = abs(sum(t['amount'] for t in trans if t['amount'] < 0))

                verifications.append({
                    'verification_id': f"{current_ver_data['series']}{current_ver_data['number']}",
                    'series': current_ver_data['series'],
                    'number': current_ver_data['number'],
                    'trans_date': current_ver_data['trans_date'],
                    'description': current_ver_data['description'],
                    'target_amount': target_amount,
                    'total_amount': total_amount,
                    'debit_amount': debit_amount,
                    'credit_amount': credit_amount,
                    'transaction_count': len(trans)
                })

            in_ver_block = False
            current_ver_data = None

        elif in_ver_block and line.startswith("#TRANS"):
            trans_match = TRANS_PATTERN.match(line)
            if trans_match and current_ver_data is not None:
                try:
                    amount = float(trans_match.group(2))
                    current_ver_data['transactions'].append({'amount': amount})
                except (ValueError, IndexError) as e:
                     logger.warning(f"Could not parse #TRANS line: {line}. Error: {e}")


    if not verifications:
        logger.warning(f"No verifications found in {filepath.name}. The file might be empty or in an unsupported format.")
        return pd.DataFrame()

    df = pd.DataFrame(verifications)
    df['trans_date'] = pd.to_datetime(df['trans_date'])

    logger.info(f"Successfully parsed {len(df)} verifications from {filepath.name}.")
    
    return df
