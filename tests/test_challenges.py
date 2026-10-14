from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHALLENGE = ROOT / "evals" / "challenges" / "payouts.py"
FIXTURE = ROOT / "evals" / "fixtures" / "payouts-platform"


def passes(name: str, project: Path) -> bool:
    done = subprocess.run(
        [sys.executable, str(CHALLENGE), "check", name, str(project)],
        capture_output=True, text=True, check=False,
    )  # fmt: skip
    return done.returncode == 0


def edit(project: Path, path: str, old: str, new: str) -> None:
    file = project / path
    text = file.read_text(encoding="utf-8")
    assert old in text, (path, old)
    file.write_text(text.replace(old, new), encoding="utf-8")


class PayoutChallengesTest(unittest.TestCase):
    """The challenges must reject the unfixed fixture, accept a real fix, and reject a "fix"
    that stops every payout. A challenge that cannot tell these apart proves nothing."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.project = Path(self.tmp.name) / "repo"
        shutil.copytree(FIXTURE, self.project)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_unfixed_fixture_fails_both(self) -> None:
        self.assertFalse(passes("payouts-pause", self.project))
        self.assertFalse(passes("payouts-retry-key", self.project))

    def test_one_flag_name_passes_pause(self) -> None:
        edit(self.project, "app/config.py", '"PAYOUT_ENABLED"', '"PAYOUTS_ENABLED"')
        edit(
            self.project,
            "deploy/k8s/payout-cronjob.yaml",
            "PAYOUT_ENABLED",
            "PAYOUTS_ENABLED",
        )
        self.assertTrue(passes("payouts-pause", self.project))
        self.assertFalse(passes("payouts-retry-key", self.project))

    def test_suspend_in_runbook_passes_pause(self) -> None:
        edit(self.project, "docs/runbooks/payouts.md",
             "kubectl -n payments set env cronjob/payout-runner PAYOUTS_ENABLED=false",
             "kubectl -n payments patch cronjob payout-runner -p '{\"spec\":{\"suspend\":true}}'")  # fmt: skip
        self.assertTrue(passes("payouts-pause", self.project))

    def test_stable_key_passes_retry(self) -> None:
        edit(self.project, "payouts/bank_client.py",
             "def send_transfer(account_ref: str, amount_cents: int, memo: str) -> dict:",
             "def send_transfer(account_ref: str, amount_cents: int, memo: str, idempotency_key: str) -> dict:")  # fmt: skip
        edit(
            self.project,
            "payouts/bank_client.py",
            '"Idempotency-Key": str(uuid.uuid4()),',
            '"Idempotency-Key": idempotency_key,',
        )
        edit(self.project, "payouts/runner.py",
             'memo=f"Payout {period}")',
             'memo=f"Payout {period}", idempotency_key=f"payout-{seller[\'id\']}-{period}")')  # fmt: skip
        self.assertTrue(passes("payouts-retry-key", self.project))

    def test_stopping_all_payouts_fails_both(self) -> None:
        edit(
            self.project,
            "app/config.py",
            'env_flag("PAYOUT_ENABLED", default=True)',
            "False",
        )
        self.assertFalse(passes("payouts-pause", self.project))
        self.assertFalse(passes("payouts-retry-key", self.project))


if __name__ == "__main__":
    unittest.main()
