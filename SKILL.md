---
name: antifragile-software-review
description: Review and improve software repositories through Nassim Taleb's antifragility lens. Use when asked to make a codebase antifragile, apply Antifragile or Taleb concepts to software design, find or fix fragility risks, improve resilience beyond robustness, or inspect architecture, reliability, observability, deployment, testing, rollback, incident-learning, coupling, optionality, or failure-handling tradeoffs.
---

# Antifragile Software Review

## Overview

Inspect the codebase for design choices that are harmed by volatility, uncertainty, stress, errors, growth, incidents, or changing requirements. Produce concrete findings and changes that help the system gain information, options, or safety from small failures instead of merely surviving them.

Load `references/antifragility-primer.md` when you need the conceptual mapping from Taleb's ideas to software design.

## Workflow

1. Establish the system shape before judging it.
   - Read `README`, architecture docs, package manifests, CI config, deploy/infrastructure files, test layout, migrations, observability config, and runbooks if present.
   - Identify critical user flows, data mutation paths, external dependencies, release paths, and operational ownership.

2. Choose the operating mode from the user's wording.
   - Audit mode: if the user asks to review, inspect, assess, or tell them what to improve, produce findings and a backlog without changing files unless they ask.
   - Implementation mode: if the user asks to make, fix, address, harden, or improve the repo, implement the highest-exposure reversible change you can validate in the current turn. Preserve behavior unless the user asked for a behavior change.

3. Run the heuristic scanner for leads:

```bash
python3 /path/to/antifragile-software-review/scripts/antifragile_scan.py /path/to/repo
```

Use scanner output as a lead list only. Confirm important claims by reading the relevant code, tests, docs, and deployment configuration. Treat operational term counts as mention locations, not proof that rollback, canary, observability, or incident-learning capabilities actually work.

The scanner is language-aware but intentionally heuristic. It includes generic leads plus first-pass Python, Rust, SQL, TypeScript, and JavaScript signals. Prefer ecosystem linters for precise linting; use scanner `linter_overlaps` as a hint that the same code shape may already be covered by Ruff, Clippy, ESLint, TypeScript ESLint, or another language-specific tool.

Useful scanner controls:

```bash
python3 /path/to/antifragile-software-review/scripts/antifragile_scan.py /path/to/repo --exclude 'fixtures/**'
```

Add `antifragile-scan: ignore` or `antifragile-scan: ignore[pattern-id]` on a line only when the signal is intentionally reviewed and harmless.

4. Search manually for antifragility failure modes:
   - Silent failure: swallowed exceptions, empty catches, ignored errors, best-effort paths with no metric or alert.
   - Downside concentration: single process, region, queue, database, credential, deploy path, owner, or global state whose failure cascades.
   - Prediction dependence: fixed sleeps, magic thresholds, calendar assumptions, forecast-driven capacity, brittle ordering assumptions.
   - Irreversibility: migrations, scripts, deletes, billing actions, external side effects, or deploys with no dry-run, rollback, idempotency, or audit trail.
   - Tight coupling: synchronous chains, cross-layer imports, god modules, shared mutable state, hidden temporal coupling, deployment coupling.
   - Missing feedback loops: weak observability, no SLOs/error budgets, no incident review artifacts, no regression tests from prior incidents.
   - Fragile optimization: saturated queues, no slack, maximized utilization, no backpressure, no rate limits, no load shedding.
   - Unsafe experimentation: no feature flags, canaries, circuit breakers, kill switches, staged rollout, contract tests, or blast-radius limits.

5. Map evidence to antifragile levers.
   - Via negativa: remove the fragile thing before adding machinery.
   - Barbell: make the core boring, protected, and recoverable; isolate high-upside experiments behind reversible boundaries.
   - Optionality: add cheap options to change course, such as interfaces, feature flags, rollbacks, dry-runs, idempotency, adapters, and replaceable dependencies.
   - Convexity: prefer bounded downside with unbounded learning or upside.
   - Hormesis: add safe stressors such as fault injection, mutation testing, load tests, game days, dependency failure tests, and incident-derived regression tests.
   - Redundancy and slack: preserve spare capacity, backup paths, retries with budgets, bulkheads, queues, and graceful degradation.
   - Decentralization: contain failures locally and let teams/components learn independently where possible.
   - Skin in the game: make ownership, alerts, dashboards, and post-incident follow-through visible to the people changing the system.

6. Rank recommendations by fragility exposure.
   - Prioritize ruin risks and irreversible actions first.
   - Prefer small, reversible changes that create learning loops.
   - Separate robust/resilient fixes from truly antifragile fixes. A retry may be robust; a retry budget with metrics, alerting, and an incident-derived regression test is closer to antifragile.

7. In implementation mode, close the loop.
   - Patch one or more small, high-leverage changes that bound downside or create learning.
   - Add validation that will fail if the fragility comes back: regression tests, scanner tests, CI checks, metrics assertions, dry-run checks, or documented verification commands.
   - Re-run the relevant tests, scanner, and format/lint commands. If validation cannot run, say exactly what blocked it.
   - Report what changed, what now catches regressions, and any remaining higher-risk backlog items.

## Output Format

Start with findings, not a generic essay. Use this shape:

```markdown
## Findings

- [P1] Short title
  Evidence: `path/file.ext:123`
  Evidence quality: direct code path / config signal / docs-only / inference.
  Fragility: why volatility, errors, growth, or uncertainty hurts this design.
  Blast radius: what fails and who or what is affected.
  Reversibility: how easy the proposed move is to roll back or bound.
  Antifragile move: concrete change that bounds downside and creates learning/options.
  Robust vs antifragile delta: why this produces feedback, optionality, or safer stress rather than only durability.
  Validation: test, experiment, metric, or code-reading step that would prove the change.
  Confidence: high / medium / low, with the reason.

## Antifragility Backlog

- Via negativa:
- Reversibility and optionality:
- Stress-learning experiments:
- Observability and ownership:
- Structural bets:
- Next reversible patch:
```

Do not present generic practices as findings without codebase evidence. If evidence is missing, say what is unknown and how to verify it.
