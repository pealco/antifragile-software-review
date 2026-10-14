from datetime import datetime, timedelta, timezone

from app import ledger


def test_fee_is_taken_from_sale(conn, seller):
    ledger.credit_sale(conn, seller, 10_000, "ch_1")
    later = datetime.now(timezone.utc) + timedelta(days=30)
    assert ledger.available_balance(conn, seller, later) == 9_000


def test_hold_period_blocks_payout(conn, seller):
    ledger.credit_sale(conn, seller, 10_000, "ch_1")
    assert ledger.available_balance(conn, seller, datetime.now(timezone.utc)) == 0


def test_payout_reduces_balance(conn, seller):
    ledger.credit_sale(conn, seller, 10_000, "ch_1")
    ledger.record_payout(conn, seller, 9_000, "tr_1")
    later = datetime.now(timezone.utc) + timedelta(days=30)
    assert ledger.available_balance(conn, seller, later) == 0
