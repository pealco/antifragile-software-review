# Example Antifragility Review Scorecard

This example shows the intended level of specificity for a small service review. It is illustrative, not evidence for this repository.

## Antifragility Thesis

- System shape: API service accepts order requests, writes order state, calls a payment provider, emits fulfillment events, and runs database migrations from CI.
- Primary stressors: payment latency, partial provider outages, duplicate requests, schema changes, bad deploys, and missing operational feedback.
- Fragility hypothesis: payment and fulfillment sit on a high-exposure path where timeout gaps and irreversible writes can turn ordinary dependency failures into customer-visible incidents.
- Antifragile opportunity: add cheap observations, reversible release gates, idempotency checks, and incident-derived tests so small failures improve future behavior.
- Evidence confidence: medium; code and CI evidence exist, but production metrics, runbooks, and restore drills are not visible.

## System Map

- Critical flows: checkout submission, payment authorization, order persistence, fulfillment event emission, refund handling.
- State and data: orders table, payment transaction ids, outbox table, migration history.
- Dependencies: payment provider API, message broker, database, CI deploy identity.
- Release path: GitHub Actions deploys after tests; rollback command is documented but not exercised in CI.
- Feedback loops: application logs and unit tests are present; SLOs, alert owners, and incident regression tests are missing.
- Ownership and optionality: provider integration is isolated behind one client, but payment behavior is not feature-flagged or contract-tested.

## Critical Flow Trace

| Step | Evidence | Missing evidence | Cheapest observation |
| --- | --- | --- | --- |
| Trigger and entrypoint | `POST /checkout` handler validates cart id and user id. | Duplicate request behavior under retry. | Add a test for two identical checkout submissions. |
| State/data mutation | Order row is created before payment authorization. | Whether failed authorization leaves recoverable state. | Add an integration test for payment timeout after order creation. |
| Dependencies | Payment client performs an outbound HTTP call. | Timeout budget and retry behavior tied to request context. | Assert explicit timeout and cancellation propagation in client tests. |
| Failure handling | Provider errors return a generic checkout failure. | Structured error category, metric, and alert owner. | Emit a tagged metric for provider timeout, decline, and unexpected error. |
| Observability and ownership | Request id appears in logs. | Dashboard, SLO, alert recipient, and runbook. | Link the metric to an alert owner and one-page runbook. |
| Rollback/degradation path | Deploy workflow has a manual rollback command. | Proof rollback was tested after migrations. | Add a rollback drill checklist or CI smoke test against a reversible migration fixture. |

- Stress response curve: superlinear until timeout, idempotency, and rollback evidence exist.
- Scanner leads that matter: outbound HTTP without timeout, destructive migration without dry-run evidence, unpinned CI action.
- Scanner leads deferred: local debug prints outside checkout and migration paths.

## Finding Scorecard

| Finding | Evidence quality | Blast radius | Irreversibility | Feedback delay | Dependency concentration | Ruin potential | Exposure |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Payment calls lack a bounded timeout and cancellation contract | direct critical-flow path | 3 | 1 | 2 | 2 | 2 | 10/15 |
| Migrations lack visible rollback or restore evidence | config/test/deploy signal | 2 | 3 | 2 | 1 | 3 | 11/15 |
| Checkout incidents do not become regression tests | missing operational evidence | 2 | 1 | 3 | 1 | 1 | 8/15 |

## Findings

### [P1] Payment dependency failure can occupy the checkout path without producing useful learning

- Evidence: checkout calls the payment provider during order creation; scanner lead indicates the outbound call has no explicit timeout.
- Evidence quality: direct critical-flow path after code confirmation.
- Analysis area: dependency / observability / testing.
- Exposure score: 10/15.
- Fragility: provider latency can consume request capacity while the system learns only that checkout failed.
- Blast radius: checkout requests, customer payment attempts, support load, and order reconciliation.
- Reversibility: low-risk change if the timeout is introduced behind a named payment client budget and tested with a fake provider.
- Stress response curve: superlinear now; capped after timeout, cancellation, idempotency, and metrics are verified.
- Antifragile move: add an explicit timeout budget, propagate cancellation, categorize provider errors, and test timeout behavior against an idempotent retry.
- Gain mechanism: smaller blast radius, faster learning, and safer experimentation with provider behavior.
- Robust vs antifragile delta: a timeout alone is robust; timeout metrics plus an incident-derived regression test make future dependency failures improve the system.
- Missing evidence: production latency distribution and alert owner.
- Cheapest observation: record provider timeout counts by endpoint and add one alert-owner note to the runbook.
- Validation: unit test fake provider timeout, integration test duplicate checkout retry, scanner no longer reports the timeout lead on the payment client.
- Confidence: medium; the recommendation depends on confirming the exact payment client call path.

## Backlog

- Via negativa: remove any checkout-side best-effort swallowing that hides payment provider categories.
- Reversibility and optionality: add a feature flag for switching the checkout payment path into authorize-only or degraded mode.
- Stress-learning experiments: run a fake provider timeout test in CI and a staging fault-injection check before major checkout releases.
- Observability and ownership: add a checkout SLO, timeout metric, alert owner, and minimal runbook.
- Structural bets: keep the payment provider behind the existing client boundary until a second provider is plausible enough to justify a deeper adapter.
- Missing evidence / cheapest observations: verify restore drill dates, migration rollback steps, and production dashboard coverage.
- Scanner leads to verify: destructive migration commands, unpinned CI action, and debug prints on checkout-adjacent paths.
- Next reversible patch: add the payment timeout contract and timeout regression test before changing broader checkout architecture.
