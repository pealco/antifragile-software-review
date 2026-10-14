import logging
import sys
from datetime import date, datetime, time, timezone

from app import config, db, ledger
from lib import metrics
from payouts import bank_client

log = logging.getLogger("payouts.runner")


def eligible_sellers(conn) -> list[dict]:
    return conn.execute(
        "SELECT id, bank_account_ref FROM sellers "
        "WHERE NOT payouts_paused AND bank_account_ref IS NOT NULL ORDER BY id"
    ).fetchall()


def pay_seller(seller: dict, period: date) -> int:
    as_of = datetime.combine(period, time.min, tzinfo=timezone.utc)
    with db.connect() as conn:
        already_paid = conn.execute(
            "SELECT 1 FROM payouts WHERE seller_id = %s AND period = %s", [seller["id"], period]
        ).fetchone()
        if already_paid:
            return 0
        balance = ledger.available_balance(conn, seller["id"], as_of)

    if balance < config.MIN_PAYOUT_CENTS:
        return 0

    transfer = bank_client.send_transfer(seller["bank_account_ref"], balance, memo=f"Payout {period}")

    with db.transaction() as conn:
        conn.execute(
            "INSERT INTO payouts (seller_id, period, amount_cents, bank_transfer_id) VALUES (%s, %s, %s, %s)",
            [seller["id"], period, balance, transfer["id"]],
        )
        ledger.record_payout(conn, seller["id"], balance, transfer["id"])
    return balance


def run(period: date) -> None:
    if not config.PAYOUTS_ENABLED:
        log.warning("payouts disabled, skipping run for %s", period)
        return

    with db.connect() as conn:
        sellers = eligible_sellers(conn)

    paid = failed = total = 0
    for seller in sellers:
        try:
            amount = pay_seller(seller, period)
        except bank_client.BankError as exc:
            failed += 1
            log.error("payout rejected for seller %s: %s", seller["id"], exc)
            metrics.incr("payouts.rejected")
            continue
        if amount:
            paid += 1
            total += amount
            metrics.incr("payouts.sent")

    metrics.gauge("payouts.last_run_total_cents", total)
    log.info("payout run %s: %d paid, %d rejected, %d cents", period, paid, failed, total)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    run(datetime.now(timezone.utc).date())
