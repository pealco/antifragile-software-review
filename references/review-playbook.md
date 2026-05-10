# Antifragility Review Playbook

This playbook keeps the review focused on architecture, operating model, design decisions, and feedback loops. The scanner is useful evidence, but it is not the review.

## Review Thesis

Start by writing a short thesis before listing findings:

- System shape: what the system appears to do, the main runtime pieces, and the critical user or business flows.
- Stressors: the volatility the system actually faces, such as dependency failure, load spikes, malformed input, schema change, incidents, cost pressure, traffic shifts, or changing requirements.
- Fragility hypothesis: where those stressors can create nonlinear harm.
- Antifragile opportunity: where small failures could be converted into learning, optionality, safer experiments, or smaller future downside.
- Evidence confidence: what is direct code/config evidence, what is docs-only evidence, and what is still unknown.

Keep the thesis falsifiable. A useful thesis names a concrete path, owner, dependency, state boundary, or release mechanism that can be inspected.

## System Map

Build a minimal map before recommending changes:

| Area | Questions |
| --- | --- |
| Critical flows | What paths create value, mutate data, move money, notify users, or control deploys? |
| State and data | Which stores are authoritative, which writes are irreversible, and which migrations can be replayed or rolled back? |
| Dependencies | Which external services, queues, secrets, vendors, regions, models, libraries, or CLIs can stall the system? |
| Release path | How are changes staged, verified, rolled back, and observed? What can be canaried or disabled? |
| Feedback loops | What metrics, logs, traces, SLOs, tests, runbooks, and incident reviews turn stress into learning? |
| Ownership | Who receives the alert, decides the rollback, owns the runbook, and pays the cost of fragile decisions? |
| Optionality | Which choices are cheap to change, and which choices lock the system into one vendor, schema, protocol, or deployment path? |

Use scanner results as search leads inside this map. For example, an uncancelled HTTP call matters more if it is on a critical request path with no queue, timeout budget, or degraded mode.

## Analysis Dimensions

Assess each important design area with these dimensions:

| Dimension | Fragile pattern | Antifragile move |
| --- | --- | --- |
| Downside concentration | One component, person, region, database, queue, credential, or deploy step can halt the whole system. | Add bulkheads, local failure handling, alternate paths, and explicit ownership. |
| Reversibility | Changes are hard to undo, replay, or inspect after impact. | Add dry-runs, rollbacks, idempotency, backups, staged migrations, and audit trails. |
| Feedback quality | Failures disappear into retries, logs nobody reads, or user reports. | Add actionable metrics, alerts, traces, tests, and incident-derived regression checks. |
| Prediction dependence | Correctness depends on fixed sleeps, assumed ordering, forecast capacity, or manually timed operations. | Replace predictions with measured readiness, deadlines, backpressure, and adaptive control. |
| Safe experimentation | Every experiment has production-wide blast radius. | Use feature flags, canaries, shadow traffic, sandboxes, kill switches, and contract tests. |
| Slack and redundancy | The system runs hot, queues are unbounded, and fallback capacity is unknown. | Preserve headroom, bounded queues, load shedding, graceful degradation, and restore drills. |
| Incident learning | Incidents create cleanup work but no durable learning. | Turn incidents into tests, dashboards, runbook updates, ownership changes, and safer defaults. |
| Optionality | A design choice locks in one vendor, schema, protocol, runtime, or team bottleneck. | Introduce replaceable boundaries only where uncertainty is real and carrying cost is justified. |

## Domain Playbooks

### Architecture And Coupling

Look for central modules, implicit temporal ordering, cross-layer imports, shared mutable state, and abstractions that hide blast radius. Prefer simpler boundaries that make failure local and replacement cheap. Do not recommend abstraction for its own sake; recommend it when it creates real optionality around uncertainty.

### Data And Migrations

Prioritize irreversible writes, destructive migrations, backfills, data repair scripts, and schema changes crossing deploy boundaries. Strong moves include expand-contract migrations, dry-run counts, idempotent backfills, checkpoints, restore drills, and data invariants that fail before damage spreads.

### Release And Deployment

Review whether the system can absorb bad releases without broad impact. Look for staged rollout, canary checks, rollback instructions, feature flags, deployment locks, workflow concurrency, artifact pinning, and observability tied to deploy events. A rollback button without verification is only partial resilience.

### Dependencies And Vendors

Map what happens when a dependency is slow, unavailable, expensive, inconsistent, compromised, or behaviorally changed. Strong moves include timeouts, budgets, circuit breakers, cached degradation, provider adapters where justified, contract tests, and explicit vendor-exit notes for high-uncertainty bets.

### Observability And Incident Learning

Check whether failures become durable knowledge. Useful evidence includes SLOs, error budgets, dashboards tied to critical flows, alerts with owners, runbooks, incident reviews, and regression tests from prior incidents. Logging alone is not a feedback loop unless someone acts on it.

### Testing And Safe Stress

Look beyond happy-path unit tests. Valuable stressors include property tests, mutation tests, load tests, fault injection, dependency failure tests, replay tests, migration dry-runs, restore drills, and game days. The key is bounded downside plus learning.

### Security And Abuse Resistance

Treat security controls as antifragility when they reduce blast radius and generate learning. Look for least privilege, credential rotation, auditability, dependency pinning, policy checks, input validation, rate limiting, and abuse telemetry. Avoid presenting scanner hints as proof of vulnerability.

## Recommendation Rules

- Prefer removing fragile mechanisms before adding new machinery.
- Tie every recommendation to a stressor and a blast radius.
- State whether the move is robust, resilient, or antifragile.
- Prefer small reversible patches that create learning loops.
- Do not overfit to scanner output. A scanner hit outside a critical path may be lower priority than an architectural single point of failure with no regex signal.
- Separate confirmed findings from open questions.
- When confidence is low, recommend the cheapest observation that would raise confidence.

## Evidence Ladder

Use this order when ranking confidence:

1. Direct code/config path on a critical flow.
2. Test, CI, migration, deploy, or infrastructure evidence.
3. Runtime/operational artifact such as logs, dashboards, runbooks, or incident notes.
4. Documentation claim with supporting implementation evidence.
5. Scanner-only or docs-only lead that still needs confirmation.

Scanner-only leads should rarely be P1 findings. They are usually prompts for code reading.
