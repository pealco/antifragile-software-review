# Antifragile Scanner Rules

47 rule(s). Empty language lists mean the rule can apply across supported text languages.

## bare-except

- Category: Silent failure and lost learning
- Concept: skin in the game / feedback
- Source kinds: code, config
- Languages: python
- Exposure dimensions: feedback_delay
- Linter overlaps: ruff:E722
- Why it matters: Broad exception handling can erase failure evidence unless it logs, measures, or re-raises nearby.
- Scanner value: Adds antifragility framing around feedback loss; Ruff provides more precise Python linting.

## debug-print

- Category: Weak observability
- Concept: feedback
- Source kinds: code, config
- Languages: any
- Exposure dimensions: feedback_delay
- Linter overlaps: none
- Why it matters: Ad hoc prints may indicate missing structured logs, metrics, or traces.
- Scanner value: Connects ad hoc output to observability gaps across Python, JavaScript, and Ruby.

## destructive-action

- Category: Irreversibility
- Concept: optionality / reversibility
- Source kinds: code, config
- Languages: any
- Exposure dimensions: irreversibility, ruin_potential
- Linter overlaps: none
- Why it matters: Destructive actions need dry-runs, rollback plans, backups, approvals, or idempotent recovery.
- Scanner value: Antifragility review lead; confirm in context before treating it as a finding.

## empty-catch

- Category: Silent failure and lost learning
- Concept: skin in the game / feedback
- Source kinds: code, config
- Languages: typescript, javascript, java, csharp
- Exposure dimensions: feedback_delay
- Linter overlaps: eslint:no-empty
- Why it matters: Empty catch blocks hide faults and prevent incident-derived improvement.
- Scanner value: Catches swallowed TypeScript/JavaScript-style exceptions as lost feedback, not syntax style.

## fixed-sleep

- Category: Prediction and timing dependence
- Concept: prediction dependence
- Source kinds: code, config
- Languages: any
- Exposure dimensions: feedback_delay, dependency_concentration
- Linter overlaps: none
- Why it matters: Fixed sleeps often encode timing predictions where event-driven checks or bounded retries are safer.
- Scanner value: Flags timing predictions across Python, Rust, SQL, TypeScript, JavaScript, Go, JVM, Ruby, and shell code.

## force-flag

- Category: Irreversibility
- Concept: optionality / reversibility
- Source kinds: code, config
- Languages: any
- Exposure dimensions: irreversibility, ruin_potential
- Linter overlaps: none
- Why it matters: Forced actions can remove useful friction around irreversible operations.
- Scanner value: Antifragility review lead; confirm in context before treating it as a finding.

## github-actions-unpinned-action

- Category: Prediction and timing dependence
- Concept: optionality / reversibility
- Source kinds: code, config
- Languages: github-actions
- Exposure dimensions: feedback_delay, dependency_concentration
- Linter overlaps: none
- Why it matters: Actions pinned to moving tags can change behavior outside the repository's control.
- Scanner value: Flags CI supply-chain drift; actionlint and policy checks can provide deeper workflow validation.

## global-state

- Category: Centralized state and tight coupling
- Concept: decentralization
- Source kinds: code, config
- Languages: any
- Exposure dimensions: dependency_concentration, blast_radius
- Linter overlaps: none
- Why it matters: Shared mutable state can concentrate downside and create hidden temporal coupling.
- Scanner value: Surfaces cross-language concentration risk; Python-only cases may overlap with Ruff.

## go-context-background

- Category: Cascade and ruin risk
- Concept: bounded downside
- Source kinds: code, config
- Languages: go
- Exposure dimensions: blast_radius, dependency_concentration, ruin_potential
- Linter overlaps: none
- Why it matters: Root contexts can lose cancellation, deadline, and ownership signals unless they are intentionally scoped.
- Scanner value: Frames Go context roots as cancellation-boundary leads; confirm whether a request or job context should flow through.

## go-global-var

