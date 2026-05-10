#!/usr/bin/env python3
"""Heuristic scanner for antifragile software review leads."""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".cache",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "bower_components",
    "vendor",
    "dist",
    "build",
    "coverage",
    "target",
    ".next",
    ".nuxt",
    "Pods",
    "DerivedData",
}

TEXT_SUFFIXES = {
    ".bat",
    ".c",
    ".cc",
    ".cfg",
    ".conf",
    ".cpp",
    ".cs",
    ".css",
    ".go",
    ".gradle",
    ".h",
    ".hpp",
    ".html",
    ".java",
    ".js",
    ".json",
    ".jsx",
    ".kt",
    ".kts",
    ".lua",
    ".md",
    ".php",
    ".pl",
    ".properties",
    ".py",
    ".rake",
    ".rb",
    ".rs",
    ".scala",
    ".sh",
    ".sql",
    ".swift",
    ".tf",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}

TEXT_FILENAMES = {
    ".dockerignore",
    ".env.example",
    ".gitlab-ci.yml",
    "Dockerfile",
    "Makefile",
    "Rakefile",
}

CONFIG_FILENAMES = {
    ".dockerignore",
    ".env.example",
    ".gitlab-ci.yml",
    "Dockerfile",
    "Makefile",
    "Rakefile",
    "package.json",
    "pyproject.toml",
    "requirements.txt",
}

CONFIG_SUFFIXES = {".cfg", ".conf", ".gradle", ".json", ".properties", ".tf", ".toml", ".yaml", ".yml"}
DOC_SUFFIXES = {".adoc", ".md", ".rst", ".txt"}
DOC_DIR_NAMES = {"doc", "docs", "reference", "references", "runbook", "runbooks"}
TEST_DIR_NAMES = {"__tests__", "spec", "test", "tests"}

INLINE_IGNORE_RE = re.compile(r"antifragile-scan:\s*ignore(?:\[([^\]]+)\])?", re.IGNORECASE)
SOURCE_KINDS = ("code", "config", "docs", "tests")


@dataclass(frozen=True)
class Pattern:
    id: str
    category: str
    concept: str
    regex: str
    why: str
    source_kinds: tuple[str, ...] = ("code", "config")


@dataclass
class Finding:
    path: str
    line: int
    source_kind: str
    pattern_id: str
    category: str
    concept: str
    why: str
    snippet: str


