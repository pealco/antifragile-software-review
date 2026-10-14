from datetime import date, datetime, timedelta, timezone

import requests
import responses

from app import config
from payouts import bank_client, runner

TRANSFERS = f"{config.NORTHWIND_BASE_URL}/transfers"


def _available_earning(conn, seller, cents):
    conn.execute(
        "INSERT INTO ledger_entries (seller_id, kind, amount_cents, available_at) VALUES (%s, 'earning', %s, %s)",
        [seller, cents, datetime.now(timezone.utc) - timedelta(days=1)],
    )
    conn.commit()


@responses.activate
def test_transfer_sends_idempotency_key():
    responses.post(TRANSFERS, json={"id": "tr_1"})
    bank_client.send_transfer("acct_1", 5_000, memo="Payout")
    assert responses.calls[0].request.headers["Idempotency-Key"]


@responses.activate
def test_transfer_retries_timeouts(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)
    responses.post(TRANSFERS, body=requests.Timeout())
    responses.post(TRANSFERS, json={"id": "tr_2"})
    assert bank_client.send_transfer("acct_1", 5_000, memo="Payout") == {"id": "tr_2"}
    assert len(responses.calls) == 2


@responses.activate
def test_rejected_transfer_is_not_retried():
    responses.post(TRANSFERS, status=422, json={"error": "closed account"})
    try:
        bank_client.send_transfer("acct_1", 5_000, memo="Payout")
    except bank_client.BankError:
        pass
    assert len(responses.calls) == 1


@responses.activate
def test_runner_pays_available_balance_once(conn, seller):
    _available_earning(conn, seller, 20_000)
    responses.post(TRANSFERS, json={"id": "tr_3"})
    today = date.today()
    runner.run(today)
    runner.run(today)
    assert len(responses.calls) == 1
    paid = conn.execute("SELECT amount_cents FROM payouts WHERE seller_id = %s", [seller]).fetchone()[0]
    assert paid == 20_000


def test_runner_respects_minimum(conn, seller):
    _available_earning(conn, seller, config.MIN_PAYOUT_CENTS - 1)
    assert runner.pay_seller({"id": seller, "bank_account_ref": "acct_1"}, date.today()) == 0
