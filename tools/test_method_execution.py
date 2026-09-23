"""Check the documented execution order and the fixed-slate budget accounting."""
from pathlib import Path
import json
import unittest

PAPER = Path(__file__).resolve().parents[1]


class MethodExecutionTests(unittest.TestCase):
    def setUp(self):
        self.method = (PAPER / "sections/03_method.tex").read_text()

    def test_duration_is_separate_from_design_and_allocation_is_separate_study(self):
        self.assertIn("training duration separately from", self.method)
        self.assertIn("main proposal-search protocol assigns each candidate 100 training rounds", self.method)
        self.assertIn(r"separate \emph{training allocation} study", self.method)
        self.assertIn("fixed slate of ten designs for 20 rounds each", self.method)
        self.assertIn("restart from their initial parameters for 100-round training", self.method)
        self.assertIn("other four finish after screening", self.method)
        protocol = json.loads((PAPER / "provenance/v6_loop_summary.json").read_text())["protocol"]
        self.assertEqual(protocol["candidate_count_per_arm"], 10)
        self.assertEqual(10 * 80, 10 * 20 + 6 * 100)
        self.assertEqual(protocol["full_client_rounds_per_arm"], 800)
        self.assertNotIn("full validation", self.method)

    def test_round_weighting_and_checkpoint_then_design_selection(self):
        for text in ("one complete local AdamW epoch per laboratory",
                     "averages parameters in proportion to these counts",
                     "Every five rounds and at the final round",
                     "same aggregated checkpoint", "s_i(a,r)",
                     "equal-laboratory mean loss", "represents its design",
                     "complete ties retain the earlier checkpoint or incumbent"):
            self.assertIn(text, self.method)

    def test_initialization_and_language_model_context_are_precise(self):
        for text in ("task's initialization procedure and the same seed",
                     "Within a fit, all participating laboratories start with identical parameters",
                     "first/last training and development diagnostics",
                     "next proposal's context", "language-model weights stay fixed"):
            self.assertIn(text, self.method)
        self.assertNotIn("The research language model remains fixed; adaptation occurs", self.method)
        self.assertIn("main collaborative comparison", self.method)

    def test_promotion_uses_best_screen_checkpoint_and_explicit_score_change(self):
        appendix = (PAPER / "sections/22_appendix_unified_protocol.tex").read_text()
        for text in ("best screening checkpoint", "round 5 to round 20",
                     "lower round-20 development loss", "prespecified scheduler"):
            self.assertIn(text, appendix)
        self.assertNotIn("strong current scores", self.method)


if __name__ == "__main__":
    unittest.main()
