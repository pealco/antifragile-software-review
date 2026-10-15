import json

import pytest

CATALOG = {
    "atlas-mini": {"input": 0.40, "output": 1.60},
    "corvid-7": {"input": 3.00, "output": 15.00},
}


def make_job(job_dir, results):
    """results: {trial_id: (arm, reward, model)}; every trial gets a complete result file."""
    trials = []
    for trial_id, (arm, reward, model) in results.items():
        trials.append({"id": trial_id, "arm": arm, "task": trial_id.split("-")[1], "difficulty": "easy"})
        d = job_dir / "trials" / trial_id
        d.mkdir(parents=True)
        usage = [{"model": model, "input_tokens": 10_000, "output_tokens": 1_000,
                  "route": "r-1" if arm == "routed" else None}]
        (d / "result.json").write_text(json.dumps({"reward": reward, "error": None, "usage": usage}))
        (d / "agent.log").write_text("elapsed_s=120.0\n")
    (job_dir / "job.json").write_text(json.dumps({"job_id": job_dir.name, "task_set": "nightly.jsonl", "trials": trials}))
    return job_dir


@pytest.fixture
def catalog():
    return CATALOG


@pytest.fixture
def job(tmp_path):
    return make_job(
        tmp_path / "job-1",
        {
            "routed-a-0": ("routed", 1.0, "atlas-mini"),
            "routed-b-0": ("routed", 0.0, "atlas-mini"),
            "fixed-a-0": ("fixed", 1.0, "corvid-7"),
            "fixed-b-0": ("fixed", 1.0, "corvid-7"),
        },
    )
