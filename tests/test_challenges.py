from __future__ import annotations

import contextlib
import io
import json
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


def apply_stable_key(project: Path) -> None:
    edit(project, "payouts/bank_client.py",
         "def send_transfer(account_ref: str, amount_cents: int, memo: str) -> dict:",
         "def send_transfer(account_ref: str, amount_cents: int, memo: str, idempotency_key: str) -> dict:")  # fmt: skip
    edit(
        project,
        "payouts/bank_client.py",
        '"Idempotency-Key": str(uuid.uuid4()),',
        '"Idempotency-Key": idempotency_key,',
    )
    edit(project, "payouts/runner.py",
         'memo=f"Payout {period}")',
         'memo=f"Payout {period}", idempotency_key=f"payout-{seller[\'id\']}-{period}")')  # fmt: skip


# A Southwind fallback that pays again when Northwind times out: the double payment E2 looks for.
FALLBACK = """

_northwind_send = send_transfer


def send_transfer(account_ref, amount_cents, memo, idempotency_key):
    try:
        return _northwind_send(account_ref, amount_cents, memo, idempotency_key)
    except requests.Timeout:
        resp = _session.post(
            "https://api.southwind-bank.example/v2/transfers",
            json={"destination": account_ref, "amount": amount_cents},
            headers={"Idempotency-Key": idempotency_key},
            timeout=(3, 10),
        )
        return resp.json()
"""


# Claims each payout once in the database before the first bank call. A later path that also
# claims cannot pay again; one that skips the claim can.
CLAIM = """

import psycopg


def claim(idempotency_key):
    with psycopg.connect("") as conn:
        conn.execute("INSERT INTO transfer_claims (idempotency_key) VALUES (%s)", [idempotency_key])


_unclaimed_send = send_transfer


def send_transfer(account_ref, amount_cents, memo, idempotency_key):
    claim(idempotency_key)
    return _unclaimed_send(account_ref, amount_cents, memo, idempotency_key)
"""


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
        apply_stable_key(self.project)
        self.assertTrue(passes("payouts-retry-key", self.project))

    def test_unfixed_fixture_fails_lost_responses(self) -> None:
        self.assertFalse(passes("payouts-lost-responses", self.project))

    def test_stable_key_passes_lost_responses(self) -> None:
        apply_stable_key(self.project)
        self.assertTrue(passes("payouts-lost-responses", self.project))

    def test_fallback_bank_on_timeout_fails_lost_responses(self) -> None:
        apply_stable_key(self.project)
        with (self.project / "payouts" / "bank_client.py").open(
            "a", encoding="utf-8"
        ) as f:
            f.write(FALLBACK)
        self.assertTrue(passes("payouts-retry-key", self.project))
        self.assertFalse(passes("payouts-lost-responses", self.project))

    def test_fallback_that_needs_its_own_key_fails_lost_responses(self) -> None:
        apply_stable_key(self.project)
        gated = FALLBACK.replace(
            "    except requests.Timeout:\n",
            "    except requests.Timeout:\n"
            "        if not __import__('os').environ.get('SOUTHWIND_API_KEY'):\n"
            "            raise\n",
        )
        with (self.project / "payouts" / "bank_client.py").open(
            "a", encoding="utf-8"
        ) as f:
            f.write(gated)
        self.assertFalse(passes("payouts-lost-responses", self.project))

    def test_claim_in_database_stops_a_fallback_that_uses_it(self) -> None:
        apply_stable_key(self.project)
        (self.project / "db" / "migrations" / "006_transfer_claims.sql").write_text(
            "CREATE TABLE transfer_claims (idempotency_key text PRIMARY KEY);\n",
            encoding="utf-8",
        )
        with (self.project / "payouts" / "bank_client.py").open(
            "a", encoding="utf-8"
        ) as f:
            f.write(CLAIM + FALLBACK.replace(
                "    except requests.Timeout:\n", "    except requests.Timeout:\n        claim(idempotency_key)\n"
            ))  # fmt: skip
        self.assertTrue(passes("payouts-lost-responses", self.project))
        self.assertTrue(passes("payouts-retry-key", self.project))

    def test_claim_does_not_stop_a_fallback_that_skips_it(self) -> None:
        apply_stable_key(self.project)
        (self.project / "db" / "migrations" / "006_transfer_claims.sql").write_text(
            "CREATE TABLE transfer_claims (idempotency_key text PRIMARY KEY);\n",
            encoding="utf-8",
        )
        with (self.project / "payouts" / "bank_client.py").open(
            "a", encoding="utf-8"
        ) as f:
            f.write(CLAIM + FALLBACK)
        self.assertFalse(passes("payouts-lost-responses", self.project))

    def test_stopping_all_payouts_fails_both(self) -> None:
        edit(
            self.project,
            "app/config.py",
            'env_flag("PAYOUT_ENABLED", default=True)',
            "False",
        )
        self.assertFalse(passes("payouts-pause", self.project))
        self.assertFalse(passes("payouts-retry-key", self.project))
        self.assertFalse(passes("payouts-lost-responses", self.project))


class RegradeTest(unittest.TestCase):
    """E2 regrading rebuilds repos from saved patches; a fallback bank added later must show
    up as a lost-responses regression without any model call."""

    def test_regrade_finds_fallback_regression(self) -> None:
        sys.path.insert(0, str(ROOT / "evals"))
        import run_agent_trap_evals as traps

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            shutil.copytree(FIXTURE, repo)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(["git", "add", "-A"], cwd=repo, check=True)

            def diff() -> (
                str
            ):  # changes since the last step, staged so the next diff starts here
                patch = subprocess.run(["git", "diff"], cwd=repo, check=True,
                                       capture_output=True, text=True).stdout  # fmt: skip
                subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
                return patch

            apply_stable_key(repo)
            hardening = diff()
            with (repo / "payouts" / "bank_client.py").open("a", encoding="utf-8") as f:
                f.write(FALLBACK)
            task = diff()

            results = Path(tmp) / "results"
            results.mkdir()
            data = {
                "hardened": [{"config": "with_skill", "run": 0, "error": None, "cost": 0.0,
                              "challenges": {}, "patch": hardening}],
                "changes": [{"config": "with_skill", "hardened_run": 0, "task": "second-bank",
                             "run": 0, "error": None, "cost": 0.0, "patch": task}],
            }  # fmt: skip
            (results / "results.json").write_text(json.dumps(data))
            names = ["payouts-retry-key", "payouts-lost-responses", "payouts-pause"]
            with contextlib.redirect_stdout(io.StringIO()):
                traps.regrade(results, names)
            regraded = json.loads((results / "results.regraded.json").read_text())

        self.assertEqual(
            {
                "payouts-retry-key": True,
                "payouts-lost-responses": True,
                "payouts-pause": False,
            },
            regraded["hardened"][0]["challenges"],
        )
        self.assertEqual(
            ["payouts-lost-responses"], regraded["changes"][0]["regressed"]
        )


if __name__ == "__main__":
    unittest.main()
