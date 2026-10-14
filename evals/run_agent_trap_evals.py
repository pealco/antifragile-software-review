#!/usr/bin/env python3
"""E2: do the controls a hardening adds stop later agents' mistakes?

Not part of CI: it calls a model. Two phases:

1. Harden. For each configuration (with or without the skill), run the harden case from
   evals/evals.json and keep each resulting repo. Record which challenges pass.
2. Change. On each hardened repo, a downstream coding agent (no skill) does ordinary tasks from
   evals/agent_traps.json that invite the same mistakes again: a new retry rule, a fallback bank,
   a renamed flag, a dry-run mode. After each task, the challenges run again.

The outcome is the regression rate: of the challenges that passed after hardening, how many fail
after a later agent's change. A control that is impossible to get wrong (a required key argument)
should survive these tasks; one that is only a comment or an easily edited test should not.
Results go to evals/results/traps-<timestamp>/.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_output_evals as out

TRAPS = out.ROOT / "evals" / "agent_traps.json"


def challenges(project: Path, names: list[str]) -> dict[str, bool]:
    run: dict = {}
    return {n: out.run_check(f"challenge:{n}", project, run) for n in names}


def harden(
    job: tuple[dict, bool, int], args: argparse.Namespace, skill_name: str, keep: Path
) -> dict:
    case, with_skill, index = job
    project = out.make_project(case, args.skill_dir if with_skill else None, skill_name)
    run = out.run_agent(case, project, with_skill, args.hardener_model, args.budget)
    config = "with_skill" if with_skill else "without_skill"
    shutil.rmtree(
        project / ".claude" / "skills", ignore_errors=True
    )  # later agents get no skill
    out.git(project, "add", "-A")
    out.git(project, "commit", "-q", "--allow-empty", "-m", "hardening")
    patch = out.git(project, "diff", "--binary", "HEAD~1", "HEAD")
    repo = keep / f"{config}-{index}"
    shutil.move(str(project), repo)
    return {
        "config": config, "run": index, "repo": str(repo), "error": run["error"], "cost": run["cost"],
        "challenges": challenges(repo, args.challenge_names), "patch": patch,
    }  # fmt: skip


def change(job: tuple[dict, dict, int], args: argparse.Namespace) -> dict:
    hardened, task, index = job
    project = Path(tempfile.mkdtemp(prefix="trap-")) / "repo"
    shutil.copytree(hardened["repo"], project)
    try:
        case = {"prompt": task["prompt"], "mode": "implementation"}
        run = out.run_agent(case, project, False, args.task_model, args.budget)
        after = challenges(project, args.challenge_names)
        out.git(project, "add", "-A")
        patch = out.git(project, "diff", "--binary", "--cached", "HEAD")
        return {
            "config": hardened["config"], "hardened_run": hardened["run"], "task": task["id"],
            "run": index, "error": run["error"], "cost": run["cost"],
            "changed": out.changed_files(project), "before": hardened["challenges"], "after": after,
            "regressed": [n for n, ok in hardened["challenges"].items() if ok and not after[n]],
            "final_text": run["final_text"], "patch": patch,
        }  # fmt: skip
    finally:
        shutil.rmtree(project.parent, ignore_errors=True)


def rebuild(patches: list[str], dest: Path) -> Path:
    """The fixture with the saved hardening and task patches applied, for regrading."""
    fixture = out.FIXTURES / json.loads(TRAPS.read_text(encoding="utf-8"))["fixture"]
    shutil.copytree(fixture, dest)
    out.git(dest, "init", "-q")
    for patch in patches:
        if patch.strip():
            subprocess.run(["git", "apply", "--whitespace=nowarn", "-"], input=patch, text=True,
                           cwd=dest, check=True, capture_output=True)  # fmt: skip
    return dest


def regrade(results_dir: Path, names: list[str]) -> int:
    """Re-run the challenges on saved patches, with no model calls. Use after a challenge changes."""
    data = json.loads((results_dir / "results.json").read_text(encoding="utf-8"))
    by_repo = {(h["config"], h["run"]): h for h in data["hardened"]}
    with tempfile.TemporaryDirectory(prefix="regrade-") as tmp:
        for i, h in enumerate(data["hardened"]):
            h["challenges"] = challenges(
                rebuild([h["patch"]], Path(tmp) / f"h{i}"), names
            )
        for i, c in enumerate(data["changes"]):
            h = by_repo[(c["config"], c["hardened_run"])]
            c["before"] = h["challenges"]
            c["after"] = challenges(
                rebuild([h["patch"], c["patch"]], Path(tmp) / f"c{i}"), names
            )
            c["regressed"] = [
                n for n, ok in c["before"].items() if ok and not c["after"][n]
            ]
    summary = summarize(data["hardened"], data["changes"], names)
    print(json.dumps(summary, indent=2))
    for r in data["changes"]:
        if r["regressed"]:
            print(
                f"regressed: {r['config']} hardened#{r['hardened_run']} task={r['task']}: {r['regressed']}"
            )
    (results_dir / "results.regraded.json").write_text(
        json.dumps(data, indent=2) + "\n"
    )
    (results_dir / "summary.regraded.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )
    return 0


def summarize(hardened: list[dict], changes: list[dict], names: list[str]) -> dict:
    summary: dict = {}
    for config in ("with_skill", "without_skill"):
        h = [r for r in hardened if r["config"] == config and not r["error"]]
        c = [r for r in changes if r["config"] == config and not r["error"]]
        if not h:
            continue
        held = sum(r["before"][n] for r in c for n in names)
        summary[config] = {
            "hardened_repos": len(h),
            "pass_after_hardening": {n: f"{sum(r['challenges'][n] for r in h)}/{len(h)}" for n in names},
            "task_runs": len(c),
            "regressions": f"{sum(len(r['regressed']) for r in c)}/{held}",
            "regressions_by_task": {
                t: f"{sum(len(r['regressed']) for r in c if r['task'] == t)}/"
                   f"{sum(r['before'][n] for r in c if r['task'] == t for n in names)}"
                for t in sorted({r["task"] for r in c})
            },
            "cost": round(sum(r["cost"] for r in h + c), 2),
        }  # fmt: skip
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--skill-dir", type=Path, default=out.ROOT)
    ap.add_argument("--configs", default="with_skill,without_skill")
    ap.add_argument(
        "--hardens", type=int, default=3, help="hardened repos per configuration"
    )
    ap.add_argument(
        "--runs", type=int, default=1, help="runs of each task on each hardened repo"
    )
    ap.add_argument("--hardener-model", default="sonnet")
    ap.add_argument("--task-model", default="sonnet")
    ap.add_argument("--only-tasks", help="comma-separated task ids")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--budget", type=float, default=3.0, help="max USD per agent run")
    ap.add_argument("--label", default="")
    ap.add_argument(
        "--regrade",
        type=Path,
        help="re-run the challenges on a saved results directory",
    )
    args = ap.parse_args()

    traps = json.loads(TRAPS.read_text(encoding="utf-8"))
    spec = json.loads(out.CASES.read_text(encoding="utf-8"))
    case = next(c for c in spec["evals"] if c["id"] == traps["harden_case"])
    tasks = [
        t
        for t in traps["tasks"]
        if not args.only_tasks or t["id"] in args.only_tasks.split(",")
    ]
    args.challenge_names = traps["challenges"]
    if args.regrade:
        return regrade(args.regrade, args.challenge_names)

    keep = Path(tempfile.mkdtemp(prefix="hardened-"))
    try:
        jobs = [
            (case, cfg == "with_skill", i)
            for cfg in args.configs.split(",")
            for i in range(args.hardens)
        ]
        with ThreadPoolExecutor(args.workers) as pool:
            hardened = list(
                pool.map(lambda j: harden(j, args, spec["skill_name"], keep), jobs)
            )
        for h in hardened:
            print(
                f"hardened {h['config']} #{h['run']}: {h['challenges']} error={h['error']}"
            )
        jobs2 = [
            (h, t, i)
            for h in hardened
            if not h["error"]
            for t in tasks
            for i in range(args.runs)
        ]
        with ThreadPoolExecutor(args.workers) as pool:
            changes = list(pool.map(lambda j: change(j, args), jobs2))
    finally:
        shutil.rmtree(keep, ignore_errors=True)

    summary = summarize(hardened, changes, args.challenge_names)
    print(json.dumps(summary, indent=2))
    for r in changes:
        if r["regressed"]:
            print(
                f"regressed: {r['config']} hardened#{r['hardened_run']} task={r['task']}: {r['regressed']}"
            )
    stamp = f"{datetime.now(timezone.utc):%Y%m%d-%H%M%S}"
    dest = (
        out.ROOT
        / "evals"
        / "results"
        / f"traps-{args.label + '-' if args.label else ''}{stamp}"
    )
    dest.mkdir(parents=True)
    (dest / "results.json").write_text(
        json.dumps({"hardened": hardened, "changes": changes}, indent=2) + "\n"
    )
    (dest / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    errors = sum(bool(r["error"]) for r in hardened + changes)
    print(
        f"total spend: ${sum(r['cost'] for r in hardened + changes):.2f}; errors: {errors}; results in {dest}"
    )
    return 1 if errors == len(hardened + changes) else 0


if __name__ == "__main__":
    raise SystemExit(main())