PATTERNS = [
    Pattern(
        "bare-except",
        "Silent failure and lost learning",
        "skin in the game / feedback",
        r"^\s*except\s*:\s*(?:#.*)?$",
        "Broad exception handling can erase failure evidence unless it logs, measures, or re-raises nearby.",
    ),
    Pattern(
        "silent-exception",
        "Silent failure and lost learning",
        "skin in the game / feedback",
        r"^\s*except\b.*:\s*(pass|return\s+None|return|continue)\b",
        "Swallowed errors convert stress into ignorance instead of learning.",
    ),
    Pattern(
        "empty-catch",
        "Silent failure and lost learning",
        "skin in the game / feedback",
        r"\bcatch\s*\([^)]*\)\s*\{\s*\}",
        "Empty catch blocks hide faults and prevent incident-derived improvement.",
    ),
    Pattern(
        "ignored-error",
        "Silent failure and lost learning",
        "skin in the game / feedback",
        r"\b(ignore|ignored|swallow|swallowed|suppress|suppressed)\b.*\b(error|exception|failure)\b",
        "Explicitly ignored failures need an owner, metric, or bounded blast radius.",
    ),
    Pattern(
        "fixed-sleep",
        "Prediction and timing dependence",
        "prediction dependence",
        r"\b(time\.)?sleep\s*\(|\bThread\.sleep\s*\(|\bsetTimeout\s*\(|\bsetInterval\s*\(|\bawait\b.*\bsleep\s*\(",
        "Fixed sleeps often encode timing predictions where event-driven checks or bounded retries are safer.",
    ),
    Pattern(
        "magic-timeout",
        "Prediction and timing dependence",
        "prediction dependence",
        r"\b(timeout|deadline|interval|delay)(_?(ms|millis|seconds|secs|minutes))?\s*[:=]\s*[0-9]{3,}",
        "Magic timeout constants should be tied to SLOs, budgets, or measured behavior.",
    ),
    Pattern(
        "impossible-assumption",
        "Prediction and timing dependence",
        "via negativa",
        r"(should never happen|cannot happen|can't happen|impossible|assume[s]?\s+(that|the|this))",
        "Claims that reality cannot vary are common sources of brittle edge cases.",
    ),
    Pattern(
        "process-abort",
        "Cascade and ruin risk",
        "bounded downside",
        r"\b(sys\.exit|process\.exit|os\.Exit|log\.Fatal|panic!|panic\s*\(|abort\s*\()",
        "Process-level aborts can turn local errors into system-wide outages.",
    ),
    Pattern(
        "unbounded-loop",
        "Cascade and ruin risk",
        "bounded downside",
        r"^\s*(while\s+True|for\s*\(\s*;\s*;\s*\))",
        "Unbounded loops need cancellation, backoff, budgets, or visible liveness signals.",
    ),
    Pattern(
        "destructive-action",
        "Irreversibility",
        "optionality / reversibility",
        r"\b(DROP\s+TABLE|TRUNCATE\s+TABLE|DELETE\s+FROM|rm\s+-rf|kubectl\s+delete|terraform\s+destroy)\b",
        "Destructive actions need dry-runs, rollback plans, backups, approvals, or idempotent recovery.",
    ),
    Pattern(
        "force-flag",
        "Irreversibility",
        "optionality / reversibility",
        r"(--force|--yes|--no-confirm|dry_?run\s*=\s*False)",
        "Forced actions can remove useful friction around irreversible operations.",
    ),
    Pattern(
        "global-state",
        "Centralized state and tight coupling",
        "decentralization",
        r"^\s*(global\s+\w+|public\s+static\s+(?!final)|static\s+mut\s+|lazy_static!|OnceCell)",
        "Shared mutable state can concentrate downside and create hidden temporal coupling.",
    ),
    Pattern(
        "singleton",
        "Centralized state and tight coupling",
        "decentralization",
        r"\b(Singleton|getInstance\s*\(|instance\s*=\s*new\s+\w+)",
        "Singleton-style access can hide central dependency and replacement risk.",
    ),
    Pattern(
        "hardcoded-endpoint",
        "Centralized state and tight coupling",
        "optionality",
        r"https?://(?!localhost|127\.0\.0\.1|0\.0\.0\.0)",
        "Hard-coded endpoints can reduce optionality unless isolated behind config or adapters.",
    ),
    Pattern(
        "debug-print",
        "Weak observability",
        "feedback",
        r"\b(print\s*\(|console\.log\s*\(|puts\s+)",
        "Ad hoc prints may indicate missing structured logs, metrics, or traces.",
    ),
    Pattern(
        "todo-debt",
        "Known fragility markers",
        "via negativa",
        r"\b(TODO|FIXME|HACK|XXX|workaround|temporary)\b",
        "Known debt is often the cheapest place to remove fragility first.",
    ),
]


PRESENCE_TERMS = {
    "rollback": re.compile(r"\b(rollback|roll back|revert)\b", re.IGNORECASE),
    "dry-run": re.compile(r"\b(dry[-_ ]?run|preview mode)\b", re.IGNORECASE),
    "feature-flags": re.compile(r"\b(feature[-_ ]?flag|flipper|launchdarkly|split\.io|kill switch)\b", re.IGNORECASE),
    "canary": re.compile(r"\b(canary|progressive rollout|staged rollout)\b", re.IGNORECASE),
    "chaos": re.compile(r"\b(chaos|fault injection|failure injection|game day|toxiproxy|gremlin)\b", re.IGNORECASE),
    "observability": re.compile(r"\b(opentelemetry|prometheus|metrics|tracing|trace_id|span_id|slo|error budget)\b", re.IGNORECASE),
    "incident-learning": re.compile(r"\b(postmortem|post-mortem|incident review|runbook|playbook)\b", re.IGNORECASE),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", nargs="?", default=".", help="Repository path to scan")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of Markdown")
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Glob path to skip, relative to repo root. Repeat for multiple excludes.",
    )
    parser.add_argument("--max-per-pattern", type=int, default=12, help="Maximum findings per pattern")
    parser.add_argument("--max-file-bytes", type=int, default=1_000_000, help="Skip files larger than this")
    return parser.parse_args()