- Category: Centralized state and tight coupling
- Concept: decentralization
- Source kinds: code, config
- Languages: go
- Exposure dimensions: dependency_concentration, blast_radius
- Linter overlaps: none
- Why it matters: Package-level mutable variables can concentrate state and make failure order-dependent.
- Scanner value: Heuristic Go mutable-state lead; confirm scope manually because the scanner is not parsing Go blocks.

## go-http-without-timeout

- Category: Cascade and ruin risk
- Concept: bounded downside
- Source kinds: code, config
- Languages: go
- Exposure dimensions: blast_radius, dependency_concentration, ruin_potential
- Linter overlaps: none
- Why it matters: Package-level Go HTTP helpers use the default client, which can wait indefinitely without an explicit timeout.
- Scanner value: Adds Go dependency-latency risk beside Python and JavaScript outbound-call cancellation leads.

## go-unbounded-goroutine

- Category: Cascade and ruin risk
- Concept: bounded downside
- Source kinds: code, config
- Languages: go
- Exposure dimensions: blast_radius, dependency_concentration, ruin_potential
- Linter overlaps: none
- Why it matters: Untracked goroutines can outlive their owner unless cancellation, backpressure, and error reporting are explicit.
- Scanner value: Surfaces Go concurrency ownership risk that needs code-reading confirmation.

## hardcoded-endpoint

- Category: Centralized state and tight coupling
- Concept: optionality
- Source kinds: code, config
- Languages: any
- Exposure dimensions: dependency_concentration, blast_radius
- Linter overlaps: none
- Why it matters: Hard-coded endpoints can reduce optionality unless isolated behind config or adapters.
- Scanner value: Antifragility review lead; confirm in context before treating it as a finding.

## ignored-error

- Category: Silent failure and lost learning
- Concept: skin in the game / feedback
- Source kinds: code, config
- Languages: any
- Exposure dimensions: feedback_delay
- Linter overlaps: none
- Why it matters: Explicitly ignored failures need an owner, metric, or bounded blast radius.
- Scanner value: Antifragility review lead; confirm in context before treating it as a finding.

## impossible-assumption

- Category: Prediction and timing dependence
- Concept: via negativa
- Source kinds: code, config
- Languages: any
- Exposure dimensions: feedback_delay, dependency_concentration
- Linter overlaps: none
- Why it matters: Claims that reality cannot vary are common sources of brittle edge cases.
- Scanner value: Antifragility review lead; confirm in context before treating it as a finding.

## java-kotlin-broad-catch

- Category: Silent failure and lost learning
- Concept: skin in the game / feedback
- Source kinds: code, config
- Languages: java, kotlin
- Exposure dimensions: feedback_delay
- Linter overlaps: none
- Why it matters: Broad JVM catches can turn failures into vague recovery paths unless logging, metrics, or rethrow behavior is explicit.
- Scanner value: Frames Java/Kotlin broad catches as feedback-loss leads rather than style violations.

## java-kotlin-static-mutable

- Category: Centralized state and tight coupling
- Concept: decentralization
- Source kinds: code, config
- Languages: java, kotlin
- Exposure dimensions: dependency_concentration, blast_radius
- Linter overlaps: none
- Why it matters: Static mutable state and companion objects can concentrate downside and hide replacement boundaries.
- Scanner value: Surfaces JVM central-state leads; confirm mutability and lifecycle in context.

## kubernetes-latest-image

- Category: Prediction and timing dependence
- Concept: optionality / reversibility
- Source kinds: code, config
- Languages: yaml
- Exposure dimensions: feedback_delay, dependency_concentration
- Linter overlaps: none
- Why it matters: Mutable latest tags make deploys harder to reproduce and roll back.
- Scanner value: Surfaces Kubernetes image reproducibility risk; confirm deployment tooling and registry policy.

## kubernetes-single-replica

- Category: Cascade and ruin risk
- Concept: redundancy and slack
- Source kinds: code, config
- Languages: yaml
- Exposure dimensions: blast_radius, dependency_concentration, ruin_potential
- Linter overlaps: none
- Why it matters: Single-replica workloads have little redundancy unless an external recovery path is explicit.
- Scanner value: Treats Kubernetes replica count as an availability lead, not proof of insufficient resilience.

