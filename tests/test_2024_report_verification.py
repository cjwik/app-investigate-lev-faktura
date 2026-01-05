# tests/test_2024_report_verification.py

"""
Comprehensive verification tests for 2024 report results.

These tests ensure that the matching algorithm produces consistent results
for the 2024 SIE file. Since the SIE file won't change, these results should
remain constant across code changes.

The expected results are stored in tests/expected_2024_results.json
"""

import json
import pytest
from pathlib import Path
from src.transaction_parser import parse_sie_transactions
from src.matcher import InvoiceMatcher


def load_expected_results():
    """Load expected results from JSON file."""
    expected_file = Path(__file__).parent / 'expected_2024_results.json'
    with open(expected_file, 'r', encoding='utf-8') as f:
        return json.load(f)


@pytest.fixture
def expected():
    """Fixture to load expected results."""
    return load_expected_results()


@pytest.fixture
def matching_results():
    """Fixture to run matching and return results."""
    sie_file_2024 = Path('Data/Input/SIE/20240101-20241231.se')
    sie_file_2025 = Path('Data/Input/SIE/20250101-20251231.se')

    if not sie_file_2024.exists():
        pytest.skip(f"SIE file not found: {sie_file_2024}")

    # Load vouchers
    vouchers_2024 = parse_sie_transactions(sie_file_2024)
    all_vouchers = list(vouchers_2024)

    # Load 2025 for cross-year matching if available
    if sie_file_2025.exists():
        vouchers_2025 = parse_sie_transactions(sie_file_2025)
        all_vouchers.extend(vouchers_2025)

    # Run matching
    matcher = InvoiceMatcher(max_days=120)
    cases = matcher.match_all(all_vouchers, receipt_year=2024)

    return {
        'vouchers_2024': vouchers_2024,
        'all_vouchers': all_vouchers,
        'cases': cases,
        'matcher': matcher
    }


def test_bookkeeping_totals(matching_results, expected):
    """Verify bookkeeping totals match expected values."""
    vouchers_2024 = matching_results['vouchers_2024']
    expected_totals = expected['bookkeeping_totals']

    # Calculate totals from ALL 2024 vouchers (including corrections)
    total_kredit = 0.0
    total_debet = 0.0

    for voucher in vouchers_2024:
        if voucher.has_account("2440"):
            trans_2440_list = voucher.get_transactions_by_account("2440")
            for trans in trans_2440_list:
                if trans.amount < 0:
                    total_kredit += abs(trans.amount)
                else:
                    total_debet += abs(trans.amount)

    outstanding_balance = total_kredit - total_debet

    # Verify with tolerance for floating point
    assert abs(total_kredit - expected_totals['kredit_receipts']) < 0.01, \
        f"Kredit mismatch: expected {expected_totals['kredit_receipts']}, got {total_kredit}"

    assert abs(total_debet - expected_totals['debet_clearings']) < 0.01, \
        f"Debet mismatch: expected {expected_totals['debet_clearings']}, got {total_debet}"

    assert abs(outstanding_balance - expected_totals['outstanding_balance']) < 0.01, \
        f"Outstanding balance mismatch: expected {expected_totals['outstanding_balance']}, got {outstanding_balance}"


def test_correction_vouchers(matching_results, expected):
    """Verify correction vouchers are correctly identified."""
    all_vouchers = matching_results['all_vouchers']
    matcher = matching_results['matcher']

    # Identify corrections for 2024 only
    exclude_ids = matcher.identify_correction_vouchers(all_vouchers, target_year=2024)

    expected_ids = set(expected['correction_vouchers']['excluded_ids'])

    assert exclude_ids == expected_ids, (
        f"Correction vouchers changed!\n"
        f"Expected: {sorted(expected_ids)}\n"
        f"Got: {sorted(exclude_ids)}\n"
        f"Missing: {sorted(expected_ids - exclude_ids)}\n"
        f"Extra: {sorted(exclude_ids - expected_ids)}"
    )


def test_validation_summary(matching_results, expected):
    """Verify validation summary counts."""
    cases = matching_results['cases']
    expected_summary = expected['validation_summary']

    total_cases = len(cases)
    paid_cases = len([c for c in cases if c.status == "OK"])
    unpaid_cases = len([c for c in cases if c.status == "Missing clearing"])
    review_cases = len([c for c in cases if c.status == "Needs review"])

    assert total_cases == expected_summary['total_invoice_cases'], \
        f"Total cases: expected {expected_summary['total_invoice_cases']}, got {total_cases}"

    assert paid_cases == expected_summary['paid_ok'], \
        f"Paid cases: expected {expected_summary['paid_ok']}, got {paid_cases}"

    assert unpaid_cases == expected_summary['unpaid_missing_clearing'], \
        f"Unpaid cases: expected {expected_summary['unpaid_missing_clearing']}, got {unpaid_cases}"

    assert review_cases == expected_summary['needs_review'], \
        f"Review cases: expected {expected_summary['needs_review']}, got {review_cases}"


def test_outstanding_invoices(matching_results, expected):
    """Verify outstanding invoice voucher IDs."""
    cases = matching_results['cases']
    outstanding_cases = [c for c in cases if c.status != "OK"]

    outstanding_ids = {c.receipt.voucher_id for c in outstanding_cases}
    expected_ids = {inv['voucher_id'] for inv in expected['outstanding_invoices']}

    assert outstanding_ids == expected_ids, (
        f"Outstanding invoices changed!\n"
        f"Expected: {sorted(expected_ids)}\n"
        f"Got: {sorted(outstanding_ids)}\n"
        f"Missing: {sorted(expected_ids - outstanding_ids)}\n"
        f"Extra: {sorted(outstanding_ids - expected_ids)}"
    )


def test_critical_matches(matching_results, expected):
    """Verify critical matches like A49 → A53."""
    cases = matching_results['cases']
    cases_dict = {c.receipt.voucher_id: c for c in cases}

    for expected_match in expected['critical_matches']:
        receipt_id = expected_match['receipt_id']
        expected_clearing_id = expected_match['clearing_id']
        expected_status = expected_match['status']

        assert receipt_id in cases_dict, f"Receipt {receipt_id} not found in cases"

        case = cases_dict[receipt_id]

        # Verify match
        assert case.clearing is not None, f"{receipt_id} should have a clearing"
        assert case.clearing.voucher_id == expected_clearing_id, \
            f"{receipt_id} should match with {expected_clearing_id}, got {case.clearing.voucher_id}"

        assert case.status == expected_status, \
            f"{receipt_id} status: expected {expected_status}, got {case.status}"


def test_same_voucher_payments(matching_results, expected):
    """Verify same-voucher payment cases."""
    cases = matching_results['cases']
    expected_same_voucher = set(expected['same_voucher_payments'])

    same_voucher_ids = {
        c.receipt.voucher_id
        for c in cases
        if c.clearing and c.clearing.voucher_id == c.receipt.voucher_id
    }

    assert same_voucher_ids == expected_same_voucher, (
        f"Same-voucher payments changed!\n"
        f"Expected: {sorted(expected_same_voucher)}\n"
        f"Got: {sorted(same_voucher_ids)}\n"
        f"Missing: {sorted(expected_same_voucher - same_voucher_ids)}\n"
        f"Extra: {sorted(same_voucher_ids - expected_same_voucher)}"
    )


if __name__ == '__main__':
    # Allow running this file directly for quick verification
    import sys
    pytest.main([__file__, '-v'] + sys.argv[1:])
