"""Launch every planned trial of a job and record the plan in job.json."""

import json
import logging
import os
import shlex
import subprocess
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from scoreboard.config import Arm, Settings

log = logging.getLogger(__name__)


def load_tasks(path: Path) -> list[dict]:
    tasks = []
    for line in path.read_text().splitlines():
        if line.strip():
            tasks.append(json.loads(line))
    return tasks


def plan(tasks: list[dict], arms: list[str], trials_per_task: int) -> list[dict]:
    planned = []
    for arm in arms:
        for task in tasks:
            for k in range(trials_per_task):
                planned.append(
                    {
                        "id": f"{arm}-{task['id']}-{k}",
                        "arm": arm,
                        "task": task["id"],
                        "difficulty": task.get("difficulty", "unknown"),
                    }
                )
    return planned


def agent_env(settings: Settings, arm: Arm, trial_id: str) -> dict[str, str]:
    written = {
        "LLM_BASE_URL": settings.proxy_url if arm.via_proxy else settings.provider_url,
        "LLM_MODEL": arm.model,
        "SCOREBOARD_ARM": arm.name,
        "SCOREBOARD_TRIAL_ID": trial_id,
    }
    if arm.via_proxy:
        written["ROUTER_POLICY"] = settings.proxy_policy
    # keep the caller's credentials and PATH for the agent
    return {**written, **os.environ}


def run_trial(settings: Settings, agent_cmd: str, job_dir: Path, trial: dict) -> int:
    arm = settings.arms[trial["arm"]]
    trial_dir = job_dir / "trials" / trial["id"]
    trial_dir.mkdir(parents=True, exist_ok=True)
    cmd = shlex.split(agent_cmd) + ["--task", trial["task"], "--out", str(trial_dir)]
    try:
        done = subprocess.run(
            cmd,
            env=agent_env(settings, arm, trial["id"]),
            cwd=trial_dir,
            timeout=settings.agent_timeout_s,
            capture_output=True,
            text=True,
        )
    except subprocess.TimeoutExpired:
        log.warning("trial %s timed out", trial["id"])
        return -1
    (trial_dir / "agent.log").write_text(done.stdout + done.stderr)
    if done.returncode != 0:
        log.warning("trial %s: agent exited %s", trial["id"], done.returncode)
    return done.returncode


def launch(
    settings: Settings,
    tasks_path: Path,
    job_dir: Path,
    arms: list[str],
    trials_per_task: int = 1,
    agent_cmd: str | None = None,
) -> Path:
    job_dir.mkdir(parents=True, exist_ok=True)
    tasks = load_tasks(tasks_path)
    trials = plan(tasks, arms, trials_per_task)
    job = {
        "job_id": job_dir.name or uuid.uuid4().hex[:8],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task_set": tasks_path.name,
        "arms": {name: vars(settings.arms[name]) for name in arms},
        "trials": trials,
    }
    (job_dir / "job.json").write_text(json.dumps(job, indent=2))
    cmd = agent_cmd or settings.agent_command
    log.info("launching %d trials (%s) with %s", len(trials), ", ".join(arms), cmd)
    with ThreadPoolExecutor(max_workers=settings.workers) as pool:
        codes = list(pool.map(lambda t: run_trial(settings, cmd, job_dir, t), trials))
    failed = sum(1 for c in codes if c != 0)
    log.info("launch finished: %d trials, %d agent errors", len(trials), failed)
    return job_dir
