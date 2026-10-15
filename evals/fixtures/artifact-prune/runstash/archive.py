"""Build the run tarball that push uploads."""

from __future__ import annotations

import os
import tarfile
import tempfile
from pathlib import Path


def make_archive(run_dir: Path, staging: Path) -> Path:
    """Write staging/<run>.tar.gz. The tarball is written to a temporary file and renamed into
    place only after it is complete and flushed, so an interrupted push never leaves a truncated
    archive under the final name."""
    staging.mkdir(parents=True, exist_ok=True)
    final = staging / f"{run_dir.name}.tar.gz"
    fd, tmp = tempfile.mkstemp(dir=staging, prefix=f".{run_dir.name}.", suffix=".partial")
    try:
        with os.fdopen(fd, "wb") as raw:
            with tarfile.open(fileobj=raw, mode="w:gz") as tar:
                tar.add(run_dir, arcname=run_dir.name)
            raw.flush()
            os.fsync(raw.fileno())
        os.replace(tmp, final)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return final
