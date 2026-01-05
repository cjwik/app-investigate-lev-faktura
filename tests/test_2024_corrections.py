# tests/test_2024_corrections.py

"""
Verification tests for 2024 correction vouchers.

These tests ensure that code changes don't accidentally change the correction
voucher detection logic. The expected correction pairs are based on the actual
2024 SIE file and should remain constant.
"""

import pytest
from pathlib import Path
from src.transaction_parser import parse_sie_transactions
from src.matcher import InvoiceMatcher


# Expected correction pairs for 2024 (will not change)
EXPECTED_2024_CORRECTIONS = {
    'A120', 'A131',  # Nibe payment (has 2440 + 1930)
    'A143', 'A170',  # Bauhaus invoice (has 2440 only)
    'A168', 'A169',  # Interest income (no 2440 or 1930)
}


def test_2024_correction_vouchers_unchanged():
    """
    Verify that 2024 correction voucher detection returns the expected pairs.

    This is a regression test to ensure code changes don't break the correction
    detection logic. The 2024 SIE file will not change, so these corrections
    should always be detected.
    """
    # Load 2024 vouchers
    sie_file = Path('Data/Input/SIE/20240101-20241231.se')

    if not sie_file.exists():
        pytest.skip(f"SIE file not found: {sie_file}")

    vouchers = parse_sie_transactions(sie_file)

    # Identify corrections (2024 only)
    matcher = InvoiceMatcher()
    exclude_ids = matcher.identify_correction_vouchers(vouchers, target_year=2024)

    # Verify the exact set of correction vouchers
    assert exclude_ids == EXPECTED_2024_CORRECTIONS, (
        f"2024 correction vouchers changed!\n"
        f"Expected: {sorted(EXPECTED_2024_CORRECTIONS)}\n"
        f"Got: {sorted(exclude_ids)}\n"
        f"Missing: {sorted(EXPECTED_2024_CORRECTIONS - exclude_ids)}\n"
        f"Extra: {sorted(exclude_ids - EXPECTED_2024_CORRECTIONS)}"
    )


def test_2024_correction_pairs_details():
    """
    Verify the details of each correction pair to ensure they have the expected accounts.
    """
    sie_file = Path('Data/Input/SIE/20240101-20241231.se')

    if not sie_file.exists():
        pytest.skip(f"SIE file not found: {sie_file}")

    vouchers = parse_sie_transactions(sie_file)
    vouchers_dict = {v.voucher_id: v for v in vouchers}

    # A120 ↔ A131 - Nibe payment (has 2440 + 1930)
    if 'A120' in vouchers_dict and 'A131' in vouchers_dict:
        a120 = vouchers_dict['A120']
        a131 = vouchers_dict['A131']

        assert a120.has_account('2440'), "A120 should have account 2440"
        assert a120.has_account('1930'), "A120 should have account 1930"
        assert a131.has_account('2440'), "A131 should have account 2440"
        assert a131.has_account('1930'), "A131 should have account 1930"
        assert 'korrigerad' in a120.description.lower(), "A120 should be marked as corrected"
        assert 'korrigering' in a131.description.lower(), "A131 should be a correction"

    # A143 ↔ A170 - Bauhaus invoice (has 2440 only)
    if 'A143' in vouchers_dict and 'A170' in vouchers_dict:
        a143 = vouchers_dict['A143']
        a170 = vouchers_dict['A170']

        assert a143.has_account('2440'), "A143 should have account 2440"
        assert not a143.has_account('1930'), "A143 should NOT have account 1930"
        assert a170.has_account('2440'), "A170 should have account 2440"
        assert not a170.has_account('1930'), "A170 should NOT have account 1930"
        assert 'korrigerad' in a143.description.lower(), "A143 should be marked as corrected"
        assert 'korrigering' in a170.description.lower(), "A170 should be a correction"

    # A168 ↔ A169 - Interest income (no 2440 or 1930)
    if 'A168' in vouchers_dict and 'A169' in vouchers_dict:
        a168 = vouchers_dict['A168']
        a169 = vouchers_dict['A169']

        assert not a168.has_account('2440'), "A168 should NOT have account 2440"
        assert not a168.has_account('1930'), "A168 should NOT have account 1930"
        assert not a169.has_account('2440'), "A169 should NOT have account 2440"
        assert not a169.has_account('1930'), "A169 should NOT have account 1930"
        assert 'korrigerad' in a168.description.lower(), "A168 should be marked as corrected"
        assert 'korrigering' in a169.description.lower(), "A169 should be a correction"


if __name__ == '__main__':
    # Allow running this file directly for quick verification
    test_2024_correction_vouchers_unchanged()
    test_2024_correction_pairs_details()
    print("✓ All 2024 correction verification tests passed!")
