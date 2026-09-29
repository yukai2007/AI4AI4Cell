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
        # The abstract stays qualitative: the quantitative comparisons live in the main text.
        self.assertIn("extends collaboration from parameter fitting to model development", abstract)
        self.assertIn("inner loop", abstract)
        self.assertIn("outer loop", abstract)
        self.assertIn("constraints can prevent centralized pooling", abstract)
        for task, display in (("native_tapb", "93.76"), ("ptpc_neural", "36.99")):
            actual = 100 * mean(run["scores"]["federated_loop"]["primary"]
                                for run in snapshot["tasks"][task]["runs"].values())
            self.assertEqual(f"{actual:.2f}", display)
            self.assertNotIn(display, abstract)
        self.assertNotRegex(abstract, r"\d")
        self.assertNotRegex(abstract, r"\bDTI\b|\bAUROC\b|\bAP\b")
        self.assertNotRegex(abstract.lower(), r"\bsota\b|state.of.the.art|all five endpoints")

    def test_same_access_controls_remain_visible(self):
        text = (PAPER / "sections/05_results.tex").read_text()
        manuscript = text + (PAPER / "sections/23_appendix_core_sensitivity.tex").read_text()
        self.assertIn("same-access control", text)
        self.assertIn("The fixed and feedback-free direct references train or search on a single site",
                      (PAPER / "tables/strong_v3/ablation.tex").read_text())
        self.assertIn("BioCoLoop is reported at one and ten laboratories",
                      (PAPER / "tables/strong_v3/ablation.tex").read_text())
        self.assertIn("participation and partitioning effects", text)
        self.assertNotIn("At fixed access, direct and loop select identical", text)
        self.assertIn("eight pairs tie", manuscript)
        scenario = (PAPER / "tables/scenario_labs_v2/table.tex").read_text()
        for outcome in ("28.82", "30.70"):
            self.assertIn(outcome, scenario)
        self.assertIn("seven ties and one decrease", manuscript)
        for outcome in ("83.65", "93.88"):
            appendix_tables = (PAPER / "tables/completed_ablation/lab_participation.tex").read_text()
            self.assertIn(outcome, appendix_tables)
        self.assertIn("laboratory_sensitivity_v2.pdf", text)

    def test_allocation_is_an_explicit_separately_evaluated_policy(self):
        text = (PAPER / "sections/03_method.tex").read_text()
        allocation = text.split("3.4 Evidence-guided training allocation", 1)[1]
        for phrase in ("ten predetermined designs", "20 rounds", "learning-rate group",
                       "round 5 to round 20", "restart from their initial parameters",
                       "100-round training", "800 aggregation rounds",
                       "160 aggregate development evaluations",
                       "independently of proposal generation",
                       "100 training rounds per candidate",
                       "Section 4.4 reports the allocation results"):
            self.assertIn(phrase, allocation)
        results = (PAPER / "sections/05_results.tex").read_text()
        self.assertLess(results.index("4.4 Evidence-guided training allocation"),
                        results.index("4.7 Development history and proposal trajectories"))

    def test_training_term_and_figure_action_labels(self):
        sources = [(PAPER / "biocoloop-main.tex").read_text()]
        sources.extend(path.read_text() for path in (PAPER / "sections").glob("*.tex"))
        self.assertNotIn("predictive learning", "\n".join(sources))
        generator = (PAPER / "tools/draw_paradigm_comparison.py").read_text()
        self.assertIn("Train locally; share updates", generator)
        self.assertNotIn("Local fits; share updates", generator)


if __name__ == "__main__":
    unittest.main()
