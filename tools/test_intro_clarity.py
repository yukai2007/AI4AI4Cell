"""Keep motivation, task scope and evidence attribution clear."""
from pathlib import Path
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

    def test_motivation_and_per_task_predictors(self):
        intro = (PAPER / "sections/01_introduction.tex").read_text()
        self.assertLess(intro.index("virtual cell"), intro.index("Data-sharing restrictions"))
        self.assertIn("different cell type", intro)
        self.assertIn("a laboratory denotes a data holder", intro)
        self.assertIn("task-specific predictor", intro)
        self.assertIn("evidence card", intro)
        self.assertNotIn("In our implementation", intro)
        method = (PAPER / "sections/03_method.tex").read_text()
        self.assertIn("same biological prediction task", method)
        self.assertIn("task-specific predictors", method)
        self.assertIn("optional residual prediction module", method)

    def test_contributions_are_bullets_and_include_findings(self):
        intro = (PAPER / "sections/01_introduction.tex").read_text()
        contributions = intro.split("Our contributions are:", 1)[1]
        self.assertEqual(contributions.count(r"\item "), 3)
        self.assertIn("evidence-guided research harness", contributions)
        self.assertIn("four of five", contributions)
        self.assertIn("source compatibility", contributions)
        self.assertNotIn("The contribution is this coupling", intro)

if __name__ == "__main__":
    unittest.main()
