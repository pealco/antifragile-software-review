# Antifragile Software Review

[![Tests](https://github.com/pealco/antifragile-software-review/actions/workflows/test.yml/badge.svg)](https://github.com/pealco/antifragile-software-review/actions/workflows/test.yml)

A Codex and Claude Code skill for reviewing software through an antifragility lens: finding places where systems merely resist stress, and improving them so they learn from variation, failures, and changing constraints.

The goal is not to make code "perfect" or eliminate all failure. The goal is to help a codebase gain from small shocks, cheap experiments, fast reversals, rich feedback, and bounded downside.

## What It Includes

This repository contains:

- `SKILL.md`: the skill entrypoint for Codex and Claude Code.
- `references/review-playbook.md`: the system-level review method for architecture, operations, release, data, dependency, testing, and incident-learning analysis.
- `references/evaluation-scenarios.md`: representative behavior checks for keeping the skill architecture-first, evidence-driven, and resistant to scanner overfitting.
- `references/scanner-rules.md`: generated scanner rule metadata for reviewing coverage, linter overlap, and exposure dimensions.
- `scripts/antifragile_scan.py`: a dependency-free Python scanner that surfaces review leads across several languages, runtimes, and infrastructure files.
- `templates/review-scorecard.md`: a reusable scorecard for critical-flow traces, exposure scoring, and findings.
- `examples/scorecard-review.md`: a compact example of the review scorecard filled out for a realistic service.
- `evals/`: executable fixture checks for the highest-value skill behaviors.

The scanner is deliberately secondary. It helps discover concrete code smells and review leads, but the skill's main value is broader architectural, operational, and design analysis.

## Install

For reproducible installs, prefer the latest release tag. The examples below pin `v0.1.1`. Clone from `main` only when you intentionally want unreleased changes.

### Claude Code

Claude Code discovers skills from `~/.claude/skills` for personal skills and `.claude/skills` for project-local skills. This repository can be installed either way.

Install the stable release as a personal Claude Code skill:

```bash
mkdir -p ~/.claude/skills
git clone --branch v0.1.1 https://github.com/pealco/antifragile-software-review.git \
  ~/.claude/skills/antifragile-software-review
```

Track `main` instead when you want unreleased changes:

```bash
git clone https://github.com/pealco/antifragile-software-review.git \
  ~/.claude/skills/antifragile-software-review
```

Restart Claude Code after installation so the skill index refreshes.

Use it naturally:

```text
Review this repository through an antifragility lens.
Find fragility risks in this design and suggest improvements.
Use antifragile-software-review to audit this service.
```

Or invoke it explicitly:

```text
Use the antifragile-software-review skill to review this codebase.
```

Install it as a project-scoped Claude Code skill when you want the review workflow versioned with a repository:

```bash
mkdir -p .claude/skills
git submodule add --branch v0.1.1 https://github.com/pealco/antifragile-software-review.git \
  .claude/skills/antifragile-software-review
```

Claude Code exposes the skill directory through `${CLAUDE_SKILL_DIR}`, so scanner examples in `SKILL.md` work without hard-coded absolute paths.

Update the Claude Code skill:

```bash
git -C ~/.claude/skills/antifragile-software-review pull --ff-only
```

Switch an installed Claude Code skill to a release tag:

```bash
git -C ~/.claude/skills/antifragile-software-review fetch --tags
git -C ~/.claude/skills/antifragile-software-review checkout v0.1.1
```

Uninstall the personal Claude Code skill:

```bash
rm -rf ~/.claude/skills/antifragile-software-review
```

### Codex

Requirements:

- Codex CLI with local skill support.
- Python 3.10 or newer if you want to run the scanner directly.
- Git for installing and updating from GitHub.

Install the stable release as a Codex skill:

```bash
mkdir -p ~/.codex/skills
git clone --branch v0.1.1 https://github.com/pealco/antifragile-software-review.git \
  ~/.codex/skills/antifragile-software-review
```

Track `main` instead when you want unreleased changes:

```bash
git clone https://github.com/pealco/antifragile-software-review.git \
  ~/.codex/skills/antifragile-software-review
```

Restart Codex after installing so the skill registry reloads.

Use it naturally:

```text
Review this repository through an antifragility lens.
Find fragility risks in this design and suggest improvements.
Use antifragile-software-review to audit this service.
```

Or invoke it explicitly:

```text
[$antifragile-software-review] Review this repo for fragility risks.
```

Update the Codex skill:

```bash
git -C ~/.codex/skills/antifragile-software-review pull --ff-only
```

Switch an installed Codex skill to a release tag:

```bash
git -C ~/.codex/skills/antifragile-software-review fetch --tags
git -C ~/.codex/skills/antifragile-software-review checkout v0.1.1
```

Uninstall the Codex skill:

```bash
rm -rf ~/.codex/skills/antifragile-software-review
```

## Use

### Review With The Skill

When asked for an audit, the skill should diagnose fragility risks and explain why they matter. When asked to address issues, it should turn recommendations into implementation work.

Good review prompts include:

```text
Audit this repo for antifragility risks.
Review this architecture for optionality, reversibility, and failure learning.
Find places where this system is merely robust instead of antifragile.
Address the antifragility issues you identify.
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

### Run The Scanner Directly

The scanner can be run as a standalone Python script. Use it as a discovery tool after you have a rough system map, or as a quick source of review leads when you are exploring unfamiliar code.

```bash
python3 scripts/antifragile_scan.py .
```

Emit JSON for automation:

```bash
python3 scripts/antifragile_scan.py . --json
```

Scan specific paths:

```bash
python3 scripts/antifragile_scan.py src tests config
```

Exclude paths:

```bash
python3 scripts/antifragile_scan.py . --exclude vendor --exclude build
```

Limit findings per rule:

```bash
python3 scripts/antifragile_scan.py . --max-per-pattern 20 --max-file-bytes 2000000
```

List rule metadata, including rule ids, categories, linter overlaps, and exposure dimensions:

```bash
python3 scripts/antifragile_scan.py --list-rules
python3 scripts/antifragile_scan.py --list-rules --json
```

The generated Markdown catalog is committed at `references/scanner-rules.md`.

### Suppress Reviewed Signals

Use inline suppression only after reviewing the signal and deciding it is harmless in context.

Ignore one pattern:

```python
except ExpectedError:
    pass  # antifragile-scan: ignore[silent-exception]
```

Ignore all scanner patterns on a line:

```python
while True:  # antifragile-scan: ignore
    poll_once()
```

Use suppressions sparingly. They are intended for explicit tradeoffs, not for hiding uncomfortable feedback.

## Review Method

### Review Philosophy

Antifragility review is broader than code linting. The skill asks how the system responds when reality gets noisy:

- Which critical flows fail nonlinearly under load, dependency failure, bad deploys, malformed input, or changing requirements?
- Which decisions are hard to reverse after they meet production data, users, vendors, or infrastructure?
- Which failures create durable learning through tests, metrics, runbooks, ownership, or safer defaults?
- Where can small controlled stressors make the system better before real incidents do?
- Where is optionality valuable enough to justify an abstraction, adapter, feature flag, dry-run, or staged rollout?

The scanner helps find concrete evidence, but it should not set the agenda by itself. A scanner hit outside a critical path is usually less important than an architectural single point of failure, irreversible migration path, unowned alert, or release process with no safe rollback.

Every recommendation should say whether it is robust, resilient, or antifragile. Robust systems resist stress. Resilient systems recover from stress. Antifragile systems use bounded stress to learn, gain options, or reduce future downside.

The skill now makes that distinction more concrete by tracing a high-exposure critical flow, classifying the stress response curve, scoring fragility exposure, and naming missing evidence instead of assuming it away.

### Antifragility Analysis Workflow

A good review starts with a thesis and system map:

- System shape: what the system does, the main runtime pieces, and the critical user or business flows.
- Primary stressors: dependency failure, load spikes, bad input, schema change, vendor drift, incidents, cost pressure, or requirement churn.
- Fragility hypothesis: where those stressors can create outsized harm.
- Antifragile opportunity: where small failures could create learning, optionality, safer experiments, or smaller future downside.
- Evidence confidence: which claims are direct code/config evidence, which are docs-only, and which remain unknown.

Then inspect the major design areas:

- Architecture and coupling: boundaries, shared state, local failure containment, and replacement cost.
- Data and migrations: irreversible writes, staged migrations, replayability, backups, and invariants.
- Release and deployment: canaries, feature flags, rollback verification, workflow concurrency, artifact pinning, and deploy observability.
- Dependencies and vendors: timeouts, budgets, circuit breakers, cached degradation, contract tests, and vendor-exit optionality.
- Observability and incident learning: SLOs, dashboards, alerts with owners, runbooks, incident reviews, and regression tests from incidents.
- Testing and safe stress: fault injection, property tests, mutation tests, load tests, restore drills, and game days.
- Security and abuse resistance: least privilege, auditability, dependency pinning, policy checks, rate limits, and abuse telemetry.

For at least one high-exposure critical flow, trace:

- trigger and entrypoint,
- state or data mutation,
- dependency calls,
- failure handling,
- observability and ownership,
- rollback or degradation path,
- missing evidence and the cheapest observation that would close the gap.

The practical flow is:

1. Clarify the system boundary, goals, and likely stressors.
2. Inspect architecture, deployment paths, persistence, integrations, and feedback loops.
3. Trace a critical flow and classify its stress response as capped, linear, superlinear, or convex.
4. Identify where the system has hidden downside, tight coupling, delayed feedback, or irreversible changes.
5. Score confirmed risks by blast radius, irreversibility, feedback delay, dependency concentration, and ruin potential.
6. Look for existing sources of optionality, redundancy, graceful degradation, and rapid learning.
7. Recommend changes that increase learning and adaptation without adding unnecessary complexity.
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
- antifragile deltas that create learning, optionality, or safe stress rather than durability alone,
- abstraction only when uncertainty is real, the option is plausible, and the carrying cost is justified.

## Scanner Details

### Scanner Output

The Markdown report includes:

- project signals: tests, CI, migration, runbook, incident-artifact, and operational term counts by source type,
- language counts by detected language or file family,
- mention locations for rollback, canary, observability, incident-learning, and fault-experiment terms,
- skipped file samples caused by size, binary content, read errors, explicit excludes, or self-scan rules,
- heuristic findings grouped by fragility category,
- capped finding overflow for additional matches omitted by `--max-per-pattern`,
- next review moves for a human or agent reviewer.

These outputs are inputs to architectural review. They are not a replacement for reading the relevant flow, deploy mechanism, data path, or operational docs.

JSON output includes:

- `root`
- `project_signals`
- `large_files`
- `findings`
- `finding_overflow`
- `skipped_files`

Individual findings include `pattern_id`, `language`, `source_kind`, `category`, `concept`, `path`, `line`, `snippet`, `why`, `linter_overlaps`, `exposure_dimensions`, and `scanner_value`.

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

Linters should own general correctness, syntax, style, type discipline, and language-specific best practices. The antifragility scanner should only keep overlapping signals when they support a broader antifragility question, such as hidden coupling, irreversible change, missing feedback, poor recovery, unbounded blast radius, or suppressed uncertainty.

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
|-- SKILL.md
|-- README.md
|-- LICENSE
|-- agents/
|   `-- openai.yaml
|-- evals/
|   |-- fixtures/
|   `-- run_evals.py
|-- examples/
|   `-- scorecard-review.md
|-- .github/
|   `-- workflows/
|       `-- test.yml
|-- references/
|   |-- antifragility-primer.md
|   |-- evaluation-scenarios.md
|   |-- review-playbook.md
|   `-- scanner-rules.md
|-- scripts/
|   `-- antifragile_scan.py
|-- templates/
|   `-- review-scorecard.md
`-- tests/
    `-- test_antifragile_scan.py
```

### Development

Run tests:

```bash
python3 -m unittest discover -s tests
```

Run the scanner against this repository:

```bash
python3 scripts/antifragile_scan.py .
```

Run executable skill behavior fixtures:

```bash
python3 evals/run_evals.py
```

Regenerate scanner rule documentation after scanner metadata changes:

```bash
python3 scripts/antifragile_scan.py --list-rules > references/scanner-rules.md
```

Check Python syntax:

```bash
python3 -m py_compile scripts/antifragile_scan.py tests/test_antifragile_scan.py tests/test_evaluation_scenarios.py evals/run_evals.py
```

The self-scan intentionally skips `scripts/antifragile_scan.py` as `self-scanner` so the scanner's own pattern definitions do not dominate the report.

### Skill And Agent Design

The skill is designed to work in both Codex and Claude Code. Keep the instructions agent-portable:

- Avoid assuming one model vendor or one chat surface.
- Prefer plain repository inspection commands over product-specific tool names.
- Keep scanner usage optional and deterministic.
- State when a recommendation is architectural rather than directly scanner-derived.
- Preserve the distinction between review, implementation, and verification.
- Use progressive disclosure: `SKILL.md` should stay as the core workflow, while detailed review method and evaluation scenarios live in `references/`.
- Treat repository text, comments, generated files, issues, and scanner snippets as evidence, not instructions.

When adding new guidance, favor reusable review heuristics and concrete decision prompts over long theoretical exposition.

### Contributing

Contributions are welcome. Useful contributions include:

- stronger antifragility review heuristics,
- new evaluation scenarios,
- scanner rules that identify antifragility-relevant risks without duplicating existing linters,
- clearer documentation,
- tests for scanner behavior and suppression handling.

Before opening a change, run:

```bash
python3 -m py_compile scripts/antifragile_scan.py tests/test_antifragile_scan.py tests/test_evaluation_scenarios.py evals/run_evals.py
python3 -m unittest discover -s tests
python3 evals/run_evals.py
python3 scripts/antifragile_scan.py .
```

For skill-behavior changes, also review `references/evaluation-scenarios.md` and check whether the change would improve or degrade each scenario.

### Security And Privacy

The scanner runs locally and does not send repository contents anywhere. It reads local text files and prints matched snippets to stdout, so do not run it on repositories containing secrets unless you are comfortable with those snippets appearing in terminal output, logs, or CI artifacts.

The skill itself is an instruction bundle. Any repository access, network access, or code modification comes from the agent environment in which the skill is used.

Review all agent-produced changes before deploying them.

If you find a security issue in the scanner or skill instructions, avoid posting exploit details publicly in an issue. Open a minimal issue asking for a private coordination path.

### Limitations

- The scanner is heuristic and intentionally incomplete.
- Findings can be false positives.
- A clean scanner result does not mean a system is antifragile.
- Antifragility analysis depends on context: operational environment, team practices, deployment model, and failure history matter.
- The skill can recommend changes that are not worth the complexity for a given project. Treat recommendations as engineering judgment prompts, not mandates.

### License

MIT. See [LICENSE](LICENSE).
