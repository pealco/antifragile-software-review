# Critical Flow Service Golden Review

## Antifragility Thesis

- System shape: small billing service with a request path that writes invoice state and calls an external billing provider.
- Primary stressors: billing provider latency, provider failure, duplicate requests, partial local writes, and weak deploy coordination.
- Fragility hypothesis: provider failure can become incorrect local charge state because the flow mutates state before and after a dependency call while swallowing provider errors.
- Antifragile opportunity: bound provider downside with timeouts and error-state handling, then turn provider failures into tests and telemetry.
- Evidence confidence: direct fixture code and CI config evidence; runtime alert ownership is unknown.

## System Map

- Critical flows: charge user request.
- State and data: invoice status updates before and after provider call.
- Dependencies: external billing provider.
- Release path: GitHub Actions deploy workflow.
- Feedback loops: sparse runbook; no visible metric, trace, or regression test.
- Ownership and optionality: billing runbook names ownership, but rollback path is missing.

## Critical Flow Trace

| Step | Evidence | Missing evidence | Cheapest observation |
| --- | --- | --- | --- |
| Trigger and entrypoint | `app/billing.py` exposes `charge_user`. | Route wiring and caller idempotency. | Trace the request route that calls `charge_user`. |
| State/data mutation | Invoice is set to `charging`, then `charged`. | Whether failed provider calls preserve failed state. | Reproduce a provider timeout against a fake billing endpoint and assert invoice state plus telemetry. |
| Dependencies | `requests.post` calls `https://billing.example.test/charges`. | Provider timeout and retry budget. | Add a fake provider timeout test. |
| Failure handling | `except Exception: pass` swallows provider errors. | Error metric, alert, compensation, or rollback. | Assert failure path records an observable error and avoids `charged`. |
| Observability and ownership | Billing runbook exists. | Alert routing and dashboard. | Inspect alert routing for billing failures. |
| Rollback/degradation path | Runbook says rollback path is not documented. | Kill switch or degraded mode. | Add rollback instructions or a feature flag check to the runbook. |

- Stress response curve: superlinear.
- Scanner leads that matter: `python-http-without-timeout`, `silent-exception`, `github-actions-missing-concurrency`.
- Scanner leads deferred: none.

## Finding Scorecard

| Finding | Evidence quality | Blast radius | Irreversibility | Feedback delay | Dependency concentration | Ruin potential | Exposure |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Billing provider timeout and swallowed errors can create incorrect charge state | direct critical-flow path | 3 | 2 | 3 | 2 | 2 | 12/15 |

## Findings

### [P1] Billing provider timeout and swallowed errors can create incorrect charge state

- Evidence: `app/billing.py`
- Evidence quality: direct critical-flow path.
- Analysis area: dependency / data / observability.
- Exposure score: 12/15.
- Fragility: provider latency or failure is hidden while local state can still move to `charged`.
- Blast radius: customer billing trust and invoice correctness.
- Reversibility: partial; local state repair is possible but manual and uncertain.
- Stress response curve: superlinear.
- Antifragile move: add an explicit timeout, preserve failed charge state, emit a metric/log, and add a provider-timeout regression test.
- Gain mechanism: faster learning and smaller blast radius.
- Robust vs antifragile delta: the timeout bounds the dependency; the regression test and telemetry convert provider failure into future learning.
- Missing evidence: alert owner, idempotency key, and rollback path.
- Cheapest observation: reproduce a provider timeout against a fake billing endpoint and assert invoice state plus telemetry.
- Validation: unit test with provider timeout plus scanner output containing `python-http-without-timeout` and `silent-exception` before the fix.
- Confidence: high from direct code evidence.

## Backlog

- Via negativa: remove swallowed exception behavior.
- Reversibility and optionality: document billing rollback and add idempotency evidence.
- Stress-learning experiments: fake provider timeout test.
- Observability and ownership: billing alert route and dashboard.
- Structural bets: only isolate provider behind an adapter if provider churn or a second provider becomes plausible.
- Missing evidence / cheapest observations: inspect route caller and alert routing.
- Scanner leads to verify: `github-actions-missing-concurrency`.
- Next reversible patch: timeout plus failed-state test.
