"""Keep motivation, task scope and evidence attribution clear."""
from pathlib import Path
import unittest
PAPER = Path(__file__).resolve().parents[1]

class IntroClarityTests(unittest.TestCase):
    def test_abstract_uses_system_comparison_not_allocation_ablation(self):
        source = (PAPER / "biocoloop-main.tex").read_text()
        abstract = source.split(r"\begin{abstract}", 1)[1].split(r"\end{abstract}", 1)[0]
        self.assertNotRegex(abstract, r"10\.84|eight ties|twelve task|four held-out wins|main-table")
        self.assertIn("matched Qwen2.5 and GPT-5.6 Luna comparisons", abstract)
        self.assertIn("four of five primary endpoints", abstract)
        results = (PAPER / "sections/05_results.tex").read_text()
        self.assertIn("+10.84-point mean effect", results)
        self.assertIn("proposal generation held fixed", results)

    def test_motivation_and_per_task_predictors(self):
        intro = (PAPER / "sections/01_introduction.tex").read_text()
        self.assertLess(intro.index("AI-for-AI systems"), intro.index("data-sharing constraints"))
        self.assertIn("different cell types", intro)
        self.assertIn("Raw data remain within each laboratory", intro)
        self.assertIn("extends collaboration from parameter fitting to model development", intro)
        self.assertIn("inner loop for collaborative training and evaluation", intro)
        self.assertIn("This can be restrictive when laboratories contain data with different biological or experimental characteristics", intro)
        self.assertIn("This leaves a gap between these two lines of work", intro)
        self.assertNotIn("In our implementation", intro)
        method = (PAPER / "sections/03_method.tex").read_text()
        self.assertIn("same biological prediction task", method)
        self.assertIn("task-specific predictors", method)
        self.assertIn("optional residual prediction module", method)

    def test_contributions_are_bullets_and_include_findings(self):
        intro = (PAPER / "sections/01_introduction.tex").read_text()
        contributions = intro.split("Our contributions are summarized as:", 1)[1]
        self.assertEqual(contributions.count(r"\item "), 3)
        self.assertIn("inner loop for collaborative training and evaluation", contributions)
        self.assertIn("four of five primary endpoints", contributions)
        self.assertIn("accumulated evaluation evidence can improve research decisions", contributions)
        self.assertIn("drug--target", contributions)
        self.assertNotIn("The contribution is this coupling", intro)

if __name__ == "__main__":
    unittest.main()
