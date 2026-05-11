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
    "fixtures",
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
    ".bash",
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
    ".tfvars",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
    ".zsh",
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

CONFIG_SUFFIXES = {".cfg", ".conf", ".gradle", ".json", ".properties", ".tf", ".tfvars", ".toml", ".yaml", ".yml"}
DOC_SUFFIXES = {".adoc", ".md", ".rst", ".txt"}
DOC_DIR_NAMES = {"doc", "docs", "reference", "references", "runbook", "runbooks"}
TEST_DIR_NAMES = {"__tests__", "spec", "test", "tests"}

INLINE_IGNORE_RE = re.compile(r"antifragile-scan:\s*ignore(?:\[([^\]]+)\])?", re.IGNORECASE)
SOURCE_KINDS = ("code", "config", "docs", "tests")
EXPOSURE_BY_CATEGORY = {
    "Silent failure and lost learning": ("feedback_delay",),
    "Prediction and timing dependence": ("feedback_delay", "dependency_concentration"),
    "Cascade and ruin risk": ("blast_radius", "dependency_concentration", "ruin_potential"),
    "Irreversibility": ("irreversibility", "ruin_potential"),
    "Centralized state and tight coupling": ("dependency_concentration", "blast_radius"),
    "Weak observability": ("feedback_delay",),
    "Known fragility markers": ("feedback_delay",),
}
EXPOSURE_REVIEW_QUESTIONS = {
    "blast_radius": "Which critical flows, users, deploys, or data sets share this failure boundary?",
    "dependency_concentration": "Which vendor, queue, region, secret, owner, or module can stall or corrupt the flow?",
    "feedback_delay": "How would an owner notice this failure before users, data drift, or incidents reveal it?",
    "irreversibility": "What dry-run, rollback, restore, replay, or audit evidence proves this can be reversed?",
    "ruin_potential": "What durable data, financial, security, legal, or trust damage could remain after recovery?",
}
EXPOSURE_NEXT_MOVES = {
    "blast_radius": "Trace the highest-value flow touching these locations and name the containment boundary.",
    "dependency_concentration": "Look for timeout budgets, degradation paths, replacement options, and owner-visible contracts.",
    "feedback_delay": "Check whether failures create metrics, alerts, logs with owners, tests, or incident follow-up.",
    "irreversibility": "Inspect migrations, scripts, and side effects for dry-runs, checkpoints, idempotency, and repair paths.",
    "ruin_potential": "Verify backups, restore drills, audit trails, compensation, and blast-radius limits before recommending broader changes.",
}
FLOW_ENTRYPOINT_RE = re.compile(
    r"(@(?:app|router|bp)\.(?:route|get|post|put|patch|delete)\b|"
    r"\b(?:app|router|server)\.(?:get|post|put|patch|delete)\s*\(|"
    r"\bdef\s+(?:main|handler|handle_\w+|\w+_handler)\b|"
    r"\bfunc\s+main\s*\(|"
    r"\bfunction\s+(?:handler|handle\w*)\b|"
    r"\bexports\.handler\b|"
    r"\bclass\s+\w*(?:Controller|Handler|Worker|Job)\b|"
    r"\b(click\.command|argparse|commander|yargs|webhook|consumer|worker|job|cron)\b)",
    re.IGNORECASE,
)
FLOW_DEPENDENCY_RE = re.compile(
    r"\b(requests|httpx|fetch|axios|grpc|subprocess|exec|spawn|boto3|redis|kafka|rabbitmq|queue|stripe|payment|provider)\b|"
    r"\bhttp\.(?:Get|Head|Post|PostForm)\s*\(|"
    r"\bclient\.(?:get|post|send|call)\s*\(|"
    r"https?://",
    re.IGNORECASE,
)
FLOW_RELEASE_OPS_RE = re.compile(
    r"\b(deploy|release|rollback|roll back|revert|canary|workflow_dispatch|environment|approval|migration)\b",
    re.IGNORECASE,
)
FLOW_FEEDBACK_RE = re.compile(
    r"\b(metric|metrics|trace|tracing|span|slo|alert|dashboard|runbook|postmortem|post-mortem|incident)\b",
    re.IGNORECASE,
)
DATA_CHANGE_PATH_RE = re.compile(r"(^|/)(migrations?|backfills?|data[-_]?migrations?|repairs?|scripts?)(/|$)|backfill|migration|repair", re.IGNORECASE)
DATA_CHANGE_ANCHOR_PATH_RE = re.compile(r"(^|/)(migrations?|backfills?|data[-_]?migrations?|repairs?)(/|$)|backfill|migration|repair", re.IGNORECASE)
DATA_MUTATION_RE = re.compile(
    r"\b(ALTER\s+TABLE|DROP\s+(TABLE|COLUMN|DATABASE|SCHEMA|INDEX|TYPE|VIEW)|TRUNCATE\s+TABLE|DELETE\s+FROM|UPDATE\s+\S+\s+SET|INSERT\s+INTO|bulk_update|update_all|delete_all|destroy_all|save!)\b",
    re.IGNORECASE,
)
FLOW_STATE_RE = re.compile(
    DATA_MUTATION_RE.pattern
    + r"|\b(?:db|database|repo|repository|session|client)\.(?:execute|save|insert|update|delete|commit)\b",
    re.IGNORECASE,
)
DATA_DRY_RUN_RE = re.compile(r"\b(dry[-_ ]?run|preview|noop|no-op|plan|--check)\b", re.IGNORECASE)
DATA_CHECKPOINT_RE = re.compile(
    r"\b(checkpoint|resume|resumable|cursor|batch|limit|page_size|chunk|idempotent|upsert|ON\s+CONFLICT)\b",
    re.IGNORECASE,
)
RETRY_RE = re.compile(r"\b(retry|retries|retried|retrying)\b", re.IGNORECASE)
RETRY_BOUND_RE = re.compile(r"\b(backoff|jitter|budget|deadline|max[-_ ]?retries|max[-_ ]?attempts|retry[-_ ]?budget|exponential|sleep|delay|timeout)\b", re.IGNORECASE)

LANGUAGE_BY_SUFFIX = {
    ".c": "c",
    ".bash": "shell",
    ".cc": "cpp",
    ".conf": "config",
    ".cpp": "cpp",
    ".cs": "csharp",
    ".css": "css",
    ".go": "go",
    ".gradle": "gradle",
    ".h": "c",
    ".hpp": "cpp",
    ".html": "html",
    ".java": "java",
    ".js": "javascript",
    ".json": "json",
    ".jsx": "javascript",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".lua": "lua",
    ".md": "markdown",
    ".php": "php",
    ".py": "python",
    ".rb": "ruby",
    ".rs": "rust",
    ".scala": "scala",
    ".sh": "shell",
    ".sql": "sql",
    ".swift": "swift",
    ".tf": "terraform",
    ".tfvars": "terraform",
    ".toml": "toml",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".xml": "xml",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".zsh": "shell",
}

