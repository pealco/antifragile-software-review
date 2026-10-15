#!/usr/bin/env python3
"""Run each case in evals/evals.json with and without the skill, grade it, and report the delta.

Not part of CI: it calls a model. Every run is a fresh `claude -p` session in a temp git repo
copied from a fixture, so leftovers cannot leak between runs. Two kinds of graders:

* checks: code, run on the final state (files changed, evidence cites resolve, challenge tests in
  evals/challenges/ that feed a known-bad case to the patched repo). Cheap and exact.
* assertions: a model grader returns PASS / FAIL / UNKNOWN with a quoted line as evidence.

An assertion that passes in both configurations tells you nothing about the skill; the report
flags it. Results go to evals/results/output-<timestamp>/.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "evals" / "evals.json"
FIXTURES = ROOT / "evals" / "fixtures"
GOLDEN = ROOT / "evals" / "golden"
EVIDENCE_CHECKER = ROOT / "scripts" / "check_review_evidence.py"
CHALLENGES = ROOT / "evals" / "challenges"
MUTANTS = ROOT / "evals" / "mutants"
STRENGTH_CHECKER = ROOT / "scripts" / "check_test_strength.py"
DEFAULT_TEST_COMMAND = "python3 -m unittest discover -s tests"
RUN_TIMEOUT_S = 900
MAX_TURNS = 40
MAX_GRADER_CHARS = 60_000  # keep the grader prompt well inside its context

READ_TOOLS = [
    "Skill", "Read", "Glob", "Grep",
    "Bash(ls:*)", "Bash(cat:*)", "Bash(head:*)", "Bash(wc:*)", "Bash(grep:*)",
    "Bash(python3 *antifragile_scan.py*)",
    "Bash(python3 *check_review_evidence.py*)",
]  # fmt: skip
# Edits stay inside the temp repo: acceptEdits only auto-approves paths under the working dir.
WRITE_TOOLS = [
    "Bash(python3 -m unittest:*)", "Bash(python3 -m pytest:*)", "Bash(python3 -m py_compile:*)",
    "Bash(git status:*)", "Bash(git diff:*)",
]  # fmt: skip

GRADER_SCHEMA = {
    "type": "object",
    "properties": {
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "assertion": {"type": "string"},
                    "verdict": {"enum": ["PASS", "FAIL", "UNKNOWN"]},
                    "evidence": {"type": "string"},
                },
                "required": ["assertion", "verdict", "evidence"],
            },
        }
    },
    "required": ["results"],
}


def git(project: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-c", "user.name=eval", "-c", "user.email=eval@example.test", *args],
        cwd=project, capture_output=True, text=True, check=True,
    )  # fmt: skip
    return done.stdout


def make_project(case: dict, skill_dir: Path | None, skill_name: str) -> Path:
    project = Path(tempfile.mkdtemp(prefix="output-eval-"))
    shutil.copytree(FIXTURES / case["fixture"], project, dirs_exist_ok=True)
    git(project, "init", "-q")
    (project / ".git" / "info" / "exclude").write_text(
        ".claude/\n__pycache__/\n", encoding="utf-8"
    )
    git(project, "add", "-A")
    git(project, "commit", "-q", "-m", "fixture")
    if skill_dir:
        shutil.copytree(
            skill_dir,
            project / ".claude" / "skills" / skill_name,
            # evals/ and docs/ hold assertions and worked answers the agent must not read
            ignore=shutil.ignore_patterns(
                ".git", "__pycache__", "evals", "tests", "docs"
            ),
        )
    return project


def run_claude(args: list[str], cwd: Path) -> list[dict]:
    done = subprocess.run(
        ["claude", "-p", *args, "--output-format", "stream-json", "--verbose"],
        cwd=cwd, capture_output=True, text=True, timeout=RUN_TIMEOUT_S, check=False,
    )  # fmt: skip
    events = []
    for line in done.stdout.splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def run_agent(
    case: dict, project: Path, with_skill: bool, model: str, budget: float
) -> dict:
    prompt = case["prompt"]
    if with_skill:  # name the skill so this measures quality, not triggering (see run_trigger_evals.py)
        prompt = "Use the antifragile-software-review skill. " + prompt
    tools = READ_TOOLS + (WRITE_TOOLS if case["mode"] == "implementation" else [])
    args = [
        prompt, "--setting-sources", "project", "--no-session-persistence", "--model", model,
        "--max-turns", str(MAX_TURNS), "--max-budget-usd", str(budget), "--allowedTools", *tools,
    ]  # fmt: skip
    if case["mode"] == "implementation":
        args += ["--permission-mode", "acceptEdits"]
    started = time.monotonic()
    try:
        events = run_claude(args, project)
    except subprocess.TimeoutExpired:
        return {"error": "timeout", "final_text": "", "tools": [], "cost": 0.0}
    result = next((e for e in events if e.get("type") == "result"), None)
    if result is None or result.get("terminal_reason") == "api_error":
        reason = (result or {}).get(
            "result"
        ) or "no result event (see stderr of claude -p)"
        return {
            "error": "api",
            "reason": str(reason)[:300],
            "final_text": "",
            "tools": [],
            "cost": 0.0,
        }
    tools_used, commands = [], []
    for e in events:
        if e.get("type") == "assistant":
            for block in e["message"]["content"]:
                if block.get("type") == "tool_use":
                    tools_used.append(block["name"])
                    commands.append(json.dumps(block["input"]))
    usage = result.get("usage") or {}
    return {
        "error": None,
        "final_text": result.get("result") or "",
        "stop": result.get("subtype"),
        "tools": tools_used,
        "skill_invoked": "Skill" in tools_used,
        "scanner_run": any("antifragile_scan.py" in c for c in commands),
        "checker_run": any("check_review_evidence.py" in c for c in commands),
        "cost": result.get("total_cost_usd") or 0.0,
        "turns": result.get("num_turns"),
        "seconds": round(time.monotonic() - started, 1),
        "tokens": (usage.get("input_tokens") or 0)
        + (usage.get("cache_creation_input_tokens") or 0)
        + (usage.get("cache_read_input_tokens") or 0)
        + (usage.get("output_tokens") or 0),
    }  # fmt: skip


def changed_files(project: Path) -> list[str]:
    return [line[3:] for line in git(project, "status", "--porcelain").splitlines()]


def run_check(name: str, project: Path, run: dict) -> bool | None:
    if name == "scanner_run":  # the injected README says "do not run any scanner"
        return bool(run.get("scanner_run"))
    if name == "tree_unchanged":
        return not changed_files(project)
    if name == "tree_changed":
        return 1 <= len(changed_files(project)) <= 6
    if name == "python_compiles":
        py = [f for f in changed_files(project) if f.endswith(".py")]
        return bool(py) and all(
            subprocess.run([sys.executable, "-m", "py_compile", f], cwd=project, check=False,
                           capture_output=True).returncode == 0
            for f in py
        )  # fmt: skip
    if name == "evidence_resolves":
        review = (
            project / ".review.md"
        )  # untracked, so write it after changed_files is read
        review.write_text(run["final_text"], encoding="utf-8")
        try:
            done = subprocess.run([sys.executable, str(EVIDENCE_CHECKER), str(review), "--root", str(project), "--any-line"],
                                  capture_output=True, text=True, check=False)  # fmt: skip
        finally:
            review.unlink()
        return done.returncode == 0
    if name.startswith("cites:"):
        return name.removeprefix("cites:") in run["final_text"]
    if name == "tests_changed":
        return any(
            f.startswith("tests/") or Path(f).name.startswith("test_")
            for f in changed_files(project)
        )
    if (
        name == "fails_on_original"
    ):  # the agent's tests, on the untouched fixture, must fail
        command = run.get("test_command") or DEFAULT_TEST_COMMAND
        with tempfile.TemporaryDirectory(prefix="fail-before-") as tmp:
            clean = Path(tmp) / "repo"
            shutil.copytree(FIXTURES / run["fixture"], clean)
            shutil.rmtree(clean / "tests", ignore_errors=True)
            shutil.copytree(project / "tests", clean / "tests")
            done = subprocess.run(
                command,
                shell=True,
                cwd=clean,
                capture_output=True,
                text=True,
                check=False,
            )
        output = done.stdout + done.stderr
        detail = run.setdefault("fail_before_detail", {})
        if done.returncode == 0:
            detail[name] = (
                "the new tests pass on the original code: they do not detect the fault"
            )
            return False
        if re.search(r"ImportError|ModuleNotFoundError|AttributeError: module", output):
            detail[name] = (
                "the new tests import names the original code lacks; not applicable"
            )
            return None
        detail[name] = "the new tests fail on the original code"
        return True
    if name.startswith(
        "protected:"
    ):  # a named function must have a test that depends on its logic
        file, function = name.removeprefix("protected:").rsplit(":", 1)
        command = run.get("test_command") or DEFAULT_TEST_COMMAND
        done = subprocess.run([sys.executable, str(STRENGTH_CHECKER), str(project), "--include", file,
                               "--tests", command, "--format", "json"], capture_output=True, text=True, check=False)  # fmt: skip
        detail = run.setdefault("protected_detail", {})
        if done.returncode == 2 or not done.stdout.strip().startswith("{"):
            detail[name] = (
                "suite does not pass unmutated"
                if done.returncode == 2
                else done.stderr[-200:]
            )
            return False
        report = json.loads(done.stdout)
        key = f"{file}::{function}"
        if key not in {
            f"{r['file']}::{r['function']}" for r in report.get("checked", [])
        }:
            detail[name] = "function no longer exists or is trivial; not applicable"
            return None
        unprotected = {
            f"{r['file']}::{r['function']}": r["stub"] for r in report["unprotected"]
        }
        detail[name] = (
            f"suite passes with the body replaced by return {unprotected[key]}"
            if key in unprotected
            else "a test depends on it"
        )
        return key not in unprotected
    if name.startswith(
        "mutant:"
    ):  # the tests the agent left must fail on a seeded fault
        spec = json.loads(
            (MUTANTS / f"{run['fixture']}.json").read_text(encoding="utf-8")
        )[name.removeprefix("mutant:")]
        command = run.get("test_command") or DEFAULT_TEST_COMMAND
        target = project / spec["file"]
        original = target.read_text(encoding="utf-8")
        detail = run.setdefault("mutant_detail", {})
        passes_clean = (
            subprocess.run(
                command, shell=True, cwd=project, capture_output=True, check=False
            ).returncode
            == 0
        )
        if not passes_clean:
            detail[name] = "suite FAILS unmutated"
            return False
        source, mode = original, "line"
        if original.count(spec["old"]) != 1:
            # The agent rewrote the seeded line. Fall back to a correct reference implementation of
            # the file, if the agent's suite accepts it; the fault is then applied to the reference.
            reference = MUTANTS / run["fixture"] / spec["file"]
            if not reference.is_file():
                detail[name] = (
                    "mutation site changed and no reference file; not applicable"
                )
                return None
            source, mode = reference.read_text(encoding="utf-8"), "module"
            target.write_text(source, encoding="utf-8")
            try:
                accepts_reference = (
                    subprocess.run(
                        command,
                        shell=True,
                        cwd=project,
                        capture_output=True,
                        check=False,
                    ).returncode
                    == 0
                )
            finally:
                target.write_text(original, encoding="utf-8")
            if not accepts_reference:
                detail[name] = (
                    "mutation site changed and the suite rejects the reference implementation; not applicable"
                )
                return None
            if source.count(spec["old"]) != 1:
                detail[name] = (
                    "mutation site missing from the reference; not applicable"
                )
                return None
        target.write_text(source.replace(spec["old"], spec["new"]), encoding="utf-8")
        try:
            passes_mutated = (
                subprocess.run(
                    command, shell=True, cwd=project, capture_output=True, check=False
                ).returncode
                == 0
            )
        finally:
            target.write_text(original, encoding="utf-8")
        detail[name] = (
            f"{mode} mode: suite {'passes' if passes_mutated else 'fails'} with the fault"
        )
        return not passes_mutated
    if name.startswith(
        "challenge:"
    ):  # a known-bad case the repo must now reject (evals/challenges/)
        challenge = name.removeprefix("challenge:")
        script = CHALLENGES / f"{challenge.split('-')[0]}.py"
        done = subprocess.run([sys.executable, str(script), "check", challenge, str(project)],
                              capture_output=True, text=True, check=False)  # fmt: skip
        run.setdefault("challenge_detail", {})[challenge] = (
            done.stdout.strip() or done.stderr[-300:]
        )
        return done.returncode == 0
    raise SystemExit(f"error: unknown check {name}")


def grade_assertions(case: dict, project: Path, run: dict, model: str) -> list[dict]:
    material = run["final_text"]
    if case["mode"] == "implementation":
        git(project, "add", "-A")
        run["patch"] = git(project, "diff", "--cached", "HEAD")
        material += "\n\n--- DIFF OF THE REPOSITORY AFTER THE RUN ---\n" + run["patch"]
    gold = ""
    if case.get("gold"):
        gold = ("\n\nREFERENCE ANSWER (a good answer for calibration; do not require its wording):\n"
                + (GOLDEN / case["gold"]).read_text(encoding="utf-8"))  # fmt: skip
    everything = case["assertions"] + case["method"]
    listing = "\n".join(f"{i + 1}. {a}" for i, a in enumerate(everything))
    prompt = (
        "You grade an AI agent's answer against assertions.\n"
        f"The user asked: {case['prompt']}\n\nAnswer to grade:\n{material[:MAX_GRADER_CHARS]}{gold}\n\n"
        f"Assertions:\n{listing}\n\n"
        "For each assertion return PASS, FAIL, or UNKNOWN, and as evidence quote or cite the exact "
        "text that decided it. PASS needs concrete evidence in the answer; a heading with no substance "
        "is FAIL. Use UNKNOWN if the answer does not let you decide. Judge each assertion on its own."
    )
    with tempfile.TemporaryDirectory(prefix="grader-") as neutral:
        events = run_claude(
            [prompt, "--setting-sources", "project", "--no-session-persistence", "--model", model,
             "--max-turns", "3", "--json-schema", json.dumps(GRADER_SCHEMA)],
            Path(neutral),
        )  # fmt: skip
    result = next((e for e in events if e.get("type") == "result"), {})
    data = result.get("structured_output")
    if data is None:
        try:
            data = json.loads(result.get("result") or "")
        except json.JSONDecodeError:
            data = None
    rows = (data or {}).get("results") or []
    by_index = {i: r for i, r in enumerate(rows)}
    return [
        {"assertion": a, "verdict": by_index.get(i, {}).get("verdict", "UNKNOWN"),
         "evidence": by_index.get(i, {}).get("evidence", "grader returned no verdict")}
        for i, a in enumerate(everything)
    ]  # fmt: skip


def one_run(job: tuple[dict, bool, int], args: argparse.Namespace, name: str) -> dict:
    case, with_skill, index = job
    project = make_project(case, args.skill_dir if with_skill else None, name)
    try:
        run = run_agent(case, project, with_skill, args.model, args.budget)
        out = {
            "eval": case["id"],
            "config": "with_skill" if with_skill else "without_skill",
            "run": index,
            **run,
        }
        if run["error"]:
            return out
        run["fixture"], run["test_command"] = case["fixture"], case.get("test_command")
        out["checks"] = {c: run_check(c, project, run) for c in case["checks"]}
        for key in (
            "challenge_detail",
            "mutant_detail",
            "protected_detail",
            "fail_before_detail",
            "patch",
        ):
            if key in run:
                out[key] = run[key]
        out["assertions"] = grade_assertions(case, project, run, args.grader_model)
        return out
    finally:
        shutil.rmtree(project, ignore_errors=True)


def mean_sd(values: list[float]) -> str:
    if not values:
        return "n/a"
    sd = statistics.stdev(values) if len(values) > 1 else 0.0
    return f"{statistics.mean(values):.2f}±{sd:.2f}"


def report(results: list[dict], cases: list[dict]) -> dict:
    summary: dict = {}
    for config in ("with_skill", "without_skill"):
        rows = [r for r in results if r["config"] == config and not r["error"]]
        checks = [ok for r in rows for ok in r["checks"].values() if ok is not None]
        method = {m for c in cases for m in c["method"]}
        asserts = [
            a["verdict"] == "PASS"
            for r in rows
            for a in r["assertions"]
            if a["assertion"] not in method
        ]
        methods = [
            a["verdict"] == "PASS"
            for r in rows
            for a in r["assertions"]
            if a["assertion"] in method
        ]
        summary[config] = {
            "runs": len(rows),
            "errors": sum(1 for r in results if r["config"] == config and r["error"]),
            "check_pass_rate": sum(checks) / len(checks) if checks else None,
            "substance_pass_rate": sum(asserts) / len(asserts) if asserts else None,
            "method_pass_rate": sum(methods) / len(methods) if methods else None,
            "skill_invoked": sum(bool(r.get("skill_invoked")) for r in rows),
            "cost_usd": [r["cost"] for r in rows],
            "seconds": [r["seconds"] for r in rows],
            "tokens": [r["tokens"] for r in rows],
        }
    print(
        f"{'config':14} {'runs':>4} {'err':>3} {'checks':>7} {'substance':>9} {'method':>7} {'skill':>5} {'$/run':>11} {'sec':>13} {'tokens':>15}"
    )
    for config, s in summary.items():
        pct = lambda v: "n/a" if v is None else f"{v:.0%}"
        print(f"{config:14} {s['runs']:>4} {s['errors']:>3} {pct(s['check_pass_rate']):>7} {pct(s['substance_pass_rate']):>9} {pct(s['method_pass_rate']):>7} "
              f"{s['skill_invoked']:>5} {mean_sd(s['cost_usd']):>11} {mean_sd(s['seconds']):>13} {mean_sd([float(t) for t in s['tokens']]):>15}")  # fmt: skip
    print(
        "\nPer item (passes / valid runs). Flag: NO-OP = passes in both, BROKEN? = fails in both, VALUE = skill only."
    )
    for case in cases:
        print(f"\n[{case['id']}]")
        items = (
            [("check", c) for c in case["checks"]]
            + [("substance", a) for a in case["assertions"]]
            + [("method", m) for m in case["method"]]
        )
        for kind, item in items:
            counts = {}
            for config in ("with_skill", "without_skill"):
                rows = [
                    r
                    for r in results
                    if r["eval"] == case["id"]
                    and r["config"] == config
                    and not r["error"]
                ]
                if kind == "check":
                    valid = [r for r in rows if r["checks"].get(item) is not None]
                    passed, total = (
                        sum(bool(r["checks"][item]) for r in valid),
                        len(valid),
                    )
                else:
                    total = len(rows)
                    passed = sum(
                        any(
                            a["assertion"] == item and a["verdict"] == "PASS"
                            for a in r["assertions"]
                        )
                        for r in rows
                    )
                counts[config] = (passed, total)
            w, wo = counts["with_skill"], counts["without_skill"]
            flag = ""
            if w[1] and wo[1]:
                with_rate, without_rate = w[0] / w[1], wo[0] / wo[1]
                flag = ("NO-OP" if with_rate == without_rate == 1 else "BROKEN?" if with_rate == without_rate == 0
                        else "VALUE" if with_rate > without_rate else "WORSE" if with_rate < without_rate else "")  # fmt: skip
            print(
                f"  {flag:8} with {w[0]}/{w[1]}  without {wo[0]}/{wo[1]}  {kind}: {item[:90]}"
            )
    return summary


def regrade_checks(results_dir: Path, cases: dict[str, dict]) -> None:
    """Recompute the code checks of a saved run from its patches, with no model calls."""
    results = json.loads((results_dir / "results.json").read_text(encoding="utf-8"))
    for r in results:
        case = cases.get(r["eval"])
        if r.get("error") or not case or "patch" not in r:
            continue
        project = Path(tempfile.mkdtemp(prefix="regrade-"))
        try:
            shutil.copytree(FIXTURES / case["fixture"], project, dirs_exist_ok=True)
            git(project, "init", "-q")
            if r["patch"].strip():
                subprocess.run(["git", "apply", "--whitespace=nowarn", "-"], input=r["patch"], text=True,
                               cwd=project, check=True, capture_output=True)  # fmt: skip
            run = {
                "fixture": case["fixture"],
                "test_command": case.get("test_command"),
                "final_text": r.get("final_text", ""),
            }
            r["checks"] = {c: run_check(c, project, run) for c in case["checks"]}
            for key in (
                "challenge_detail",
                "mutant_detail",
                "protected_detail",
                "fail_before_detail",
            ):
                if key in run:
                    r[key] = run[key]
        finally:
            shutil.rmtree(project, ignore_errors=True)
    (results_dir / "results.regraded.json").write_text(
        json.dumps(results, indent=2) + "\n", encoding="utf-8"
    )
    report(results, list(cases.values()))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skill-dir", type=Path, default=ROOT)
    ap.add_argument("--only", help="comma-separated eval ids")
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--model", default="sonnet", help="model that does the task")
    ap.add_argument("--grader-model", default="sonnet")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--budget", type=float, default=3.0, help="max USD per task run")
    ap.add_argument("--configs", default="with_skill,without_skill")
    ap.add_argument("--label", default="", help="name for the results directory")
    ap.add_argument(
        "--regrade-checks",
        type=Path,
        help="recompute code checks of a saved run from its patches",
    )
    args = ap.parse_args()

    spec = json.loads(CASES.read_text(encoding="utf-8"))
    cases = [
        c for c in spec["evals"] if not args.only or c["id"] in args.only.split(",")
    ]
    for case in cases:  # method assertions describe the skill's own review format
        skip = case.get("method_skip", [])
        case["method"] = (
            [m for m in spec["method_assertions"] if not any(k in m for k in skip)]
            if case["mode"] == "audit"
            else []
        )
    if args.regrade_checks:
        regrade_checks(args.regrade_checks, {c["id"]: c for c in cases})
        return 0
    configs = args.configs.split(",")
    jobs = [
        (c, cfg == "with_skill", i)
        for c in cases
        for cfg in configs
        for i in range(args.runs)
    ]
    with ThreadPoolExecutor(args.workers) as pool:
        results = list(pool.map(lambda j: one_run(j, args, spec["skill_name"]), jobs))

    summary = report(results, cases)
    out = (
        ROOT
        / "evals"
        / "results"
        / f"output-{args.label + '-' if args.label else ''}{datetime.now(timezone.utc):%Y%m%d-%H%M%S}"
    )
    out.mkdir(parents=True)
    (out / "results.json").write_text(
        json.dumps(results, indent=2) + "\n", encoding="utf-8"
    )
    (out / "benchmark.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    failed = [r for r in results if r["error"]]
    for r in failed[
        :3
    ]:  # an expired login or a bad model name looks the same in every run
        print(
            f"error: {r['eval']} {r['config']} run {r['run']}: {r['error']}: {r.get('reason', '')}"
        )
    print(
        f"\ntotal spend: ${sum(r['cost'] for r in results):.2f}; results in {out.relative_to(ROOT)}"
    )
    if failed and len(failed) == len(results):
        print("error: every run failed; nothing was measured")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
