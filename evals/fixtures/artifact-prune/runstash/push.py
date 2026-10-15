"""runstash push: archive a local run and upload it."""

from __future__ import annotations

import logging

from runstash import store
from runstash.archive import make_archive
from runstash.config import Config
from runstash.progress import Progress

log = logging.getLogger(__name__)


def push(cfg: Config, run: str) -> None:
    run_dir = cfg.runs_dir / run
    if not (run_dir / "run.json").is_file():
        raise SystemExit(f"runstash: {run_dir} is not a run directory (no run.json)")
    staging = cfg.runs_dir.parent / ".runstash" / "staging"
    archive = make_archive(run_dir, staging)
    try:
        size = archive.stat().st_size
        store.upload(cfg, run, archive, Progress(run, size))
        store.verify(cfg, run, size)
    finally:
        archive.unlink(missing_ok=True)
    log.info("pushed %s to s3://%s/%s (%.1f MB)", run, cfg.bucket, store.key_for(cfg, run), size / 1e6)
