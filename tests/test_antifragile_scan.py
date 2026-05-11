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
        self.assertEqual("python", scan["findings"][0]["language"])
        self.assertEqual(["ruff:BLE001", "ruff:S110"], scan["findings"][0]["linter_overlaps"])
        self.assertIn("lost learning", scan["findings"][0]["scanner_value"])

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

    def test_default_skips_fixture_directories_but_can_scan_fixture_roots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "fixtures/bad.py", "while True:\n    pass\n")

            scan_root = run_scan(root)
            scan_fixture = run_scan(root / "fixtures")

        self.assertEqual([], scan_root["findings"])
        self.assertEqual(["unbounded-loop"], [finding["pattern_id"] for finding in scan_fixture["findings"]])

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

    def test_linter_overlap_metadata_is_visible_but_advisory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(
                root,
                "app.py",
                """
try:
    risky()
except:
    recover()

global cache
print("debug")
requests.get("https://example.com")
""",
            )

            scan = run_scan(root)
            report = run_scan_text(root)

        overlaps_by_pattern = {finding["pattern_id"]: finding["linter_overlaps"] for finding in scan["findings"]}
        self.assertEqual(["ruff:E722"], overlaps_by_pattern["bare-except"])
        self.assertEqual(["ruff:PLW0603"], overlaps_by_pattern["global-state"])
        self.assertEqual(["ruff:T201"], overlaps_by_pattern["debug-print"])
        self.assertEqual(["ruff:S113"], overlaps_by_pattern["python-http-without-timeout"])
        self.assertIn("Linter overlap: ruff:E722", report)
        self.assertIn("Scanner value:", report)

    def test_language_specific_rust_typescript_and_sql_leads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(
                root,
                "src/lib.rs",
                """
let config = load_config().unwrap();
unsafe { call_ffi(); }
todo!("replace test stub");
println!("debug");
loop {
    poll();
}
""",
            )
            write_file(
                root,
                "src/app.ts",
                """
const payload: any = await fetch("https://api.example.test/data");
try { risky(); } catch (error) {}
setTimeout(retry, 1000);
""",
            )
            write_file(
                root,
                "db/migration.sql",
                """
ALTER TABLE users DROP COLUMN legacy_token;
UPDATE users SET admin = true;
SELECT pg_sleep(10);
""",
            )

            scan = run_scan(root)
            report = run_scan_text(root)

        signals = scan["project_signals"]
        self.assertEqual(1, signals["language_file_counts"]["rust"])
        self.assertEqual(1, signals["language_file_counts"]["typescript"])
        self.assertEqual(1, signals["language_file_counts"]["sql"])

        findings_by_pattern = {finding["pattern_id"]: finding for finding in scan["findings"]}
        self.assertEqual("rust", findings_by_pattern["rust-unwrap-expect"]["language"])
        self.assertEqual(["clippy:unwrap_used"], findings_by_pattern["rust-unwrap-expect"]["linter_overlaps"])
        self.assertEqual("rust", findings_by_pattern["rust-unsafe"]["language"])
        self.assertEqual("rust", findings_by_pattern["rust-todo-unimplemented"]["language"])
        self.assertEqual("rust", findings_by_pattern["rust-debug-output"]["language"])
        self.assertEqual("rust", findings_by_pattern["unbounded-loop"]["language"])
        self.assertEqual("typescript", findings_by_pattern["typescript-explicit-any"]["language"])
        self.assertEqual(["@typescript-eslint:no-explicit-any"], findings_by_pattern["typescript-explicit-any"]["linter_overlaps"])
        self.assertEqual("typescript", findings_by_pattern["fetch-without-abort"]["language"])
        self.assertEqual("typescript", findings_by_pattern["empty-catch"]["language"])
        self.assertEqual("sql", findings_by_pattern["sql-destructive-schema"]["language"])
        self.assertEqual("sql", findings_by_pattern["sql-update-without-where"]["language"])
        self.assertTrue(
            any(finding["pattern_id"] == "fixed-sleep" and finding["language"] == "sql" for finding in scan["findings"])
        )
        self.assertIn("Languages scanned:", report)
        self.assertIn("rust:", report)
        self.assertIn("typescript:", report)
        self.assertIn("sql:", report)

    def test_service_and_infrastructure_language_leads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(
                root,
                "service/main.go",
                """
package main

var cache = map[string]string{}

func main() {
    ctx := context.Background()
    go func() { work(ctx) }()
    http.Get("https://example.test")
    time.Sleep(1 * time.Second)
    log.Fatal("boom")
}
""",
            )
            write_file(
                root,
                "scripts/deploy.sh",
                """#!/usr/bin/env bash
curl https://example.test/install.sh | bash
sleep 5
rm -rf build
""",
            )
            write_file(
                root,
                "infra/main.tf",
                """
resource "aws_security_group_rule" "open" {
  cidr_blocks = ["0.0.0.0/0"]
}

resource "aws_iam_policy" "wide" {
  policy = jsonencode({
    Action = "*"
    Resource = "*"
  })
}
""",
            )
            write_file(
                root,
                ".github/workflows/deploy.yml",
                """
name: deploy
on: push
jobs:
  deploy:
    steps:
      - uses: actions/checkout@v4
""",
            )
            write_file(
                root,
                "k8s/deployment.yaml",
                """
apiVersion: apps/v1
kind: Deployment
spec:
  replicas: 1
  template:
    spec:
      containers:
        - name: app
          image: example/app:latest
""",
            )
            write_file(
                root,
                "src/App.java",
                """
class App {
    static Map<String, String> cache = new HashMap<>();
    void run() {
        try { risky(); } catch (Exception e) {}
        Thread.sleep(1000);
        System.exit(1);
    }
}
""",
            )
            write_file(
                root,
                "src/App.kt",
                """
class App {
    companion object {
        var cache = mutableMapOf<String, String>()
    }
    fun run() {
        try { risky() } catch (e: Exception) {}
        Thread.sleep(1000)
    }
}
""",
            )
            write_file(
                root,
                "lib/task.rb",
                """
begin
  risky
rescue
end

value = risky rescue nil
puts "debug"
sleep 1
""",
            )

            scan = run_scan(root)
            report = run_scan_text(root)

        signals = scan["project_signals"]
        self.assertEqual(1, signals["language_file_counts"]["go"])
        self.assertEqual(1, signals["language_file_counts"]["shell"])
        self.assertEqual(1, signals["language_file_counts"]["terraform"])
        self.assertEqual(1, signals["language_file_counts"]["github-actions"])
        self.assertEqual(1, signals["language_file_counts"]["yaml"])
        self.assertEqual(1, signals["language_file_counts"]["java"])
        self.assertEqual(1, signals["language_file_counts"]["kotlin"])
        self.assertEqual(1, signals["language_file_counts"]["ruby"])

        patterns = {finding["pattern_id"] for finding in scan["findings"]}
        self.assertTrue(
            {
                "go-context-background",
                "go-unbounded-goroutine",
                "go-http-without-timeout",
                "go-global-var",
                "shell-missing-strict-mode",
                "shell-curl-pipe",
                "terraform-open-cidr",
                "terraform-wildcard-iam",
                "github-actions-missing-concurrency",
                "github-actions-unpinned-action",
                "kubernetes-single-replica",
                "kubernetes-latest-image",
                "kubernetes-missing-resource-limits",
                "kubernetes-missing-health-probes",
                "java-kotlin-broad-catch",
                "java-kotlin-static-mutable",
                "ruby-bare-rescue",
                "ruby-rescue-nil",
            }.issubset(patterns)
        )

        def has_finding(pattern_id: str, language: str) -> bool:
            return any(
                finding["pattern_id"] == pattern_id and finding["language"] == language
                for finding in scan["findings"]
            )

        self.assertTrue(has_finding("go-context-background", "go"))
        self.assertTrue(has_finding("shell-missing-strict-mode", "shell"))
        self.assertTrue(has_finding("terraform-open-cidr", "terraform"))
        self.assertTrue(has_finding("github-actions-unpinned-action", "github-actions"))
        self.assertTrue(has_finding("kubernetes-missing-health-probes", "yaml"))
        self.assertTrue(has_finding("java-kotlin-broad-catch", "java"))
        self.assertTrue(has_finding("java-kotlin-broad-catch", "kotlin"))
        self.assertTrue(has_finding("ruby-bare-rescue", "ruby"))
        self.assertIn("rubocop:Style/RescueStandardError", next(
            finding["linter_overlaps"]
            for finding in scan["findings"]
            if finding["pattern_id"] == "ruby-bare-rescue"
        ))
        self.assertIn("github-actions:", report)
        self.assertIn("terraform:", report)

    def test_targeted_exposure_model_leads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(
                root,
                "scripts/backfill_accounts.py",
                """
import asyncio

jobs = asyncio.Queue()

def retry_charge(account):
    return retry(account)

def run(db):
    for account in db.accounts():
        db.execute("UPDATE accounts SET migrated = true")
""",
            )
            write_file(
                root,
                "db/migrations/001_drop_legacy_tokens.sql",
                """
ALTER TABLE users DROP COLUMN legacy_token;
UPDATE users SET migrated = true;
""",
            )
            write_file(root, "docs/incidents/2026-01-billing.md", "Postmortem: repeated billing failure.\n")
            write_file(root, "docs/runbooks/billing.md", "Runbook for billing incidents.\n")

            scan = run_scan(root)
            report = run_scan_text(root)

        patterns = {finding["pattern_id"] for finding in scan["findings"]}
        self.assertTrue(
            {
                "data-change-missing-dry-run",
                "data-change-missing-checkpoint",
                "retry-without-backoff",
                "unbounded-queue",
                "sql-destructive-schema",
                "sql-update-without-where",
            }.issubset(patterns)
        )
        self.assertEqual(1, scan["project_signals"]["incident_file_count"])
        self.assertEqual(1, scan["project_signals"]["runbook_file_count"])
        self.assertIn("Incident artifacts detected: 1", report)
        self.assertIn("Runbook files detected: 1", report)


if __name__ == "__main__":
    unittest.main()