def is_text_path(path: Path) -> bool:
    return path.name in TEXT_FILENAMES or path.suffix.lower() in TEXT_SUFFIXES


def iter_candidate_files(root: Path, max_file_bytes: int):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(name for name in dirnames if name not in SKIP_DIRS)
        for filename in sorted(filenames):
            path = Path(dirpath) / filename
            if not is_text_path(path):
                continue
            try:
                if path.stat().st_size > max_file_bytes:
                    yield path, "too-large"
                    continue
            except OSError:
                yield path, "stat-error"
                continue
            yield path, None


def read_text(path: Path) -> tuple[str | None, str | None]:
    try:
        data = path.read_bytes()
    except OSError:
        return None, "read-error"
    if b"\0" in data:
        return None, "binary"
    try:
        return data.decode("utf-8"), None
    except UnicodeDecodeError:
        try:
            return data.decode("latin-1"), None
        except UnicodeDecodeError:
            return None, "decode-error"


def rel_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def classify_path(path: Path) -> str:
    parts = {part.lower() for part in path.parts}
    suffix = path.suffix.lower()
    name = path.name
    lower_name = name.lower()

    if parts & TEST_DIR_NAMES or lower_name.startswith("test_") or lower_name.endswith(
        ("_test.py", ".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx", "_test.go")
    ):
        return "tests"
    if suffix in DOC_SUFFIXES or parts & DOC_DIR_NAMES:
        return "docs"
    if suffix in CONFIG_SUFFIXES or name in CONFIG_FILENAMES or ".github" in parts:
        return "config"
    return "code"


def ignore_applies(line: str, pattern_id: str) -> bool:
    match = INLINE_IGNORE_RE.search(line)
    if not match:
        return False
    raw_ids = match.group(1)
    if not raw_ids:
        return True
    ignored_ids = {item.strip() for item in re.split(r"[,\s]+", raw_ids) if item.strip()}
    return pattern_id in ignored_ids


def strip_inline_ignore(line: str) -> str:
    return INLINE_IGNORE_RE.sub("", line)


def skip_reason(root: Path, path: Path, exclude_globs: list[str], scanner_path: Path) -> str | None:
    rel = rel_path(path, root)
    if path.resolve() == scanner_path and root in scanner_path.parents:
        return "self-scanner"
    for pattern in exclude_globs:
        if fnmatch.fnmatch(rel, pattern) or fnmatch.fnmatch(path.name, pattern):
            return f"excluded:{pattern}"
    return None


def find_pattern_matches(
    root: Path,
    path: Path,
    text: str,
    max_per_pattern: int,
    pattern_counts: dict[str, int],
    omitted_counts: dict[str, int],
):
    findings: list[Finding] = []
    compiled = [(pattern, re.compile(pattern.regex, re.IGNORECASE)) for pattern in PATTERNS]
    source_kind = classify_path(path)

    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        search_line = strip_inline_ignore(line)

        for pattern, regex in compiled:
            if source_kind not in pattern.source_kinds:
                continue
            if ignore_applies(line, pattern.id):
                continue
            if pattern.id == "hardcoded-endpoint" and path.suffix.lower() in {".md", ".txt"}:
                continue
            if regex.search(search_line):
                if pattern_counts.get(pattern.id, 0) >= max_per_pattern:
                    omitted_counts[pattern.id] = omitted_counts.get(pattern.id, 0) + 1
                    continue
                pattern_counts[pattern.id] = pattern_counts.get(pattern.id, 0) + 1
                findings.append(
                    Finding(
                        path=rel_path(path, root),
                        line=line_number,
                        source_kind=source_kind,
                        pattern_id=pattern.id,
                        category=pattern.category,
                        concept=pattern.concept,
                        why=pattern.why,
                        snippet=stripped[:220],
                    )
                )

        custom = custom_line_findings(root, path, source_kind, line_number, line)
        for finding in custom:
            if ignore_applies(line, finding.pattern_id):
                continue
            if pattern_counts.get(finding.pattern_id, 0) >= max_per_pattern:
                omitted_counts[finding.pattern_id] = omitted_counts.get(finding.pattern_id, 0) + 1
                continue
            pattern_counts[finding.pattern_id] = pattern_counts.get(finding.pattern_id, 0) + 1
            findings.append(finding)

    return findings