## magic-timeout

- Category: Prediction and timing dependence
- Concept: prediction dependence
- Source kinds: code, config
- Languages: any
- Exposure dimensions: feedback_delay, dependency_concentration
- Linter overlaps: none
- Why it matters: Magic timeout constants should be tied to SLOs, budgets, or measured behavior.
- Scanner value: Antifragility review lead; confirm in context before treating it as a finding.

## process-abort

- Category: Cascade and ruin risk
- Concept: bounded downside
- Source kinds: code, config
- Languages: any
- Exposure dimensions: blast_radius, dependency_concentration, ruin_potential
- Linter overlaps: none
- Why it matters: Process-level aborts can turn local errors into system-wide outages.
- Scanner value: Surfaces process-level aborts across runtimes so reviewers can bound local failures.

## ruby-bare-rescue

- Category: Silent failure and lost learning
- Concept: skin in the game / feedback
- Source kinds: code, config
- Languages: ruby
- Exposure dimensions: feedback_delay
- Linter overlaps: rubocop:Style/RescueStandardError
- Why it matters: Bare rescue hides the failure class and can turn incidents into ambiguous recovery paths.
- Scanner value: Adds Ruby failure-feedback framing while leaving precise Ruby style enforcement to RuboCop.

## ruby-rescue-nil

- Category: Silent failure and lost learning
- Concept: skin in the game / feedback
- Source kinds: code, config
- Languages: ruby
- Exposure dimensions: feedback_delay
- Linter overlaps: none
- Why it matters: Rescue-to-nil can erase failure evidence and make downstream behavior depend on absence rather than ownership.
- Scanner value: Highlights Ruby fallback paths that may need logging, metrics, or narrower rescue boundaries.

## rust-debug-output

- Category: Weak observability
- Concept: feedback
- Source kinds: code, config
- Languages: rust
- Exposure dimensions: feedback_delay
- Linter overlaps: none
- Why it matters: Ad hoc Rust output can hide missing structured logging, metrics, or trace context.
- Scanner value: Connects Rust debug output to operational feedback quality.

## rust-todo-unimplemented

- Category: Known fragility markers
- Concept: via negativa
- Source kinds: code, config
- Languages: rust
- Exposure dimensions: feedback_delay
- Linter overlaps: none
- Why it matters: Placeholder or unreachable macros need ownership before they become production failure paths.
- Scanner value: Treats Rust placeholder and unreachable assumptions as review leads for ownership and blast radius.

## rust-unsafe

- Category: Centralized state and tight coupling
- Concept: bounded downside
- Source kinds: code, config
- Languages: rust
- Exposure dimensions: dependency_concentration, blast_radius
- Linter overlaps: none
- Why it matters: Unsafe Rust removes compiler guarantees and needs a small, well-tested, well-owned boundary.
- Scanner value: Highlights Rust safety-boundary concentration rather than treating unsafe as automatically wrong.

## rust-unwrap-expect

- Category: Cascade and ruin risk
- Concept: bounded downside
- Source kinds: code, config
- Languages: rust
- Exposure dimensions: blast_radius, dependency_concentration, ruin_potential
- Linter overlaps: none
- Why it matters: Rust unwrap/expect can turn recoverable errors into panics unless isolated at an intentional boundary.
- Scanner value: Adds Rust failure-boundary context; Clippy is better for precise Rust linting.

## shell-curl-pipe

- Category: Irreversibility
- Concept: optionality / reversibility
- Source kinds: code, config
- Languages: shell
- Exposure dimensions: irreversibility, ruin_potential
- Linter overlaps: none
- Why it matters: Piping downloaded code into a shell removes review, pinning, and rollback opportunities.
- Scanner value: Flags shell supply-chain and reversibility risk; dedicated shell/security tools should do deeper validation.

## silent-exception

