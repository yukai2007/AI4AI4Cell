"""Keep the introduction's scenario, design scope and evidence levels explicit."""
from pathlib import Path
import re
import unittest

PAPER = Path(__file__).resolve().parents[1]


class IntroClarityTests(unittest.TestCase):
    def test_abstract_uses_system_comparison_not_allocation_ablation(self):
        source = (PAPER / "biocoloop-main.tex").read_text()
        abstract = source.split(r"\begin{abstract}", 1)[1].split(r"\end{abstract}", 1)[0]
        self.assertNotRegex(abstract, r"10\.84|eight ties|twelve task|four held-out wins|main-table")
        self.assertIn("ten simulated laboratories", abstract)
        self.assertIn("single-laboratory fixed-model and direct-optimization baselines", abstract)
        results = (PAPER / "sections/05_results.tex").read_text()
        self.assertIn("+10.84-point mean effect", results)
        self.assertIn("proposal generation held fixed", results)

    def test_intro_defines_the_collaborative_setting_and_editable_design(self):
        intro = (PAPER / "sections/01_introduction.tex").read_text()
        self.assertIn("while retaining their own data", intro)
        self.assertIn("Each task uses its own predictor", intro)
        self.assertIn("We define an executable design", intro)
        self.assertIn("trainable prediction components", intro)
        self.assertIn("keeping the biological task and laboratory-local training interface fixed", intro)
        self.assertNotIn("In our implementation", intro)

    def test_experimental_contribution_names_the_comparisons(self):
        intro = (PAPER / "sections/01_introduction.tex").read_text()
        third = intro.split("Third, ", 1)[1]
        for term in ("laboratory participation", "proposal feedback", "training-budget allocation",
                     "research model", "participating laboratories", "independent datasets", "research iterations"):
            self.assertIn(term, third)
        self.assertNotIn("The contribution is this coupling", intro)


if __name__ == "__main__":
    unittest.main()
