# src/matcher.py

"""
Matching engine for supplier invoice validation.

This module implements the core matching logic to:
1. Identify receipt events (2440 Kredit or 2440 Debet without 1930)
2. Find corresponding clearing events (2440 Debet with 1930)
3. Validate amounts match exactly
4. Check date windows (1-40 days optimal, up to configurable max)
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from src.transaction_parser import Voucher, Transaction

logger = logging.getLogger(__name__)


@dataclass
class ReceiptEvent:
    """Represents a receipt event (invoice or credit note)."""
    voucher: Voucher
    amount_2440: float  # The signed amount on account 2440
    trans_2440: Transaction  # The actual 2440 transaction
    is_credit_note: bool  # True if this is a credit note (2440 Debet without 1930)

    @property
    def voucher_id(self) -> str:
        return self.voucher.voucher_id

    @property
    def date(self) -> datetime:
        return self.voucher.date

    @property
    def description(self) -> str:
        return self.voucher.description

    def extract_supplier(self) -> str:
        """Extracts supplier name from voucher description (best effort)."""
        # Common patterns: "Leverantörsfaktura - YYYY-MM-DD - SUPPLIER - ..."
        # Note: Date with dashes will be split into multiple parts
        desc = self.description
        parts = [p.strip() for p in desc.split('-')]

        # Filter out parts that are clearly not supplier names
        supplier_candidates = []
        skip_next = 0

        for i, part in enumerate(parts):
            if skip_next > 0:
                skip_next -= 1
                continue

            # Skip first part (typically "Leverantörsfaktura")
            if i == 0:
                continue

            # Skip numeric-only parts (likely part of date or invoice number)
            if part.isdigit():
                continue

            # Skip very short parts
            if len(part) <= 2:
                continue

            # Skip if it starts with "Faktura" or "Invoice"
            if part.lower().startswith(('faktura', 'invoice', 'fatura')):
                continue

            # This is likely a supplier name
            supplier_candidates.append(part)

        # Return the first valid candidate, or empty string
        return supplier_candidates[0] if supplier_candidates else ""


@dataclass
class ClearingEvent:
    """Represents a clearing event (payment or refund)."""
    voucher: Voucher
    amount_2440: float  # The signed amount on account 2440
    amount_1930: float  # The signed amount on account 1930
    trans_2440: Transaction  # The actual 2440 transaction
    trans_1930: Transaction  # The actual 1930 transaction

    @property
    def voucher_id(self) -> str:
        return self.voucher.voucher_id

    @property
    def date(self) -> datetime:
        return self.voucher.date


@dataclass
class InvoiceCase:
    """Represents one invoice case (one row in final report)."""
    receipt: ReceiptEvent
    clearing: Optional[ClearingEvent] = None
    status: str = "Pending"
    match_confidence: int = 0
    comment: str = ""

    def calculate_days_to_clearing(self) -> Optional[int]:
        """Returns number of days between receipt and clearing."""
        if not self.clearing:
            return None
        delta = self.clearing.date - self.receipt.date
        return delta.days


class InvoiceMatcher:
    """Matches receipts with clearing vouchers."""

    def __init__(self, max_days: int = 120):
        """
        Args:
            max_days: Maximum days to search for clearing (default 120)
        """
        self.max_days = max_days

    def identify_receipts(self, vouchers: List[Voucher]) -> List[ReceiptEvent]:
        """
        Identifies all receipt events from vouchers.

        Receipt logic:
        - 2440 Kredit (negative) → Always a receipt (normal invoice)
        - 2440 Debet (positive) WITHOUT 1930 in voucher → Credit note receipt

        Note: A voucher can have both receipt and clearing (same-voucher payment)
        """
        receipts = []

        for voucher in vouchers:
            # Only process vouchers with account 2440
            if not voucher.has_account("2440"):
                continue

            # Get all 2440 transactions
            trans_2440_list = voucher.get_transactions_by_account("2440")
            has_1930 = voucher.has_account("1930")

            for trans_2440 in trans_2440_list:
                # Receipt identification per transaction:
                # - 2440 Kredit (negative) → Always receipt
                # - 2440 Debet (positive) + NO 1930 → Credit note receipt

                if trans_2440.amount < 0:
                    # Kredit = receipt (normal invoice)
                    receipt = ReceiptEvent(
                        voucher=voucher,
                        amount_2440=trans_2440.amount,
                        trans_2440=trans_2440,
                        is_credit_note=False
                    )
                    receipts.append(receipt)
                elif trans_2440.amount > 0 and not has_1930:
                    # Debet without 1930 = credit note receipt
                    receipt = ReceiptEvent(
                        voucher=voucher,
                        amount_2440=trans_2440.amount,
                        trans_2440=trans_2440,
                        is_credit_note=True
                    )
                    receipts.append(receipt)

        logger.info(f"Identified {len(receipts)} receipt events")
        credit_notes = sum(1 for r in receipts if r.is_credit_note)
        logger.info(f"  - Normal invoices: {len(receipts) - credit_notes}")
        logger.info(f"  - Credit notes: {credit_notes}")

        return receipts

    def identify_clearings(self, vouchers: List[Voucher]) -> List[ClearingEvent]:
        """
        Identifies all clearing events from vouchers.

        Clearing logic:
        - Voucher must have BOTH 2440 and 1930
        - Payment: 2440 Debet (positive) + 1930 Kredit (negative)
        - Refund: 2440 Kredit (negative) + 1930 Debet (positive)
        """
        clearings = []

        for voucher in vouchers:
            # Must have both 2440 and 1930
            if not (voucher.has_account("2440") and voucher.has_account("1930")):
                continue

            # Get all 2440 and 1930 transactions
            trans_2440_list = voucher.get_transactions_by_account("2440")
            trans_1930_list = voucher.get_transactions_by_account("1930")

            # Handle multiple 2440 lines in same clearing voucher
            for trans_2440 in trans_2440_list:
                # For each 2440, find corresponding 1930
                # In most cases, there's one 1930 that matches
                for trans_1930 in trans_1930_list:
                    clearing = ClearingEvent(
                        voucher=voucher,
                        amount_2440=trans_2440.amount,
                        amount_1930=trans_1930.amount,
                        trans_2440=trans_2440,
                        trans_1930=trans_1930
                    )
                    clearings.append(clearing)

        logger.info(f"Identified {len(clearings)} clearing events")
        return clearings

    def find_clearing_for_receipt(
        self,
        receipt: ReceiptEvent,
        clearings: List[ClearingEvent]
    ) -> Tuple[Optional[ClearingEvent], str]:
        """
        Finds the matching clearing for a receipt.

        Returns:
            Tuple of (ClearingEvent or None, comment string)

        Matching rules:
        1. Amounts must match exactly (absolute value)
        2. Clearing date must be after receipt date
        3. Prefer clearings within 1-40 days
        4. Accept clearings up to max_days with note
        """
        # Filter candidates by amount match (exact absolute value)
        abs_receipt_amount = abs(receipt.amount_2440)
        candidates = [
            c for c in clearings
            if abs(abs(c.amount_2440) - abs_receipt_amount) < 0.01
        ]

        if not candidates:
            return None, "No clearing found with matching amount"

        # Filter by date: clearing must be after receipt
        candidates = [
            c for c in candidates
            if c.date >= receipt.date
        ]

        if not candidates:
            return None, f"Found {len(candidates)} amount matches but all before receipt date"

        # Calculate days for each candidate
        candidates_with_days = [
            (c, (c.date - receipt.date).days)
            for c in candidates
        ]

        # Sort by days (prefer closest)
        candidates_with_days.sort(key=lambda x: x[1])

        best_clearing, days = candidates_with_days[0]

        # Build comment based on day count
        if days == 0:
            comment = "Receipt and clearing in same voucher date"
        elif days <= 40:
            comment = f"Clearing found {days} day{'s' if days != 1 else ''} after receipt"
        elif days <= self.max_days:
            comment = f"Late clearing: {days} days after receipt"
        else:
            return None, f"Clearing found but {days} days after receipt (exceeds max {self.max_days} days)"

        # Check for ambiguity (multiple candidates with same days)
        same_day_candidates = [c for c, d in candidates_with_days if d == days]
        if len(same_day_candidates) > 1:
            comment += f" (Warning: {len(same_day_candidates)} candidates with same date)"

        return best_clearing, comment

    def match_all(self, vouchers: List[Voucher]) -> List[InvoiceCase]:
        """
        Performs complete matching of all receipts with clearings.

        Returns a list of InvoiceCase objects (one per receipt).
        """
        logger.info(f"Starting matching process for {len(vouchers)} vouchers...")

        # Step 1: Identify all receipts and clearings
        receipts = self.identify_receipts(vouchers)
        clearings = self.identify_clearings(vouchers)

        # Step 2: Match each receipt with its clearing
        cases = []
        for receipt in receipts:
            clearing, comment = self.find_clearing_for_receipt(receipt, clearings)

            # Determine status
            if clearing:
                # Check for same voucher case
                if clearing.voucher_id == receipt.voucher_id:
                    status = "OK"
                    comment = "Receipt and clearing in same voucher"
                    confidence = 100
                else:
                    # Validate amounts match exactly
                    if abs(abs(clearing.amount_2440) - abs(receipt.amount_2440)) < 0.01:
                        status = "OK"
                        confidence = 100
                    else:
                        status = "Needs review"
                        comment = "Amount mismatch: " + comment
                        confidence = 50
            else:
                status = "Missing clearing"
                confidence = 0

            case = InvoiceCase(
                receipt=receipt,
                clearing=clearing,
                status=status,
                match_confidence=confidence,
                comment=comment
            )
            cases.append(case)

        # Log statistics
        ok_count = sum(1 for c in cases if c.status == "OK")
        missing_count = sum(1 for c in cases if c.status == "Missing clearing")
        review_count = sum(1 for c in cases if c.status == "Needs review")

        logger.info("=" * 60)
        logger.info("Matching Complete")
        logger.info("=" * 60)
        logger.info(f"Total invoice cases: {len(cases)}")
        logger.info(f"  - OK: {ok_count}")
        logger.info(f"  - Missing clearing: {missing_count}")
        logger.info(f"  - Needs review: {review_count}")

        return cases