- Category: Silent failure and lost learning
- Concept: skin in the game / feedback
- Source kinds: code, config
- Languages: python
- Exposure dimensions: feedback_delay
- Linter overlaps: none
- Why it matters: Swallowed errors convert stress into ignorance instead of learning.
- Scanner value: Highlights lost learning and missing ownership even when a Python linter also flags the construct.

## singleton

- Category: Centralized state and tight coupling
- Concept: decentralization
- Source kinds: code, config
- Languages: any
- Exposure dimensions: dependency_concentration, blast_radius
- Linter overlaps: none
- Why it matters: Singleton-style access can hide central dependency and replacement risk.
- Scanner value: Antifragility review lead; confirm in context before treating it as a finding.

## sql-destructive-schema

- Category: Irreversibility
- Concept: optionality / reversibility
- Source kinds: code, config
- Languages: sql
- Exposure dimensions: irreversibility, ruin_potential
- Linter overlaps: none
- Why it matters: Destructive schema changes need rollback, backups, staged deploys, or explicit recovery plans.
- Scanner value: Extends irreversible-change review to SQL schema operations beyond DROP TABLE.

## sql-update-without-where

- Category: Irreversibility
- Concept: optionality / reversibility
- Source kinds: code, config
- Languages: sql
- Exposure dimensions: irreversibility, ruin_potential
- Linter overlaps: none
- Why it matters: Bulk updates without an inline WHERE clause can create large irreversible data changes.
- Scanner value: Flags data mutation blast radius for reviewer confirmation; multiline SQL needs manual review.

## terraform-open-cidr

- Category: Cascade and ruin risk
- Concept: bounded downside
- Source kinds: code, config
- Languages: terraform
- Exposure dimensions: blast_radius, dependency_concentration, ruin_potential
- Linter overlaps: none
- Why it matters: Open ingress or egress CIDRs can create broad blast radius unless deliberately bounded by other controls.
- Scanner value: Surfaces Terraform exposure leads for reviewer confirmation; infrastructure security scanners should provide precision.

## terraform-wildcard-iam

- Category: Cascade and ruin risk
- Concept: bounded downside
- Source kinds: code, config
- Languages: terraform
- Exposure dimensions: blast_radius, dependency_concentration, ruin_potential
- Linter overlaps: none
- Why it matters: Wildcard IAM actions or resources can concentrate privilege and expand blast radius.
- Scanner value: Flags Terraform IAM optionality and downside-concentration leads without replacing policy analyzers.

## todo-debt

- Category: Known fragility markers
- Concept: via negativa
- Source kinds: code, config
- Languages: any
- Exposure dimensions: feedback_delay
- Linter overlaps: none
- Why it matters: Known debt is often the cheapest place to remove fragility first.
- Scanner value: Antifragility review lead; confirm in context before treating it as a finding.

## typescript-explicit-any

- Category: Prediction and timing dependence
- Concept: optionality / feedback
- Source kinds: code, config
- Languages: typescript
- Exposure dimensions: feedback_delay, dependency_concentration
- Linter overlaps: @typescript-eslint:no-explicit-any
- Why it matters: Explicit any removes type feedback and can let contract drift reach runtime.
- Scanner value: Frames TypeScript type erasure as lost feedback and contract optionality.

## unbounded-loop

- Category: Cascade and ruin risk
- Concept: bounded downside
- Source kinds: code, config
- Languages: any
- Exposure dimensions: blast_radius, dependency_concentration, ruin_potential
- Linter overlaps: none
- Why it matters: Unbounded loops need cancellation, backoff, budgets, or visible liveness signals.
- Scanner value: Looks for unbounded loop forms across Python, JavaScript, TypeScript, C-style languages, and Rust.

## unbounded-queue

- Category: Cascade and ruin risk
- Concept: redundancy and slack
- Source kinds: code, config
- Languages: any
- Exposure dimensions: blast_radius, dependency_concentration, ruin_potential
- Linter overlaps: none
- Why it matters: Unbounded queues can convert traffic spikes into memory pressure, feedback delay, and retry cascades.
- Scanner value: Feeds exposure scoring for slack and backpressure review; confirm producer and consumer bounds in context.

## data-change-missing-checkpoint

