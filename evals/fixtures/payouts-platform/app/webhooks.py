import hashlib
import hmac
import json

import psycopg
from flask import Blueprint, abort, request

from app import config, db, ledger
from lib import metrics

bp = Blueprint("webhooks", __name__)


def _verify(payload: bytes, signature: str) -> bool:
    expected = hmac.new(config.PROVIDER_WEBHOOK_SECRET.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@bp.post("/webhooks/provider")
def provider_webhook():
    payload = request.get_data()
    if not _verify(payload, request.headers.get("X-Provider-Signature", "")):
        abort(401)
    event = json.loads(payload)
    if event["type"] != "charge.succeeded":
        return {"ignored": event["type"]}, 200

    charge = event["data"]
    try:
        with db.transaction() as conn:
            conn.execute("INSERT INTO processed_events (event_id) VALUES (%s)", [event["id"]])
            ledger.credit_sale(conn, int(charge["seller_id"]), int(charge["amount"]), charge["id"])
    except psycopg.errors.UniqueViolation:
        metrics.incr("webhooks.duplicate")
        return {"duplicate": event["id"]}, 200

    metrics.incr("webhooks.credited")
    return {"credited": event["id"]}, 200