def custom_line_findings(root: Path, path: Path, source_kind: str, line_number: int, line: str) -> list[Finding]:
    findings: list[Finding] = []
    stripped = line.strip()

    if source_kind not in {"code", "config"}:
        return findings

    if re.search(r"\b(requests|httpx)\.(get|post|put|patch|delete)\s*\(", line) and "timeout=" not in line:
        findings.append(
            Finding(
                path=rel_path(path, root),
                line=line_number,
                source_kind=source_kind,
                pattern_id="python-http-without-timeout",
                category="Cascade and ruin risk",
                concept="bounded downside",
                why="Outbound calls without explicit timeouts can turn dependency latency into thread or worker exhaustion.",
                snippet=stripped[:220],
            )
        )

    if re.search(r"\bfetch\s*\(", line) and "signal" not in line and "AbortController" not in line:
        findings.append(
            Finding(
                path=rel_path(path, root),
                line=line_number,
                source_kind=source_kind,
                pattern_id="fetch-without-abort",
                category="Cascade and ruin risk",
                concept="bounded downside",
                why="Fetch calls without cancellation can outlive their usefulness under latency or navigation changes.",
                snippet=stripped[:220],
            )
        )

    return findings


def term_evidence(root: Path, texts: dict[Path, str]) -> tuple[dict[str, int], dict[str, dict[str, int]], dict[str, list[dict[str, object]]]]:
    term_counts = dict.fromkeys(PRESENCE_TERMS, 0)
    term_counts_by_source = {name: dict.fromkeys(SOURCE_KINDS, 0) for name in PRESENCE_TERMS}
    term_locations: dict[str, list[dict[str, object]]] = {name: [] for name in PRESENCE_TERMS}

    for path, text in texts.items():
        source_kind = classify_path(path)
        for line_number, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if not stripped:
                continue
            for name, regex in PRESENCE_TERMS.items():
                matches = list(regex.finditer(line))
                if not matches:
                    continue
                count = len(matches)
                term_counts[name] += count
                term_counts_by_source[name][source_kind] += count
                if len(term_locations[name]) < 8:
                    term_locations[name].append(
                        {
                            "path": rel_path(path, root),
                            "line": line_number,
                            "source_kind": source_kind,
                            "snippet": stripped[:180],
                        }
                    )

    return term_counts, term_counts_by_source, term_locations


def detect_project_signals(root: Path, files: list[Path], texts: dict[Path, str]) -> dict[str, object]:
    rels = [rel_path(path, root).lower() for path in files]
    joined_paths = "\n".join(rels)

    test_files = [
        rel
        for rel in rels
        if "/test/" in f"/{rel}/"
        or "/tests/" in f"/{rel}/"
        or "/spec/" in f"/{rel}/"
        or "/__tests__/" in f"/{rel}/"
        or Path(rel).name.startswith("test_")
        or Path(rel).name.endswith(("_test.py", ".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx", "_test.go"))
    ]

    ci_files = [
        rel
        for rel in rels
        if rel.startswith(".github/workflows/")
        or rel in {".gitlab-ci.yml", "circle.yml", ".circleci/config.yml", "azure-pipelines.yml"}
    ]

    migration_files = [rel for rel in rels if "migration" in rel or "/migrate/" in rel or "/migrations/" in rel]
    term_counts, term_counts_by_source, term_locations = term_evidence(root, texts)

    return {
        "files_scanned": len(files),
        "tests_present": bool(test_files),
        "test_file_count": len(test_files),
        "ci_present": bool(ci_files),
        "ci_files": ci_files[:10],
        "migration_file_count": len(migration_files),
        "term_counts": term_counts,
        "term_counts_by_source": term_counts_by_source,
        "term_locations": term_locations,
        "path_hints": {
            "docs": "docs/" in joined_paths or "/docs/" in joined_paths,
            "infrastructure": any(part in joined_paths for part in ["terraform", ".tf", "helm", "k8s", "kubernetes"]),
        },
    }


