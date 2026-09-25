import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import publish_public_harness_one_lab as publisher


class OneLabTableTests(unittest.TestCase):
    def snapshot(self):
        tasks = {}
        for task in publisher.TASKS:
            tasks[task] = {
                "core": {
                    "single_fixed": {"mean": .10, "sd": .01, "seed42": .10},
                    "single_direct": {"mean": .20, "sd": .02, "seed42": .20},
                    "federated_loop": {"mean": .30, "sd": .03, "seed42": .30},
                },
                "public": {
                    "ai_scientist_v2": {"status": "scored", "primary": .22},
                    "ai_researcher": {"status": "failed", "display": r"$F_{\mathrm{tool}}$"},
                },
            }
        return {"tasks": tasks}

    def test_access_labels_and_ranking(self):
        text = publisher.table_text(self.snapshot())
        self.assertIn("AI-Scientist-v2 (1 lab)", text)
        self.assertIn("AI-Researcher (1 lab)", text)
        self.assertNotIn("AI-Scientist-v2 (10 labs)", text)
        self.assertIn(r"\textbf{BioCoLoop} (10 labs) & \textbf{30.00}", text)
        self.assertIn(r"AI-Scientist-v2 (1 lab) & \underline{22.00}", text)
        self.assertIn("public controllers use laboratory 0", text)

    def test_failure_has_no_imputed_score(self):
        text = publisher.table_text(self.snapshot())
        row = next(line for line in text.splitlines() if line.startswith("AI-Researcher"))
        self.assertEqual(row.count(r"$F_{\mathrm{tool}}$"), 5)


if __name__ == "__main__":
    unittest.main()
