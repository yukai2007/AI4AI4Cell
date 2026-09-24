"""Bind the stronger presentation to the existing comparison scopes and scores."""
import json
from pathlib import Path
from statistics import mean
import unittest

PAPER = Path(__file__).resolve().parents[1]


class EvidenceLedNarrativeTests(unittest.TestCase):
    def test_headline_uses_the_stronger_single_lab_reference(self):
        snapshot = json.loads((PAPER / "tables/strong_v3/snapshot.json").read_text())
        wins = {}
        for task, record in snapshot["tasks"].items():
            scores = {
                arm: mean(run["scores"][arm]["primary"] for run in record["runs"].values())
                for arm in ("single_fixed", "single_direct", "single_loop", "federated_loop")
            }
            gap = 100 * (scores["federated_loop"] -
                         max(scores["single_fixed"], scores["single_direct"]))
            if gap > 0:
                wins[task] = f"{gap:.2f}"
            self.assertGreater(scores["federated_loop"], scores["single_loop"])
        self.assertEqual(wins, {
            "native_tapb": "3.87", "ptpc_neural": "11.94",
            "vcc_corrected": "1.61", "tahoe_drug_corrected": "2.99"})
        entry = (PAPER / "biocoloop-main.tex").read_text()
        abstract = entry.split(r"\begin{abstract}", 1)[1].split(r"\end{abstract}", 1)[0]
        self.assertIn("single-laboratory fixed-model and direct-optimization baselines", abstract)
        for task, display in (("native_tapb", "93.76"), ("ptpc_neural", "36.99")):
            actual = 100 * mean(run["scores"]["federated_loop"]["primary"]
                                for run in snapshot["tasks"][task]["runs"].values())
            self.assertEqual(f"{actual:.2f}", display)
            self.assertNotIn(display, abstract)
        self.assertIn("four of five endpoints", abstract)
        self.assertNotRegex(abstract, r"\bDTI\b|\bAUROC\b|\bAP\b")
        self.assertNotRegex(abstract.lower(), r"\bsota\b|state.of.the.art|all five endpoints")

    def test_same_access_controls_remain_visible(self):
        text = (PAPER / "sections/05_results.tex").read_text()
        self.assertIn("At ten laboratories", text)
        self.assertIn("37.07 AP and 25.87 Top-1", text)
        self.assertIn("its one-laboratory fixed model remains best at 25.56", text)
        self.assertNotIn("At fixed access, direct and loop select identical", text)
        for outcome in ("eight pairs tie", "seven ties and one decrease",
                        "28.82", "30.70", "82.44", "84.30"):
            self.assertIn(outcome, text)

    def test_allocation_is_an_explicit_separately_evaluated_policy(self):
        text = (PAPER / "sections/03_method.tex").read_text()
        allocation = text.split("3.4 Trajectory-guided training allocation", 1)[1]
        for phrase in ("ten predetermined designs", "20 rounds", "learning-rate group",
                       "round 5 to round 20", "restart from their initial parameters",
                       "100-round training", "800 aggregation rounds",
                       "160 aggregate development evaluations",
                       "does not generate language-model proposals",
                       "they do not use the allocation policy",
                       "improves Norman Top-1 by 10.84 percentage points"):
            self.assertIn(phrase, allocation)
        results = (PAPER / "sections/05_results.tex").read_text()
        self.assertLess(results.index("4.4 Measured trajectories"),
                        results.index("4.7 How does feedback"))

    def test_training_term_and_figure_action_labels(self):
        sources = [(PAPER / "biocoloop-main.tex").read_text()]
        sources.extend(path.read_text() for path in (PAPER / "sections").glob("*.tex"))
        self.assertNotIn("predictive learning", "\n".join(sources))
        generator = (PAPER / "tools/draw_paradigm_comparison.py").read_text()
        self.assertIn("Train locally; share updates", generator)
        self.assertNotIn("Local fits; share updates", generator)


if __name__ == "__main__":
    unittest.main()