- Category: Irreversibility
- Concept: optionality / reversibility
- Source kinds: code, config
- Languages: any
- Exposure dimensions: irreversibility, ruin_potential
- Linter overlaps: none
- Why it matters: Data-changing migrations, backfills, and repair scripts need checkpoints, batching, or resumability to bound partial failure.
- Scanner value: Feeds exposure scoring for irreversible data work by surfacing missing resumability evidence.

## data-change-missing-dry-run

- Category: Irreversibility
- Concept: optionality / reversibility
- Source kinds: code, config
- Languages: any
- Exposure dimensions: irreversibility, ruin_potential
- Linter overlaps: none
- Why it matters: Data-changing migrations, backfills, and repair scripts need dry-run or preview evidence before touching real state.
- Scanner value: Feeds the data-ruin review path by finding irreversible operations that lack cheap preflight feedback.

## fetch-without-abort

- Category: Cascade and ruin risk
- Concept: bounded downside
- Source kinds: code
- Languages: javascript, typescript
- Exposure dimensions: blast_radius, dependency_concentration, feedback_delay
- Linter overlaps: none
- Why it matters: Fetch calls without cancellation can outlive their usefulness under latency or navigation changes.
- Scanner value: Covers browser and JavaScript cancellation risk outside Ruff's Python-only scope.

## github-actions-missing-concurrency

- Category: Cascade and ruin risk
- Concept: bounded downside
- Source kinds: config
- Languages: github-actions
- Exposure dimensions: blast_radius, dependency_concentration, ruin_potential
- Linter overlaps: none
- Why it matters: Workflows without concurrency controls can overlap deploys or repeated expensive jobs under churn.
- Scanner value: Treats workflow concurrency as a blast-radius lead for CI/CD review, not a universal requirement.

## kubernetes-missing-health-probes

- Category: Silent failure and lost learning
- Concept: feedback
- Source kinds: config
- Languages: yaml
- Exposure dimensions: feedback_delay
- Linter overlaps: none
- Why it matters: Kubernetes workloads without readiness or liveness probes provide weak feedback to schedulers and deploys.
- Scanner value: Surfaces workload feedback-loop gaps; confirm whether probes are injected or managed elsewhere.

## kubernetes-missing-resource-limits

- Category: Cascade and ruin risk
- Concept: bounded downside
- Source kinds: config
- Languages: yaml
- Exposure dimensions: blast_radius, dependency_concentration, ruin_potential
- Linter overlaps: none
- Why it matters: Kubernetes workloads without resource settings can let one workload consume shared cluster capacity.
- Scanner value: Surfaces capacity-blast-radius leads; confirm defaults, LimitRanges, and platform policy in context.

## python-http-without-timeout

- Category: Cascade and ruin risk
- Concept: bounded downside
- Source kinds: code
- Languages: python
- Exposure dimensions: blast_radius, dependency_concentration, feedback_delay
- Linter overlaps: ruff:S113
- Why it matters: Outbound calls without explicit timeouts can turn dependency latency into thread or worker exhaustion.
- Scanner value: Keeps timeout risk in the antifragility report beside non-Python cancellation and cascade signals.

## retry-without-backoff

- Category: Cascade and ruin risk
- Concept: bounded downside / feedback
- Source kinds: code, config
- Languages: any
- Exposure dimensions: blast_radius, dependency_concentration, ruin_potential
- Linter overlaps: none
- Why it matters: Retry paths without backoff, jitter, deadlines, or budgets can amplify dependency stress into a retry storm.
- Scanner value: Feeds critical-flow exposure review for superlinear harm under dependency latency or failure.

## shell-missing-strict-mode

- Category: Silent failure and lost learning
- Concept: skin in the game / feedback
- Source kinds: code, config
- Languages: shell
- Exposure dimensions: feedback_delay
- Linter overlaps: none
- Why it matters: Shell scripts without strict error handling can continue after failed commands and lose failure evidence.
- Scanner value: Checks a shell-script-level failure mode that line linters may not frame as operational feedback loss.
