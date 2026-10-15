"""The backup-retention fixture's tests must tolerate every seeded fault (so the mutant checks can
tell a strengthened suite from the original), and a reference strong test must reject each one."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "evals" / "fixtures" / "backup-retention"
MUTANTS = json.loads(
    (ROOT / "evals" / "mutants" / "backup-retention.json").read_text(encoding="utf-8")
)
REFERENCE = ROOT / "evals" / "mutants" / "backup-retention"

# Literal expected names for a fixed date: fails on the current code (it keeps 3 weekly backups
# beyond the daily window, not 4) and on every mutant.
STRONG_TEST = """
import unittest
from datetime import date, timedelta
from unittest.mock import MagicMock

from retention.policy import Backup, keep_set
from retention.prune import prune

TODAY = date(2026, 10, 15)


def daily(days):
    return [Backup(f"b{d}", TODAY - timedelta(days=d)) for d in range(days)]


class StrongTest(unittest.TestCase):
    def test_keeps_seven_daily_four_weekly_and_monthly(self):
        kept = keep_set(daily(60), TODAY)
        self.assertEqual({"b0", "b1", "b2", "b3", "b4", "b5", "b6"}, {n for n in kept if int(n[1:]) < 7})
        self.assertIn("b7", kept)   # newest of the first full week beyond the daily window
        self.assertIn("b14", kept)
        self.assertIn("b21", kept)
        self.assertIn("b28", kept)  # fourth weekly backup
        self.assertNotIn("b8", kept)

    def test_refuses_to_delete_everything(self):
        store = MagicMock()
        store.list_backups.return_value = [Backup("old", TODAY - timedelta(days=400))]
        with self.assertRaises(RuntimeError):
            prune(store, TODAY)
        store.delete.assert_not_called()
"""


def suite_passes(repo: Path) -> bool:
    done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=repo,
                          capture_output=True, text=True, check=False)  # fmt: skip
    return done.returncode == 0


def mutated(repo: Path, name: str) -> None:
    spec = MUTANTS[name]
    path = repo / spec["file"]
    text = path.read_text(encoding="utf-8")
    assert text.count(spec["old"]) == 1, name
    path.write_text(text.replace(spec["old"], spec["new"]), encoding="utf-8")


class RetentionMutantsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "repo"
        shutil.copytree(FIXTURE, self.repo)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_weak_suite_passes_and_tolerates_every_mutant(self) -> None:
        self.assertTrue(suite_passes(self.repo))
        for name in MUTANTS:
            with self.subTest(mutant=name):
                shutil.rmtree(self.repo)
                shutil.copytree(FIXTURE, self.repo)
                mutated(self.repo, name)
                self.assertTrue(
                    suite_passes(self.repo), f"the weak suite already catches {name}"
                )

    def test_strong_test_fails_on_current_code_and_on_every_mutant(self) -> None:
        (self.repo / "tests" / "test_strong.py").write_text(
            STRONG_TEST, encoding="utf-8"
        )
        self.assertFalse(
            suite_passes(self.repo), "the current policy has the off-by-one"
        )
        fixed = (self.repo / "retention" / "policy.py").read_text(encoding="utf-8")
        fixed = fixed.replace(
            "        week = age // 7\n",
            "        week = (age - 7) // 7 if age >= 7 else -1\n",
        )
        (self.repo / "retention" / "policy.py").write_text(fixed, encoding="utf-8")
        self.assertTrue(
            suite_passes(self.repo),
            "the strong test passes once the weekly window is fixed",
        )
        for name in MUTANTS:
            with self.subTest(mutant=name):
                before = (self.repo / MUTANTS[name]["file"]).read_text(encoding="utf-8")
                mutated(self.repo, name)
                self.assertFalse(
                    suite_passes(self.repo), f"the strong test tolerates {name}"
                )
                (self.repo / MUTANTS[name]["file"]).write_text(before, encoding="utf-8")


class ReferenceTest(unittest.TestCase):
    """The reference implementation keeps the promise, the weak suite accepts it, every mutant
    applies to it, and the strong test rejects every mutant applied to it."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "repo"
        shutil.copytree(FIXTURE, self.repo)
        for rel in ("retention/policy.py", "retention/prune.py"):
            shutil.copy(REFERENCE / rel, self.repo / rel)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_weak_and_strong_suites_pass_on_the_reference(self) -> None:
        self.assertTrue(suite_passes(self.repo))
        (self.repo / "tests" / "test_strong.py").write_text(
            STRONG_TEST, encoding="utf-8"
        )
        self.assertTrue(suite_passes(self.repo))

    def test_reference_keeps_the_promise(self) -> None:
        sys.path.insert(0, str(self.repo))
        for mod in list(sys.modules):
            if mod.startswith("retention"):
                del sys.modules[mod]
        from datetime import date, timedelta

        from retention.policy import Backup, keep_set

        today = date(2026, 10, 15)
        kept = keep_set(
            [Backup(f"b{d}", today - timedelta(days=d)) for d in range(400)], today
        )
        ages = sorted(int(n[1:]) for n in kept)
        self.assertEqual([0, 1, 2, 3, 4, 5, 6, 7, 14, 21, 28], ages[:11])
        self.assertGreaterEqual(max(ages), 365)
        sys.path.remove(str(self.repo))

    def test_every_mutant_applies_to_the_reference_and_strong_test_rejects_it(
        self,
    ) -> None:
        (self.repo / "tests" / "test_strong.py").write_text(
            STRONG_TEST, encoding="utf-8"
        )
        for name in MUTANTS:
            with self.subTest(mutant=name):
                before = (self.repo / MUTANTS[name]["file"]).read_text(encoding="utf-8")
                mutated(self.repo, name)
                self.assertFalse(
                    suite_passes(self.repo),
                    f"the strong test tolerates {name} on the reference",
                )
                (self.repo / MUTANTS[name]["file"]).write_text(before, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
