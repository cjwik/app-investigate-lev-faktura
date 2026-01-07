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

    @property
    def description(self) -> str:
        return self.voucher.description

    def extract_supplier(self) -> Optional[str]:
        """Extracts supplier from voucher description."""
        return self.voucher.extract_supplier()

    def extract_invoice_number(self) -> Optional[str]:
        """Extracts invoice number from voucher description."""
        return self.voucher.extract_invoice_number()

    def extract_referenced_invoice_numbers(self) -> List[str]:
        """Extracts list of invoice numbers referenced in description."""
        return self.voucher.extract_referenced_invoice_numbers()


@dataclass
class CorrectionEvent:
    """Represents a correction event that clears a liability without payment."""
    voucher: Voucher
    amount_2440: float  # The signed amount on account 2440 (positive = debit)
    trans_2440: Transaction
    payment_voucher_id: str  # Referenced payment voucher (e.g., A159)
    receipt_voucher_id: str  # Referenced receipt voucher (e.g., A133)

    @property
    def voucher_id(self) -> str:
        return self.voucher.voucher_id

    @property
    def date(self) -> datetime:
        return self.voucher.date

    @property
    def description(self) -> str:
        return self.voucher.description


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

    def identify_correction_vouchers(self, vouchers: List[Voucher], target_year: int = None) -> tuple[set[str], dict]:
        """
        Identifies correction voucher pairs that should be excluded from matching.

        Correction vouchers are identified by:
        - "korrigerad" (corrected) in description with reference to another voucher
        - "Korrigering" (correction) in description with reference to another voucher
        - "Rättelse av felbokad betalning" (2024 payment corrections in 2025)

        These represent accounting corrections that cancel each other out, not actual invoices.

        Args:
            vouchers: List of all vouchers to search
            target_year: If provided, only exclude corrections where BOTH vouchers are from this year.
                        This prevents cross-year voucher ID collisions (e.g., 2024-A53 vs 2025-A53)

        Returns:
            Tuple of (exclude_ids: set, correction_mappings: dict)
            - exclude_ids: Set of voucher IDs to exclude
            - correction_mappings: Dict of {correction_id: {'payment_id': str, 'receipt_id': str, 'correction_voucher': Voucher}}
        """
        exclude_ids = set()
        correction_mappings = {}
        import re


        for voucher in vouchers:
            desc_lower = voucher.description.lower()

            # For regular correction pairs (same-year), filter by target year
            # But for payment corrections that reference other years, check all vouchers

            # Check for "korrigerad" (corrected with reference to another voucher)
            # Only check vouchers from target year for same-year corrections
            if "korrigerad" in desc_lower and (not target_year or voucher.date.year == target_year):
                # Extract referenced voucher ID (pattern: "korrigerad med verifikation A131")
                match = re.search(r'korrigerad.*?([A-Z]\d+)', voucher.description, re.IGNORECASE)
                if match:
                    referenced_id = match.group(1)

                    # Find the referenced voucher to check its year
                    ref_voucher = next((v for v in vouchers if v.voucher_id == referenced_id), None)

                    # Only exclude if both vouchers are from the same year (or no year filter)
                    if ref_voucher and (not target_year or ref_voucher.date.year == target_year):
                        exclude_ids.add(voucher.voucher_id)
                        exclude_ids.add(referenced_id)
                        logger.info(f"Excluding correction pair: {voucher.voucher_id} <-> {referenced_id}")

            # Check for "korrigering" (correction of another voucher)
            # Only check vouchers from target year for same-year corrections
            if "korrigering" in desc_lower and (not target_year or voucher.date.year == target_year):
                # Extract referenced voucher ID (pattern: "Korrigering av ver.nr. A120")
                match = re.search(r'korrigering.*?([A-Z]\d+)', voucher.description, re.IGNORECASE)
                if match:
                    referenced_id = match.group(1)

                    # Find the referenced voucher to check its year
                    ref_voucher = next((v for v in vouchers if v.voucher_id == referenced_id), None)

                    # Only exclude if both vouchers are from the same year (or no year filter)
                    if ref_voucher and (not target_year or ref_voucher.date.year == target_year):
                        exclude_ids.add(voucher.voucher_id)
                        exclude_ids.add(referenced_id)
                        logger.info(f"Excluding correction pair: {voucher.voucher_id} <-> {referenced_id}")

            # Check for "Rättelse av felbokad betalning" (2024 payment corrections in 2025)
            # The SIE file is encoded in CP850/CP437 and properly decoded to Swedish characters
            desc = voucher.description
            is_payment_correction = (
                "rättelse av felbokad betalning" in desc_lower and
                ("i stället för 2440" in desc_lower or "i stället för 2440" in desc_lower) and
                "rättas i 2025" in desc_lower
            )


            if is_payment_correction:
                # Extract payment voucher: "felbokad betalning A159 2024-11-25"
                payment_match = re.search(r'felbokad betalning ([A-Z]\d+)', desc, re.IGNORECASE)

                # Extract receipt voucher: "faktura A133 2024-11-08"
                receipt_match = re.search(r'faktura ([A-Z]\d+)', desc, re.IGNORECASE)

                if payment_match and receipt_match:
                    payment_id = payment_match.group(1)
                    receipt_id = receipt_match.group(1)

                    # This is a correction voucher - exclude from normal receipt/clearing processing
                    # Store mapping for later matching
                    correction_mappings[voucher.voucher_id] = {
                        'payment_id': payment_id,
                        'receipt_id': receipt_id,
                        'correction_voucher': voucher
                    }
                    exclude_ids.add(voucher.voucher_id)
                    logger.info(f"Excluding 2025 payment correction: {voucher.voucher_id} -> Receipt {receipt_id} (Payment {payment_id} bypassed 2440)")

        if exclude_ids:
            logger.info(f"Total correction vouchers excluded: {len(exclude_ids)} ({', '.join(sorted(exclude_ids))})")

        if correction_mappings:
            logger.info(f"Payment corrections found: {len(correction_mappings)} ({', '.join(sorted(correction_mappings.keys()))})")

        return exclude_ids, correction_mappings

    def identify_receipts(self, vouchers: List[Voucher]) -> List[ReceiptEvent]:
        """
        Identifies all receipt events from vouchers.

        Receipt logic:
        - 2440 Kredit (negative) → Always a receipt (normal invoice)
        - 2440 Debet (positive) WITHOUT 1930 in voucher → Credit note receipt

        Note: A voucher can have both receipt and clearing (same-voucher payment)

        Exclusions:
        - Self-canceling vouchers without payment (invoice + credit in same voucher, no 1930)
        """
        receipts = []
        excluded_self_canceling = []

        for voucher in vouchers:
            # Only process vouchers with account 2440
            if not voucher.has_account("2440"):
                continue

            # Get all 2440 transactions
            trans_2440_list = voucher.get_transactions_by_account("2440")
            has_1930 = voucher.has_account("1930")

            # Check for self-canceling vouchers without payment
            # (e.g., invoice + credit note in same voucher)
            total_2440 = sum(t.amount for t in trans_2440_list)
            is_self_canceling_without_payment = (abs(total_2440) < 0.01 and not has_1930)

            if is_self_canceling_without_payment:
                excluded_self_canceling.append(voucher.voucher_id)
                logger.info(f"Excluding self-canceling voucher without payment: {voucher.voucher_id}")
                continue

            for trans_2440 in trans_2440_list:
                # Receipt identification per transaction:
                # - 2440 Kredit (negative) WITHOUT 1930 → Receipt (normal invoice)
                # - 2440 Kredit (negative) WITH 1930 AND multiple 2440 entries → Same-voucher payment receipt
                # - 2440 Kredit (negative) WITH 1930 AND single 2440 entry → Payment of credit invoices (NOT a receipt)
                # - 2440 Debet (positive) + NO 1930 → Credit note receipt

                if trans_2440.amount < 0:
                    # Kredit - check if this is a receipt or payment of credit invoices
                    # If there are multiple 2440 transactions, this is a same-voucher payment (receipt + clearing)
                    # If there's only one 2440 transaction WITH 1930, it's a payment of credit invoices (exclude)
                    if has_1930 and len(trans_2440_list) == 1:
                        # Single 2440 Credit + 1930 = payment of credit invoices, not a receipt
                        continue

                    # Otherwise, it's a receipt (normal invoice or same-voucher payment)
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
        if excluded_self_canceling:
            logger.info(f"  - Excluded self-canceling without payment: {excluded_self_canceling}")

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
                # For each 2440, find the BEST matching 1930 transaction
                # Priority: exact amount match, then any valid payment/refund pair
                best_trans_1930 = None
                best_match_score = -1

                for trans_1930 in trans_1930_list:
                    # Only consider valid payment/refund pairs:
                    # - Payment: 2440 Debet (positive) + 1930 Kredit (negative)
                    # - Refund: 2440 Kredit (negative) + 1930 Debet (positive)
                    is_payment = trans_2440.amount > 0 and trans_1930.amount < 0
                    is_refund = trans_2440.amount < 0 and trans_1930.amount > 0

                    if is_payment or is_refund:
                        # Score: 2 for exact amount match, 1 for valid pair
                        match_score = 2 if abs(abs(trans_2440.amount) - abs(trans_1930.amount)) < 0.01 else 1
                        if match_score > best_match_score:
                            best_match_score = match_score
                            best_trans_1930 = trans_1930

                # Only create one clearing per 2440 transaction (the best match)
                if best_trans_1930:
                    clearing = ClearingEvent(
                        voucher=voucher,
                        amount_2440=trans_2440.amount,
                        amount_1930=best_trans_1930.amount,
                        trans_2440=trans_2440,
                        trans_1930=best_trans_1930
                    )
                    clearings.append(clearing)

        logger.info(f"Identified {len(clearings)} clearing events")
        return clearings

    def identify_corrections(self, vouchers: List[Voucher], correction_mappings: dict) -> List[CorrectionEvent]:
        """
        Identifies correction events from vouchers.

        Correction events are accounting adjustments that clear 2440 liabilities
        without actual bank transactions (no 1930). These are used when payments
        were incorrectly posted to expense accounts instead of clearing liabilities.

        Args:
            vouchers: List of all vouchers
            correction_mappings: Dict of {correction_id: {'payment_id': str, 'receipt_id': str, 'correction_voucher': Voucher}}

        Returns:
            List of CorrectionEvent objects
        """
        corrections = []

        for correction_id, mapping in correction_mappings.items():
            correction_voucher = mapping['correction_voucher']

            # Get 2440 Debit transaction (should be positive)
            trans_2440_list = correction_voucher.get_transactions_by_account("2440")

            for trans_2440 in trans_2440_list:
                if trans_2440.amount > 0:  # Only Debit (liability clearing)
                    correction = CorrectionEvent(
                        voucher=correction_voucher,
                        amount_2440=trans_2440.amount,
                        trans_2440=trans_2440,
                        payment_voucher_id=mapping['payment_id'],
                        receipt_voucher_id=mapping['receipt_id']
                    )
                    corrections.append(correction)
                    break  # Only one 2440 Debit per correction

        logger.info(f"Identified {len(corrections)} correction events")
        for c in corrections:
            logger.info(f"  - {c.voucher_id}: Corrects {c.receipt_voucher_id} (paid by {c.payment_voucher_id})")

        return corrections

    def find_clearing_for_receipt(
        self,
        receipt: ReceiptEvent,
        clearings: List[ClearingEvent],
        receipt_year: int = None,
        clearing_balances: dict = None
    ) -> Tuple[Optional[ClearingEvent], str]:
        """
        Finds the matching clearing for a receipt.

        Args:
            receipt: The receipt event to find clearing for
            clearings: List of all available clearing events (can include multiple years)
            receipt_year: Optional year of the receipt for cross-year detection
            clearing_balances: Dict of {id(clearing): remaining_amount}

        Returns:
            Tuple of (ClearingEvent or None, comment string)

        Matching rules:
        1. Amounts must match exactly (absolute value)
        2. Clearing date must be after receipt date
        3. Clearing not already used by another receipt
        4. Prefer same invoice number (if available)
        5. Prefer clearings within 1-40 days
        6. Accept clearings up to max_days with note
        7. Flag cross-year payments (e.g., 2024 receipt paid in 2025)
        """
        abs_receipt_amount = abs(receipt.amount_2440)
        # Extract invoice numbers and suppliers for better matching
        receipt_invoice_no = receipt.voucher.extract_invoice_number()
        receipt_supplier = receipt.voucher.extract_supplier()

        # Strategy 1: Exact Amount Match (Primary)
        # ----------------------------------------
        amount_candidates = []
        for c in clearings:
            # Check if clearing has enough balance (if tracking balances)
            remaining = clearing_balances.get(id(c), 0.0) if clearing_balances is not None else abs(c.amount_2440)
            
            # Check for exact match with the *original* amount (standard 1:1 match)
            # OR check if remaining balance matches (if partially used)
            if abs(abs(c.amount_2440) - abs_receipt_amount) < 0.01 or abs(remaining - abs_receipt_amount) < 0.01:
                if c.date >= receipt.date:
                    # Ensure we don't reuse fully exhausted clearings
                    if remaining >= abs_receipt_amount - 0.01:
                        amount_candidates.append(c)

        # Strategy 2: Explicit Invoice Reference Match (Fallback for Bulk Payments)
        # -------------------------------------------------------------------------
        # If A232 pays for A186, A215 etc. in one lump sum, amounts won't match 1:1.
        # We check if the clearing description explicitly lists the receipt's invoice number.
        reference_candidates = []
        if receipt_invoice_no:
            for c in clearings:
                
                # Check date
                if c.date < receipt.date:
                    continue

                # Check balance
                remaining = clearing_balances.get(id(c), 0.0) if clearing_balances is not None else abs(c.amount_2440)
                if remaining < abs_receipt_amount - 0.01:
                    continue

                # Check description for invoice number
                referenced_invoices = c.extract_referenced_invoice_numbers()
                if receipt_invoice_no in referenced_invoices:
                    reference_candidates.append(c)

        # Combine candidates, prioritizing exact amount matches
        # Deduplicate while preserving order (amount matches first)
        candidates = []
        seen_ids = set()
        for c in amount_candidates + reference_candidates:
            if id(c) not in seen_ids:
                candidates.append(c)
                seen_ids.add(id(c))

        if not candidates:
            return None, "No clearing found (checked amount and invoice references)"

        # Calculate days and check invoice number + supplier match for each candidate
        candidates_with_info = []
        for c in candidates:
            days_diff = (c.date - receipt.date).days
            clearing_invoice_no = c.voucher.extract_invoice_number()
            clearing_supplier = c.voucher.extract_supplier()

            # Check if amounts match exactly
            amount_match = abs(abs(c.amount_2440) - abs_receipt_amount) < 0.01

            # Check if invoice numbers match
            invoice_match = (clearing_invoice_no == receipt_invoice_no
                           if (receipt_invoice_no and clearing_invoice_no) else False)

            # Check if suppliers match (case-insensitive)
            supplier_match = (clearing_supplier and receipt_supplier and
                            clearing_supplier.lower() == receipt_supplier.lower())

            # Both should match for standardized format
            both_match = invoice_match and supplier_match

            # Check if matched via reference (Strategy 2)
            is_ref_match = c in reference_candidates

            candidates_with_info.append((c, days_diff, invoice_match, supplier_match, both_match, is_ref_match, amount_match))

        # Sort by:
        # 1. Exact amount match (NEW - highest priority for 1:1 payments)
        # 2. Both match (invoice# AND supplier)
        # 3. Explicit Reference Match (for multi-invoice bulk payments)
        # 4. Invoice number match only
        # 5. Days difference (closest first)
        #
        # Rationale: When amounts match exactly, that's the strongest signal (1:1 payment).
        # Bulk payments (reference matches) are lower priority since they involve multiple invoices.
        candidates_with_info.sort(key=lambda x: (not x[6], not x[4], not x[5], not x[2], x[1]))

        best_clearing, days, invoice_match, supplier_match, both_match, is_ref_match, amount_match = candidates_with_info[0]

        # Build comment based on day count
        # Note: Explicit reference matches (bulk payments) bypass max_days check
        # because invoice number is explicitly listed in payment description
        if days == 0:
            comment = "Receipt and clearing in same voucher date"
        elif days <= 40:
            comment = f"Clearing found {days} day{'s' if days != 1 else ''} after receipt"
        elif days <= self.max_days or is_ref_match:
            # Accept if within max_days OR if explicit reference match
            if days > self.max_days:
                comment = f"Bulk payment clearing: {days} days after receipt (date tolerance relaxed for explicit reference)"
            else:
                comment = f"Late clearing: {days} days after receipt"
        else:
            return None, f"Clearing found but {days} days after receipt (exceeds max {self.max_days} days)"

        # Add match quality indicators with detailed mismatch information
        if is_ref_match:
            comment += f" ✓ BULK MATCH (Found invoice {receipt_invoice_no} in clearing description)"
        elif both_match:
            comment += " ✓ FULL MATCH (supplier + invoice#)"
        elif invoice_match and not supplier_match:
            # Invoice matches but supplier doesn't - flag for SIE file correction
            receipt_sup = receipt.voucher.extract_supplier() or "MISSING"
            clearing_sup = best_clearing.voucher.extract_supplier() or "MISSING"

            # Provide specific guidance based on what's missing
            if receipt_sup == "MISSING" and clearing_sup == "MISSING":
                comment += f" ⚠ TITLE MISMATCH: Both vouchers missing supplier in title (Invoice# OK) - FIX: Add supplier to 3rd field"
            elif receipt_sup == "MISSING":
                comment += f" ⚠ TITLE MISMATCH: Receipt {receipt.voucher_id} missing supplier in title (Invoice# OK) - FIX: Should be 'Leverantörsfaktura - Mottagen - {clearing_sup} - {receipt_invoice_no}'"
            elif clearing_sup == "MISSING":
                comment += f" ⚠ TITLE MISMATCH: Clearing {best_clearing.voucher_id} missing supplier in title (Invoice# OK) - FIX: Should be 'Leverantörsfaktura - Betalat - {receipt_sup} - {receipt_invoice_no}'"
            else:
                comment += f" ⚠ TITLE MISMATCH: Supplier names differ (Invoice# OK) - Receipt has '{receipt_sup}' but Clearing has '{clearing_sup}' - FIX: Use same supplier name in both"

        elif supplier_match and not invoice_match:
            # Supplier matches but invoice doesn't - flag for SIE file correction
            receipt_inv = receipt.voucher.extract_invoice_number() or "MISSING"
            clearing_inv = best_clearing.voucher.extract_invoice_number() or "MISSING"

            # Provide specific guidance based on what's missing
            if receipt_inv == "MISSING" and clearing_inv == "MISSING":
                comment += f" ⚠ TITLE MISMATCH: Both vouchers missing invoice# in title (Supplier OK) - FIX: Add invoice# to 4th field"
            elif receipt_inv == "MISSING":
                comment += f" ⚠ TITLE MISMATCH: Receipt {receipt.voucher_id} missing invoice# in title (Supplier OK) - FIX: Add '{clearing_inv}' to 4th field"
            elif clearing_inv == "MISSING":
                comment += f" ⚠ TITLE MISMATCH: Clearing {best_clearing.voucher_id} missing invoice# in title (Supplier OK) - FIX: Add '{receipt_inv}' to 4th field"
            else:
                comment += f" ⚠ TITLE MISMATCH: Invoice numbers differ (Supplier OK) - Receipt has '{receipt_inv}' but Clearing has '{clearing_inv}' - FIX: Use same invoice# in both"

        elif not invoice_match and not supplier_match:
            # Neither matches - either old format or needs correction
            receipt_sup = receipt.voucher.extract_supplier() or "MISSING"
            receipt_inv = receipt.voucher.extract_invoice_number() or "MISSING"
            clearing_sup = best_clearing.voucher.extract_supplier() or "MISSING"
            clearing_inv = best_clearing.voucher.extract_invoice_number() or "MISSING"

            if receipt_sup == "MISSING" or receipt_inv == "MISSING" or clearing_sup == "MISSING" or clearing_inv == "MISSING":
                comment += f" ⚠ TITLE MISMATCH: Incomplete standardized format - Receipt({receipt.voucher_id}): supplier='{receipt_sup}' invoice#='{receipt_inv}' | Clearing({best_clearing.voucher_id}): supplier='{clearing_sup}' invoice#='{clearing_inv}' - FIX: Use format 'Leverantörsfaktura - Mottagen/Betalat - [Supplier] - [Invoice#]'"
            else:
                comment += f" ⚠ TITLE MISMATCH: Both supplier AND invoice# differ - Receipt has '{receipt_sup}'/'{receipt_inv}' but Clearing has '{clearing_sup}'/'{clearing_inv}' - CHECK: Wrong match or data entry error?"

        # Check for cross-year payment
        if receipt_year and best_clearing.date.year != receipt_year:
            comment += f" [CROSS-YEAR: {receipt_year} invoice paid in {best_clearing.date.year}]"

        # Check for ambiguity (multiple candidates with same days)
        same_day_candidates = [c for c, d, _, _, _, _, _ in candidates_with_info if d == days]
        if len(same_day_candidates) > 1:
            comment += f" (Warning: {len(same_day_candidates)} candidates with same date)"

        return best_clearing, comment

    def match_all(self, vouchers: List[Voucher], receipt_year: int = None) -> List[InvoiceCase]:
        """
        Performs complete matching of all receipts with clearings.

        Args:
            vouchers: List of all vouchers (can include multiple years for cross-year matching)
            receipt_year: Optional year to filter receipts by (e.g., 2024). If provided,
                         only receipts from this year will be processed, but clearings
                         from all years in vouchers will be available for matching.

        Returns a list of InvoiceCase objects (one per receipt).
        """
        logger.info(f"Starting matching process for {len(vouchers)} vouchers...")

        # Step 0: Identify and exclude correction vouchers (only from the target year to avoid cross-year ID collisions)
        exclude_ids, correction_mappings = self.identify_correction_vouchers(vouchers, target_year=receipt_year)
        filtered_vouchers = [v for v in vouchers if v.voucher_id not in exclude_ids]
        logger.info(f"Processing {len(filtered_vouchers)} vouchers after excluding {len(exclude_ids)} correction vouchers")

        # Filter receipts by year if specified
        receipts_vouchers = [v for v in filtered_vouchers if receipt_year is None or v.date.year == receipt_year]
        logger.info(f"Filtering receipts to year {receipt_year}: {len(receipts_vouchers)} vouchers" if receipt_year else "Processing all years")

        # Step 1: Identify all receipts and clearings
        receipts = self.identify_receipts(receipts_vouchers)
        clearings = self.identify_clearings(filtered_vouchers)  # Search ALL years for clearings

        # Step 1.5: Identify corrections (accounting adjustments that clear liabilities without bank transactions)
        corrections = self.identify_corrections(vouchers, correction_mappings)

        # Step 2: Match each receipt with its clearing
        cases = []
        # Track remaining balance for each clearing to allow bulk payments
        clearing_balances = {id(c): abs(c.amount_2440) for c in clearings}

        for receipt in receipts:
            clearing, comment = self.find_clearing_for_receipt(
                receipt,
                clearings,
                receipt_year=receipt_year,
                clearing_balances=clearing_balances
            )

            # Determine status
            if clearing:
                # Deduct amount from clearing balance
                clearing_balances[id(clearing)] -= abs(receipt.amount_2440)
                
                # Check for same voucher case
                if clearing.voucher_id == receipt.voucher_id:
                    status = "OK"
                    comment = "Receipt and clearing in same voucher"
                    confidence = 100
                else:
                    # Validate amounts match exactly
                    # Note: For bulk matches, clearing amount > receipt amount, but we trust the reference match
                    if abs(abs(clearing.amount_2440) - abs(receipt.amount_2440)) < 0.01 or "BULK MATCH" in comment:
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

        # Step 2.5: Match receipts with corrections (2024 invoices corrected in 2025)
        for correction in corrections:
            # Find the receipt this correction is for
            receipt = next((r for r in receipts if r.voucher_id == correction.receipt_voucher_id), None)

            if receipt and abs(abs(correction.amount_2440) - abs(receipt.amount_2440)) < 0.01:
                # Amount matches - this correction clears this receipt

                # Find if this receipt already has a case (might be "Missing clearing")
                existing_case = next((c for c in cases if c.receipt and c.receipt.voucher_id == receipt.voucher_id), None)

                if existing_case:
                    # Update existing case
                    existing_case.clearing = None  # No standard clearing
                    existing_case.status = "OK"
                    existing_case.match_confidence = 100
                    existing_case.comment = f"Corrected in 2025 by {correction.voucher_id} (payment {correction.payment_voucher_id} bypassed 2440)"
                else:
                    # Create new case (shouldn't happen, but handle it)
                    case = InvoiceCase(
                        receipt=receipt,
                        clearing=None,
                        status="OK",
                        match_confidence=100,
                        comment=f"Corrected in 2025 by {correction.voucher_id} (payment {correction.payment_voucher_id} bypassed 2440)"
                    )
                    cases.append(case)

                logger.info(f"Matched correction: {receipt.voucher_id} <- {correction.voucher_id}")

        # Step 3: Find unmatched clearings (payments without receipts)
        # Filter clearings to the target year if specified
        clearings_for_year = [c for c in clearings if receipt_year is None or c.date.year == receipt_year]

        unmatched_clearings = [
            c for c in clearings_for_year
            if abs(clearing_balances[id(c)] - abs(c.amount_2440)) < 0.01  # Only show completely unused clearings
        ]

        # Step 3.5: Check if unmatched clearings match previous year receipts
        # This handles cross-year clearings (e.g., 2025 payment for 2024 invoice)
        previous_year_receipts = []
        if receipt_year:
            # Load previous year's receipts to check for cross-year matches
            prev_year_vouchers = [v for v in filtered_vouchers if v.date.year == receipt_year - 1]
            if prev_year_vouchers:
                previous_year_receipts = self.identify_receipts(prev_year_vouchers)
                logger.info(f"Loaded {len(previous_year_receipts)} receipts from {receipt_year - 1} for cross-year clearing detection")

        # Create cases for unmatched clearings (payment without receipt)
        for clearing in unmatched_clearings:
            # Check if this clearing matches a previous year's receipt
            cross_year_match = None
            if previous_year_receipts:
                # Try to find a matching receipt from previous year
                for prev_receipt in previous_year_receipts:
                    # Check amount match
                    if abs(abs(clearing.amount_2440) - abs(prev_receipt.amount_2440)) < 0.01:
                        # Found potential match - verify it's reasonable
                        cross_year_match = prev_receipt
                        break

            if cross_year_match:
                # This is a cross-year clearing - mark as OK
                case = InvoiceCase(
                    receipt=None,  # Receipt is in previous year, not included in this report
                    clearing=clearing,
                    status="OK",
                    match_confidence=100,
                    comment=f"Cross-year clearing: {receipt_year} payment for {receipt_year - 1} invoice {cross_year_match.voucher_id}"
                )
            else:
                # Truly missing receipt - needs review
                case = InvoiceCase(
                    receipt=None,  # No receipt voucher
                    clearing=clearing,
                    status="Missing receipt",
                    match_confidence=0,
                    comment="Payment made but no receipt voucher found - needs receipt verification"
                )
            cases.append(case)

        # Log statistics
        ok_count = sum(1 for c in cases if c.status == "OK")
        missing_clearing_count = sum(1 for c in cases if c.status == "Missing clearing")
        missing_receipt_count = sum(1 for c in cases if c.status == "Missing receipt")
        review_count = sum(1 for c in cases if c.status == "Needs review")
        correction_count = sum(1 for c in cases if c.comment and "Corrected in 2025" in c.comment)

        logger.info("=" * 60)
        logger.info("Matching Complete")
        logger.info("=" * 60)
        logger.info(f"Total invoice cases: {len(cases)}")
        logger.info(f"  - OK: {ok_count}")
        logger.info(f"  - Missing clearing (unpaid invoices): {missing_clearing_count}")
        logger.info(f"  - Missing receipt (payments without invoice): {missing_receipt_count}")
        logger.info(f"  - Needs review: {review_count}")
        if correction_count > 0:
            logger.info(f"  - Corrected in 2025: {correction_count}")

        return cases
