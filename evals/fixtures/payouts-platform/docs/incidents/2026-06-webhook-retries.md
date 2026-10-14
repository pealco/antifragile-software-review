# 2026-06-11: sellers credited twice after provider webhook retries

## What happened

The payment provider had a partial outage and redelivered about 4,000 `charge.succeeded` events.
Our handler credited each delivery, so 312 sellers saw doubled pending earnings for six hours.
No money left the platform: the 7-day hold meant none of the duplicates were paid out.

## Fix

- Migration `003_processed_events.sql` adds `processed_events` with a primary key on the provider
  event id.
- `app/webhooks.py` records the event id in the same transaction as the ledger credit and returns
  200 on a duplicate.
- Duplicate ledger rows were reversed with a one-off script (`ledger_entries.kind = 'reversal'`).

## Follow-ups

- [x] Dedupe webhook events by provider event id.
- [x] Regression test: `tests/test_webhooks.py::test_redelivered_event_credits_once`.
- [ ] Alert on webhook redelivery rate.
