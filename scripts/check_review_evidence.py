#!/usr/bin/env python3
"""Check that every file cited on an `Evidence:` line of a review exists in the repository.

Usage: check_review_evidence.py REVIEW.md|- [--root REPO] [--any-line]   (- reads the review from stdin)

With --any-line, backticked cites on every line are checked, not only on `Evidence:` lines. The
evals use it so that a review in any format gets credit for accurate cites.

Cites look like `path/file.ext`, `path/file.ext:123`, `path/file.ext:123-130`, or `path/file.ext:5,7-10`. A cite fails
if the file is missing, resolves outside the repository, or the line is past the end of the file.
A missing file passes when its Evidence line says it is missing (for example "does not exist").
Exit code is 1 if any cite fails, or if the review has no checkable cites.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# "Evidence:" only. "Evidence quality:" and "Evidence confidence:" do not cite files.
EVIDENCE_LINE = re.compile(
    r"\bEvidence:(?:\*\*)?\s"
)  # also matches bold "**Evidence:**"
BACKTICKED = re.compile(r"`([^`\s]+)`")
CITE = re.compile(
    r"^(?P<path>[\w./@-]+?)(?::(?P<lines>\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*))?$"
)
# A cite of a missing file is fine when the line says the file is missing: absence is evidence too.
ABSENCE = re.compile(
    r"\b(missing|does not exist|doesn't exist|absent|not present|no such|not found|not in the repo(?:sitory)?|never)\b",
    re.IGNORECASE,
)
# A bare name like `requests.post` is code, not a path. Require a slash or a source extension.
SOURCE_EXTENSIONS = {
    "py", "ts", "tsx", "js", "jsx", "go", "rs", "java", "kt", "rb", "sh", "sql",
    "tf", "yaml", "yml", "json", "toml", "md", "cfg", "ini", "txt",
}  # fmt: skip


def cites(review: str, any_line: bool = False) -> list[tuple[str, int | None, bool]]:
    found = []
    for line in review.splitlines():
        if not any_line and not EVIDENCE_LINE.search(line):
            continue
        for token in BACKTICKED.findall(line):
            match = CITE.match(token)
            if not match:
                continue
            path = match["path"]
            if "/" not in path and path.rsplit(".", 1)[-1] not in SOURCE_EXTENSIONS:
                continue
            # "5,7-10,12" cites several ranges; the last line cited is the one that can overrun.
            lines = [int(n) for n in re.findall(r"\d+", match["lines"] or "")]
            absent = bool(
                ABSENCE.search(BACKTICKED.sub("", line))
            )  # words in a path do not count
            found.append((path, max(lines) if lines else None, absent))
    return found


def problem(root: Path, path: str, line: int | None, absence_claim: bool) -> str | None:
    target = (root / path).resolve()
    if root not in target.parents:
        return "outside the repository"
    if not target.is_file():
        if absence_claim:
            return None
        matches = [
            p
            for p in root.rglob(Path(path).name)
            if p.is_file() and ".git" not in p.parts
        ]
        hint = (
            f"; did you mean {matches[0].relative_to(root)}?"
            if len(matches) == 1
            else ""
        )
        return "file not found" + hint
    if line is not None:
        count = len(target.read_text(encoding="utf-8", errors="replace").splitlines())
        if line < 1 or line > count:
            return f"line {line} is past the end of the file ({count} lines)"
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("review", help="review markdown file, or - for stdin")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="repository root")
    parser.add_argument(
        "--any-line",
        action="store_true",
        help="check cites on every line, not only Evidence: lines",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    text = (
        sys.stdin.read()
        if args.review == "-"
        else Path(args.review).read_text(encoding="utf-8")
    )
    found = cites(text, any_line=args.any_line)
    if not found:
        where = "" if args.any_line else " on `Evidence:` lines"
        sys.stdout.write(f"error: no cites with file paths found{where}\n")
        return 1
    failures = 0
    for path, line, absence_claim in found:
        why = problem(root, path, line, absence_claim)
        if why:
            failures += 1
            sys.stdout.write(f"FAIL {path}{f':{line}' if line else ''}: {why}\n")
    sys.stdout.write(f"{len(found) - failures}/{len(found)} evidence cites resolve\n")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
