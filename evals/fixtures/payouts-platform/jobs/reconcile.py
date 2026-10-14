import logging
import sys
from datetime import datetime, timedelta, timezone

from app import db
from lib import metrics
from payouts import bank_client

log = logging.getLogger("jobs.reconcile")

SETTLEMENT_LAG_DAYS = 2


def reconcile(day) -> int:
    settled = bank_client.fetch_settlement(day.isoformat())
    bank_total = sum(t["amount"] for t in settled)
    with db.connect() as conn:
        row = conn.execute(
            "SELECT coalesce(sum(amount_cents), 0) AS total FROM payouts WHERE period = %s", [day]
        ).fetchone()
    ours = int(row["total"])
    mismatch = bank_total - ours
    metrics.gauge("reconcile_mismatch_cents", mismatch)
    if mismatch:
        log.error("settlement mismatch for %s: bank=%d ours=%d", day, bank_total, ours)
    return mismatch


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    reconcile(datetime.now(timezone.utc).date() - timedelta(days=SETTLEMENT_LAG_DAYS))
