import hashlib
import hmac
import json

from app import config
from app.api import create_app


def _post(client, event):
    body = json.dumps(event).encode()
    sig = hmac.new(config.PROVIDER_WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return client.post("/webhooks/provider", data=body, headers={"X-Provider-Signature": sig})


def _event(seller):
    return {"id": "evt_1", "type": "charge.succeeded",
            "data": {"id": "ch_1", "seller_id": seller, "amount": 10_000}}


def test_bad_signature_is_rejected(conn, seller):
    client = create_app().test_client()
    resp = client.post("/webhooks/provider", data=b"{}", headers={"X-Provider-Signature": "nope"})
    assert resp.status_code == 401


def test_charge_credits_seller_minus_fee(conn, seller):
    client = create_app().test_client()
    assert _post(client, _event(seller)).status_code == 200
    total = conn.execute("SELECT sum(amount_cents) FROM ledger_entries WHERE seller_id = %s", [seller]).fetchone()[0]
    assert total == 9_000


def test_redelivered_event_credits_once(conn, seller):
    client = create_app().test_client()
    _post(client, _event(seller))
    resp = _post(client, _event(seller))
    assert resp.status_code == 200
    assert resp.json == {"duplicate": "evt_1"}
    count = conn.execute("SELECT count(*) FROM ledger_entries WHERE kind = 'earning'").fetchone()[0]
    assert count == 1
