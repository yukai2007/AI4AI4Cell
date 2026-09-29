"""Keep motivation, task scope and evidence attribution clear."""
from pathlib import Path
import unittest
PAPER = Path(__file__).resolve().parents[1]

class IntroClarityTests(unittest.TestCase):
    def test_abstract_uses_system_comparison_not_allocation_ablation(self):
        source = (PAPER / "biocoloop-main.tex").read_text()
        abstract = source.split(r"\begin{abstract}", 1)[1].split(r"\end{abstract}", 1)[0]
        self.assertNotRegex(abstract, r"10\.84|eight ties|twelve task|four held-out wins|main-table")
        # The abstract reports the coupling qualitatively and leaves numbers to the main text.
        self.assertIn("inner loop", abstract)
        self.assertIn("outer loop", abstract)
        intro = (PAPER / "sections/01_introduction.tex").read_text()
        self.assertIn("AI-Scientist-v2 and AI-Researcher", intro)
        results = (PAPER / "sections/05_results.tex").read_text()
        self.assertIn(r"Top-1 increases from 11.48\% to 22.32\%", results)
        self.assertIn("with positive gains in all three seeds", results)

    def test_motivation_and_per_task_predictors(self):
        intro = (PAPER / "sections/01_introduction.tex").read_text()
        self.assertLess(intro.lower().index("self-improving agents"), intro.lower().index("data-sharing constraints"))
        self.assertIn("different cell types", intro)
        self.assertIn("without pooling the underlying data", intro)
        self.assertIn("extends collaboration from parameter fitting to model development", intro)
        self.assertIn("inner loop for collaborative training and evaluation", intro)
        self.assertIn("limiting how local biological and experimental differences inform subsequent design choices", intro)
        self.assertIn("Local development evidence provides a complementary research signal", intro)
        self.assertNotIn("In our implementation", intro)
        method = (PAPER / "sections/03_method.tex").read_text()
        self.assertIn("same biological prediction task", method)
        self.assertIn("task-specific predictors", method)
        self.assertIn("optional residual prediction module", method)

    def test_contributions_are_bullets_and_include_findings(self):
        intro = (PAPER / "sections/01_introduction.tex").read_text()
        contributions = intro.split("Our contributions are:", 1)[1]
        self.assertEqual(contributions.count(r"\item "), 3)
        self.assertIn("inner loop for collaborative training and evaluation", contributions)
        self.assertIn("improved training allocation at matched budgets", contributions)
        self.assertIn("AI-Scientist-v2 and AI-Researcher baselines", intro)
        self.assertIn("drug--target", contributions)
        self.assertNotIn("The contribution is this coupling", intro)

if __name__ == "__main__":
    unittest.main()
