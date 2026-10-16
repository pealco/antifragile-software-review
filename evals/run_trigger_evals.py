#!/usr/bin/env python3
"""Measure how often headless Claude Code loads this skill for each trigger query.

Not part of CI: it calls a model. Each run uses a fresh `claude -p` session in a temp
project that holds a copy of the skill. A run that errors counts as "unknown", never as
"did not trigger", so network or auth failures cannot pass a should-not-trigger query.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import statistics
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skills" / "fragility-review"
QUERIES = ROOT / "evals" / "trigger_queries.json"
THRESHOLD = (
    0.5  # agentskills.io default: trigger rate above this passes a should-trigger query
)
MAX_TURNS = 6
RUN_TIMEOUT_S = 240  # a blocked network retries for ~3 minutes before failing


def skill_name(skill_dir: Path) -> str:
    for line in (skill_dir / "SKILL.md").read_text(encoding="utf-8").splitlines():
        if line.startswith("name:"):
            return line.partition(":")[2].strip()
    raise SystemExit("error: SKILL.md has no name field")


def make_project(
    skill_dir: Path, name: str | None, description: str | None = None
) -> Path:
    project = Path(tempfile.mkdtemp(prefix="trigger-eval-"))
    # Real content, so exploring the "repo" gives the model something to find, as in real use.
    for fixture in sorted((ROOT / "evals" / "fixtures").iterdir()):
        if (
            fixture.name != "untrusted-instructions"
        ):  # its README is an injection test string
            shutil.copytree(fixture, project / fixture.name)
    if name:
        shutil.copytree(
            skill_dir,
            project / ".claude" / "skills" / name,
            ignore=shutil.ignore_patterns(
                ".git", "__pycache__", "evals", "tests", "docs"
            ),
        )
        if description is not None:  # judge a candidate description on its own
            skill_md = project / ".claude" / "skills" / name / "SKILL.md"
            text = skill_md.read_text(encoding="utf-8")
            text = re.sub(r"^when_to_use:.*\n", "", text, count=1, flags=re.MULTILINE)
            text = re.sub(
                r"^description:.*$",
                lambda _: (
                    "description: " + json.dumps(description)
                ),  # JSON string is valid YAML
                text,
                count=1,
                flags=re.MULTILINE,
            )
            skill_md.write_text(text, encoding="utf-8")
    return project


def run_once(
    project: Path, name: str, query: str, model: str, budget: float
) -> tuple[str, list[str], float]:
    """Return (outcome, tool names in order, USD cost). Outcome is "triggered",
    "not-triggered", or "error:<reason>"."""
    cmd = [
        "claude",
        "-p",
        query,
        "--output-format",
        "stream-json",
        "--verbose",
        # A model often explores before it picks a skill, so allow several turns. Only read-only
        # tools are allowed. No find or rg: both can run other commands.
        "--max-turns",
        str(MAX_TURNS),
        "--setting-sources",
        "project",  # leave user skills, hooks, and memory out
        "--allowedTools",
        "Skill",
        "Read",
        "Glob",
        "Grep",
        "Bash(ls:*)",
        "Bash(cat:*)",
        "Bash(head:*)",
        "Bash(wc:*)",
        "Bash(grep:*)",
        "--no-session-persistence",
        "--model",
        model,
        "--max-budget-usd",
        str(budget),
    ]
    try:
        done = subprocess.run(
            cmd,
            cwd=project,
            capture_output=True,
            text=True,
            timeout=RUN_TIMEOUT_S,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return "error:timeout", [], 0.0
    events = []
    for line in done.stdout.splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    if any(
        e.get("is_api_error_message") or e.get("terminal_reason") == "api_error"
        for e in events
    ):
        return "error:api", [], 0.0
    if not any(e.get("type") == "result" for e in events):
        return "error:no-result", [], 0.0
    tools, triggered = [], False
    for event in events:
        if event.get("type") != "assistant":
            continue
        for block in event["message"]["content"]:
            if block.get("type") == "tool_use":
                tools.append(block["name"])
                triggered |= block["name"] == "Skill" and block["input"].get(
                    "skill", ""
                ).endswith(name)
    cost = sum(
        e.get("total_cost_usd") or 0 for e in events if e.get("type") == "result"
    )
    return ("triggered" if triggered else "not-triggered"), tools, cost


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--skill-dir", type=Path, default=SKILL_DIR, help="skill under test"
    )
    ap.add_argument("--queries", type=Path, default=QUERIES)
    ap.add_argument(
        "--split", choices=("train", "validation", "holdout", "all"), default="all"
    )
    ap.add_argument("--only", help="comma-separated query ids")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--budget", type=float, default=0.25, help="max USD per run")
    ap.add_argument(
        "--description-file",
        type=Path,
        help="test this description text instead of the skill's own (drops when_to_use)",
    )
    ap.add_argument(
        "--no-skill", action="store_true", help="baseline: skill not installed"
    )
    ap.add_argument("--out", type=Path, help="write per-query results as JSON")
    args = ap.parse_args()

    queries = json.loads(args.queries.read_text(encoding="utf-8"))
    # "all" is train + validation. Run the holdout split on its own, once per description.
    queries = [
        q
        for q in queries
        if q["split"] == args.split or (args.split == "all" and q["split"] != "holdout")
    ]
    if args.only:
        wanted = set(args.only.split(","))
        queries = [q for q in queries if q["id"] in wanted]

    name = skill_name(args.skill_dir)
    description = (
        args.description_file.read_text(encoding="utf-8").strip()
        if args.description_file
        else None
    )
    if description is not None and len(description) > 1024:
        raise SystemExit(
            f"error: description is {len(description)} chars; limit is 1024"
        )
    project = make_project(args.skill_dir, None if args.no_skill else name, description)
    try:
        jobs = [(q, i) for q in queries for i in range(args.runs)]
        with ThreadPoolExecutor(args.workers) as pool:
            outcomes = list(
                pool.map(
                    lambda j: run_once(
                        project, name, j[0]["query"], args.model, args.budget
                    ),
                    jobs,
                )
            )
    finally:
        shutil.rmtree(project, ignore_errors=True)

    results = []
    for q in queries:
        pairs = [o for (jq, _), o in zip(jobs, outcomes, strict=True) if jq is q]
        runs = [outcome for outcome, _, _ in pairs]
        valid = [o for o in runs if not o.startswith("error")]
        rate = sum(o == "triggered" for o in valid) / len(valid) if valid else None
        if rate is None:
            verdict = "UNKNOWN"
        elif q["should_trigger"]:
            verdict = "pass" if rate > THRESHOLD else "FAIL"
        else:
            verdict = "pass" if rate < THRESHOLD else "FAIL"
        results.append(
            {
                **q,
                "runs": runs,
                "tools": [t for _, t, _ in pairs],
                "trigger_rate": rate,
                "verdict": verdict,
            }
        )

    for r in results:
        rate = "n/a" if r["trigger_rate"] is None else f"{r['trigger_rate']:.2f}"
        want = "trigger" if r["should_trigger"] else "skip   "
        print(
            f"{r['verdict']:7} {r['id']} {r['split']:10} want {want} rate {rate}  {r['query'][:60]}"
        )
    for split in ("train", "validation", "holdout"):
        rows = [r for r in results if r["split"] == split]
        if rows:
            passed = sum(r["verdict"] == "pass" for r in rows)
            unknown = sum(r["verdict"] == "UNKNOWN" for r in rows)
            print(f"{split}: {passed}/{len(rows)} pass, {unknown} unknown")
    pos = [
        r["trigger_rate"]
        for r in results
        if r["should_trigger"] and r["trigger_rate"] is not None
    ]
    neg = [
        r["trigger_rate"]
        for r in results
        if not r["should_trigger"] and r["trigger_rate"] is not None
    ]
    if pos and neg:
        print(
            f"mean trigger rate: should-trigger {statistics.mean(pos):.2f}, should-not-trigger {statistics.mean(neg):.2f}"
        )
    print(f"spend: ${sum(c for _, _, c in outcomes):.2f} over {len(outcomes)} runs")
    if args.out:
        args.out.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    return 0 if all(r["verdict"] == "pass" for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
