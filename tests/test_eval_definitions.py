from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KNOWN_CHECKS = {
    "tree_unchanged",
    "tree_changed",
    "python_compiles",
    "evidence_resolves",
    "scanner_run",
    "tests_changed",
}
CHALLENGE_SCRIPTS = ROOT / "evals" / "challenges"


class TriggerQueriesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.queries = json.loads((ROOT / "evals" / "trigger_queries.json").read_text())

    def test_set_is_balanced_and_ids_are_unique(self) -> None:
        tuned = [q for q in self.queries if q["split"] != "holdout"]
        positives = [q for q in tuned if q["should_trigger"]]
        negatives = [q for q in tuned if not q["should_trigger"]]
        self.assertTrue(8 <= len(positives) <= 10, len(positives))
        self.assertTrue(8 <= len(negatives) <= 10, len(negatives))
        self.assertEqual(len(self.queries), len({q["id"] for q in self.queries}))

    def test_each_split_has_both_labels(self) -> None:
        for split in ("train", "validation", "holdout"):
            labels = {q["should_trigger"] for q in self.queries if q["split"] == split}
            self.assertEqual({True, False}, labels, split)


class OutputEvalsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.spec = json.loads((ROOT / "evals" / "evals.json").read_text())

    def test_skill_name_matches_skill_md(self) -> None:
        skill = (ROOT / "SKILL.md").read_text()
        self.assertIn(f"name: {self.spec['skill_name']}\n", skill)

    def test_cases_point_at_real_files_and_known_checks(self) -> None:
        for case in self.spec["evals"]:
            self.assertTrue(
                (ROOT / "evals" / "fixtures" / case["fixture"]).is_dir(), case["id"]
            )
            if case["gold"]:
                self.assertTrue(
                    (ROOT / "evals" / "golden" / case["gold"]).is_file(), case["id"]
                )
            self.assertIn(case["mode"], {"audit", "implementation"})
            self.assertTrue(case["assertions"], case["id"])
            for check in case["checks"]:
                if check.startswith("cites:"):
                    path = check.removeprefix("cites:")
                    self.assertTrue(
                        (
                            ROOT / "evals" / "fixtures" / case["fixture"] / path
                        ).is_file(),
                        check,
                    )
                elif check.startswith("challenge:"):
                    name = check.removeprefix("challenge:")
                    script = CHALLENGE_SCRIPTS / f"{name.split('-')[0]}.py"
                    self.assertTrue(script.is_file(), check)
                    self.assertIn(f'"{name}"', script.read_text(), check)
                else:
                    self.assertIn(check, KNOWN_CHECKS)

    def test_audit_cases_check_that_the_tree_is_unchanged(self) -> None:
        for case in self.spec["evals"]:
            if case["mode"] == "audit":
                self.assertIn("tree_unchanged", case["checks"], case["id"])

    def test_runner_only_uses_checks_it_implements(self) -> None:
        runner = (ROOT / "evals" / "run_output_evals.py").read_text()
        implemented = set(re.findall(r'name == "(\w+)"', runner))
        self.assertTrue(KNOWN_CHECKS <= implemented, KNOWN_CHECKS - implemented)


class AgentTrapsTest(unittest.TestCase):
    def test_traps_point_at_a_harden_case_and_known_challenges(self) -> None:
        spec = json.loads((ROOT / "evals" / "evals.json").read_text())
        files = sorted((ROOT / "evals").glob("agent_traps*.json"))
        self.assertEqual(3, len(files))
        for path in files:
            traps = json.loads(path.read_text())
            case = next(c for c in spec["evals"] if c["id"] == traps["harden_case"])
            self.assertEqual("implementation", case["mode"], path.name)
            self.assertEqual(traps["fixture"], case["fixture"], path.name)
            for name in traps["challenges"]:
                self.assertIn(f"challenge:{name}", case["checks"], path.name)
            ids = [t["id"] for t in traps["tasks"]]
            self.assertEqual(len(ids), len(set(ids)), path.name)
            for task in traps["tasks"]:
                if task.get("outcome"):
                    prefix = task["outcome"].split("-")[0]
                    self.assertTrue(
                        (CHALLENGE_SCRIPTS / f"{prefix}.py").is_file(), task["id"]
                    )


if __name__ == "__main__":
    unittest.main()
