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
        self.assertEqual(text.count("Fixed model"), 2)
        self.assertEqual(text.count("AI-Researcher"), 2)
        self.assertIn(r"\textbf{50.00} $\pm$ 1.00", text)
        self.assertEqual(text.count(r"\cmidrule(lr){4-6}"), 1)
        self.assertIn(r"\textbf{BioCoLoop}", text)
        self.assertIn(r"\shortstack{Mean rank\\$\downarrow$}", text)

    def test_incomplete_method_is_not_ranked_or_imputed(self):
        text = publisher.table_text(self.snapshot(incomplete=True))
        luna = text.split("GPT-5.6 Luna (low reasoning)", 1)[1]
        row = next(line for line in luna.splitlines() if line.startswith("AI-Researcher"))
        self.assertEqual(row.count(r"\TblPartial"), len(publisher.TASKS))
        self.assertNotIn(r"\underline", row)
        self.assertNotIn(r"\textbf", row)
        self.assertIn(r"$\dagger$ partial and {\TblZero} unscored cells are not imputed", text)
        zero = publisher.table_text(self.zero_snapshot())
        self.assertIn(r"\TblZero", zero)
        self.assertIn(r"\textcolor{TblInk}{--}", zero)
        self.assertNotIn(r"$F_{\mathrm{ctx}}$\,(0/3)", zero)

    def test_rank_column_marks_change_against_the_fixed_reference(self):
        text = publisher.table_text(self.snapshot())
        ranks = publisher.task_ranks(self.snapshot(), "qwen")
        self.assertAlmostEqual(ranks["federated_loop"], 1.0)
        self.assertAlmostEqual(ranks["single_fixed"], 5.0)
        for delta in ("1.0", "2.0", "3.0", "4.0"):
            self.assertEqual(text.count(r"\TblUp{" + delta + "}"), 2)
        self.assertEqual(text.count(r"\TblDown{"), 0)

    def test_committed_artifact_matches_generator(self):
        snapshot = json.loads(
            (publisher.PAPER / "tables/public_harness_comparison"
             / "snapshot_llm_grouped_three_seed.json").read_text())
        on_disk = (publisher.PAPER / "tables/public_harness_comparison"
                   / "main_public_harness_three_seed.tex").read_text()
        self.assertEqual(publisher.table_text(snapshot), on_disk)
        self.assertIn(r"\renewcommand{\arraystretch}{0.84}", on_disk)
        self.assertIn(r"\usepackage{xcolor}",
                      (publisher.PAPER / "biocoloop-main.tex").read_text())
        self.assertIn("averages those ranks, so lower is better", on_disk)
        self.assertIn(r"\providecommand{\TblZero}", on_disk)
        self.assertIn(r"\definecolor{TblUp}{RGB}", on_disk)

    def zero_snapshot(self):
        snapshot = self.snapshot()
        for task in publisher.TASKS:
            snapshot["models"]["luna"][task]["ai_researcher"] = {
                "complete": False, "completed": 0, "attempted": 3,
                "mean": None, "sd": None,
                "failure_tokens": [r"$F_{\mathrm{ctx}}$", r"$F_{\mathrm{svc}}$"],
            }
        return snapshot

    def test_transient_service_failure_has_explicit_token(self):
        self.assertEqual(
            publisher.LUNA_FAILURE_TOKENS[
                "GPT-5.6 Luna transport/tool-isolation failure"
            ],
            r"$F_{\mathrm{svc}}$",
        )

    def test_single_completed_seed_shows_count_without_fabricated_sd(self):
        snapshot = self.snapshot()
        snapshot["models"]["luna"]["native_tapb"]["ai_researcher"] = {
            "complete": False, "completed": 1, "attempted": 3,
            "mean": .35, "sd": None, "failure_tokens": [r"$F_{\mathrm{ctx}}$"],
        }
        text = publisher.table_text(snapshot)
        luna = text.split("GPT-5.6 Luna (low reasoning)", 1)[1]
        row = next(line for line in luna.splitlines() if line.startswith("AI-Researcher"))
        self.assertIn(r"35.00\,(1/3)\TblPartial", row)
        self.assertNotIn("None", row)


if __name__ == "__main__":
    unittest.main()
