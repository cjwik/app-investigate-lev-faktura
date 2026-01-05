# src/transaction_parser.py

"""
Transaction-level SIE parser for matching supplier invoices.

This module parses SIE files and extracts full transaction-level detail,
including individual #TRANS lines with account numbers, amounts, and descriptions.

This is different from sie_parser.py which only extracts voucher summaries.
The transaction-level data is required for matching receipts (account 2440)
with clearings (account 1930).
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Regex patterns for parsing SIE format
# VER pattern handles both quoted and unquoted descriptions
# Pattern stops before opening brace { if present on same line
VER_PATTERN = re.compile(r'^#VER\s+([A-Za-z0-9]+)\s+([^\s]+)\s+(\d{8})\s+(.*?)(?:\s*\{)?$')
TRANS_PATTERN = re.compile(r'^#TRANS\s+(\d+)\s+\{.*?\}\s+([-]?\d+\.?\d*)\s*(\d{8})?\s*(?:"?(.*?)"?)?$')


class Transaction:
    """Represents a single #TRANS line in a voucher."""

    def __init__(self, account: str, amount: float, date: Optional[datetime] = None, description: str = ""):
        self.account = account
        self.amount = amount
        self.date = date
        self.description = description

    def __repr__(self):
        return f"Transaction(account={self.account}, amount={self.amount:.2f})"


class Voucher:
    """Represents a complete #VER block with all its transactions."""

    def __init__(self, series: str, number: int, date: datetime, description: str):
        self.series = series
        self.number = number
        self.date = date
        self.description = description
        self.transactions: List[Transaction] = []

    @property
    def voucher_id(self) -> str:
        """Returns the voucher identifier (e.g., 'A110')."""
        return f"{self.series}{self.number}"

    def get_transactions_by_account(self, account: str) -> List[Transaction]:
        """Returns all transactions for a specific account."""
        return [t for t in self.transactions if t.account == account]

    def has_account(self, account: str) -> bool:
        """Checks if voucher has any transaction with the specified account."""
        return any(t.account == account for t in self.transactions)

    def get_total_for_account(self, account: str) -> float:
        """Returns the sum of all amounts for a specific account."""
        return sum(t.amount for t in self.transactions if t.account == account)

    def is_balanced(self) -> bool:
        """Checks if the voucher is balanced (sum of all transactions = 0)."""
        total = sum(t.amount for t in self.transactions)
        return abs(total) < 0.01

    def extract_supplier(self) -> Optional[str]:
        """
        Extracts supplier name from standardized voucher description.

        Standardized format:
        - Receipt: "Leverantörsfaktura - Mottagen - [Supplier] - [Invoice#]"
        - Payment: "Leverantörsfaktura - Betalt - [Supplier] - [Invoice#] [optional info]"

        Returns the supplier name (3rd field) or None if not in standardized format.
        """
        parts = [p.strip() for p in self.description.split(' - ')]

        # Check for standardized format
        if len(parts) >= 3 and parts[0] == "Leverantörsfaktura":
            if parts[1] in ["Mottagen", "Betalt"]:
                return parts[2]

        return None

    def extract_invoice_number(self) -> Optional[str]:
        """
        Extracts invoice number from standardized voucher description.

        Standardized format:
        - Receipt: "Leverantörsfaktura - Mottagen - [Supplier] - [Invoice#]"
        - Payment: "Leverantörsfaktura - Betalt - [Supplier] - [Invoice#] [optional info]"

        The invoice number is in the 4th field and may be followed by correction info in parentheses.
        Example: "4962010809 (korrigerad med verifikation A532...)"

        For non-standardized format (old data), falls back to finding first 8+ digit sequence.

        Returns the invoice number or None if not found.
        """
        import re

        parts = [p.strip() for p in self.description.split(' - ')]

        # Try standardized format first
        if len(parts) >= 4 and parts[0] == "Leverantörsfaktura":
            if parts[1] in ["Mottagen", "Betalt"]:
                # 4th field contains invoice number, possibly with correction info
                invoice_field = parts[3]
                # Extract first word (invoice number) before any parentheses or spaces
                match = re.match(r'^(\d+)', invoice_field)
                if match:
                    return match.group(1)

        # Fallback: Look for sequences of 8+ digits anywhere in description
        match = re.search(r'\d{8,}', self.description)
        return match.group(0) if match else None

    def __repr__(self):
        return f"Voucher({self.voucher_id}, {self.date.date()}, {len(self.transactions)} trans)"


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


