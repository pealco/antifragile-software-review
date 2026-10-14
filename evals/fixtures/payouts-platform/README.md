# Payouts Platform (EVAL FIXTURE)

Marketplace backend that records seller earnings and pays sellers out to their bank accounts.

- `app/`: HTTP API. Receives payment-provider webhooks and credits the seller ledger.
- `payouts/`: nightly payout job. Pays each seller's available balance through the bank partner.
- `jobs/`: housekeeping and reconciliation jobs.
- `deploy/k8s/`: Kubernetes manifests. `monitoring/`: alert rules.

See `docs/architecture.md` and `docs/runbooks/payouts.md`.

## Local development

```bash
uv sync
uv run python scripts/seed_dev.py
uv run pytest
```
