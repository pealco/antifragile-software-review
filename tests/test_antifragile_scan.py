from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCANNER = ROOT / "scripts" / "antifragile_scan.py"


def write_file(root: Path, relative_path: str, text: str) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_bytes(root: Path, relative_path: str, data: bytes) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def run_scan(root: Path, *extra_args: str) -> dict[str, object]:
    result = subprocess.run(
        [sys.executable, str(SCANNER), str(root), "--json", *extra_args],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def run_scan_text(root: Path, *extra_args: str) -> str:
    result = subprocess.run(
        [sys.executable, str(SCANNER), str(root), *extra_args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


class AntifragileScanTest(unittest.TestCase):
    def test_detects_code_findings_without_turning_docs_into_findings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(
                root,
                "app.py",
                """
try:
    risky()
except Exception: pass
""",
            )
            write_file(root, "README.md", "This should never happen in normal operation.\n")

            scan = run_scan(root)

        self.assertEqual(["app.py"], [finding["path"] for finding in scan["findings"]])
        self.assertEqual("silent-exception", scan["findings"][0]["pattern_id"])
        self.assertEqual("code", scan["findings"][0]["source_kind"])

    def test_inline_suppression_can_ignore_one_pattern_or_a_whole_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(
                root,
                "worker.py",
                """
try:
    risky()
except Exception: pass  # antifragile-scan: ignore[silent-exception]

while True:  # antifragile-scan: ignore
    break
""",
            )

            scan = run_scan(root)

        self.assertEqual([], scan["findings"])

    def test_presence_terms_include_source_provenance_and_locations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "docs/runbook.md", "Rollback playbook for deploy recovery.\n")
            write_file(root, ".github/workflows/deploy.yml", "name: canary deploy\non: push\n")
            write_file(root, "app.py", 'trace_id = "abc123"\n')

            scan = run_scan(root)

        signals = scan["project_signals"]
        self.assertEqual(1, signals["term_counts_by_source"]["rollback"]["docs"])
        self.assertEqual(1, signals["term_counts_by_source"]["canary"]["config"])
        self.assertEqual(1, signals["term_counts_by_source"]["observability"]["code"])
        self.assertEqual("docs/runbook.md", signals["term_locations"]["rollback"][0]["path"])
        self.assertEqual("docs", signals["term_locations"]["rollback"][0]["source_kind"])

    def test_exclude_glob_skips_matching_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "bad.py", "while True:\n    pass\n")

            scan = run_scan(root, "--exclude", "bad.py")

        self.assertEqual([], scan["findings"])
        self.assertEqual([{"path": "bad.py", "reason": "excluded:bad.py"}], scan["skipped_files"])

    def test_self_scan_skips_the_scanner_implementation(self) -> None:
        scan = run_scan(ROOT)

        self.assertIn(
            {"path": "scripts/antifragile_scan.py", "reason": "self-scanner"},
            scan["skipped_files"],
        )
        self.assertNotIn("scripts/antifragile_scan.py", {finding["path"] for finding in scan["findings"]})

    def test_reports_skipped_files_that_reduce_scan_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "large.py", "print('large file with enough bytes to cross the test cap')\n")
            write_bytes(root, "binary.py", b"x\0\n")
            try:
                (root / "broken.py").symlink_to("missing.py")
            except OSError as exc:
                self.skipTest(f"symlink creation unavailable: {exc}")

            scan = run_scan(root, "--max-file-bytes", "8")
            report = run_scan_text(root, "--max-file-bytes", "8")

        skipped = {(item["path"], item["reason"]) for item in scan["skipped_files"]}
        self.assertIn(("large.py", "too-large"), skipped)
        self.assertIn(("binary.py", "binary"), skipped)
        self.assertIn(("broken.py", "stat-error"), skipped)
        self.assertIn("## Project Signals", report)
        self.assertIn("### Skipped File Samples", report)
        self.assertIn("`large.py`: too-large", report)

    def test_capped_patterns_report_omitted_match_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "a.py", "try:\n    risky()\nexcept Exception: pass\n")
            write_file(root, "b.py", "try:\n    risky()\nexcept Exception: pass\n")
            write_file(root, "c.py", "try:\n    risky()\nexcept Exception: pass\n")

            scan = run_scan(root, "--max-per-pattern", "2")
            report = run_scan_text(root, "--max-per-pattern", "2")

        self.assertEqual(["a.py", "b.py"], [finding["path"] for finding in scan["findings"]])
        self.assertEqual({"silent-exception": 1}, scan["finding_overflow"])
        self.assertIn("## Capped Finding Overflow", report)
        self.assertIn("`silent-exception`: 1 additional matches omitted", report)


if __name__ == "__main__":
    unittest.main()
