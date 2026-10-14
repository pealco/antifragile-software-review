# Architecture

## Money flow

1. A buyer pays through the payment provider. The provider sends a `charge.succeeded` webhook
   to `POST /webhooks/provider`.
2. `app/webhooks.py` verifies the signature and credits the seller in `ledger_entries`
   (amount minus platform fee). Earnings become available for payout after a 7-day hold.
3. Every night at 01:00 UTC the `payout-runner` CronJob (`payouts/runner.py`) pays each seller's
   available balance through the bank partner's transfer API and records a row in `payouts`.
4. `jobs/reconcile.py` compares our `payouts` table with the bank partner's settlement file.

Refunds and disputes are debited by the payment provider from the platform reserve account. They do
not touch seller balances in this service.

## Components

- One Postgres primary (RDS, multi-AZ, daily snapshots kept 14 days). No read replicas.
- API: 3 replicas behind the ingress. Stateless.
- Payout runner: Kubernetes CronJob, one pod per run.
- Bank partner: single provider (Northwind Bank transfer API). Transfers are final once accepted;
  a recall must be requested from the bank by phone and is not guaranteed.
- Settlement files from the bank arrive two business days after the transfer date (T+2).

## Ownership

- Payments team owns `app/` and `payouts/`. On-call rotation in PagerDuty: `payments-primary`.
- Platform team owns the cluster and CI.
