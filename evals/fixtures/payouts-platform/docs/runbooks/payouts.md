# Payouts runbook

## Pause payouts

If payouts look wrong (wrong amounts, unexpected sellers, bank errors), pause the job first:

```bash
kubectl -n payments set env cronjob/payout-runner PAYOUTS_ENABLED=false
```

The next scheduled run will exit without sending transfers. Re-enable with `PAYOUTS_ENABLED=true`.

## Re-run a failed night

Kubernetes retries a failed run automatically (see `backoffLimit`). If all retries fail, fix the cause
and trigger a manual run:

```bash
kubectl -n payments create job --from=cronjob/payout-runner payout-manual-$(date +%s)
```

Sellers that already have a `payouts` row for the period are skipped, so re-running is safe.

## Bank partner errors

Northwind sometimes answers slowly during their batch window (00:45-01:30 UTC). The client retries
timeouts and connection errors, so slow responses usually resolve themselves.

## Reconciliation mismatches

`reconcile-settlements` alerts when the bank settlement total for a day differs from our `payouts`
total. Investigate in the bank portal, then contact Northwind support for recalls.