LANGUAGE_BY_FILENAME = {
    ".dockerignore": "dockerignore",
    ".env.example": "dotenv",
    ".gitlab-ci.yml": "yaml",
    "Dockerfile": "dockerfile",
    "Makefile": "make",
    "Rakefile": "ruby",
}


@dataclass(frozen=True)
class Pattern:
    id: str
    category: str
    concept: str
    regex: str
    why: str
    source_kinds: tuple[str, ...] = ("code", "config")
    languages: tuple[str, ...] = ()
    linter_overlaps: tuple[str, ...] = ()
    exposure_dimensions: tuple[str, ...] = ()
    scanner_value: str = "Antifragility review lead; confirm in context before treating it as a finding."


@dataclass
class Finding:
    path: str
    line: int
    source_kind: str
    language: str
    pattern_id: str
    category: str
    concept: str
    why: str
    linter_overlaps: tuple[str, ...]
    exposure_dimensions: tuple[str, ...]
    scanner_value: str
    snippet: str


@dataclass(frozen=True)
class RuleInfo:
    id: str
    category: str
    concept: str
    why: str
    source_kinds: tuple[str, ...]
    languages: tuple[str, ...]
    linter_overlaps: tuple[str, ...]
    exposure_dimensions: tuple[str, ...]
    scanner_value: str


