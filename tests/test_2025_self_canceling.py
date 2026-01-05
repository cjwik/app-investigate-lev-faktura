# tests/test_2025_self_canceling.py

"""
Verification test for 2025 self-canceling vouchers.

Ensures that self-canceling vouchers without payment (e.g., invoice + credit note
in same voucher) are correctly excluded from matching.
"""

import pytest
from pathlib import Path
from src.transaction_parser import parse_sie_transactions
from src.matcher import InvoiceMatcher


def test_a111_self_canceling_excluded():
    """
    Verify that A111 (invoice + credit note in same voucher) is excluded from matching.

    A111 contains:
    - Invoice: 2440 Kredit -2,636 SEK
    - Credit note: 2440 Debet +2,636 SEK
    - No 1930 (no payment)
    - Net effect: 0 SEK

    This should be excluded because it's self-canceling without payment.
    """
    sie_file = Path('Data/Input/SIE/20250101-20251231.se')

    if not sie_file.exists():
        pytest.skip(f"SIE file not found: {sie_file}")

    vouchers = parse_sie_transactions(sie_file)

    # Find A111
    a111 = next((v for v in vouchers if v.voucher_id == 'A111'), None)
    assert a111 is not None, "A111 should exist in 2025 data"

    # Verify it's self-canceling
    trans_2440 = a111.get_transactions_by_account('2440')
    total_2440 = sum(t.amount for t in trans_2440)
    assert abs(total_2440) < 0.01, "A111 should have net zero on account 2440"
    assert not a111.has_account('1930'), "A111 should not have account 1930"

    # Verify it's excluded from receipts
    matcher = InvoiceMatcher()
    receipts = matcher.identify_receipts(vouchers)

    a111_receipts = [r for r in receipts if r.voucher_id == 'A111']
    assert len(a111_receipts) == 0, (
        f"A111 should be excluded from receipts (self-canceling without payment), "
        f"but found {len(a111_receipts)} receipt events"
    )


def test_a111_voucher_structure():
    """
    Verify the exact structure of A111 to document what we're excluding.
    """
    sie_file = Path('Data/Input/SIE/20250101-20251231.se')

    if not sie_file.exists():
        pytest.skip(f"SIE file not found: {sie_file}")

    vouchers = parse_sie_transactions(sie_file)
    a111 = next((v for v in vouchers if v.voucher_id == 'A111'), None)

    assert a111 is not None
    assert 'kredit' in a111.description.lower() or 'credit' in a111.description.lower(), \
        "A111 description should mention credit/kredit"

    # Should have exactly 6 transactions (3 for invoice, 3 for credit)
    assert len(a111.transactions) == 6, f"Expected 6 transactions, got {len(a111.transactions)}"

    # Should have 2 transactions on 2440 that cancel each other
    trans_2440 = a111.get_transactions_by_account('2440')
    assert len(trans_2440) == 2, f"Expected 2 transactions on 2440, got {len(trans_2440)}"

    amounts = sorted([t.amount for t in trans_2440])
    assert amounts[0] < 0 and amounts[1] > 0, "Should have one negative and one positive"
    assert abs(amounts[0] + amounts[1]) < 0.01, "Should cancel each other out"


if __name__ == '__main__':
    # Allow running this file directly for quick verification
    test_a111_self_canceling_excluded()
    test_a111_voucher_structure()
    print("✓ All 2025 self-canceling verification tests passed!")
