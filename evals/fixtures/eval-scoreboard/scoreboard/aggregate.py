"""Turn a job directory of per-trial result files into per-arm numbers."""

import json
import logging
from collections import defaultdict
from pathlib import Path

from scoreboard import pricing

log = logging.getLogger(__name__)

PASS_THRESHOLD = 1.0


def load_job(job_dir: Path) -> dict:
    return json.loads((job_dir / "job.json").read_text())


def read_result(job_dir: Path, trial_id: str) -> dict | None:
    path = job_dir / "trials" / trial_id / "result.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        log.warning("unreadable result for %s", trial_id)
        return None


def mean_duration(job_dir: Path, trial_ids: list[str]) -> float | None:
    durations = []
    for trial_id in trial_ids:
        log_path = job_dir / "trials" / trial_id / "agent.log"
        for line in log_path.read_text().splitlines():
            if line.startswith("elapsed_s="):
                durations.append(float(line.split("=", 1)[1]))
    return round(sum(durations) / len(durations), 1) if durations else None


def summarize_job(job_dir: Path, catalog: dict) -> dict:
    job = load_job(job_dir)
    arms: dict[str, dict] = defaultdict(
        lambda: {
            "trials": 0,
            "passed": 0,
            "cost_usd": 0.0,
            "input_tokens": 0,
            "output_tokens": 0,
            "routed_calls": 0,
        }
    )
    seen: dict[str, list[str]] = defaultdict(list)
    for trial in job["trials"]:
        result = read_result(job_dir, trial["id"])
        if result is None:
            log.warning("no result for %s, skipping", trial["id"])
            continue
        if result.get("reward") is None:
            log.warning("trial %s has no reward (%s)", trial["id"], result.get("error"))
            continue
        stats = arms[trial["arm"]]
        seen[trial["arm"]].append(trial["id"])
        stats["trials"] += 1
        if result["reward"] >= PASS_THRESHOLD:
            stats["passed"] += 1
        usage = result.get("usage", [])
        stats["cost_usd"] += pricing.trial_cost(catalog, usage)
        stats["input_tokens"] += sum(c.get("input_tokens", 0) for c in usage)
        stats["output_tokens"] += sum(c.get("output_tokens", 0) for c in usage)
        stats["routed_calls"] += sum(1 for c in usage if c.get("route"))

    summary = {"job_id": job["job_id"], "task_set": job["task_set"], "arms": {}}
    for name, stats in arms.items():
        stats["pass_rate"] = round(stats["passed"] / stats["trials"], 4) if stats["trials"] else None
        stats["cost_usd"] = round(stats["cost_usd"], 6)
        try:
            stats["mean_duration_s"] = mean_duration(job_dir, seen[name])
        except Exception:
            pass
        summary["arms"][name] = stats
    return summary
