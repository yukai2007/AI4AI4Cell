import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import publish_public_harness_multiseed as publisher


class MultiSeedTableTests(unittest.TestCase):
    def snapshot(self, fail=False):
        tasks = {}
        for task in publisher.TASKS:
            core = {
                method: {"mean": value, "sd": .01, "seed42": value}
                for method, value in (("single_fixed", .10), ("single_direct", .20),
                                      ("federated_loop", .40))
            }
            public = {}
            for method, value in (("ai_scientist_v2", .30), ("ai_researcher", .25)):
                if fail and method == "ai_scientist_v2":
                    public[method] = {"complete": False, "completed": 0, "attempted": 3,
                                      "failure_tokens": [r"$F_{\mathrm{pipe}}$"], "runs": {}}
                else:
                    public[method] = {"complete": True, "completed": 3, "attempted": 3,
                                      "mean": value, "sd": .02, "failure_tokens": [], "runs": {}}
            tasks[task] = {"core": core, "public": public}
        return {"tasks": tasks}

    def test_flat_table_has_five_methods_and_variance(self):
        text = publisher.table_text(self.snapshot())
        self.assertNotIn("A. Core comparison", text)
        self.assertNotIn("B. Research-controller comparison", text)
        for label in publisher.LABELS.values():
            self.assertIn(label, text)
        self.assertIn(r"AI-Scientist-v2 (1 lab) & \underline{30.00} $\pm$ 2.00", text)
        self.assertIn(r"\textbf{BioCoLoop} (10 labs) & \textbf{40.00} $\pm$ 1.00", text)

    def test_failure_reports_completion_without_imputation(self):
        text = publisher.table_text(self.snapshot(fail=True))
        row = next(line for line in text.splitlines() if line.startswith("AI-Scientist-v2"))
        self.assertEqual(row.count(r"$F_{\mathrm{pipe}}$\,(0/3)"), 5)
        self.assertNotIn(r"\underline", row)


if __name__ == "__main__":
    unittest.main()
