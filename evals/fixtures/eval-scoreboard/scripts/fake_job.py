"""Dev helper: write a fake job directory so you can work on the report without running agents.

    uv run python scripts/fake_job.py jobs/fake && uv run python -m scoreboard summarize jobs/fake
"""

import json
import random
import sys
from pathlib import Path

from scoreboard.launch import load_tasks, plan

ROOT = Path(__file__).resolve().parents[1]


def main(out: str) -> None:
    job_dir = Path(out)
    tasks = load_tasks(ROOT / "tasks" / "nightly.jsonl")
    trials = plan(tasks, ["routed", "fixed"], 1)
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "job.json").write_text(json.dumps({"job_id": job_dir.name, "task_set": "nightly.jsonl", "trials": trials}))
    for t in trials:
        d = job_dir / "trials" / t["id"]
        d.mkdir(parents=True, exist_ok=True)
        model = "atlas-mini" if t["arm"] == "routed" else "corvid-7"
        usage = [{"model": model, "input_tokens": random.randint(5000, 40000), "output_tokens": random.randint(500, 4000),
                  "route": "r-dev" if t["arm"] == "routed" else None}]
        (d / "result.json").write_text(json.dumps({"reward": float(random.random() > 0.4), "error": None, "usage": usage}))
        (d / "agent.log").write_text(f"elapsed_s={random.uniform(30, 600):.1f}\n")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "jobs/fake")
