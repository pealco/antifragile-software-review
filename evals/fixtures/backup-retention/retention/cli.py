import argparse
import logging
import sys
from datetime import date
from pathlib import Path

from retention.policy import Backup
from retention.prune import Store, prune


class DirectoryStore(Store):
    """Backups are files named <name>.dump with the backup date in their modification time."""

    def __init__(self, root: Path):
        self.root = root

    def list_backups(self) -> list[Backup]:
        out = []
        for path in sorted(self.root.glob("*.dump")):
            taken = date.fromtimestamp(path.stat().st_mtime)
            out.append(Backup(path.stem, taken))
        return out

    def delete(self, name: str) -> None:
        (self.root / f"{name}.dump").unlink()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path("/var/backups/db"))
    ap.add_argument("--today", type=date.fromisoformat, default=date.today())
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    for name in prune(DirectoryStore(args.root), args.today, dry_run=args.dry_run):
        print(("would delete " if args.dry_run else "deleted ") + name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