PATTERNS = [
    Pattern(
        "bare-except",
        "Silent failure and lost learning",
        "skin in the game / feedback",
        r"^\s*except\s*:\s*(?:#.*)?$",
        "Broad exception handling can erase failure evidence unless it logs, measures, or re-raises nearby.",
        languages=("python",),
        linter_overlaps=("ruff:E722",),
        scanner_value="Adds antifragility framing around feedback loss; Ruff provides more precise Python linting.",
    ),
    Pattern(
        "silent-exception",
        "Silent failure and lost learning",
        "skin in the game / feedback",
        r"^\s*except\b.*:\s*(pass|return\s+None|return|continue)\b",
        "Swallowed errors convert stress into ignorance instead of learning.",
        languages=("python",),
        scanner_value="Highlights lost learning and missing ownership even when a Python linter also flags the construct.",
    ),
    Pattern(
        "empty-catch",
        "Silent failure and lost learning",
        "skin in the game / feedback",
        r"\bcatch\s*(?:\([^)]*\))?\s*\{\s*\}",
        "Empty catch blocks hide faults and prevent incident-derived improvement.",
        languages=("typescript", "javascript", "java", "csharp"),
        linter_overlaps=("eslint:no-empty",),
        scanner_value="Catches swallowed TypeScript/JavaScript-style exceptions as lost feedback, not syntax style.",
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
        r"\b(time\.)?sleep\s*\(|\bThread\.sleep\s*\(|\bthread::sleep\s*\(|\btokio::time::sleep\s*\(|\bpg_sleep\s*\(|\bsetTimeout\s*\(|\bsetInterval\s*\(|\bawait\b.*\bsleep\s*\(|^\s*sleep\s+[0-9.]",
        "Fixed sleeps often encode timing predictions where event-driven checks or bounded retries are safer.",
        scanner_value="Flags timing predictions across Python, Rust, SQL, TypeScript, JavaScript, Go, JVM, Ruby, and shell code.",
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
        r"\b(sys\.exit|process\.exit|std::process::exit|Deno\.exit|System\.exit|os\.Exit|log\.Fatal|panic!|panic\s*\(|abort\s*\(|exit\s+[0-9])",
        "Process-level aborts can turn local errors into system-wide outages.",
        scanner_value="Surfaces process-level aborts across runtimes so reviewers can bound local failures.",
    ),
    Pattern(
        "unbounded-loop",
        "Cascade and ruin risk",
        "bounded downside",
        r"^\s*(while\s+True|for\s*\(\s*;\s*;\s*\)|loop\s*\{)",
        "Unbounded loops need cancellation, backoff, budgets, or visible liveness signals.",
        scanner_value="Looks for unbounded loop forms across Python, JavaScript, TypeScript, C-style languages, and Rust.",
    ),
    Pattern(
        "unbounded-queue",
        "Cascade and ruin risk",
        "redundancy and slack",
        r"\b(queue\.Queue|asyncio\.Queue|multiprocessing\.Queue)\s*\(\s*\)|\bChannel\.UNLIMITED\b|\bnew\s+ArrayBlockingQueue\s*\(\s*Integer\.MAX_VALUE\s*\)",
        "Unbounded queues can convert traffic spikes into memory pressure, feedback delay, and retry cascades.",
        scanner_value="Feeds exposure scoring for slack and backpressure review; confirm producer and consumer bounds in context.",
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
        scanner_value="Surfaces cross-language concentration risk; Python-only cases may overlap with Ruff.",
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
        scanner_value="Connects ad hoc output to observability gaps across Python, JavaScript, and Ruby.",
    ),
    Pattern(
        "rust-unwrap-expect",
        "Cascade and ruin risk",
        "bounded downside",
        r"\.(unwrap|expect)\s*\(",
        "Rust unwrap/expect can turn recoverable errors into panics unless isolated at an intentional boundary.",
        languages=("rust",),
        scanner_value="Adds Rust failure-boundary context; Clippy is better for precise Rust linting.",
    ),
    Pattern(
        "rust-todo-unimplemented",
        "Known fragility markers",
        "via negativa",
        r"\b(todo!|unimplemented!|unreachable!)\s*\(",
        "Placeholder or unreachable macros need ownership before they become production failure paths.",
        languages=("rust",),
        scanner_value="Treats Rust placeholder and unreachable assumptions as review leads for ownership and blast radius.",
    ),
    Pattern(
        "rust-unsafe",
        "Centralized state and tight coupling",
        "bounded downside",
        r"^\s*unsafe\s*(\{|fn\b|impl\b|trait\b)",
        "Unsafe Rust removes compiler guarantees and needs a small, well-tested, well-owned boundary.",
        languages=("rust",),
        scanner_value="Highlights Rust safety-boundary concentration rather than treating unsafe as automatically wrong.",
    ),
    Pattern(
        "rust-debug-output",
        "Weak observability",
        "feedback",
        r"\b(dbg!|print!|println!|eprintln!)\s*\(",
        "Ad hoc Rust output can hide missing structured logging, metrics, or trace context.",
        languages=("rust",),
        scanner_value="Connects Rust debug output to operational feedback quality.",
    ),
    Pattern(
        "go-context-background",
        "Cascade and ruin risk",
        "bounded downside",
        r"\bcontext\.(Background|TODO)\s*\(",
        "Root contexts can lose cancellation, deadline, and ownership signals unless they are intentionally scoped.",
        languages=("go",),
        scanner_value="Frames Go context roots as cancellation-boundary leads; confirm whether a request or job context should flow through.",
    ),
    Pattern(
        "go-unbounded-goroutine",
        "Cascade and ruin risk",
        "bounded downside",
        r"^\s*go\s+(func\s*\(|\w+\s*\()",
        "Untracked goroutines can outlive their owner unless cancellation, backpressure, and error reporting are explicit.",
        languages=("go",),
        scanner_value="Surfaces Go concurrency ownership risk that needs code-reading confirmation.",
    ),
    Pattern(
        "go-http-without-timeout",
        "Cascade and ruin risk",
        "bounded downside",
        r"\bhttp\.(Get|Head|Post|PostForm)\s*\(",
        "Package-level Go HTTP helpers use the default client, which can wait indefinitely without an explicit timeout.",
        languages=("go",),
        scanner_value="Adds Go dependency-latency risk beside Python and JavaScript outbound-call cancellation leads.",
    ),
    Pattern(
        "go-global-var",
        "Centralized state and tight coupling",
        "decentralization",
        r"^\s*var\s+\w+(?:\s|=|\[)",
        "Package-level mutable variables can concentrate state and make failure order-dependent.",
        languages=("go",),
        scanner_value="Heuristic Go mutable-state lead; confirm scope manually because the scanner is not parsing Go blocks.",
    ),
    Pattern(
        "java-kotlin-broad-catch",
        "Silent failure and lost learning",
        "skin in the game / feedback",
        r"\bcatch\s*\(\s*(?:(?:\w+)\s*:\s*)?(?:[\w.]+\.)?(Exception|Throwable)\b",
        "Broad JVM catches can turn failures into vague recovery paths unless logging, metrics, or rethrow behavior is explicit.",
        languages=("java", "kotlin"),
        scanner_value="Frames Java/Kotlin broad catches as feedback-loss leads rather than style violations.",
    ),
    Pattern(
        "java-kotlin-static-mutable",
        "Centralized state and tight coupling",
        "decentralization",
        r"^\s*(?:public|private|protected)?\s*static\s+(?!final\b)|\bcompanion\s+object\b",
        "Static mutable state and companion objects can concentrate downside and hide replacement boundaries.",
        languages=("java", "kotlin"),
        scanner_value="Surfaces JVM central-state leads; confirm mutability and lifecycle in context.",
    ),
    Pattern(
        "typescript-explicit-any",
        "Prediction and timing dependence",
        "optionality / feedback",
        r"\b(as\s+any|:\s*any\b|<any>)",
        "Explicit any removes type feedback and can let contract drift reach runtime.",
        languages=("typescript",),
        linter_overlaps=("@typescript-eslint:no-explicit-any",),
        scanner_value="Frames TypeScript type erasure as lost feedback and contract optionality.",
    ),
    Pattern(
        "ruby-bare-rescue",
        "Silent failure and lost learning",
        "skin in the game / feedback",
        r"^\s*rescue\s*(?:#.*)?$",
        "Bare rescue hides the failure class and can turn incidents into ambiguous recovery paths.",
        languages=("ruby",),
        linter_overlaps=("rubocop:Style/RescueStandardError",),
        scanner_value="Adds Ruby failure-feedback framing while leaving precise Ruby style enforcement to RuboCop.",
    ),
    Pattern(
        "ruby-rescue-nil",
        "Silent failure and lost learning",
        "skin in the game / feedback",
        r"\brescue\s+nil\b",
        "Rescue-to-nil can erase failure evidence and make downstream behavior depend on absence rather than ownership.",
        languages=("ruby",),
        scanner_value="Highlights Ruby fallback paths that may need logging, metrics, or narrower rescue boundaries.",
    ),
    Pattern(
        "shell-curl-pipe",
        "Irreversibility",
        "optionality / reversibility",
        r"\b(curl|wget)\b.*\|\s*(sh|bash|zsh)\b",
        "Piping downloaded code into a shell removes review, pinning, and rollback opportunities.",
        languages=("shell",),
        scanner_value="Flags shell supply-chain and reversibility risk; dedicated shell/security tools should do deeper validation.",
    ),
    Pattern(
        "terraform-open-cidr",
        "Cascade and ruin risk",
        "bounded downside",
        r"0\.0\.0\.0/0",
        "Open ingress or egress CIDRs can create broad blast radius unless deliberately bounded by other controls.",
        languages=("terraform",),
        scanner_value="Surfaces Terraform exposure leads for reviewer confirmation; infrastructure security scanners should provide precision.",
    ),
    Pattern(
        "terraform-wildcard-iam",
        "Cascade and ruin risk",
        "bounded downside",
        r"\b(Action|Resource)\s*=\s*\"\*\"",
        "Wildcard IAM actions or resources can concentrate privilege and expand blast radius.",
        languages=("terraform",),
        scanner_value="Flags Terraform IAM optionality and downside-concentration leads without replacing policy analyzers.",
    ),
    Pattern(
        "kubernetes-single-replica",
        "Cascade and ruin risk",
        "redundancy and slack",
        r"^\s*replicas\s*:\s*1\s*(?:#.*)?$",
        "Single-replica workloads have little redundancy unless an external recovery path is explicit.",
        languages=("yaml",),
        scanner_value="Treats Kubernetes replica count as an availability lead, not proof of insufficient resilience.",
    ),
    Pattern(
        "kubernetes-latest-image",
        "Prediction and timing dependence",
        "optionality / reversibility",
        r"^\s*image\s*:\s*[^#\s]+:latest\s*(?:#.*)?$",
        "Mutable latest tags make deploys harder to reproduce and roll back.",
        languages=("yaml",),
        scanner_value="Surfaces Kubernetes image reproducibility risk; confirm deployment tooling and registry policy.",
    ),
    Pattern(
        "github-actions-unpinned-action",
        "Prediction and timing dependence",
        "optionality / reversibility",
        r"^\s*-\s*uses\s*:\s*[^@\s#]+@(?![a-f0-9]{40}\b)[^\s#]+",
        "Actions pinned to moving tags can change behavior outside the repository's control.",
        languages=("github-actions",),
        scanner_value="Flags CI supply-chain drift; actionlint and policy checks can provide deeper workflow validation.",
    ),
    Pattern(
        "sql-destructive-schema",
        "Irreversibility",
        "optionality / reversibility",
        r"\b(ALTER\s+TABLE\b.*\bDROP\s+(COLUMN|CONSTRAINT)|DROP\s+(DATABASE|SCHEMA|INDEX|TYPE|VIEW|MATERIALIZED\s+VIEW))\b",
        "Destructive schema changes need rollback, backups, staged deploys, or explicit recovery plans.",
        languages=("sql",),
        scanner_value="Extends irreversible-change review to SQL schema operations beyond DROP TABLE.",
    ),
    Pattern(
        "sql-update-without-where",
        "Irreversibility",
        "optionality / reversibility",
        r"^\s*UPDATE\s+\S+\s+SET\b(?!.*\bWHERE\b)",
        "Bulk updates without an inline WHERE clause can create large irreversible data changes.",
        languages=("sql",),
        scanner_value="Flags data mutation blast radius for reviewer confirmation; multiline SQL needs manual review.",
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
    parser.add_argument("--list-rules", action="store_true", help="List scanner rules and exit")
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


def language_for_path(path: Path) -> str:
    parts = {part.lower() for part in path.parts}
    if path.suffix.lower() in {".yaml", ".yml"} and ".github" in parts and "workflows" in parts:
        return "github-actions"
    if path.name in LANGUAGE_BY_FILENAME:
        return LANGUAGE_BY_FILENAME[path.name]
    return LANGUAGE_BY_SUFFIX.get(path.suffix.lower(), "text")


def first_matching_line(text: str, regex: str) -> tuple[int, str] | None:
    compiled = re.compile(regex, re.IGNORECASE)
    for line_number, line in enumerate(text.splitlines(), start=1):
        if compiled.search(line):
            return line_number, line.strip()[:220]
    return None


def first_nonempty_line(text: str) -> tuple[int, str]:
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped:
            return line_number, stripped[:220]
    return 1, ""


def shell_strict_mode_present(text: str) -> bool:
    has_errexit = False
    has_nounset = False
    has_pipefail = False

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("set "):
            continue
        has_errexit = has_errexit or bool(re.search(r"(^|\s)-[A-Za-z]*e[A-Za-z]*\b|\berrexit\b", stripped))
        has_nounset = has_nounset or bool(re.search(r"(^|\s)-[A-Za-z]*u[A-Za-z]*\b|\bnounset\b", stripped))
        has_pipefail = has_pipefail or "pipefail" in stripped

    return has_errexit and has_nounset and has_pipefail


def file_ignore_applies(text: str, pattern_id: str) -> bool:
    for line in text.splitlines():
        match = INLINE_IGNORE_RE.search(line)
        if not match or not match.group(1):
            continue
        ignored_ids = {item.strip() for item in re.split(r"[,\s]+", match.group(1)) if item.strip()}
        if pattern_id in ignored_ids:
            return True
    return False


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


def linter_overlaps_for_pattern(pattern: Pattern, line: str) -> tuple[str, ...]:
    overlaps = list(pattern.linter_overlaps)

    if pattern.id == "silent-exception":
        if re.search(r"except\s+(BaseException|Exception)\b", line):
            overlaps.append("ruff:BLE001")
        if re.search(r":\s*pass\b", line):
            overlaps.append("ruff:S110")
        if re.search(r":\s*continue\b", line):
            overlaps.append("ruff:S112")

    if pattern.id == "global-state" and re.search(r"^\s*global\s+\w+", line):
        overlaps.append("ruff:PLW0603")

    if pattern.id == "debug-print" and re.search(r"\bprint\s*\(", line):
        overlaps.append("ruff:T201")

    if pattern.id == "rust-unwrap-expect":
        if re.search(r"\.unwrap\s*\(", line):
            overlaps.append("clippy:unwrap_used")
        if re.search(r"\.expect\s*\(", line):
            overlaps.append("clippy:expect_used")

    if pattern.id == "rust-todo-unimplemented":
        if re.search(r"\btodo!\s*\(", line):
            overlaps.append("clippy:todo")
        if re.search(r"\bunimplemented!\s*\(", line):
            overlaps.append("clippy:unimplemented")
        if re.search(r"\bunreachable!\s*\(", line):
            overlaps.append("clippy:unreachable")

    if pattern.id == "rust-debug-output":
        if re.search(r"\bdbg!\s*\(", line):
            overlaps.append("clippy:dbg_macro")
        if re.search(r"\b(print!|println!)\s*\(", line):
            overlaps.append("clippy:print_stdout")
        if re.search(r"\beprintln!\s*\(", line):
            overlaps.append("clippy:print_stderr")

    return tuple(dict.fromkeys(overlaps))


def exposure_dimensions_for(category: str, dimensions: tuple[str, ...] = ()) -> tuple[str, ...]:
    if dimensions:
        return dimensions
    return EXPOSURE_BY_CATEGORY.get(category, ())


CUSTOM_RULES = (
    RuleInfo(
        "shell-missing-strict-mode",
        "Silent failure and lost learning",
        "skin in the game / feedback",
        "Shell scripts without strict error handling can continue after failed commands and lose failure evidence.",
        ("code", "config"),
        ("shell",),
        (),
        exposure_dimensions_for("Silent failure and lost learning"),
        "Checks a shell-script-level failure mode that line linters may not frame as operational feedback loss.",
    ),
    RuleInfo(
        "github-actions-missing-concurrency",
        "Cascade and ruin risk",
        "bounded downside",
        "Workflows without concurrency controls can overlap deploys or repeated expensive jobs under churn.",
        ("config",),
        ("github-actions",),
        (),
        exposure_dimensions_for("Cascade and ruin risk"),
        "Treats workflow concurrency as a blast-radius lead for CI/CD review, not a universal requirement.",
    ),
    RuleInfo(
        "data-change-missing-dry-run",
        "Irreversibility",
        "optionality / reversibility",
        "Data-changing migrations, backfills, and repair scripts need dry-run or preview evidence before touching real state.",
        ("code", "config"),
        (),
        (),
        exposure_dimensions_for("Irreversibility"),
        "Feeds the data-ruin review path by finding irreversible operations that lack cheap preflight feedback.",
    ),
    RuleInfo(
        "data-change-missing-checkpoint",
        "Irreversibility",
        "optionality / reversibility",
        "Data-changing migrations, backfills, and repair scripts need checkpoints, batching, or resumability to bound partial failure.",
        ("code", "config"),
        (),
        (),
        exposure_dimensions_for("Irreversibility"),
        "Feeds exposure scoring for irreversible data work by surfacing missing resumability evidence.",
    ),
    RuleInfo(
        "retry-without-backoff",
        "Cascade and ruin risk",
        "bounded downside / feedback",
        "Retry paths without backoff, jitter, deadlines, or budgets can amplify dependency stress into a retry storm.",
        ("code", "config"),
        (),
        (),
        exposure_dimensions_for("Cascade and ruin risk"),
        "Feeds critical-flow exposure review for superlinear harm under dependency latency or failure.",
    ),
    RuleInfo(
        "kubernetes-missing-resource-limits",
        "Cascade and ruin risk",
        "bounded downside",
        "Kubernetes workloads without resource settings can let one workload consume shared cluster capacity.",
        ("config",),
        ("yaml",),
        (),
        exposure_dimensions_for("Cascade and ruin risk"),
        "Surfaces capacity-blast-radius leads; confirm defaults, LimitRanges, and platform policy in context.",
    ),
    RuleInfo(
        "kubernetes-missing-health-probes",
        "Silent failure and lost learning",
        "feedback",
        "Kubernetes workloads without readiness or liveness probes provide weak feedback to schedulers and deploys.",
        ("config",),
        ("yaml",),
        (),
        exposure_dimensions_for("Silent failure and lost learning"),
        "Surfaces workload feedback-loop gaps; confirm whether probes are injected or managed elsewhere.",
    ),
    RuleInfo(
        "python-http-without-timeout",
        "Cascade and ruin risk",
        "bounded downside",
        "Outbound calls without explicit timeouts can turn dependency latency into thread or worker exhaustion.",
        ("code",),
        ("python",),
        ("ruff:S113",),
        ("blast_radius", "dependency_concentration", "feedback_delay"),
        "Keeps timeout risk in the antifragility report beside non-Python cancellation and cascade signals.",
    ),
    RuleInfo(
        "fetch-without-abort",
        "Cascade and ruin risk",
        "bounded downside",
        "Fetch calls without cancellation can outlive their usefulness under latency or navigation changes.",
        ("code",),
        ("javascript", "typescript"),
        (),
        ("blast_radius", "dependency_concentration", "feedback_delay"),
        "Covers browser and JavaScript cancellation risk outside Ruff's Python-only scope.",
    ),
)


def rule_info_for_pattern(pattern: Pattern) -> RuleInfo:
    return RuleInfo(
        id=pattern.id,
        category=pattern.category,
        concept=pattern.concept,
        why=pattern.why,
        source_kinds=pattern.source_kinds,
        languages=pattern.languages,
        linter_overlaps=pattern.linter_overlaps,
        exposure_dimensions=exposure_dimensions_for(pattern.category, pattern.exposure_dimensions),
        scanner_value=pattern.scanner_value,
    )


def all_rule_info() -> list[RuleInfo]:
    return sorted((rule_info_for_pattern(pattern) for pattern in PATTERNS), key=lambda item: item.id) + sorted(
        CUSTOM_RULES, key=lambda item: item.id
    )


def rule_info_as_dict(rule: RuleInfo) -> dict[str, object]:
    return {
        "id": rule.id,
        "category": rule.category,
        "concept": rule.concept,
        "why": rule.why,
        "source_kinds": list(rule.source_kinds),
        "languages": list(rule.languages),
        "linter_overlaps": list(rule.linter_overlaps),
        "exposure_dimensions": list(rule.exposure_dimensions),
        "scanner_value": rule.scanner_value,
    }


def rules_markdown(rules: list[RuleInfo]) -> str:
    lines = [
        "# Antifragile Scanner Rules",
        "",
        f"{len(rules)} rule(s). Empty language lists mean the rule can apply across supported text languages.",
        "",
    ]
    for rule in rules:
        lines.extend(
            [
                f"## {rule.id}",
                "",
                f"- Category: {rule.category}",
                f"- Concept: {rule.concept}",
                f"- Source kinds: {', '.join(rule.source_kinds)}",
                f"- Languages: {', '.join(rule.languages) if rule.languages else 'any'}",
                f"- Exposure dimensions: {', '.join(rule.exposure_dimensions) if rule.exposure_dimensions else 'none'}",
                f"- Linter overlaps: {', '.join(rule.linter_overlaps) if rule.linter_overlaps else 'none'}",
                f"- Why it matters: {rule.why}",
                f"- Scanner value: {rule.scanner_value}",
                "",
            ]
        )
    return "\n".join(lines).rstrip()


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
    language = language_for_path(path)

    for finding in custom_file_findings(root, path, source_kind, language, text):
        if pattern_counts.get(finding.pattern_id, 0) >= max_per_pattern:
            omitted_counts[finding.pattern_id] = omitted_counts.get(finding.pattern_id, 0) + 1
            continue
        pattern_counts[finding.pattern_id] = pattern_counts.get(finding.pattern_id, 0) + 1
        findings.append(finding)

    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        search_line = strip_inline_ignore(line)

        for pattern, regex in compiled:
            if source_kind not in pattern.source_kinds:
                continue
            if pattern.languages and language not in pattern.languages:
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
                        language=language,
                        pattern_id=pattern.id,
                        category=pattern.category,
                        concept=pattern.concept,
                        why=pattern.why,
                        linter_overlaps=linter_overlaps_for_pattern(pattern, search_line),
                        exposure_dimensions=exposure_dimensions_for(pattern.category, pattern.exposure_dimensions),
                        scanner_value=pattern.scanner_value,
                        snippet=stripped[:220],
                    )
                )

        custom = custom_line_findings(root, path, source_kind, language, line_number, line)
        for finding in custom:
            if ignore_applies(line, finding.pattern_id):
                continue
            if pattern_counts.get(finding.pattern_id, 0) >= max_per_pattern:
                omitted_counts[finding.pattern_id] = omitted_counts.get(finding.pattern_id, 0) + 1
                continue
            pattern_counts[finding.pattern_id] = pattern_counts.get(finding.pattern_id, 0) + 1
            findings.append(finding)

    return findings


