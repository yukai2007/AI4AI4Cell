import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import publish_llm_grouped_main as publisher


class GroupedMainTableTests(unittest.TestCase):
    def snapshot(self, incomplete=False):
        models = {}
        for model in publisher.MODEL_LABELS:
            models[model] = {}
            for task in publisher.TASKS:
                methods = {}
                for index, method in enumerate(publisher.METHODS, 1):
                    methods[method] = {
                        "complete": True, "completed": 3, "attempted": 3,
                        "mean": index / 10, "sd": .01, "failure_tokens": [],
                    }
                if incomplete and model == "luna":
                    methods["ai_researcher"] = {
                        "complete": False, "completed": 2, "attempted": 3,
                        "mean": .35, "sd": .02,
                        "failure_tokens": [r"$F_{\mathrm{ctx}}$"],
                    }
                models[model][task] = methods
        return {"models": models}

    def test_two_model_blocks_repeat_all_methods(self):
        text = publisher.table_text(self.snapshot())
        for label in publisher.MODEL_LABELS.values():
            self.assertIn(label, text)
        self.assertEqual(text.count("Fixed model (1 lab)"), 2)
        self.assertEqual(text.count("AI-Researcher (1 lab)"), 2)
        self.assertIn(r"\textbf{50.00} $\pm$ 1.00", text)

    def test_incomplete_method_is_not_ranked_or_imputed(self):
        text = publisher.table_text(self.snapshot(incomplete=True))
        luna = text.split("GPT-5.6 Luna (low reasoning)", 1)[1]
        row = next(line for line in luna.splitlines() if line.startswith("AI-Researcher"))
        self.assertEqual(row.count(r"35.00 $\pm$ 2.00,\,$F_{\mathrm{ctx}}$\,(2/3)"), len(publisher.TASKS))
        self.assertEqual(row.count(r"$F_{\mathrm{ctx}}$"), len(publisher.TASKS))
        self.assertNotIn(r"\underline", row)
        self.assertNotIn(r"\textbf", row)

    def test_committed_artifact_matches_generator(self):
        snapshot = json.loads(
            (publisher.PAPER / "tables/public_harness_comparison"
             / "snapshot_llm_grouped_three_seed.json").read_text())
        on_disk = (publisher.PAPER / "tables/public_harness_comparison"
                   / "main_public_harness_three_seed.tex").read_text()
        self.assertEqual(publisher.table_text(snapshot), on_disk)
        self.assertIn(r"\renewcommand{\arraystretch}{0.82}", on_disk)
        self.assertIn("best/second-best complete result per block", on_disk)

    def test_transient_service_failure_has_explicit_token(self):
        self.assertEqual(
            publisher.LUNA_FAILURE_TOKENS[
                "GPT-5.6 Luna transport/tool-isolation failure"
            ],
            r"$F_{\mathrm{svc}}$",
        )


if __name__ == "__main__":
    unittest.main()
