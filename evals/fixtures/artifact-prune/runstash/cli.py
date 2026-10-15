"""Command line entry point."""

from __future__ import annotations

import argparse
import logging
import os

from botocore.exceptions import ClientError

from runstash import config, store
from runstash.prune import local_runs, prune
from runstash.push import push

log = logging.getLogger("runstash")


def list_runs(cfg: config.Config) -> int:
    local = {p.name for p in local_runs(cfg)}
    remote = store.remote_runs(cfg)
    print(f"{'RUN':40} {'LOCAL':6} {'REMOTE':6} {'REMOTE SIZE':>12}")
    for name in sorted(local | set(remote)):
        size = f"{remote[name]['Size'] / 1e9:.2f} GB" if name in remote else ""
        print(f"{name:40} {'yes' if name in local else '':6} {'yes' if name in remote else '':6} {size:>12}")
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=os.environ.get("RUNSTASH_LOG", "INFO"), format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(prog="runstash", description="Archive experiment runs and prune local copies.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("push", help="archive runs and upload them to the bucket")
    p.add_argument("runs", nargs="+", metavar="RUN")

    p = sub.add_parser("prune", help="delete local runs that already have a remote copy")
    p.add_argument("--dry-run", action="store_true", help="list what would be deleted and exit")
    p.add_argument("-f", "--force", action="store_true", help="do not ask for confirmation")

    sub.add_parser("list", help="show local and remote runs")

    args = parser.parse_args(argv)
    if args.command == "push":
        cfg = config.load_project()
        failed = []
        for run in args.runs:
            try:
                push(cfg, run)
            except (ClientError, store.UploadMismatch, OSError) as exc:
                log.error("push %s failed: %s", run, exc)
                failed.append(run)
        return 1 if failed else 0
    if args.command == "prune":
        return prune(config.load(), dry_run=args.dry_run, force=args.force)
    return list_runs(config.load())


if __name__ == "__main__":
    raise SystemExit(main())
