from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts" / "check_test_strength.py"

# `tax` has a real test; `discount` has a tautological one (expected computed by the subject);
# `label` has a test that only checks the result is not None; `noop` is trivial and skipped.
MODULE = """
def tax(cents, bps):
    return cents * bps // 10_000


def discount(cents, pct):
    return cents - cents * pct // 100


def label(order):
    return f"order-{order['id']}"


def noop():
    pass
"""

TESTS = """
import unittest
from app.money import tax, discount, label


class MoneyTest(unittest.TestCase):
    def test_tax_literal(self):
        self.assertEqual(100, tax(10_000, 100))

    def test_discount_tautology(self):
        self.assertEqual(discount(500, 10), discount(500, 10))

    def test_label_exists(self):
        self.assertIsNotNone(label({"id": 7}))
"""


def repo(tmp: str) -> Path:
    root = Path(tmp) / "repo"
    (root / "app").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / "app" / "__init__.py").write_text("", encoding="utf-8")
    (root / "app" / "money.py").write_text(textwrap.dedent(MODULE), encoding="utf-8")
    (root / "tests" / "__init__.py").write_text("", encoding="utf-8")
    (root / "tests" / "test_money.py").write_text(
        textwrap.dedent(TESTS), encoding="utf-8"
    )
    return root


def run(root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECKER), str(root), "--format", "json", *extra],
        capture_output=True, text=True, check=False,
    )  # fmt: skip


class TestStrengthTest(unittest.TestCase):
    def test_finds_functions_no_test_depends_on(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            done = run(repo(tmp))
        self.assertEqual(1, done.returncode, done.stderr)
        report = json.loads(done.stdout)
        self.assertEqual(
            ["tax", "discount", "label"], [r["function"] for r in report["checked"]]
        )  # noop is trivial
        self.assertEqual(
            ["discount", "label"], [r["function"] for r in report["unprotected"]]
        )

    def test_exit_two_when_suite_fails_unmutated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = repo(tmp)
            (root / "tests" / "test_money.py").write_text(
                "import unittest\nclass T(unittest.TestCase):\n    def test_x(self):\n        self.fail()\n",
                encoding="utf-8",
            )
            done = run(root)
        self.assertEqual(2, done.returncode)
        self.assertIn("does not pass unmutated", done.stderr)


if __name__ == "__main__":
    unittest.main()
