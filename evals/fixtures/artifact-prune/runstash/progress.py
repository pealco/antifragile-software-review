"""Upload progress on stderr, as an upload_file Callback."""

from __future__ import annotations

import sys
import threading


class Progress:
    def __init__(self, label: str, total: int):
        self.label = label
        self.total = max(total, 1)
        self.seen = 0
        self._lock = threading.Lock()

    def __call__(self, nbytes: int) -> None:
        try:
            with self._lock:
                self.seen += nbytes
                if sys.stderr.isatty():
                    pct = 100 * self.seen / self.total
                    sys.stderr.write(f"\r{self.label}: {pct:5.1f}%")
                    if self.seen >= self.total:
                        sys.stderr.write("\n")
                    sys.stderr.flush()
        except Exception:
            pass
