#!/usr/bin/env python3
"""Find functions whose logic no test depends on: stub each one out and see whether the suite
still passes.

A test is a control only if it fails when the code it guards is wrong. The cheapest wrong
version of a function is one with no logic at all: its body replaced by `return None`, and then
by `return True` (a truthy constant, which survives "is not None", "truthy" and "greater than 0"
assertions). If the whole suite still passes with either stub in place, nothing in the suite
depends on that function's behavior. The function is unprotected, whatever the coverage report
says. This is "extreme mutation" (Niedermayr et al. 2016; Vera-Perez et al. 2018, Descartes),
reduced to the standard library.

Usage:
  check_test_strength.py REPO [--tests CMD] [--include GLOB ...] [--max-functions N] [--format json]

Defaults: tests run with `python3 -m unittest discover -s tests` inside a temporary copy of REPO;
functions come from every *.py outside tests, migrations and generated files, except trivial
ones (a body of one `return`, `pass`, or a dunder). Exit code 1 if any function is unprotected,
2 if the suite does not pass unmutated (then nothing can be concluded).
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKIP_DIRS = {
    ".git", "__pycache__", "tests", "test", "migrations", "node_modules", ".venv", "venv", "build", "dist",
}  # fmt: skip
DEFAULT_TESTS = "python3 -m unittest discover -s tests"
STUBS = ("None", "True")

FunctionNode = ast.FunctionDef | ast.AsyncFunctionDef


def body_without_docstring(fn: FunctionNode) -> list[ast.stmt]:
    body = fn.body
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
    ):
        return body[1:]
    return body


def is_trivial(fn: FunctionNode) -> bool:
    if fn.name.startswith("__") and fn.name.endswith("__"):
        return True
    body = body_without_docstring(fn)
    if not body:
        return True
    if len(body) != 1:
        return False
    only = body[0]
    if isinstance(only, ast.Pass):
        return True
    return isinstance(only, ast.Return) and (
        only.value is None or isinstance(only.value, (ast.Constant, ast.Name))
    )


def functions(path: Path, source: str) -> list[FunctionNode]:
    tree = ast.parse(source, filename=str(path))
    return [
        n
        for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and not is_trivial(n)
    ]


def stubbed(source: str, fn: FunctionNode, value: str) -> str:
    """The module source with `fn`'s body replaced by `return <value>`, keeping its signature."""
    lines = source.splitlines(keepends=True)
    first = body_without_docstring(fn)[0]
    start, end = first.lineno - 1, fn.end_lineno or first.lineno
    indent = " " * first.col_offset
    return (
        "".join(lines[:start])
        + f"{indent}return {value}  # stubbed by check_test_strength\n"
        + "".join(lines[end:])
    )


def run_tests(repo: Path, command: str) -> bool:
    done = subprocess.run(
        command,
        shell=True,
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        timeout=600,
    )
    return done.returncode == 0


def targets(repo: Path, include: list[str]) -> list[Path]:
    out = []
    for path in sorted(repo.rglob("*.py")):
        rel = path.relative_to(repo)
        if (
            any(part in SKIP_DIRS for part in rel.parts)
            or rel.name.startswith("test_")
            or rel.name.endswith("_test.py")
        ):
            continue
        if include and not any(fnmatch.fnmatch(str(rel), g) for g in include):
            continue
        out.append(rel)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("repo", type=Path)
    ap.add_argument(
        "--tests", default=DEFAULT_TESTS, help="test command, run in a copy of the repo"
    )
    ap.add_argument(
        "--include",
        action="append",
        default=[],
        help="only files matching this glob (repeatable)",
    )
    ap.add_argument("--max-functions", type=int, default=200)
    ap.add_argument("--format", choices=["text", "json"], default="text")
    args = ap.parse_args(argv)

    with tempfile.TemporaryDirectory(prefix="test-strength-") as tmp:
        repo = Path(tmp) / "repo"
        shutil.copytree(
            args.repo,
            repo,
            ignore=shutil.ignore_patterns(
                ".git", "__pycache__", ".venv", "venv", "node_modules"
            ),
        )
        if not run_tests(repo, args.tests):
            print(
                "error: the test suite does not pass unmutated; nothing can be concluded",
                file=sys.stderr,
            )
            return 2
        results: list[dict] = []
        for rel in targets(repo, args.include):
            original = (repo / rel).read_text(encoding="utf-8")
            try:
                fns = functions(rel, original)
            except SyntaxError:
                continue
            for fn in fns:
                if len(results) >= args.max_functions:
                    break
                survived = None
                for value in STUBS:
                    (repo / rel).write_text(
                        stubbed(original, fn, value), encoding="utf-8"
                    )
                    try:
                        still_passes = run_tests(repo, args.tests)
                    finally:
                        (repo / rel).write_text(original, encoding="utf-8")
                    if still_passes:
                        survived = value
                        break
                results.append({"file": str(rel), "function": fn.name, "line": fn.lineno,
                                "unprotected": survived is not None, "stub": survived})  # fmt: skip

    unprotected = [r for r in results if r["unprotected"]]
    if args.format == "json":
        print(json.dumps({"checked": results, "unprotected": unprotected}, indent=2))
    else:
        for r in unprotected:
            print(
                f"UNPROTECTED {r['file']}:{r['line']} {r['function']}: the suite passes with its body replaced by `return {r['stub']}`"
            )
        print(
            f"{len(results) - len(unprotected)}/{len(results)} functions have a test that depends on their logic"
        )
    return 1 if unprotected else 0


if __name__ == "__main__":
    raise SystemExit(main())
