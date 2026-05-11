# Data Ruin And Incident Learning Golden Review

## Antifragility Thesis

- System shape: repo with destructive migration, account backfill, runbook, and incident note.
- Primary stressors: partial backfill, destructive schema change, repeated billing failure, and manual repair.
- Fragility hypothesis: data changes can cause durable harm because dry-run, checkpoint, restore, and incident-derived regression evidence is absent.
- Antifragile opportunity: add dry-run counts, resumable batches, restore evidence, and convert the repeated incident into a regression test and runbook update.
- Evidence confidence: direct SQL/script/docs evidence; restore drill evidence is missing.

## System Map

- Critical flows: schema migration and billing account backfill.
- State and data: users table and accounts billing state.
- Dependencies: database and manual repair workflow.
- Release path: not visible in fixture.
- Feedback loops: incident note and runbook exist, but no linked test or restore proof.
- Ownership and optionality: manual repair path is described but not validated.

## Critical Flow Trace

| Step | Evidence | Missing evidence | Cheapest observation |
| --- | --- | --- | --- |
| Trigger and entrypoint | migration SQL and `scripts/backfill_accounts.py`. | Deploy runner and operator command. | Inspect migration runner or script invocation docs. |
| State/data mutation | `DROP COLUMN`, `UPDATE users`, and account updates. | Dry-run row counts and sampled impact. | Run against fixture DB in dry-run mode or add dry-run support. |
| Dependencies | database. | backup freshness and restore proof. | Locate latest restore drill or run local restore rehearsal. |
| Failure handling | no checkpoint or resumability evidence. | interruption behavior. | Interrupt a small fixture backfill and resume it. |
| Observability and ownership | incident note and runbook. | regression test, alert, dashboard, owner. | Add a regression test linked from the incident note. |
| Rollback/degradation path | runbook mentions manual repair. | tested restore or repair path. | Execute restore or replay rehearsal in nonproduction. |

- Stress response curve: superlinear.
- Scanner leads that matter: `data-change-missing-dry-run`, `data-change-missing-checkpoint`, `sql-destructive-schema`, `sql-update-without-where`.
- Scanner leads deferred: none.

## Finding Scorecard

| Finding | Evidence quality | Blast radius | Irreversibility | Feedback delay | Dependency concentration | Ruin potential | Exposure |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Destructive data changes lack dry-run and checkpoint evidence | direct code/config path | 3 | 3 | 2 | 2 | 3 | 13/15 |

## Findings

### [P1] Destructive data changes lack dry-run and checkpoint evidence

- Evidence: `db/migrations/001_drop_legacy_tokens.sql`, `scripts/backfill_accounts.py`, `docs/incidents/2026-01-billing.md`.
- Evidence quality: direct code/config path plus docs.
- Analysis area: data / observability / testing.
- Exposure score: 13/15.
- Fragility: destructive and broad data writes can leave durable damage if interrupted or wrong.
- Blast radius: user data integrity and billing repair trust.
- Reversibility: weak until dry-run, checkpoint, and restore evidence exists.
- Stress response curve: superlinear.
- Antifragile move: add dry-run counts, resumable batches, restore rehearsal notes, and a regression test linked from the incident.
- Gain mechanism: cheaper reversal and incident-to-test conversion.
- Robust vs antifragile delta: recovery docs alone are resilient; incident-derived tests and restore rehearsals turn failures into durable learning.
- Missing evidence: backup freshness, restore drill, operator command, and alert owner.
- Cheapest observation: run the backfill in dry-run mode against a fixture and interrupt it to verify resumability.
- Validation: executable dry-run/checkpoint test and updated incident note referencing the regression.
- Confidence: high for missing dry-run/checkpoint evidence; medium for restore posture.

## Backlog

- Via negativa: avoid destructive schema removal until consumers are proven migrated.
- Reversibility and optionality: add dry-run and checkpoint support.
- Stress-learning experiments: restore rehearsal and interrupted-backfill test.
- Observability and ownership: link incident to alert owner and regression test.
- Structural bets: none before recovery mechanics are proven.
- Missing evidence / cheapest observations: locate restore drill and operator invocation.
- Scanner leads to verify: `sql-update-without-where`.
- Next reversible patch: add dry-run output to the backfill script.
