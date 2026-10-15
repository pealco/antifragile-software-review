"""Delete stale scratch output from local experiments. Development machines only.

trainkit writes throwaway debugging output to ./scratch when run with --debug. This removes
scratch directories older than a week.
"""

import shutil
import sys
import time
from pathlib import Path

SCRATCH = Path(__file__).resolve().parents[1] / "scratch"
MAX_AGE = 7 * 24 * 3600

if not SCRATCH.is_dir():
    sys.exit(0)

now = time.time()
for entry in SCRATCH.iterdir():
    if entry.is_dir() and now - entry.stat().st_mtime > MAX_AGE:
        shutil.rmtree(entry, ignore_errors=True)
        print(f"removed {entry}")
