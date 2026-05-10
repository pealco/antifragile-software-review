# Antifragile Software Review

[![Tests](https://github.com/pealco/antifragile-software-review/actions/workflows/test.yml/badge.svg)](https://github.com/pealco/antifragile-software-review/actions/workflows/test.yml)

A Codex skill and lightweight scanner for reviewing software through Nassim Taleb's antifragility lens.

The goal is not to label a codebase as "good" or "bad." The goal is to find places where volatility, dependency failure, growth, incidents, irreversible actions, or changing requirements can create outsized harm, then turn those stressors into feedback, optionality, safer experiments, or smaller blast radii.

## What It Does

This repository contains two useful pieces:

- `SKILL.md`: a Codex skill for auditing or improving a repository with an antifragility-focused review workflow.
- `scripts/antifragile_scan.py`: a dependency-free Python scanner that surfaces review leads across Python, Rust, SQL, TypeScript, JavaScript, and other text-based project files.

The scanner is intentionally heuristic. It produces leads for a reviewer to confirm in context, not final judgments.

## Install For Codex

Requirements:

- Codex with local skill support.
- Git.
- Python 3.10 or newer if you want to run the scanner directly.

Clone this repository into your Codex skills directory:

```bash
mkdir -p ~/.codex/skills
git clone https://github.com/pealco/antifragile-software-review.git ~/.codex/skills/antifragile-software-review
```

Restart Codex or start a new session so the skill list refreshes.

Then ask Codex to use the skill:

```text
Use $antifragile-software-review to audit this repo.
```

For implementation mode, be explicit:

```text
Use $antifragile-software-review to address the highest-risk reversible issue in this repo.
```

The skill distinguishes between audit wording and implementation wording:

- Audit mode: review, inspect, assess, or tell me what to improve.
- Implementation mode: make, fix, address, harden, or improve.

Update the installed skill:

```bash
git -C ~/.codex/skills/antifragile-software-review pull --ff-only
```

Uninstall it:

```bash
rm -rf ~/.codex/skills/antifragile-software-review
```

## Use The Scanner Directly

You can run the scanner without installing the Codex skill. It only needs Python 3.10 or newer.

```bash
python3 scripts/antifragile_scan.py /path/to/repo
```

Emit JSON for scripts or CI experiments:

```bash
python3 scripts/antifragile_scan.py /path/to/repo --json
```

Exclude noisy paths:

```bash
python3 scripts/antifragile_scan.py /path/to/repo --exclude 'fixtures/**' --exclude 'snapshots/**'
```

Control output volume:

```bash
python3 scripts/antifragile_scan.py /path/to/repo --max-per-pattern 25 --max-file-bytes 2000000
```

## Scanner Output

The Markdown report includes:

- Project signals: tests, CI, migration hints, and operational term counts by source type.
- Language counts: scanned file counts by detected language or file family.
- Mention locations: sample locations for rollback, canary, observability, incident-learning, and fault-experiment terms.
- Skipped file samples: files skipped due to size, binary content, read errors, explicit excludes, or self-scan rules.
- Heuristic findings: pattern matches grouped by fragility category.
- Capped finding overflow: additional matches omitted by `--max-per-pattern`.
- Next review moves: suggested follow-up steps for a human or agent reviewer.

JSON output includes the same core data in machine-readable form:

```json
{
  "project_signals": {},
  "findings": [
    {
      "pattern_id": "python-http-without-timeout",
      "language": "python",
      "linter_overlaps": ["ruff:S113"],
      "scanner_value": "Keeps timeout risk in the antifragility report beside non-Python cancellation and cascade signals."
    }
  ],
  "finding_overflow": {},
  "skipped_files": []
}
```

## What It Looks For

The scanner currently looks for leads in these areas:

- Silent failure and lost learning: bare `except`, swallowed exceptions, empty catches, ignored errors.
- Prediction and timing dependence: fixed sleeps, magic timeout constants, impossible assumptions.
- Cascade and ruin risk: process aborts, unbounded loops, outbound HTTP calls without timeouts, fetch calls without cancellation.
- Irreversibility: destructive database or infrastructure commands, forced confirmation flags.
- Centralized state and tight coupling: global mutable state, singleton access, hard-coded endpoints.
- Weak observability: ad hoc debug prints where structured logging or metrics might be missing.
- Known fragility markers: TODO, FIXME, HACK, workaround, temporary.

Language-specific coverage includes:

- Rust: `unwrap` / `expect`, `unsafe` boundaries, `todo!` / `unimplemented!` / `unreachable!`, debug output macros, `loop {}`, `panic!`, and `std::process::exit`.
- SQL: destructive schema changes, bulk `UPDATE` lines without `WHERE`, destructive statements, and `pg_sleep`.
- TypeScript and JavaScript: explicit `any`, empty catches, uncancelled `fetch`, timers, `console.log`, `process.exit`, and hard-coded endpoints.
- Python: bare or silent exceptions, `requests` / `httpx` calls without timeouts, debug prints, process exits, sleeps, and global state.

It also counts operational concepts such as rollback, dry-run, feature flags, canaries, fault injection, observability, SLOs, runbooks, and postmortems. These counts are evidence locations only. They do not prove the capability exists or works.

## Relationship To Linters

This scanner is not intended to replace language-native linters or become a general-purpose linter. If a mature linter can analyze your code precisely, use that linter.

Some scanner rules intentionally overlap with tools such as [Ruff](https://docs.astral.sh/ruff/), Clippy, ESLint, and TypeScript ESLint because the antifragility report uses the same code shape as a lead for a different question. For example:

- `bare-except` overlaps Ruff [`E722`](https://docs.astral.sh/ruff/rules/bare-except/), but the scanner frames it as lost failure evidence.
- `silent-exception` can overlap Ruff [`BLE001`](https://docs.astral.sh/ruff/rules/blind-except/), [`S110`](https://docs.astral.sh/ruff/rules/try-except-pass/), or [`S112`](https://docs.astral.sh/ruff/rules/try-except-continue/), but the scanner asks whether the failure creates learning, ownership, or metrics.
- `python-http-without-timeout` overlaps Ruff [`S113`](https://docs.astral.sh/ruff/rules/request-without-timeout/), but the scanner groups it with broader cascade and cancellation risk.
- Python `print()` matches overlap Ruff [`T201`](https://docs.astral.sh/ruff/rules/print/), while the same scanner pattern also catches `console.log` and Ruby `puts`.
- Python `global` statements overlap Ruff [`PLW0603`](https://docs.astral.sh/ruff/rules/global-statement/), while the scanner also catches selected non-Python global-state patterns.
- Rust `unwrap`, `expect`, `dbg!`, `println!`, and placeholder macros can overlap Clippy, but the scanner asks where panics or ad hoc output create fragile operational boundaries.
- TypeScript `any` overlaps TypeScript ESLint, but the scanner frames it as contract-feedback loss.

When a finding overlaps known linter behavior, JSON and Markdown output include `linter_overlaps`. That metadata is meant to make overlap explicit, not to make the scanner authoritative. Prefer ecosystem linters for precise linting, and use this scanner for cross-language leads, operational signals, and antifragility review prompts.

## Suppress Reviewed Signals

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

## Repository Layout

```text
.
|-- SKILL.md                         # Codex skill instructions
|-- agents/openai.yaml               # Codex app metadata and default prompt
|-- references/antifragility-primer.md
|-- scripts/antifragile_scan.py      # Standalone scanner
|-- tests/test_antifragile_scan.py   # Scanner regression tests
`-- .github/workflows/test.yml       # CI
```

## Development

Run the test suite:

```bash
python3 -m unittest discover -s tests
```

Check syntax:

```bash
python3 -m py_compile scripts/antifragile_scan.py
```

Run a self-scan:

```bash
python3 scripts/antifragile_scan.py .
```

The self-scan intentionally skips `scripts/antifragile_scan.py` as `self-scanner` so the scanner's own pattern definitions do not dominate the report.

## Design Principles

- Evidence before advice: findings should cite real files and line numbers.
- Leads, not verdicts: heuristic matches need code-reading confirmation.
- Complement linters, do not clone them: overlaps should be explicit and justified by scanner value.
- Audit before mutation: review-style prompts should not edit repositories.
- Bounded downside: prefer reversible changes, dry-runs, explicit skip reasons, and small patches.
- Feedback loops: scanner failures, skipped files, and capped results should be visible.
- Antifragile delta: distinguish durability from changes that create learning, optionality, or safe stress.

## Contributing

Contributions are welcome. Good pull requests usually include:

- A focused scanner rule or skill behavior improvement.
- A regression test that fails without the change.
- Clear wording that avoids presenting heuristic output as proof.
- Updated README or skill docs when user-facing behavior changes.

Before opening a pull request, run:

```bash
python3 -m py_compile scripts/antifragile_scan.py
python3 -m unittest discover -s tests
python3 scripts/antifragile_scan.py .
```

## Security And Privacy

The scanner reads local text files and prints matched snippets to stdout. Do not run it on repositories containing secrets unless you are comfortable with those snippets appearing in terminal output, logs, or CI artifacts.

If you find a security issue in the scanner or skill instructions, please avoid posting exploit details publicly in an issue. Open a minimal issue asking for a private coordination path.

## Limitations

- This is not a static analyzer with complete language parsing.
- Regex rules can miss multiline or dynamically generated behavior.
- Operational term counts show mentions, not working rollback, canary, observability, or incident-learning systems.
- The scanner skips large, binary, unreadable, and explicitly excluded files, and reports those skips as coverage signals.

## License

No license file is included yet. Until a license is added, all rights are reserved by default. Add a `LICENSE` file before treating this repository as open source for reuse.
