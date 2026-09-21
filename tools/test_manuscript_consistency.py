"""Editorial regressions independent of any favorable score or completion count."""
from pathlib import Path
import re
import unittest

PAPER = Path(__file__).resolve().parents[1]


class ManuscriptConsistencyTests(unittest.TestCase):
    def test_active_framing_and_implementation_disclosure(self):
        source = (PAPER / 'ai4ai4cell-main.tex').read_text()
        self.assertIn('Collaborative Evidence-Guided Research', source.replace(r'\\', ' '))
        abstract = source.split(r'\begin{abstract}', 1)[1].split(r'\end{abstract}', 1)[0]
        self.assertNotRegex(abstract.lower(), r'federat|\bsota\b')
        self.assertIn('six-arm ablation', abstract)
        self.assertIn('retrospective held-out', abstract)
        self.assertIn('FedAvg', (PAPER / 'sections/03_method.tex').read_text())

    def test_seed_counts_are_generated_not_stale_literal_words(self):
        source = (PAPER / 'ai4ai4cell-main.tex').read_text()
        source += (PAPER / 'sections/05_results.tex').read_text()
        self.assertIn(r'\StrongDTISeeds{}', source)
        self.assertNotRegex(source.lower(), r'(one|two) completed tapb seeds?')
        self.assertNotIn('same trainer, research interface', source)

    def test_main_figures_match_collaborative_framing(self):
        for filename in ('paradigm_comparison.svg', 'unified_pipeline.svg'):
            text = (PAPER / 'assets' / filename).read_text()
            self.assertNotRegex(text.lower(), 'federat')
            self.assertIn('collaborative', text.lower())

    def test_current_uncertainty_is_included(self):
        text = (PAPER / 'sections/22_appendix_unified_protocol.tex').read_text()
        self.assertIn(r'\input{tables/strong_v3/dti_uncertainty}', text)
        self.assertIn('after training and held-out scoring', text)
        self.assertIn('between-training-seed', text)


if __name__ == '__main__':
    unittest.main()