def parse_sie_transactions(filepath: Path) -> List[Voucher]:
    """
    Parses a SIE file and extracts full transaction-level data.

    Returns a list of Voucher objects, each containing all its Transaction objects.
    This provides the detailed data needed for matching receipts with clearings.

    Args:
        filepath: Path to the SIE file

    Returns:
        List of Voucher objects with full transaction details
    """
    logger.info(f"Starting transaction-level parsing of SIE file: {filepath.name}")

    try:
        content = _try_read_file(filepath)
    except ValueError as e:
        logger.error(e)
        return []

    vouchers = []
    current_voucher: Optional[Voucher] = None
    in_ver_block = False

    lines = content.splitlines()
    for i, line in enumerate(lines):
        line = line.strip()

        # Parse #VER line (start of voucher)
        if line.startswith("#VER"):
            # Handle multi-line descriptions
            if not line.endswith('"') and (i + 1) < len(lines):
                line += lines[i + 1].strip()

            ver_match = VER_PATTERN.match(line)
            if ver_match:
                try:
                    ver_num_str = ver_match.group(2).strip('"')
                    ver_num = int(ver_num_str) if ver_num_str else 0

                    current_voucher = Voucher(
                        series=ver_match.group(1),
                        number=ver_num,
                        date=datetime.strptime(ver_match.group(3), '%Y%m%d'),
                        description=ver_match.group(4).strip('"')
                    )
                except (ValueError, IndexError) as e:
                    logger.warning(f"Could not parse #VER line: {line}. Error: {e}")
                    current_voucher = None

        # Start of transaction block
        elif line.startswith("{") and current_voucher:
            in_ver_block = True

        # End of transaction block
        elif line.startswith("}") and in_ver_block:
            if current_voucher and current_voucher.transactions:
                vouchers.append(current_voucher)
            in_ver_block = False
            current_voucher = None

        # Parse #TRANS line (transaction within voucher)
        elif in_ver_block and line.startswith("#TRANS") and current_voucher:
            trans_match = TRANS_PATTERN.match(line)
            if trans_match:
                try:
                    account = trans_match.group(1)
                    amount = float(trans_match.group(2))

                    # Transaction date is optional
                    trans_date = None
                    if trans_match.group(3):
                        trans_date = datetime.strptime(trans_match.group(3), '%Y%m%d')

                    # Transaction description is optional
                    trans_desc = trans_match.group(4) if trans_match.group(4) else ""

                    transaction = Transaction(
                        account=account,
                        amount=amount,
                        date=trans_date,
                        description=trans_desc.strip('"')
                    )
                    current_voucher.transactions.append(transaction)

                except (ValueError, IndexError) as e:
                    logger.warning(f"Could not parse #TRANS line: {line}. Error: {e}")

    if not vouchers:
        logger.warning(f"No vouchers found in {filepath.name}")
        return []

    logger.info(f"Successfully parsed {len(vouchers)} vouchers with transaction details from {filepath.name}")

    # Log validation statistics
    balanced = sum(1 for v in vouchers if v.is_balanced())
    logger.info(f"Balanced vouchers: {balanced}/{len(vouchers)}")

    # Log account 2440 statistics
    vouchers_with_2440 = [v for v in vouchers if v.has_account("2440")]
    logger.info(f"Vouchers with account 2440 (Leverantörsskulder): {len(vouchers_with_2440)}")

    return vouchers
