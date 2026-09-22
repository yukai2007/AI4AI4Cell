"""Editorial regressions independent of any favorable score or completion count."""
from pathlib import Path
import json
import re
import unittest

PAPER = Path(__file__).resolve().parents[1]


class ManuscriptConsistencyTests(unittest.TestCase):
    def test_active_framing_and_implementation_disclosure(self):
        source = (PAPER / 'ai4ai4cell-main.tex').read_text()
        self.assertIn('Collaborative Evidence-Guided Research', source.replace(r'\\', ' '))
        abstract = source.split(r'\begin{abstract}', 1)[1].split(r'\end{abstract}', 1)[0]
        self.assertNotRegex(abstract.lower(), r'federat|\bsota\b')
        self.assertIn('AI4AI4Cell, a collaborative research framework', abstract)
        self.assertIn('Collaborative learning typically optimizes fixed models', abstract)
        self.assertIn('Across three biological settings', abstract)
        self.assertNotIn(r'\Strong', abstract)
        self.assertIn('FedAvg', (PAPER / 'sections/03_method.tex').read_text())

    def test_official_submission_header_and_spacing_are_not_patched(self):
        source = (PAPER / 'ai4ai4cell-main.tex').read_text()
        self.assertIn(r'\usepackage{iclr2027_conference}', source)
        self.assertNotIn(r'\patchcmd{\@maketitle}', source)
        self.assertNotIn(r'\setlength{\parskip}', source)
        self.assertNotIn(r'\iclrfinalcopy', source)

    def test_seed_counts_stay_out_of_main_presentation(self):
        source = (PAPER / 'ai4ai4cell-main.tex').read_text()
        source += (PAPER / 'sections/05_results.tex').read_text()
        self.assertNotIn(r'\StrongDTISeeds{}', source)
        self.assertNotIn('planned seeds', source)
        self.assertIn('Completed seeds', (PAPER / 'tables/strong_v3/ablation.tex').read_text())
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

    def test_compute_matched_loop_claims_are_bound_to_public_summary(self):
        summary = json.loads((PAPER / 'provenance/v6_loop_summary.json').read_text())
        table = (PAPER / 'tables/strong_v3/effects.tex').read_text()
        results = (PAPER / 'sections/05_results.tex').read_text()
        self.assertEqual(summary['heldout_wins_ties_losses'], [4, 8, 0])
        self.assertAlmostEqual(
            summary['heldout_loop_minus_direct']['norman_double_gene']['mean'],
            0.10839506172839508)
        for token in ('+10.84', '[4.54, 17.73]', '4/8/0'):
            self.assertIn(token, table + results)
        self.assertIn('800 full-client', table)
        self.assertIn('no DTI held-out claim', table)


if __name__ == '__main__':
    unittest.main()
