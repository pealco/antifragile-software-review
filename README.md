# Fragility Review

[![Tests](https://github.com/pealco/antifragile-software-review/actions/workflows/test.yml/badge.svg)](https://github.com/pealco/antifragile-software-review/actions/workflows/test.yml)

A Claude Code plugin, and an Agent Skill for Codex and other clients, for finding where a software system gets hurt by stress or by a mistake, and for fixing the worst of it. It draws on mistake-proofing (poka-yoke), human-error and system-safety research, and antifragility, and it credits only controls that something has proven.

The goal is not to make code perfect or to eliminate failure. The goal is a codebase where a mistake or a shock cannot travel far enough to cause harm that cannot be undone, and where each failure leaves a test, an alert, or a safer default behind.

## What It Does

Fragility Review gives an agent a structured way to review a repository for design choices that get worse under stress or that invite mistakes. It asks the agent to build a system map, identify critical flows, trace at least one high-exposure path, rate the control that stops each mistake along it, score exposure, and recommend changes that bound the downside, stop the mistake at its source, or turn failures into learning.

In practice, the skill helps find questions like:

- What happens when a dependency is slow, unavailable, or changes behavior?
- Which migrations, backfills, deletes, or external side effects are hard to reverse?
- What can an on-call engineer or a coding agent get wrong here, and what stops it before it does harm?
- Which kill switches, rollbacks, restores, and tests have never been shown to work?
- Where do errors disappear without metrics, alerts, ownership, or regression tests?
- Which deploy, CI, rollback, or release paths can overlap, drift, or fail silently?
- Where is a proposed abstraction adding real options, and where is it just extra coupling?
- Which incident notes, runbooks, tests, and dashboards prove that past failures made the system better?

It is useful when you want to:

- audit a codebase or architecture for fragility risks,
- choose the first critical flow to investigate in an unfamiliar repo,
- convert vague reliability concerns into evidence-backed findings,
- rank recommendations by blast radius, irreversibility, feedback delay, dependency concentration, and ruin potential,
- implement small reversible improvements with validation, instead of producing a generic best-practices checklist.

This is different from a linter. Linters are excellent at local correctness, style, security rules, and language-specific best practices. This skill is concerned with system behavior under stress, and under the mistakes of the people and coding agents who change it: coupling, recovery, reversibility, observability, deployment safety, dependency optionality, and whether incidents create durable learning. The included scanner is only a discovery aid; it points the agent toward likely review leads and critical-flow candidates, but the final judgment should come from reading the relevant code, config, tests, and operational artifacts in context.

What the evals show, as of October 2026: on three fixtures, Claude Opus 5.5 finds the planted problems a little more often with the skill than without (27/27 vs 21/27, 20/21 vs 17/21, 18/21 vs 17/21 substance assertions over 3 runs each), and every configuration fixes the main faults when asked to harden. The skill's larger measured effect is on what it leaves in the code. When it hardens a repository it states the invariant in the code, and a later coding agent asked to make an unsafe change then declined or built it safely in 14 of 15 skill-hardened repositories, against 0 of 15 hardened without the skill, across three runs. When the request insisted on the unsafe change, neither configuration held (1 of 10 skill-hardened repositories stayed safe, 0 of 10 others); a CI check that runs the challenge test blocked every unsafe build. The skill's wording was cleaned after those runs without changing the method. The method, its sources, and the measurements are in `docs/mistake-proofing-research.md`.

## What It Includes

This repository contains:

- `skills/fragility-review/`: the skill itself, laid out as an Agent Skill: `SKILL.md`, with `references/`, `scripts/`, `templates/`, and `examples/` beside it.
- `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`: the Claude Code plugin manifest and the one-entry marketplace that makes this repository installable with `/plugin install`.
- `VERSION`: the released version; the manifests and the install examples must agree with it, and the contract check enforces that.
- `skills/fragility-review/references/review-playbook.md`: the system-level review method for architecture, operations, release, data, dependency, testing, and incident-learning analysis.
- `skills/fragility-review/references/lenses.md`: the ideas behind the method, one lens each: mistake-proofing (Shingo), human error (Reason, Norman), system safety (Leveson, Hollnagel), dependability (Avižienis), and antifragility (Taleb).
- `skills/fragility-review/references/evaluation-scenarios.md`: representative behavior checks for keeping the skill architecture-first, evidence-driven, and resistant to scanner overfitting.
- `skills/fragility-review/references/scanner-rules.md`: generated scanner rule metadata for reviewing coverage, linter overlap, and exposure dimensions.
- `skills/fragility-review/scripts/fragility_scan.py`: a dependency-free Python scanner that surfaces review leads across several languages, runtimes, and infrastructure files.
- `tools/check_package_contract.py`: a CI-enforced consistency check for skill metadata, references, plugin manifests, release pins, generated docs, and workflow pins.
- `skills/fragility-review/templates/review-scorecard.md`: a reusable scorecard for critical-flow traces, exposure scoring, and findings.
- `skills/fragility-review/examples/scorecard-review.md`: a compact example of the review scorecard filled out for a realistic service.
- `evals/`: scanner-and-golden-file checks that run in CI, plus model-in-the-loop evals for triggering and review quality (see Skill Evals).
- `skills/fragility-review/scripts/check_review_evidence.py`: checks that every file and line a review cites on an `Evidence:` line exists. `SKILL.md` tells the agent to run it before it sends a review.
- `skills/fragility-review/scripts/check_test_strength.py`: stubs each function out (`return None`, then `return True`) and reruns the test suite; a function whose stub the suite tolerates has no test that depends on its logic. The scanner's `test-*` rules flag the static shapes of a test that cannot fail: an expected value computed by the code under test, loose or call-only assertions, no assertion at all, fixed sleeps, swallowed exceptions, and skips without a reason.
- `docs/mistake-proofing-research.md`: the research behind the mistake-proofing method (poka-yoke, safety science, software practice, coding agents), the control strength scale, and how the method is measured.
- `evals/challenges/`: challenge tests that feed a known-bad case to a repository after an agent changed it and check that the mistake no longer gets through; `evals/run_agent_trap_evals.py` runs later coding agents against hardened repositories, with tasks from `evals/agent_traps*.json`, and reports whether their changes reopen the mistake.

The scanner is deliberately secondary. It helps discover concrete code smells and review leads, but the skill's main value is broader architectural, operational, and design analysis.

## Install

This repository is a Claude Code plugin and its own marketplace. The skill inside it follows the Agent Skills layout (`skills/fragility-review/SKILL.md`, with `scripts/`, `references/`, and `templates/` beside it), so it also installs as a plain skill in Claude Code, Codex, or any client that reads `SKILL.md`. The examples below pin `v0.3.0`. Install from `main` only when you want unreleased changes.

### Claude Code plugin

One step, in a session (Claude Code 2.1.275 or later):

```text
/plugin install fragility-review --marketplace pealco/antifragile-software-review
```

Or add the marketplace first, pinned to a release, then install:

```text
/plugin marketplace add pealco/antifragile-software-review#v0.3.0
/plugin install fragility-review@pealco
```

From a shell:

```bash
claude plugin install fragility-review --marketplace pealco/antifragile-software-review --scope user
```

The skill triggers on its own when a request matches its description. Invoke it by hand with `/fragility-review:fragility-review`. Third-party marketplaces do not auto-update, so update with:

```bash
claude plugin update fragility-review@pealco
```

Remove it with:

```bash
claude plugin uninstall fragility-review@pealco
```

If you installed version 0.2.0 or earlier under the old name `antifragile-software-review`, `claude plugin update` cannot follow the rename: it removes the old record and downloads the new version without registering it. Install the new name (if the uninstall says the plugin is not found, skip it):

```bash
claude plugin uninstall antifragile-software-review@pealco
claude plugin install fragility-review@pealco --scope user
```

Try it for one session without installing:

```bash
git clone https://github.com/pealco/antifragile-software-review.git
claude --plugin-dir ./fragility-review
```

### Claude Code skill directory

Without the plugin system, clone the repository into the personal skills directory. Claude Code loads a folder there that carries `.claude-plugin/plugin.json` as a plugin named `fragility-review@skills-dir` and finds the skill under `skills/`:

```bash
mkdir -p ~/.claude/skills
git clone --branch v0.3.0 https://github.com/pealco/antifragile-software-review.git \
  ~/.claude/skills/fragility-review
```

Update it with `git -C ~/.claude/skills/fragility-review pull --ff-only`, switch releases with `git -C ~/.claude/skills/fragility-review checkout v0.3.0` after a `fetch --tags`, and uninstall by deleting the directory. Restart Claude Code after installing so the skill index refreshes.

For a project-local install, add the repository as a submodule anywhere in the project and link the skill folder into `.claude/skills`:

```bash
git submodule add --branch v0.3.0 https://github.com/pealco/antifragile-software-review.git \
  vendor/fragility-review
mkdir -p .claude/skills
ln -s ../../vendor/fragility-review/skills/fragility-review \
  .claude/skills/fragility-review
```

Claude Code exposes the skill directory through `${CLAUDE_SKILL_DIR}`, so the scanner commands in `SKILL.md` work without hard-coded paths.

### Codex

Requirements: Codex CLI with local skill support, Git, and Python 3.10 or newer to run the scripts.

Codex reads `~/.codex/skills/<name>/SKILL.md`, so link the skill folder there:

```bash
git clone --branch v0.3.0 https://github.com/pealco/antifragile-software-review.git \
  ~/src/fragility-review
mkdir -p ~/.codex/skills
ln -s ~/src/fragility-review/skills/fragility-review \
  ~/.codex/skills/fragility-review
```

Restart Codex after installing so the skill registry reloads. Update with `git -C ~/src/fragility-review pull --ff-only`; switch releases with `git -C ~/src/fragility-review checkout v0.3.0` after a `fetch --tags`; uninstall by removing the link and the clone.

Invoke it explicitly:

```text
[$fragility-review] Review this repo for fragility risks.
```

### Other clients

Copy or link `skills/fragility-review` wherever your client reads Agent Skills. The frontmatter uses one Claude Code-only key, `argument-hint`; clients that reject unknown keys (claude.ai skill uploads do) need it removed.

Use it naturally in any client:

```text
Review this repository for fragility: what breaks badly under stress, and what a person or a coding agent can get wrong.
Find fragility risks in this design and suggest improvements.
Use fragility-review to audit this service.
```

## Use

### Review With The Skill

When asked for an audit, the skill should diagnose fragility risks and explain why they matter. When asked to address issues, it should turn recommendations into implementation work.

Good review prompts include:

```text
Audit this repo for what breaks badly under stress.
Review this architecture for reversibility, failure learning, and the controls that stop mistakes.
Idiot-proof the ops scripts: what should be impossible to get wrong?
Review this through an antifragility lens.
Address the fragility issues you identify.
```

The review should focus on:

- architectural decisions and coupling,
- operational feedback loops,
- failure handling and rollback,
- observability and incident learning,
- deployment and change-management practices,
- tests and scenario coverage,
- optionality, reversibility, and bounded downside.

The skill distinguishes between audit wording and implementation wording:

- Audit mode: review, inspect, assess, or tell me what to improve.
- Implementation mode: make, fix, address, harden, or improve.

In implementation mode, each control the skill adds comes with a challenge test: a test that feeds the known-bad case, fails on the original code, and passes on the patched code, while a known-good case keeps passing.

### Run The Scanner Directly

The scanner can be run as a standalone Python script. Use it as a discovery tool after you have a rough system map, or as a quick source of review leads when you are exploring unfamiliar code.

```bash
python3 skills/fragility-review/scripts/fragility_scan.py .
```

Emit JSON for automation:

```bash
python3 skills/fragility-review/scripts/fragility_scan.py . --json
```

Scan specific paths:

```bash
python3 skills/fragility-review/scripts/fragility_scan.py src tests config
```

Exclude paths:

```bash
python3 skills/fragility-review/scripts/fragility_scan.py . --exclude vendor --exclude build
```

Limit findings per rule:

```bash
python3 skills/fragility-review/scripts/fragility_scan.py . --max-per-pattern 20 --max-file-bytes 2000000
```

List rule metadata, including rule ids, categories, linter overlaps, and exposure dimensions:

```bash
python3 skills/fragility-review/scripts/fragility_scan.py --list-rules
python3 skills/fragility-review/scripts/fragility_scan.py --list-rules --json
```

The generated Markdown catalog is committed at `skills/fragility-review/references/scanner-rules.md`.

### Suppress Reviewed Signals

Use inline suppression only after reviewing the signal and deciding it is harmless in context.

Ignore one pattern:

```python
except ExpectedError:
    pass  # fragility-scan: ignore[silent-exception]
```

Ignore all scanner patterns on a line:

```python
while True:  # fragility-scan: ignore
    poll_once()
```

Use suppressions sparingly. They are intended for explicit tradeoffs, not for hiding uncomfortable feedback.

## Review Method

### What The Review Asks

A fragility review is broader than code linting. It asks where the system gets hurt when reality gets noisy and when the people and agents who change it make mistakes:

- Which critical flows fail badly under load, dependency failure, bad deploys, malformed input, or changing requirements?
- Which decisions are hard to reverse after they meet production data, users, vendors, or infrastructure?
- At each step of a critical flow, what can a developer, an operator, or a coding agent get wrong, and what stops it?
- Which of those controls has anything proven, and which are kill switches, restores, and tests that have never been seen to work?
- Which failures create durable learning through tests, metrics, runbooks, ownership, or safer defaults?
- Where is an abstraction, adapter, feature flag, dry-run, or staged rollout worth its carrying cost?

The scanner helps find concrete evidence, but it does not set the agenda. A scanner hit outside a critical path is usually less important than an architectural single point of failure, an irreversible migration path, an unowned alert, or a release process with no safe rollback.

Every control the review relies on is rated from C0 (nothing) to C5 (the mistake cannot be expressed), credited only when a challenge test or drill proves it, and compared with the strength the harm requires: irreversible harm needs C4 or better for every actor who can reach it. Tests are rated the same way, T0 to T5, and a test counts only once it has been seen failing on the fault it guards. The scales, the control audit, and the rules for code that coding agents change are in `skills/fragility-review/references/review-playbook.md`; the ideas behind them are in `skills/fragility-review/references/lenses.md`.

### Workflow

A review starts with a short summary and a system map:

- System shape: what the system does, the main runtime pieces, and the critical user or business flows.
- Stressors and actors: dependency failure, load spikes, bad input, schema change, vendor drift, incidents, cost pressure, or requirement churn, and the people and coding agents who change and operate the code.
- Hypothesis: where a stressor or a mistake causes harm that compounds or cannot be undone.
- Evidence confidence: which claims are direct code/config evidence, which are docs-only, and which remain unknown.

Then inspect the major design areas:

- Architecture and coupling: boundaries, shared state, local failure containment, and replacement cost.
- Data and migrations: irreversible writes, staged migrations, replayability, backups, and invariants.
- Release and deployment: canaries, feature flags, rollback verification, workflow concurrency, artifact pinning, and deploy observability.
- Dependencies and vendors: timeouts, budgets, circuit breakers, cached degradation, contract tests, and vendor-exit options.
- Observability and incident learning: SLOs, dashboards, alerts with owners, runbooks, incident reviews, and regression tests from incidents.
- Testing and safe stress: tests that can fail, fault injection, property tests, mutation tests, load tests, restore drills, and game days.
- Code that people and coding agents change: one name per concept, docs that match the code, invariants enforced by types, schema, or CI, fast local checks, safe defaults, explicit targets for dangerous commands.
- Security and abuse resistance: least privilege, auditability, dependency pinning, policy checks, rate limits, and abuse telemetry.

For at least one high-exposure critical flow, trace:

- trigger and entrypoint,
- state or data mutation,
- dependency calls,
- failure handling,
- the strongest control that stops a mistake at each step (C0 to C5) and whether a test proves it,
- observability and ownership,
- rollback or degradation path,
- missing evidence and the cheapest observation that would close the gap.

The practical flow is:

1. Clarify the system boundary, goals, stressors, and actors.
2. Inspect architecture, deployment paths, persistence, integrations, and feedback loops.
3. Trace a critical flow and rate the control at each step.
4. Identify where the system has hidden downside, tight coupling, delayed feedback, irreversible changes, or unproven controls.
5. Score confirmed risks by blast radius, irreversibility, feedback delay, dependency concentration, and ruin potential, and compare each control's strength with what the harm requires.
6. Look for existing sources of optionality, redundancy, graceful degradation, and rapid learning.
7. Recommend changes in this order: remove, bound the downside, mistake-proof the action, add feedback, add safe stress, keep options open; say what each change buys.
8. Separate quick code-level fixes from larger architectural or operational recommendations.

The scanner can support evidence gathering, but should not replace the broader analysis.

### Design Principles

The skill favors:

- evidence before advice: findings should cite real files and line numbers,
- leads, not verdicts: heuristic matches need code-reading confirmation,
- complementing linters instead of cloning them,
- architecture before scanner output,
- audit before mutation,
- bounded downside through reversible changes, dry-runs, explicit skip reasons, and small patches,
- feedback loops that make scanner failures, skipped files, and capped results visible,
- changes that stop a mistake, shrink the blast radius, make reversal cheaper, detect faster, or turn an incident into a test, rather than durability alone,
- controls over instructions: a check that stops a mistake outranks a document that asks actors to avoid it, and a control counts only when a test proves it,
- tests as controls: a test earns credit only once it has been seen failing on the fault it guards,
- abstraction only when uncertainty is real, the option is plausible, and the carrying cost is justified.

## Scanner Details

### Scanner Output

The Markdown report includes:

- project signals: tests, CI, migration, runbook, incident-artifact, and operational term counts by source type,
- language counts by detected language or file family,
- mention locations for rollback, canary, observability, incident-learning, and fault-experiment terms,
- skipped file samples caused by size, binary content, read errors, explicit excludes, or self-scan rules,
- critical-flow candidates that combine entrypoint, state mutation, dependency, release/ops, feedback, and exposure-overlap evidence,
- exposure review leads that group findings by blast radius, irreversibility, feedback delay, dependency concentration, and ruin potential,
- heuristic findings grouped by fragility category,
- capped finding overflow for additional matches omitted by `--max-per-pattern`,
- next review moves for a human or agent reviewer.

These outputs are inputs to architectural review. They are not a replacement for reading the relevant flow, deploy mechanism, data path, or operational docs.

JSON output includes:

- `root`
- `project_signals`
- `large_files`
- `findings`
- `critical_flow_candidates`
- `exposure_summary`
- `finding_overflow`
- `skipped_files`

Individual findings include `pattern_id`, `language`, `source_kind`, `category`, `concept`, `path`, `line`, `snippet`, `why`, `linter_overlaps`, `exposure_dimensions`, and `scanner_value`.

Critical-flow candidates are the scanner's first bridge back to architectural review. They suggest files that may be worth tracing because they combine flow anchors such as routes, jobs, database writes, dependency calls, deploy workflows, runbooks, incidents, and exposure-overlap findings. The exposure summary then groups scanner leads by exposure dimension, gives representative evidence locations, and names review questions such as whether a destructive path has dry-run, rollback, restore, replay, or audit evidence. Use both to decide where to trace a critical flow next.

### What It Looks For

The scanner currently looks for code and configuration leads in these areas:

- Silent failure and lost learning: bare `except`, swallowed exceptions, empty catches, ignored errors.
- Prediction and timing dependence: fixed sleeps, magic timeout constants, impossible assumptions.
- Cascade and ruin risk: process aborts, unbounded loops and queues, retry paths without backoff, outbound HTTP calls without timeouts, fetch calls without cancellation.
- Irreversibility: destructive database or infrastructure commands, forced confirmation flags, data changes without dry-run or checkpoint evidence.
- Centralized state and tight coupling: global mutable state, singleton access, hard-coded endpoints.
- Weak observability: ad hoc debug prints where structured logging or metrics might be missing.
- Known fragility markers: TODO, FIXME, HACK, workaround, temporary.

Language-specific coverage includes:

- Rust: `unwrap` / `expect`, `unsafe` boundaries, `todo!` / `unimplemented!` / `unreachable!`, debug output macros, `loop {}`, `panic!`, and `std::process::exit`.
- SQL: destructive schema changes, bulk `UPDATE` lines without `WHERE`, destructive statements, and `pg_sleep`.
- TypeScript and JavaScript: explicit `any`, empty catches, uncancelled `fetch`, timers, `console.log`, `process.exit`, and hard-coded endpoints.
- Go: root contexts, untracked goroutines, package-level HTTP helpers without explicit client timeouts, package variables, sleeps, `panic`, `log.Fatal`, and `os.Exit`.
- Java and Kotlin: broad `Exception` / `Throwable` catches, static or companion-object state leads, `Thread.sleep`, and `System.exit`.
- Ruby: bare `rescue`, `rescue nil`, `puts`, sleeps, and process exits.
- Shell: missing strict-mode setup, `curl` / `wget` piped into a shell, sleeps, destructive commands, and forced actions.
- Terraform: open `0.0.0.0/0` CIDR exposure and wildcard IAM actions or resources.
- Kubernetes and GitHub Actions YAML: single replicas, mutable `:latest` images, missing workload resource/probe hints, unpinned actions, and missing workflow concurrency controls.
- Python: bare or silent exceptions, `requests` / `httpx` calls without timeouts, debug prints, process exits, sleeps, and global state.

It also counts operational concepts such as rollback, dry-run, feature flags, canaries, fault injection, observability, SLOs, runbooks, and postmortems. These counts are evidence locations only. They do not prove the capability exists or works.

These signals are prompts for review, not final judgments.

### Relationship To Linters

This scanner is intentionally not a replacement for Ruff, ESLint, Clippy, ShellCheck, Hadolint, Checkov, or other mature language and infrastructure linters. If a mature linter can analyze your code precisely, use that linter.

Linters should own general correctness, syntax, style, type discipline, and language-specific best practices. The fragility scanner should only keep overlapping signals when they support a broader fragility question, such as hidden coupling, irreversible change, missing feedback, poor recovery, unbounded blast radius, or suppressed uncertainty.

For example:

- `bare-except` overlaps Ruff `E722`, but the scanner frames it as lost failure evidence.
- `silent-exception` can overlap Ruff `BLE001`, `S110`, or `S112`, but the scanner asks whether the failure creates learning, ownership, or metrics.
- `python-http-without-timeout` overlaps Ruff `S113`, but the scanner groups it with broader cascade and cancellation risk.
- Python `print()` matches overlap Ruff `T201`, while the same scanner pattern also catches `console.log` and Ruby `puts`.
- Python `global` statements overlap Ruff `PLW0603`, while the scanner also catches selected non-Python global-state patterns.
- Rust `unwrap`, `expect`, `dbg!`, `println!`, and placeholder macros can overlap Clippy, but the scanner asks where panics or ad hoc output create fragile operational boundaries.
- TypeScript `any` overlaps TypeScript ESLint, but the scanner frames it as contract-feedback loss.
- Ruby bare `rescue` can overlap RuboCop, but the scanner asks whether the rescue path preserves failure evidence.
- Shell, Terraform, Kubernetes, and GitHub Actions leads are intentionally shallow. Use ShellCheck, actionlint, tfsec, Checkov, kube-linter, or platform policy tools for precise validation.

When a finding overlaps known linter behavior, JSON and Markdown output include `linter_overlaps`. That metadata is meant to make overlap explicit, not to make the scanner authoritative.

The scanner should not try to become a meta-linter. It should surface review leads that connect concrete code to system adaptation, reversibility, and stress response. Scanner-only leads should usually be treated as prompts for code reading. They become high-priority findings only when confirmed on an important flow or tied to a meaningful blast radius.

## Project Maintenance

### Repository Layout

```text
.
|-- .claude-plugin/
|   |-- marketplace.json
|   `-- plugin.json
|-- README.md
|-- LICENSE
|-- VERSION
|-- skills/
|   `-- fragility-review/
|       |-- SKILL.md
|       |-- agents/openai.yaml
|       |-- examples/scorecard-review.md
|       |-- references/
|       |   |-- lenses.md
|       |   |-- evaluation-scenarios.md
|       |   |-- review-playbook.md
|       |   `-- scanner-rules.md
|       |-- scripts/
|       |   |-- fragility_scan.py
|       |   |-- check_review_evidence.py
|       |   `-- check_test_strength.py
|       `-- templates/review-scorecard.md
|-- docs/
|   `-- mistake-proofing-research.md
|-- evals/
|   |-- agent_traps.json, agent_traps_artifacts.json, agent_traps_scoreboard.json
|   |-- challenges/
|   |-- descriptions/
|   |-- evals.json
|   |-- fixtures/
|   |-- golden/
|   |-- mutants/
|   |-- run_agent_trap_evals.py
|   |-- run_evals.py
|   |-- run_output_evals.py
|   |-- run_trigger_evals.py
|   `-- trigger_queries.json
|-- .github/
|   `-- workflows/
|       `-- test.yml
|-- tools/
|   `-- check_package_contract.py
`-- tests/
```

### Development

Run tests:

```bash
python3 -m unittest discover -s tests
```

Run the scanner against this repository:

```bash
python3 skills/fragility-review/scripts/fragility_scan.py .
```

Run package contract checks:

```bash
python3 tools/check_package_contract.py
```

Run the scanner-and-golden-file fixture checks (no model, runs in CI):

```bash
python3 evals/run_evals.py
```

Regenerate scanner rule documentation after scanner metadata changes:

```bash
python3 skills/fragility-review/scripts/fragility_scan.py --list-rules > skills/fragility-review/references/scanner-rules.md
```

Validate the plugin and marketplace manifests and the skill frontmatter (the installed `claude` CLI):

```bash
claude plugin validate --strict .
```

Release: set the new version in `VERSION`, `.claude-plugin/plugin.json`, and `.claude-plugin/marketplace.json`, update the pinned version in this README, run the contract check, then tag and push `vX.Y.Z`. Installed plugins pick the new version up on `claude plugin update`.

Check Python syntax:

```bash
python3 -m py_compile skills/fragility-review/scripts/*.py tools/*.py tests/*.py evals/*.py evals/challenges/*.py
```

The self-scan intentionally skips `skills/fragility-review/scripts/fragility_scan.py` as `self-scanner` so the scanner's own pattern definitions do not dominate the report.

### Skill Evals

`evals/run_evals.py` and the unit tests run the scanner on fixtures and check hand-written golden reviews. They pass whatever a model does with the skill. Two other runners call `claude -p` and cost money, so CI does not run them. Each run is a fresh session in a temporary copy of the fixtures, using `--setting-sources project` so user skills and memory do not leak in.

Triggering. `evals/trigger_queries.json` holds realistic prompts labeled `should_trigger`, split into `train`, `validation`, and `holdout`. Negatives are near-misses that share keywords with the skill. A query passes when its trigger rate over 3 runs is above 0.5 (should-trigger) or below 0.5 (should-not-trigger).

```bash
python3 evals/run_trigger_evals.py --runs 3                       # train + validation
python3 evals/run_trigger_evals.py --split holdout --runs 3       # run once per description, do not tune on it
python3 evals/run_trigger_evals.py --description-file evals/descriptions/C-goal-led-with-boundary.txt
python3 evals/run_trigger_evals.py --model haiku                  # repeat on each model you target
```

Review quality. `evals/evals.json` holds cases with code `checks` and model-graded `assertions`. `run_output_evals.py` runs each case with and without the skill and flags every item as `NO-OP` (passes in both, so it tests nothing), `BROKEN?` (fails in both), `VALUE`, or `WORSE`. A grader that cannot decide returns `UNKNOWN`, which never counts as a pass.

```bash
python3 evals/run_output_evals.py --runs 3
python3 evals/run_output_evals.py --configs with_skill --runs 3 --skill-dir /path/to/candidate
```

Hardening. Implementation cases in `evals/evals.json` can list `challenge:<name>` checks. A challenge (`evals/challenges/`) runs the fixture's real entrypoint with stubbed services against a known-bad case and checks that the mistake no longer gets through; each also keeps a known-good case passing, so a patch that stops all work does not pass. The unit tests in `tests/test_*challenges.py` prove that each challenge rejects the unfixed fixture and accepts a reference fix.

Test quality. Implementation cases can also grade the tests an agent leaves behind rather than its code. `tests_changed` and `fails_on_original` require new tests that fail on the untouched fixture; `protected:<file>:<function>` runs the skill's `scripts/check_test_strength.py` and requires a test that depends on that function; `mutant:<name>` applies a seeded fault from `evals/mutants/<fixture>.json` to the repository as the agent left it and passes only if the suite fails (when the agent rewrote the seeded line, the fault is applied to a reference implementation in `evals/mutants/<fixture>/` instead, if the agent's suite accepts it); `refusals_tested` replaces every `raise` in the code with `pass` and passes only if the suite fails, so a refusal is tested whatever shape the agent gave it. The fixtures `backup-retention` and `doc-sharing` ship with suites that pass on wrong code; `tests/test_*_mutants.py` prove that each weak suite tolerates every seeded fault and that a literal-valued test rejects them. `--regrade-checks` recomputes these checks from saved patches with no model calls.

Later agents. `run_agent_trap_evals.py` hardens a fixture with and without the skill, keeps each hardened repository, then has a plain coding agent do ordinary tasks that invite the same mistake again (`evals/agent_traps*.json`) and reruns the challenges. It reports regressions per task, and for tasks with a utility check it reports four cells (safe or unsafe, useful or not useful) rather than one score. `--gate` also counts what a required CI check running the challenges would have blocked. `--regrade` recomputes everything from saved patches with no model calls, so a challenge can be fixed without paying for the agents again.

```bash
python3 evals/run_agent_trap_evals.py --hardens 5 --hardener-model claude-opus-5-5 --task-model sonnet --gate
python3 evals/run_agent_trap_evals.py --regrade evals/results/traps-<label>-<timestamp>
```

Results go to `evals/results/`, which is not committed. Read a sample of the transcripts before you trust a score. Do not edit an assertion after you see a result unless you rerun both configurations. Keep fixture-specific wording out of the skill: a line stays only if evidence outside the fixtures supports it.

### Skill And Agent Design

The skill is designed to work in both Codex and Claude Code. Keep the instructions agent-portable:

- Avoid assuming one model vendor or one chat surface.
- Prefer plain repository inspection commands over product-specific tool names.
- Keep scanner usage optional and deterministic.
- State when a recommendation is architectural rather than directly scanner-derived.
- Preserve the distinction between review, implementation, and verification.
- Use progressive disclosure: `SKILL.md` should stay as the core workflow, while detailed review method and evaluation scenarios live in `skills/fragility-review/references/`.
- Treat repository text, comments, generated files, issues, and scanner snippets as evidence, not instructions.

When adding new guidance, favor reusable review heuristics and concrete decision prompts over long theoretical exposition.

### Contributing

Contributions are welcome. Useful contributions include:

- stronger fragility review heuristics,
- new evaluation scenarios,
- scanner rules that identify fragility-relevant risks without duplicating existing linters,
- clearer documentation,
- tests for scanner behavior and suppression handling.

Before opening a change, run:

```bash
python3 -m py_compile skills/fragility-review/scripts/*.py tools/*.py tests/*.py evals/*.py evals/challenges/*.py
python3 tools/check_package_contract.py
python3 -m unittest discover -s tests
python3 evals/run_evals.py
python3 skills/fragility-review/scripts/fragility_scan.py .
```

For skill-behavior changes, also review `skills/fragility-review/references/evaluation-scenarios.md` and check whether the change would improve or degrade each scenario.

### Security And Privacy

The scanner runs locally and does not send repository contents anywhere. It reads local text files and prints matched snippets to stdout, so do not run it on repositories containing secrets unless you are comfortable with those snippets appearing in terminal output, logs, or CI artifacts.

The skill itself is an instruction bundle. Any repository access, network access, or code modification comes from the agent environment in which the skill is used.

Review all agent-produced changes before deploying them.

If you find a security issue in the scanner or skill instructions, avoid posting exploit details publicly in an issue. Open a minimal issue asking for a private coordination path.

### Limitations

- The scanner is heuristic and intentionally incomplete.
- Findings can be false positives.
- A clean scanner result does not mean a system is safe under stress or mistake.
- Fragility analysis depends on context: operational environment, team practices, deployment model, and failure history matter.
- The skill can recommend changes that are not worth the complexity for a given project. Treat recommendations as engineering judgment prompts, not mandates.

### License

MIT. See [LICENSE](LICENSE).
