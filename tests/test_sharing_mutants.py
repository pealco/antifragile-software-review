"""The doc-sharing fixture's tests must tolerate every seeded fault (so the mutant checks can tell
a strengthened suite from the original), and a reference strong test must reject each one."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evals"))
import run_output_evals as out

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "evals" / "fixtures" / "doc-sharing"
MUTANTS = json.loads(
    (ROOT / "evals" / "mutants" / "doc-sharing.json").read_text(encoding="utf-8")
)
REFERENCE = ROOT / "evals" / "mutants" / "doc-sharing"
REFERENCE_FILES = ("sharing/policy.py", "sharing/api.py")

# Literal allow/deny decisions taken from docs/policy.md: fails on the current code (a suspended
# owner keeps access; support can edit) and on every mutant.
STRONG_TEST = """
import unittest
from datetime import date
from unittest.mock import MagicMock

from sharing.api import Forbidden, perform
from sharing.model import Account, Document, Share
from sharing.policy import can

TODAY = date(2026, 10, 15)
ACTIONS = ("read", "comment", "edit", "share", "delete")
DOC = Document("d1", owner_id="olivia", shares={
    "vic": Share("viewer"), "cam": Share("commenter"), "ed": Share("editor"),
    "exp": Share("editor", until=date(2026, 10, 15)),
})


def allowed(account, today=TODAY):
    return {a for a in ACTIONS if can(account, a, DOC, today)}


class StrongTest(unittest.TestCase):
    def test_role_table(self):
        self.assertEqual({"read"}, allowed(Account("vic")))
        self.assertEqual({"read", "comment"}, allowed(Account("cam")))
        self.assertEqual({"read", "comment", "edit"}, allowed(Account("ed")))
        self.assertEqual(set(ACTIONS), allowed(Account("olivia")))
        self.assertEqual(set(), allowed(Account("nobody")))

    def test_suspended_owner_can_do_nothing(self):
        self.assertEqual(set(), allowed(Account("olivia", suspended=True)))

    def test_support_reads_only(self):
        self.assertEqual({"read"}, allowed(Account("sam", support=True)))

    def test_share_expires_at_start_of_until_day(self):
        self.assertEqual({"read", "comment", "edit"}, allowed(Account("exp"), date(2026, 10, 14)))
        self.assertEqual(set(), allowed(Account("exp"), date(2026, 10, 15)))

    def test_denied_action_raises_and_has_no_effect(self):
        audit, effect = MagicMock(), MagicMock()
        with self.assertRaises(Forbidden):
            perform(Account("vic"), "edit", DOC, TODAY, audit, effect)
        effect.assert_not_called()
        audit.record.assert_called_once_with("vic", "edit", "d1", False)
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


class SharingMutantsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "repo"
        shutil.copytree(FIXTURE, self.repo)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def use_reference(self) -> None:
        for rel in REFERENCE_FILES:
            shutil.copy(REFERENCE / rel, self.repo / rel)

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

    def test_weak_suite_accepts_the_reference(self) -> None:
        self.use_reference()
        self.assertTrue(suite_passes(self.repo))

    def test_strong_test_fails_on_current_code_and_passes_on_the_reference(
        self,
    ) -> None:
        (self.repo / "tests" / "test_strong.py").write_text(
            STRONG_TEST, encoding="utf-8"
        )
        self.assertFalse(
            suite_passes(self.repo), "the current policy breaks the promise"
        )
        self.use_reference()
        self.assertTrue(
            suite_passes(self.repo), "the strong test passes on the reference"
        )

    def test_every_mutant_applies_to_the_reference_and_strong_test_rejects_it(
        self,
    ) -> None:
        self.use_reference()
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


class RefusalsTestedCheckTest(unittest.TestCase):
    """`refusals_tested` strips every raise from the code: the weak suite still passes (no test
    observes a refusal) and the strong test fails."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "repo"
        shutil.copytree(FIXTURE, self.repo)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_weak_suite_fails_the_check_and_strong_test_passes_it(self) -> None:
        run: dict = {}
        self.assertFalse(out.run_check("refusals_tested", self.repo, run))
        (self.repo / "tests" / "test_strong.py").write_text(
            STRONG_TEST, encoding="utf-8"
        )
        for rel in REFERENCE_FILES:
            shutil.copy(REFERENCE / rel, self.repo / rel)
        self.assertTrue(out.run_check("refusals_tested", self.repo, run))
        self.assertTrue(suite_passes(self.repo), "the code is restored after the check")


if __name__ == "__main__":
    unittest.main()
