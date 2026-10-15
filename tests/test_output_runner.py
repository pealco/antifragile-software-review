"""one_run must carry the agent's patch and the check details into the saved result, so a run
can be regraded without paying for the agent again."""

from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evals"))
import run_output_evals as out


class OutputRunnerTest(unittest.TestCase):
    def test_patch_and_details_reach_the_result(self) -> None:
        case = {
            "id": "fake", "mode": "implementation", "fixture": "backup-retention", "gold": None,
            "prompt": "x", "checks": ["tests_changed", "fails_on_original"], "assertions": ["a"], "method": [],
        }  # fmt: skip

        def fake_agent(case, project, with_skill, model, budget):
            (project / "tests" / "test_new.py").write_text(
                "import unittest\nfrom retention.policy import keep_set\n\n\n"
                "class T(unittest.TestCase):\n    def test_x(self):\n        self.assertEqual(set(), keep_set([], None))\n",
                encoding="utf-8",
            )
            return {"error": None, "final_text": "done", "tools": [], "cost": 0.0}

        def fake_grader(case, project, run, model):
            out.git(project, "add", "-A")
            run["patch"] = out.git(project, "diff", "--cached", "HEAD")
            return [{"assertion": "a", "verdict": "PASS", "evidence": "x"}]

        args = argparse.Namespace(
            skill_dir=None, model="m", budget=1.0, grader_model="g"
        )
        with (
            mock.patch.object(out, "run_agent", fake_agent),
            mock.patch.object(out, "grade_assertions", fake_grader),
        ):
            result = out.one_run((case, False, 0), args, "skill")

        self.assertIn("tests/test_new.py", result["patch"])
        self.assertTrue(result["checks"]["tests_changed"])
        self.assertIn("fails_on_original", result["fail_before_detail"])


if __name__ == "__main__":
    unittest.main()
