#!/usr/bin/env python3
"""Run lightweight executable checks for antifragility skill scenarios."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCANNER = ROOT / "scripts" / "antifragile_scan.py"
SCENARIOS = ROOT / "references" / "evaluation-scenarios.md"
FIXTURES = ROOT / "evals" / "fixtures"

REQUIRED_REVIEW_MARKERS = (
    "## Antifragility Thesis",
    "## System Map",
    "## Critical Flow Trace",
    "Exposure score:",
    "Stress response curve:",
    "Gain mechanism:",
    "Missing evidence",
    "Cheapest observation",
)

EVAL_CASES = (
    {
        "title": "Critical-Flow Exposure Trace",
        "fixture": "critical-flow-service",
        "expected_patterns": {
            "python-http-without-timeout",
            "silent-exception",
            "github-actions-missing-concurrency",
        },
        "expected_incident_files": 0,
        "expected_runbook_files": 1,
    },
    {
        "title": "Data-Ruin And Incident-Learning Review",
        "fixture": "data-ruin-incident-learning",
        "expected_patterns": {
            "data-change-missing-dry-run",
            "data-change-missing-checkpoint",
            "sql-destructive-schema",
            "sql-update-without-where",
        },
        "expected_incident_files": 1,
        "expected_runbook_files": 1,
    },
    {
        "title": "Optionality Without Premature Abstraction",
        "fixture": "optionality-premature-abstraction",
        "expected_patterns": set(),
        "expected_incident_files": 0,
        "expected_runbook_files": 0,
        "max_findings": 0,
    },
)


def fail(message: str) -> None:
    raise SystemExit(f"error: {message}")


def parse_scenario_titles() -> set[str]:
    text = SCENARIOS.read_text(encoding="utf-8")
    for block in re.findall(r"```json\n(.*?)\n```", text, re.S):
        json.loads(block)
    return set(re.findall(r"^## Scenario \d+: (.+)$", text, re.M))


def run_scan(fixture: Path) -> dict[str, object]:
    result = subprocess.run(
        [sys.executable, str(SCANNER), str(fixture), "--json"],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def validate_fixture_case(case: dict[str, object], scenario_titles: set[str]) -> None:
    title = str(case["title"])
    if title not in scenario_titles:
        fail(f"scenario heading missing from {SCENARIOS}: {title}")

    fixture = FIXTURES / str(case["fixture"])
    if not fixture.is_dir():
        fail(f"fixture directory missing: {fixture}")

    scan = run_scan(fixture)
    patterns = {finding["pattern_id"] for finding in scan["findings"]}
    expected_patterns = set(case["expected_patterns"])
    missing_patterns = sorted(expected_patterns - patterns)
    if missing_patterns:
        fail(f"{title}: missing scanner patterns: {', '.join(missing_patterns)}")

    max_findings = case.get("max_findings")
    if max_findings is not None and len(scan["findings"]) > int(max_findings):
        fail(f"{title}: expected at most {max_findings} findings, got {len(scan['findings'])}")

    signals = scan["project_signals"]
    for key in ("incident_file_count", "runbook_file_count"):
        expected_key = f"expected_{key.removesuffix('_count')}s"
        if expected_key in case and signals[key] != case[expected_key]:
            fail(f"{title}: expected {key}={case[expected_key]}, got {signals[key]}")


def validate_review_output(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    missing = [marker for marker in REQUIRED_REVIEW_MARKERS if marker not in text]
    if missing:
        fail(f"review output is missing required marker(s): {', '.join(missing)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--review-output",
        type=Path,
        help="Optional generated review markdown to check for required scorecard markers.",
    )
    args = parser.parse_args()

    scenario_titles = parse_scenario_titles()
    for case in EVAL_CASES:
        validate_fixture_case(case, scenario_titles)

    if args.review_output:
        validate_review_output(args.review_output)

    sys.stdout.write(f"validated {len(EVAL_CASES)} executable scenario fixture(s)\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
