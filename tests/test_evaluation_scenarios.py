from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SkillEvaluationScenarioTest(unittest.TestCase):
    def test_scenario_blocks_parse_and_are_numbered(self) -> None:
        text = (ROOT / "references" / "evaluation-scenarios.md").read_text(encoding="utf-8")
        blocks = re.findall(r"```json\n(.*?)\n```", text, re.S)
        headings = re.findall(r"^## Scenario (\d+):", text, re.M)

        self.assertEqual(8, len(blocks))
        self.assertEqual([str(index) for index in range(1, 9)], headings)
        for block in blocks:
            scenario = json.loads(block)
            self.assertIn("query", scenario)
            self.assertIn("fixture", scenario)
            self.assertIn("expected_behavior", scenario)

    def test_executable_eval_harness_passes(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "evals" / "run_evals.py")],
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertIn("validated 3 executable scenario fixture(s)", result.stdout)

    def test_scorecard_template_satisfies_review_output_markers(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "evals" / "run_evals.py"),
                "--review-output",
                str(ROOT / "templates" / "review-scorecard.md"),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertIn("validated 3 executable scenario fixture(s)", result.stdout)


if __name__ == "__main__":
    unittest.main()
