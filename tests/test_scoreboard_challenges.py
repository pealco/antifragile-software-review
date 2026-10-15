from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHALLENGE = ROOT / "evals" / "challenges" / "scoreboard.py"
FIXTURE = ROOT / "evals" / "fixtures" / "eval-scoreboard"


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


AGGREGATE = "scoreboard/aggregate.py"


def count_every_planned_trial(project: Path) -> None:
    edit(project, AGGREGATE,
         '            log.warning("no result for %s, skipping", trial["id"])\n            continue\n',
         '            result = {"reward": 0.0, "error": "no result"}\n')  # fmt: skip
    edit(project, AGGREGATE,
         '            log.warning("trial %s has no reward (%s)", trial["id"], result.get("error"))\n            continue\n',
         '            result = {**result, "reward": 0.0}\n')  # fmt: skip


def refuse_unpriced(project: Path) -> None:
    edit(
        project,
        "scoreboard/pricing.py",
        'price = catalog.get(call.get("model"), {})',
        'price = catalog[call["model"]]',
    )


def list_unpriced(project: Path) -> None:
    edit(project, AGGREGATE, '        usage = result.get("usage", [])\n',
         '        usage = result.get("usage", [])\n'
         '        stats["unpriced_models"] = sorted(set(stats.get("unpriced_models", []))'
         ' | {c["model"] for c in usage if c["model"] not in catalog})\n')  # fmt: skip


def written_env_wins(project: Path) -> None:
    edit(
        project,
        "scoreboard/launch.py",
        "return {**written, **os.environ}",
        "return {**os.environ, **written}",
    )


def flag_unrouted(project: Path) -> None:
    edit(project, AGGREGATE, "        summary[\"arms\"][name] = stats\n",
         '        if job["arms"].get(name, {}).get("via_proxy") and stats["routed_calls"] == 0:\n'
         '            stats["warnings"] = ["no routed calls: the proxy was bypassed"]\n'
         '        summary["arms"][name] = stats\n')  # fmt: skip


def by_difficulty(project: Path) -> None:
    edit(project, AGGREGATE, '        stats["trials"] += 1\n',
         '        stats["trials"] += 1\n'
         '        bucket = stats.setdefault("by_difficulty", {}).setdefault(trial["difficulty"], {"trials": 0, "passed": 0})\n'
         '        bucket["trials"] += 1\n')  # fmt: skip
    edit(project, AGGREGATE, '            stats["passed"] += 1\n',
         '            stats["passed"] += 1\n            bucket["passed"] += 1\n')  # fmt: skip
    edit(project, AGGREGATE, '        stats["cost_usd"] = round(stats["cost_usd"], 6)\n',
         '        stats["cost_usd"] = round(stats["cost_usd"], 6)\n'
         '        for b in stats.get("by_difficulty", {}).values():\n'
         '            b["pass_rate"] = round(b["passed"] / b["trials"], 4)\n')  # fmt: skip


SAFETY = ["scoreboard-denominator", "scoreboard-unpriced", "scoreboard-routing-bypass"]


class ScoreboardChallengesTest(unittest.TestCase):
    """Each challenge must reject the unfixed fixture, accept a small real fix, and reject a
    "fix" that breaks the known-good job (all arms 0/N, every launch refused, every summary
    failed)."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.project = Path(self.tmp.name) / "repo"
        shutil.copytree(
            FIXTURE, self.project, ignore=shutil.ignore_patterns("__pycache__")
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_unfixed_fixture_fails_every_challenge(self) -> None:
        for name in [*SAFETY, "scoreboard-difficulty-works"]:
            self.assertFalse(passes(name, self.project), name)

    def test_counting_every_planned_trial_passes_denominator(self) -> None:
        count_every_planned_trial(self.project)
        self.assertTrue(passes("scoreboard-denominator", self.project))
        self.assertFalse(passes("scoreboard-unpriced", self.project))

    def test_reporting_every_arm_as_zero_fails_denominator(self) -> None:
        count_every_planned_trial(self.project)
        edit(
            self.project,
            AGGREGATE,
            'if result["reward"] >= PASS_THRESHOLD:',
            "if False:",
        )
        self.assertFalse(passes("scoreboard-denominator", self.project))

    def test_refusing_unpriced_model_passes_unpriced(self) -> None:
        refuse_unpriced(self.project)
        self.assertTrue(passes("scoreboard-unpriced", self.project))

    def test_listing_unpriced_models_passes_unpriced(self) -> None:
        list_unpriced(self.project)
        self.assertTrue(passes("scoreboard-unpriced", self.project))

    def test_listing_every_model_without_a_mark_fails_unpriced(self) -> None:
        edit(self.project, AGGREGATE, '        usage = result.get("usage", [])\n',
             '        usage = result.get("usage", [])\n'
             '        stats["models"] = sorted(set(stats.get("models", [])) | {c["model"] for c in usage})\n')  # fmt: skip
        self.assertFalse(passes("scoreboard-unpriced", self.project))

    def test_failing_every_summary_fails_unpriced(self) -> None:
        edit(
            self.project,
            "scoreboard/cli.py",
            "    return summary\n",
            "    raise SystemExit(1)\n",
        )
        self.assertFalse(passes("scoreboard-unpriced", self.project))

    def test_written_env_and_unrouted_flag_pass_routing(self) -> None:
        written_env_wins(self.project)
        flag_unrouted(self.project)
        self.assertTrue(passes("scoreboard-routing-bypass", self.project))

    def test_refusing_an_exported_base_url_passes_routing(self) -> None:
        edit(self.project, "scoreboard/launch.py", "    job_dir.mkdir(parents=True, exist_ok=True)\n",
             '    if os.environ.get("LLM_BASE_URL"):\n'
             '        raise SystemExit("LLM_BASE_URL is set in the environment; unset it, the launcher sets it per arm")\n'
             "    job_dir.mkdir(parents=True, exist_ok=True)\n")  # fmt: skip
        flag_unrouted(self.project)
        self.assertTrue(passes("scoreboard-routing-bypass", self.project))

    def test_each_half_of_the_routing_fix_alone_fails(self) -> None:
        written_env_wins(self.project)
        self.assertFalse(passes("scoreboard-routing-bypass", self.project))
        shutil.rmtree(self.project)
        shutil.copytree(
            FIXTURE, self.project, ignore=shutil.ignore_patterns("__pycache__")
        )
        flag_unrouted(self.project)
        self.assertFalse(passes("scoreboard-routing-bypass", self.project))

    def test_refusing_every_launch_fails_routing(self) -> None:
        edit(self.project, "scoreboard/launch.py", "    job_dir.mkdir(parents=True, exist_ok=True)\n",
             '    raise SystemExit("launch disabled")\n')  # fmt: skip
        flag_unrouted(self.project)
        self.assertFalse(passes("scoreboard-routing-bypass", self.project))

    def test_all_three_fixes_together_pass(self) -> None:
        count_every_planned_trial(self.project)
        refuse_unpriced(self.project)
        written_env_wins(self.project)
        flag_unrouted(self.project)
        for name in SAFETY:
            self.assertTrue(passes(name, self.project), name)

    def test_by_difficulty_passes_utility(self) -> None:
        by_difficulty(self.project)
        self.assertTrue(passes("scoreboard-difficulty-works", self.project))


if __name__ == "__main__":
    unittest.main()