def large_file_signals(root: Path, texts: dict[Path, str]) -> list[dict[str, object]]:
    signals = []
    for path, text in texts.items():
        line_count = text.count("\n") + 1
        if line_count >= 800:
            signals.append({"path": rel_path(path, root), "lines": line_count})
    return sorted(signals, key=lambda item: item["lines"], reverse=True)[:20]


def combined_term_counts(signals: dict[str, object], *names: str) -> tuple[int, dict[str, int]]:
    term_counts = signals["term_counts"]
    term_counts_by_source = signals["term_counts_by_source"]
    total = sum(term_counts[name] for name in names)
    by_source = {source_kind: 0 for source_kind in SOURCE_KINDS}
    for name in names:
        for source_kind in SOURCE_KINDS:
            by_source[source_kind] += term_counts_by_source[name][source_kind]
    return total, by_source


def format_source_counts(counts: dict[str, int]) -> str:
    return ", ".join(f"{source_kind}: {counts[source_kind]}" for source_kind in SOURCE_KINDS)


def sample_term_locations(signals: dict[str, object], *names: str, max_items: int = 3) -> list[dict[str, object]]:
    locations = []
    seen = set()
    term_locations = signals["term_locations"]
    for name in names:
        for location in term_locations[name]:
            key = (location["path"], location["line"], location["source_kind"])
            if key in seen:
                continue
            seen.add(key)
            locations.append(location)
            if len(locations) >= max_items:
                return locations
    return locations


