import argparse
import logging
import os
import sys
from datetime import date
from pathlib import Path

from scoreboard import aggregate, config, pricing, report
from scoreboard.launch import launch


def summarize(job_dir: Path, settings: config.Settings, post: bool) -> dict:
    catalog = pricing.load_catalog(settings.prices_path)
    summary = aggregate.summarize_job(job_dir, catalog)
    report.write_summary(summary, job_dir / "summary.json")
    print(report.format_message(summary))
    if post:
        report.post_summary(summary, os.environ.get("SCOREBOARD_WEBHOOK_URL"))
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="scoreboard")
    sub = parser.add_subparsers(dest="command", required=True)

    def launch_args(p):
        p.add_argument("--tasks", type=Path, required=True)
        p.add_argument("--job-dir", type=Path, default=None)
        p.add_argument("--arms", default="routed,fixed")
        p.add_argument("--trials", type=int, default=1, help="trials per task per arm")
        p.add_argument("--agent-cmd", default=None)

    launch_args(sub.add_parser("launch", help="run every planned trial"))
    s = sub.add_parser("summarize", help="aggregate a job directory")
    s.add_argument("job_dir", type=Path)
    s.add_argument("--post", action="store_true")
    r = sub.add_parser("run", help="launch, then summarize")
    launch_args(r)
    r.add_argument("--post", action="store_true")

    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    settings = config.load()

    if args.command in ("launch", "run"):
        job_dir = args.job_dir or Path("jobs") / date.today().isoformat()
        arms = [a.strip() for a in args.arms.split(",") if a.strip()]
        unknown = [a for a in arms if a not in settings.arms]
        if unknown:
            parser.error(f"unknown arm(s): {', '.join(unknown)}")
        launch(settings, args.tasks, job_dir, arms, args.trials, args.agent_cmd)
        if args.command == "run":
            summarize(job_dir, settings, args.post)
        return 0
    summarize(args.job_dir, settings, args.post)
    return 0


if __name__ == "__main__":
    sys.exit(main())