def custom_file_findings(
    root: Path,
    path: Path,
    source_kind: str,
    language: str,
    text: str,
) -> list[Finding]:
    findings: list[Finding] = []

    if source_kind not in {"code", "config"}:
        return findings

    def add(
        pattern_id: str,
        category: str,
        concept: str,
        why: str,
        scanner_value: str,
        line_number: int,
        snippet: str,
        exposure_dimensions: tuple[str, ...] = (),
    ) -> None:
        if file_ignore_applies(text, pattern_id):
            return
        findings.append(
            Finding(
                path=rel_path(path, root),
                line=line_number,
                source_kind=source_kind,
                language=language,
                pattern_id=pattern_id,
                category=category,
                concept=concept,
                why=why,
                linter_overlaps=(),
                exposure_dimensions=exposure_dimensions_for(category, exposure_dimensions),
                scanner_value=scanner_value,
                snippet=snippet,
            )
        )

    if language == "shell" and not shell_strict_mode_present(text):
        line_number, snippet = first_nonempty_line(text)
        add(
            "shell-missing-strict-mode",
            "Silent failure and lost learning",
            "skin in the game / feedback",
            "Shell scripts without strict error handling can continue after failed commands and lose failure evidence.",
            "Checks a shell-script-level failure mode that line linters may not frame as operational feedback loss.",
            line_number,
            snippet,
        )

    if language == "github-actions" and not re.search(r"^\s*concurrency\s*:", text, re.IGNORECASE | re.MULTILINE):
        line_number, snippet = first_nonempty_line(text)
        add(
            "github-actions-missing-concurrency",
            "Cascade and ruin risk",
            "bounded downside",
            "Workflows without concurrency controls can overlap deploys or repeated expensive jobs under churn.",
            "Treats workflow concurrency as a blast-radius lead for CI/CD review, not a universal requirement.",
            line_number,
            snippet,
        )

    rel = rel_path(path, root)
    if DATA_CHANGE_PATH_RE.search(rel) and DATA_MUTATION_RE.search(text):
        mutation_match = first_matching_line(text, DATA_MUTATION_RE.pattern) or first_nonempty_line(text)
        line_number, snippet = mutation_match
        if not DATA_DRY_RUN_RE.search(text):
            add(
                "data-change-missing-dry-run",
                "Irreversibility",
                "optionality / reversibility",
                "Data-changing migrations, backfills, and repair scripts need dry-run or preview evidence before touching real state.",
                "Feeds the data-ruin review path by finding irreversible operations that lack cheap preflight feedback.",
                line_number,
                snippet,
            )
        if not DATA_CHECKPOINT_RE.search(text):
            add(
                "data-change-missing-checkpoint",
                "Irreversibility",
                "optionality / reversibility",
                "Data-changing migrations, backfills, and repair scripts need checkpoints, batching, or resumability to bound partial failure.",
                "Feeds exposure scoring for irreversible data work by surfacing missing resumability evidence.",
                line_number,
                snippet,
            )

    retry_match = first_matching_line(text, RETRY_RE.pattern)
    if retry_match and not RETRY_BOUND_RE.search(text):
        line_number, snippet = retry_match
        add(
            "retry-without-backoff",
            "Cascade and ruin risk",
            "bounded downside / feedback",
            "Retry paths without backoff, jitter, deadlines, or budgets can amplify dependency stress into a retry storm.",
            "Feeds critical-flow exposure review for superlinear harm under dependency latency or failure.",
            line_number,
            snippet,
        )

    workload_match = first_matching_line(text, r"^\s*kind\s*:\s*(Deployment|StatefulSet|DaemonSet)\s*$")
    if language == "yaml" and workload_match:
        kind_line, kind_snippet = workload_match
        if not re.search(r"^\s*resources\s*:", text, re.IGNORECASE | re.MULTILINE):
            add(
                "kubernetes-missing-resource-limits",
                "Cascade and ruin risk",
                "bounded downside",
                "Kubernetes workloads without resource settings can let one workload consume shared cluster capacity.",
                "Surfaces capacity-blast-radius leads; confirm defaults, LimitRanges, and platform policy in context.",
                kind_line,
                kind_snippet,
            )
        if not re.search(r"^\s*(readinessProbe|livenessProbe)\s*:", text, re.IGNORECASE | re.MULTILINE):
            add(
                "kubernetes-missing-health-probes",
                "Silent failure and lost learning",
                "feedback",
                "Kubernetes workloads without readiness or liveness probes provide weak feedback to schedulers and deploys.",
                "Surfaces workload feedback-loop gaps; confirm whether probes are injected or managed elsewhere.",
                kind_line,
                kind_snippet,
            )

    return findings


