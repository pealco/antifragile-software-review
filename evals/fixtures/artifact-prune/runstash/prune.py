"""runstash prune: free local disk by deleting runs that already have a remote copy."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from runstash import store
from runstash.config import Config

log = logging.getLogger(__name__)


def local_runs(cfg: Config) -> list[Path]:
    if not cfg.runs_dir.is_dir():
        return []
    return sorted(p for p in cfg.runs_dir.iterdir() if (p / "run.json").is_file())


def candidates(cfg: Config, runs: list[Path]) -> list[Path]:
    """The local runs that are already in the bucket."""
    remote = store.remote_runs(cfg)
    return [run for run in runs if run.name in remote]


def disk_usage(path: Path) -> int:
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def prune(cfg: Config, *, dry_run: bool = False, force: bool = False) -> int:
    runs = candidates(cfg, local_runs(cfg))
    if not runs:
        print("nothing to prune")
        return 0
    sizes = {run: disk_usage(run) for run in runs}
    total = sum(sizes.values())
    verb = "would delete" if dry_run else "delete"
    for run in runs:
        print(f"{verb} {run.name} ({sizes[run] / 1e9:.2f} GB)")
    if dry_run:
        print(f"dry run: {len(runs)} runs, {total / 1e9:.2f} GB would be freed")
        return 0
    if not force:
        answer = input(f"Delete {len(runs)} local runs ({total / 1e9:.2f} GB)? [y/N] ")
        if answer.strip().lower() != "y":
            print("aborted")
            return 1
    for run in runs:
        shutil.rmtree(run)
        log.info("deleted %s", run)
    print(f"freed {total / 1e9:.2f} GB")
    return 0
