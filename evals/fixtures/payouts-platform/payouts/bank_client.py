import uuid

import requests

from app import config
from lib.http import with_retries

_session = requests.Session()


class BankError(Exception):
    """The bank rejected the transfer. Not retried."""


class BankUnavailable(BankError):
    """The bank answered 5xx. Retried."""


@with_retries(attempts=4, retry_on=(requests.Timeout, requests.ConnectionError, BankUnavailable), backoff=2.0)
def send_transfer(account_ref: str, amount_cents: int, memo: str) -> dict:
    resp = _session.post(
        f"{config.NORTHWIND_BASE_URL}/transfers",
        json={"destination": account_ref, "amount": amount_cents, "currency": "USD", "memo": memo},
        headers={
            "Authorization": f"Bearer {config.NORTHWIND_API_KEY}",
            "Idempotency-Key": str(uuid.uuid4()),
        },
        timeout=(3, 10),
    )
    if resp.status_code >= 500:
        raise BankUnavailable(f"{resp.status_code}: {resp.text[:200]}")
    if resp.status_code >= 400:
        raise BankError(f"{resp.status_code}: {resp.text[:200]}")
    return resp.json()


@with_retries(attempts=3, retry_on=(requests.Timeout, requests.ConnectionError))
def fetch_settlement(day: str) -> list[dict]:
    resp = _session.get(
        f"{config.NORTHWIND_BASE_URL}/settlements/{day}",
        headers={"Authorization": f"Bearer {config.NORTHWIND_API_KEY}"},
        timeout=(3, 30),
    )
    resp.raise_for_status()
    return resp.json()["transfers"]
