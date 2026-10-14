from datetime import datetime, timedelta, timezone

from app import config


def credit_sale(conn, seller_id: int, gross_cents: int, reference: str) -> None:
    fee = gross_cents * config.PLATFORM_FEE_BPS // 10_000
    available_at = datetime.now(timezone.utc) + timedelta(days=config.HOLD_DAYS)
    conn.execute(
        "INSERT INTO ledger_entries (seller_id, kind, amount_cents, available_at, reference) "
        "VALUES (%s, 'earning', %s, %s, %s), (%s, 'fee', %s, %s, %s)",
        [seller_id, gross_cents, available_at, reference,
         seller_id, -fee, available_at, reference],
    )


def available_balance(conn, seller_id: int, as_of: datetime) -> int:
    row = conn.execute(
        "SELECT coalesce(sum(amount_cents), 0) AS balance FROM ledger_entries "
        "WHERE seller_id = %s AND available_at <= %s",
        [seller_id, as_of],
    ).fetchone()
    return int(row["balance"])


def record_payout(conn, seller_id: int, amount_cents: int, reference: str) -> None:
    conn.execute(
        "INSERT INTO ledger_entries (seller_id, kind, amount_cents, available_at, reference) "
        "VALUES (%s, 'payout', %s, now(), %s)",
        [seller_id, -amount_cents, reference],
    )
