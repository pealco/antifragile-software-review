import json
import logging
import os
import tempfile
from pathlib import Path

log = logging.getLogger(__name__)


def write_summary(summary: dict, path: Path) -> None:
    # Written to a temp file and renamed, so a reader never sees half a summary.
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".summary-", suffix=".json")
    with os.fdopen(fd, "w") as f:
        json.dump(summary, f, indent=2, sort_keys=True)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def format_message(summary: dict) -> str:
    lines = [f"*Nightly eval {summary['job_id']}* ({summary['task_set']})"]
    for name, arm in sorted(summary["arms"].items()):
        rate = "n/a" if arm["pass_rate"] is None else f"{arm['pass_rate']:.1%}"
        lines.append(
            f"- {name}: {rate} ({arm['passed']}/{arm['trials']}), ${arm['cost_usd']:.2f}, "
            f"{arm['input_tokens'] + arm['output_tokens']:,} tokens"
        )
    return "\n".join(lines)


def post_summary(summary: dict, webhook_url: str | None) -> bool:
    if not webhook_url:
        log.info("no webhook configured, not posting")
        return False
    import requests

    try:
        resp = requests.post(webhook_url, json={"text": format_message(summary)}, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as exc:
        # summary.json is already written; a failed post only loses the chat message
        log.error("posting summary failed: %s", exc)
        return False
    return True