def markdown_report(result: dict[str, object]) -> str:
    findings = [Finding(**item) for item in result["findings"]]
    grouped: dict[str, list[Finding]] = {}
    for finding in findings:
        grouped.setdefault(finding.category, []).append(finding)

    lines = [
        "# Antifragile Codebase Scan",
        "",
        f"Scanned {result['project_signals']['files_scanned']} text files under `{result['root']}`.",
        "",
        "Treat these as review leads, not final findings. Confirm each important signal in context.",
        "",
        "## Project Signals",
        "",
    ]

    signals = result["project_signals"]
    rollback_total, rollback_by_source = combined_term_counts(signals, "rollback", "dry-run")
    rollout_total, rollout_by_source = combined_term_counts(signals, "feature-flags", "canary")
    chaos_total, chaos_by_source = combined_term_counts(signals, "chaos")
    observability_total, observability_by_source = combined_term_counts(signals, "observability")
    incident_total, incident_by_source = combined_term_counts(signals, "incident-learning")
    lines.extend(
        [
            f"- Tests present: {'yes' if signals['tests_present'] else 'not detected'} ({signals['test_file_count']} files)",
            f"- CI present: {'yes' if signals['ci_present'] else 'not detected'}",
            f"- Migration files detected: {signals['migration_file_count']}",
            f"- Rollback/dry-run mentions: {rollback_total} ({format_source_counts(rollback_by_source)})",
            f"- Feature flag/canary mentions: {rollout_total} ({format_source_counts(rollout_by_source)})",
            f"- Chaos/fault experiment mentions: {chaos_total} ({format_source_counts(chaos_by_source)})",
            f"- Observability/SLO mentions: {observability_total} ({format_source_counts(observability_by_source)})",
            f"- Runbook/postmortem mentions: {incident_total} ({format_source_counts(incident_by_source)})",
            f"- Skipped files: {len(result['skipped_files'])}",
            "",
            "Operational mentions are evidence locations, not proof that a capability works.",
            "",
        ]
    )

    location_groups = [
        ("Rollback/dry-run", ("rollback", "dry-run")),
        ("Feature flag/canary", ("feature-flags", "canary")),
        ("Chaos/fault experiment", ("chaos",)),
        ("Observability/SLO", ("observability",)),
        ("Runbook/postmortem", ("incident-learning",)),
    ]
    sampled = [(label, sample_term_locations(signals, *names)) for label, names in location_groups]
    sampled = [(label, locations) for label, locations in sampled if locations]
    skipped_files = result["skipped_files"]
    if skipped_files:
        lines.extend(["### Skipped File Samples", ""])
        for item in skipped_files[:8]:
            lines.append(f"- `{item['path']}`: {item['reason']}")
        if len(skipped_files) > 8:
            lines.append(f"- ... {len(skipped_files) - 8} more skipped files")
        lines.append("")

    if sampled:
        lines.extend(["### Mention Location Samples", ""])
        for label, locations in sampled:
            rendered = ", ".join(
                f"`{location['path']}:{location['line']}` [{location['source_kind']}]" for location in locations
            )
            lines.append(f"- {label}: {rendered}")
        lines.append("")

    large_files = result["large_files"]
    if large_files:
        lines.extend(["## Large File Signals", ""])
        for item in large_files:
            lines.append(f"- `{item['path']}`: {item['lines']} lines")
        lines.append("")

    if grouped:
        lines.extend(["## Heuristic Findings", ""])
        for category, items in grouped.items():
            lines.extend([f"### {category}", ""])
            for item in items:
                lines.append(
                    f"- `{item.path}:{item.line}` [{item.source_kind}; {item.pattern_id}; {item.concept}] {item.snippet}"
                )
                lines.append(f"  - Why it matters: {item.why}")
            lines.append("")
    else:
        lines.extend(["## Heuristic Findings", "", "No pattern findings detected.", ""])

    finding_overflow = result["finding_overflow"]
    if finding_overflow:
        lines.extend(["## Capped Finding Overflow", ""])
        for pattern_id, count in sorted(finding_overflow.items()):
            lines.append(f"- `{pattern_id}`: {count} additional matches omitted by `--max-per-pattern`")
        lines.append("")

    lines.extend(
        [
            "## Next Review Moves",
            "",
            "- Verify whether the highest-risk signals sit on critical user, data mutation, deployment, or billing paths.",
            "- Convert confirmed findings into via negativa, reversibility, feedback-loop, or safe-stress recommendations.",
            "- Prefer fixes with explicit validation: test, metric, alert, rollback drill, load test, or fault-injection experiment.",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    root = Path(args.repo).expanduser().resolve()
    if not root.exists():
        print(f"error: repo path does not exist: {root}", file=sys.stderr)
        return 2

    files: list[Path] = []
    texts: dict[Path, str] = {}
    findings: list[Finding] = []
    pattern_counts: dict[str, int] = {}
    omitted_counts: dict[str, int] = {}
    skipped_files: list[dict[str, str]] = []
    scanner_path = Path(__file__).resolve()

    for path, candidate_skip_reason in iter_candidate_files(root, args.max_file_bytes):
        reason = skip_reason(root, path, args.exclude, scanner_path)
        if reason is None:
            reason = candidate_skip_reason
        if reason:
            skipped_files.append({"path": rel_path(path, root), "reason": reason})
            continue
        text, read_skip_reason = read_text(path)
        if text is None:
            skipped_files.append({"path": rel_path(path, root), "reason": read_skip_reason or "read-error"})
            continue
        files.append(path)
        texts[path] = text
        findings.extend(find_pattern_matches(root, path, text, args.max_per_pattern, pattern_counts, omitted_counts))

    result = {
        "root": root.as_posix(),
        "project_signals": detect_project_signals(root, files, texts),
        "large_files": large_file_signals(root, texts),
        "findings": [asdict(finding) for finding in findings],
        "finding_overflow": dict(sorted(omitted_counts.items())),
        "skipped_files": skipped_files,
    }

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(markdown_report(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