def custom_line_findings(
    root: Path,
    path: Path,
    source_kind: str,
    language: str,
    line_number: int,
    line: str,
) -> list[Finding]:
    findings: list[Finding] = []
    stripped = line.strip()

    if source_kind not in {"code", "config"}:
        return findings

    if (
        language == "python"
        and re.search(r"\b(requests|httpx)\.(get|post|put|patch|delete)\s*\(", line)
        and "timeout=" not in line
    ):
        findings.append(
            Finding(
                path=rel_path(path, root),
                line=line_number,
                source_kind=source_kind,
                language=language,
                pattern_id="python-http-without-timeout",
                category="Cascade and ruin risk",
                concept="bounded downside",
                why="Outbound calls without explicit timeouts can turn dependency latency into thread or worker exhaustion.",
                linter_overlaps=("ruff:S113",),
                exposure_dimensions=exposure_dimensions_for(
                    "Cascade and ruin risk",
                    ("blast_radius", "dependency_concentration", "feedback_delay"),
                ),
                scanner_value="Keeps timeout risk in the antifragility report beside non-Python cancellation and cascade signals.",
                snippet=stripped[:220],
            )
        )

    if language in {"javascript", "typescript"} and re.search(r"\bfetch\s*\(", line) and "signal" not in line and "AbortController" not in line:
        findings.append(
            Finding(
                path=rel_path(path, root),
                line=line_number,
                source_kind=source_kind,
                language=language,
                pattern_id="fetch-without-abort",
                category="Cascade and ruin risk",
                concept="bounded downside",
                why="Fetch calls without cancellation can outlive their usefulness under latency or navigation changes.",
                linter_overlaps=(),
                exposure_dimensions=exposure_dimensions_for(
                    "Cascade and ruin risk",
                    ("blast_radius", "dependency_concentration", "feedback_delay"),
                ),
                scanner_value="Covers browser and JavaScript cancellation risk outside Ruff's Python-only scope.",
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


def language_file_counts(files: list[Path]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for path in files:
        language = language_for_path(path)
        counts[language] = counts.get(language, 0) + 1
    return dict(sorted(counts.items()))


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
    incident_files = [
        rel
        for rel in rels
        if "incident" in rel or "postmortem" in rel or "post-mortem" in rel
    ]
    runbook_files = [rel for rel in rels if "runbook" in rel]
    term_counts, term_counts_by_source, term_locations = term_evidence(root, texts)

    return {
        "files_scanned": len(files),
        "tests_present": bool(test_files),
        "test_file_count": len(test_files),
        "ci_present": bool(ci_files),
        "ci_files": ci_files[:10],
        "language_file_counts": language_file_counts(files),
        "migration_file_count": len(migration_files),
        "incident_file_count": len(incident_files),
        "incident_files": incident_files[:10],
        "runbook_file_count": len(runbook_files),
        "runbook_files": runbook_files[:10],
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


def format_language_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "none detected"
    return ", ".join(f"{language}: {count}" for language, count in sorted(counts.items()))


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


def first_matching_compiled(text: str, regex: re.Pattern[str]) -> tuple[int, str] | None:
    for line_number, line in enumerate(text.splitlines(), start=1):
        if regex.search(line):
            return line_number, line.strip()[:220]
    return None


def flow_anchor_evidence(root: Path, path: Path, text: str) -> list[dict[str, object]]:
    rel = rel_path(path, root)
    lower_rel = rel.lower()
    language = language_for_path(path)
    evidence: list[dict[str, object]] = []
    seen_kinds: set[str] = set()

    def add(kind: str, detail: str, line: int, snippet: str) -> None:
        if kind in seen_kinds:
            return
        seen_kinds.add(kind)
        evidence.append(
            {
                "kind": kind,
                "detail": detail,
                "line": line,
                "snippet": snippet[:220],
            }
        )

    for kind, detail, regex in (
        ("entrypoint", "route, handler, job, CLI, webhook, or consumer marker", FLOW_ENTRYPOINT_RE),
        ("state_mutation", "state mutation or external side-effect marker", FLOW_STATE_RE),
        ("dependency", "external dependency, queue, provider, subprocess, or HTTP marker", FLOW_DEPENDENCY_RE),
        ("release_ops", "release, deploy, rollback, canary, or migration marker", FLOW_RELEASE_OPS_RE),
        ("feedback_loop", "metric, alert, trace, runbook, or incident marker", FLOW_FEEDBACK_RE),
    ):
        match = first_matching_compiled(text, regex)
        if match:
            line_number, snippet = match
            add(kind, detail, line_number, snippet)

    if language == "github-actions":
        add("release_ops", "GitHub Actions workflow file", 1, rel)
    if DATA_CHANGE_ANCHOR_PATH_RE.search(rel):
        add("state_mutation", "migration, backfill, repair, or data-change path", 1, rel)
    if re.search(r"(^|/)(api|routes?|controllers?|handlers?|views?|webhooks?)(/|$)", lower_rel):
        add("entrypoint", "entrypoint-like path", 1, rel)
    if re.search(r"(^|/)(jobs?|workers?|consumers?|cron|tasks?)(/|$)", lower_rel):
        add("entrypoint", "job, worker, consumer, cron, or task path", 1, rel)
    if re.search(r"(^|/)(runbooks?|incidents?|postmortems?)(/|$)", lower_rel):
        add("feedback_loop", "runbook or incident path", 1, rel)

    return evidence


def flow_type_for(path: str, language: str, anchor_kinds: list[str]) -> str:
    anchors = set(anchor_kinds)
    if language == "github-actions" or "release_ops" in anchors and ".github/workflows/" in path:
        return "ci/release path"
    if "state_mutation" in anchors and DATA_CHANGE_ANCHOR_PATH_RE.search(path):
        return "data mutation path"
    if {"entrypoint", "state_mutation", "dependency"} <= anchors:
        return "request or job critical path"
    if {"entrypoint", "dependency"} <= anchors:
        return "dependency-facing entrypoint"
    if "entrypoint" in anchors:
        return "entrypoint"
    if "feedback_loop" in anchors:
        return "operational feedback path"
    return "review path"


def trace_question_for(flow_type: str, path: str, exposure_dimensions: list[str]) -> str:
    if flow_type == "ci/release path":
        return "Trace from trigger to jobs, permissions, concurrency, dependencies, artifacts, and release or rollback verification if it deploys."
    if flow_type == "data mutation path":
        return "Trace the data change from target selection to mutation, dry-run, checkpoint, rollback or repair, and audit evidence."
    if flow_type == "request or job critical path":
        return "Trace from entrypoint to state mutation, dependency calls, failure handling, observability, and degradation or rollback."
    if flow_type == "dependency-facing entrypoint":
        return "Trace dependency timeout, cancellation, retry budget, fallback, and owner-visible failure evidence from this entrypoint."
    if "feedback_delay" in exposure_dimensions:
        return "Trace how this path turns failure into metrics, alerts, tests, runbooks, or incident follow-up."
    return f"Trace `{path}` across trigger, state, dependency, failure handling, feedback, and reversal evidence."


def critical_flow_candidates(root: Path, texts: dict[Path, str], findings: list[Finding]) -> list[dict[str, object]]:
    findings_by_path: dict[str, list[Finding]] = {}
    for finding in findings:
        findings_by_path.setdefault(finding.path, []).append(finding)

    candidates: list[dict[str, object]] = []
    for path, text in texts.items():
        rel = rel_path(path, root)
        source_kind = classify_path(path)
        operational_doc = bool(re.search(r"(^|/)(runbooks?|incidents?|postmortems?)(/|$)", rel, re.IGNORECASE))
        if source_kind == "tests" or (source_kind == "docs" and not operational_doc):
            continue

        evidence = flow_anchor_evidence(root, path, text)
        if not evidence:
            continue

        path_findings = findings_by_path.get(rel, [])
        exposure_dimensions = sorted(
            {
                dimension
                for finding in path_findings
                for dimension in finding.exposure_dimensions
            }
        )
        anchor_kinds = [item["kind"] for item in evidence]
        anchor_set = set(anchor_kinds)
        if not exposure_dimensions:
            meaningful_without_exposure = (
                language_for_path(path) == "github-actions"
                or operational_doc
                or {"entrypoint", "state_mutation", "dependency"} <= anchor_set
                or {"state_mutation", "dependency"} <= anchor_set
                or "state_mutation" in anchor_set and DATA_CHANGE_ANCHOR_PATH_RE.search(rel)
            )
            if not meaningful_without_exposure:
                continue

        pattern_counts: dict[str, int] = {}
        for finding in path_findings:
            pattern_counts[finding.pattern_id] = pattern_counts.get(finding.pattern_id, 0) + 1
        supporting_patterns = [
            pattern_id for pattern_id, _count in sorted(pattern_counts.items(), key=lambda entry: (-entry[1], entry[0]))[:6]
        ]

        language = language_for_path(path)
        flow_type = flow_type_for(rel, language, anchor_kinds)
        score = len(anchor_set) * 2 + len(exposure_dimensions) * 3 + min(len(path_findings), 6)
        if flow_type in {"request or job critical path", "data mutation path", "ci/release path"}:
            score += 3

        candidates.append(
            {
                "path": rel,
                "source_kind": source_kind,
                "language": language,
                "flow_type": flow_type,
                "score": score,
                "anchor_kinds": anchor_kinds,
                "exposure_dimensions": exposure_dimensions,
                "supporting_patterns": supporting_patterns,
                "evidence": evidence[:5],
                "trace_question": trace_question_for(flow_type, rel, exposure_dimensions),
            }
        )

    return sorted(candidates, key=lambda item: (-int(item["score"]), str(item["path"])))[:10]


def exposure_summary(findings: list[Finding]) -> dict[str, object]:
    dimension_items: dict[str, list[Finding]] = {}
    for finding in findings:
        for dimension in finding.exposure_dimensions:
            dimension_items.setdefault(dimension, []).append(finding)

    dimensions: dict[str, object] = {}
    ordered_dimensions = sorted(
        dimension_items,
        key=lambda dimension: (-len(dimension_items[dimension]), dimension),
    )
    for dimension in ordered_dimensions:
        items = dimension_items[dimension]
        pattern_counts: dict[str, int] = {}
        path_counts: dict[str, int] = {}
        categories: set[str] = set()
        examples = []
        seen_examples: set[tuple[str, int, str]] = set()
        for item in items:
            pattern_counts[item.pattern_id] = pattern_counts.get(item.pattern_id, 0) + 1
            path_counts[item.path] = path_counts.get(item.path, 0) + 1
            categories.add(item.category)
            example_key = (item.path, item.line, item.pattern_id)
            if example_key not in seen_examples and len(examples) < 3:
                seen_examples.add(example_key)
                examples.append(
                    {
                        "path": item.path,
                        "line": item.line,
                        "pattern_id": item.pattern_id,
                        "source_kind": item.source_kind,
                        "language": item.language,
                        "snippet": item.snippet,
                    }
                )

        top_patterns = [
            {"pattern_id": pattern_id, "count": count}
            for pattern_id, count in sorted(pattern_counts.items(), key=lambda entry: (-entry[1], entry[0]))[:5]
        ]
        top_paths = [
            {"path": path, "count": count}
            for path, count in sorted(path_counts.items(), key=lambda entry: (-entry[1], entry[0]))[:5]
        ]
        dimensions[dimension] = {
            "finding_count": len(items),
            "categories": sorted(categories),
            "top_patterns": top_patterns,
            "top_paths": top_paths,
            "examples": examples,
            "review_question": EXPOSURE_REVIEW_QUESTIONS.get(dimension, "What critical flow makes this signal matter?"),
            "next_move": EXPOSURE_NEXT_MOVES.get(dimension, "Confirm whether these leads sit on an important flow."),
        }

    return {
        "dimension_order": ordered_dimensions,
        "dimensions": dimensions,
    }


def format_counted_items(items: list[dict[str, object]], key: str) -> str:
    if not items:
        return "none"
    return ", ".join(f"{item[key]} ({item['count']})" for item in items)


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
            f"- Languages scanned: {format_language_counts(signals['language_file_counts'])}",
            f"- Migration files detected: {signals['migration_file_count']}",
            f"- Incident artifacts detected: {signals['incident_file_count']}",
            f"- Runbook files detected: {signals['runbook_file_count']}",
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

    flow_candidates = result["critical_flow_candidates"]
    if flow_candidates:
        lines.extend(["## Critical Flow Candidates", ""])
        for item in flow_candidates:
            lines.append(f"- `{item['path']}` [{item['flow_type']}; score {item['score']}]")
            lines.append(f"  - Anchors: {', '.join(item['anchor_kinds'])}")
            if item["exposure_dimensions"]:
                lines.append(f"  - Exposure overlap: {', '.join(item['exposure_dimensions'])}")
            if item["supporting_patterns"]:
                lines.append(f"  - Supporting patterns: {', '.join(item['supporting_patterns'])}")
            lines.append(f"  - Trace question: {item['trace_question']}")
            if item["evidence"]:
                rendered_evidence = ", ".join(
                    f"`{item['path']}:{evidence['line']}` [{evidence['kind']}]"
                    for evidence in item["evidence"]
                )
                lines.append(f"  - Evidence: {rendered_evidence}")
        lines.append("")

    summary = result["exposure_summary"]
    if summary["dimension_order"]:
        lines.extend(["## Exposure Review Leads", ""])
        for dimension in summary["dimension_order"]:
            item = summary["dimensions"][dimension]
            lines.append(f"### {dimension}")
            lines.append("")
            lines.append(f"- Findings: {item['finding_count']}")
            lines.append(f"- Categories: {', '.join(item['categories'])}")
            lines.append(f"- Top patterns: {format_counted_items(item['top_patterns'], 'pattern_id')}")
            lines.append(f"- Top paths: {format_counted_items(item['top_paths'], 'path')}")
            lines.append(f"- Review question: {item['review_question']}")
            lines.append(f"- Next move: {item['next_move']}")
            if item["examples"]:
                rendered_examples = ", ".join(
                    f"`{example['path']}:{example['line']}` [{example['pattern_id']}]"
                    for example in item["examples"]
                )
                lines.append(f"- Sample evidence: {rendered_examples}")
            lines.append("")

    if grouped:
        lines.extend(["## Heuristic Findings", ""])
        for category, items in grouped.items():
            lines.extend([f"### {category}", ""])
            for item in items:
                lines.append(
                    f"- `{item.path}:{item.line}` [{item.source_kind}; {item.language}; {item.pattern_id}; {item.concept}] {item.snippet}"
                )
                lines.append(f"  - Why it matters: {item.why}")
                if item.linter_overlaps:
                    overlaps = ", ".join(item.linter_overlaps)
                    lines.append(f"  - Linter overlap: {overlaps}")
                if item.exposure_dimensions:
                    dimensions = ", ".join(item.exposure_dimensions)
                    lines.append(f"  - Exposure dimensions: {dimensions}")
                lines.append(f"  - Scanner value: {item.scanner_value}")
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

    if args.list_rules:
        rules = all_rule_info()
        if args.json:
            print(json.dumps({"rule_count": len(rules), "rules": [rule_info_as_dict(rule) for rule in rules]}, indent=2))
        else:
            print(rules_markdown(rules))
        return 0

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
        "critical_flow_candidates": critical_flow_candidates(root, texts, findings),
        "exposure_summary": exposure_summary(findings),
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
