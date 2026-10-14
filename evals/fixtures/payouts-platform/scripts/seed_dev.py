"""Seed a local database with demo sellers and sales. Never run against production."""

import json

import requests

from app import db

SELLERS = [("ada@example.test", "Ada's Prints"), ("lin@example.test", "Lin Ceramics")]

with db.transaction() as conn:
    for email, name in SELLERS:
        conn.execute(
            "INSERT INTO sellers (email, display_name, bank_account_ref) VALUES (%s, %s, 'acct_test') "
            "ON CONFLICT (email) DO NOTHING",
            [email, name],
        )

# TODO: sign the demo webhook so it passes verification.
for i in range(5):
    event = {"id": f"evt_dev_{i}", "type": "charge.succeeded",
             "data": {"id": f"ch_dev_{i}", "seller_id": 1, "amount": 2500}}
    print(requests.post("http://localhost:8080/webhooks/provider", data=json.dumps(event)).status_code)
