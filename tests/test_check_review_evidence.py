from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts" / "check_review_evidence.py"


def check(review: str, repo_files: dict[str, str]) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        for name, text in repo_files.items():
            (repo / name).parent.mkdir(parents=True, exist_ok=True)
            (repo / name).write_text(text, encoding="utf-8")
        review_path = Path(tmp) / "review.md"
        review_path.write_text(review, encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(CHECKER), str(review_path), "--root", str(repo)],
            capture_output=True,
            text=True,
            check=False,
        )


class ReviewEvidenceTest(unittest.TestCase):
    def test_existing_file_and_line_pass(self) -> None:
        result = check("- Evidence: `app/a.py:2`", {"app/a.py": "x\ny\n"})
        self.assertEqual(0, result.returncode, result.stdout)

    def test_missing_file_fails(self) -> None:
        result = check("- Evidence: `app/missing.py:1`", {"app/a.py": "x\n"})
        self.assertEqual(1, result.returncode)
        self.assertIn("file not found", result.stdout)

    def test_line_past_end_of_file_fails(self) -> None:
        result = check("- Evidence: `app/a.py:9`", {"app/a.py": "x\ny\n"})
        self.assertEqual(1, result.returncode)
        self.assertIn("past the end", result.stdout)

    def test_path_outside_repo_fails(self) -> None:
        result = check("- Evidence: `../review.md`", {"app/a.py": "x\n"})
        self.assertEqual(1, result.returncode)
        self.assertIn("outside the repository", result.stdout)

    def test_code_names_and_other_evidence_labels_are_ignored(self) -> None:
        review = (
            "- Evidence: `app/a.py` calls `requests.post`.\n"
            "- Evidence quality: `docs/not-checked.md`\n"
        )
        result = check(review, {"app/a.py": "x\n"})
        self.assertEqual(0, result.returncode, result.stdout)
        self.assertIn("1/1", result.stdout)

    def test_bold_label_and_line_lists_are_checked(self) -> None:
        ok = check("- **Evidence:** `app/a.py:1,2-3`", {"app/a.py": "x\ny\nz\n"})
        self.assertEqual(0, ok.returncode, ok.stdout)
        bad = check("- **Evidence:** `app/a.py:1,2-9`", {"app/a.py": "x\ny\nz\n"})
        self.assertEqual(1, bad.returncode)
        self.assertIn("past the end", bad.stdout)

    def test_missing_file_passes_when_the_line_says_it_is_missing(self) -> None:
        ok = check(
            "- Evidence: `scripts/rollback.sh` does not exist.", {"app/a.py": "x\n"}
        )
        self.assertEqual(0, ok.returncode, ok.stdout)
        bad = check(
            "- Evidence: `scripts/rollback.sh` is called by deploy.",
            {"app/a.py": "x\n"},
        )
        self.assertEqual(1, bad.returncode)

    def test_basename_only_cite_gets_a_path_hint(self) -> None:
        result = check(
            "- Evidence: `deploy.yml:1`", {".github/workflows/deploy.yml": "x\n"}
        )
        self.assertEqual(1, result.returncode)
        self.assertIn("did you mean .github/workflows/deploy.yml", result.stdout)

    def test_review_can_be_read_from_stdin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "a.py").write_text("x\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(CHECKER), "-", "--root", tmp],
                input="- Evidence: `a.py:1`\n",
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(0, result.returncode, result.stdout)

    def test_review_without_cites_fails(self) -> None:
        result = check("No findings.", {"app/a.py": "x\n"})
        self.assertEqual(1, result.returncode)


if __name__ == "__main__":
    unittest.main()
