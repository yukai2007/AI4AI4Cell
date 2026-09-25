"""Editorial regressions independent of any favorable score or completion count."""
from pathlib import Path
import json
import re
import unittest

PAPER = Path(__file__).resolve().parents[1]


class ManuscriptConsistencyTests(unittest.TestCase):
    def test_active_framing_and_implementation_disclosure(self):
        source = (PAPER / 'biocoloop-main.tex').read_text()
        self.assertIn('Collaborative Agentic Research', source.replace(r'\\', ' '))
        abstract = source.split(r'\begin{abstract}', 1)[1].split(r'\end{abstract}', 1)[0]
        self.assertNotRegex(abstract.lower(), r'federat|\bsota\b')
        self.assertIn('BioCoLoop, a collaborative research framework', abstract)
        self.assertIn('Collaborative learning can train shared models', abstract)
        self.assertIn('Across drug--target interaction prediction', abstract)
        self.assertNotIn(r'\Strong', abstract)
        self.assertIn(r'\citep{McMahan2017}', (PAPER / 'sections/03_method.tex').read_text())

    def test_official_submission_header_and_spacing_are_not_patched(self):
        source = (PAPER / 'biocoloop-main.tex').read_text()
        self.assertIn(r'\usepackage{iclr2027_conference}', source)
        self.assertNotIn(r'\patchcmd{\@maketitle}', source)
        self.assertNotIn(r'\setlength{\parskip}', source)
        self.assertNotIn(r'\iclrfinalcopy', source)

    def test_seed_counts_stay_out_of_main_presentation(self):
        source = (PAPER / 'biocoloop-main.tex').read_text()
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
        self.assertIn('BioCoLoop Statistical Supplement', text)
        supplement = (PAPER / 'statistical-supplement.tex').read_text()
        self.assertIn(r'\input{tables/strong_v3/dti_uncertainty}', supplement)
        self.assertIn(r'\input{tables/strong_v3/uncertainty}', supplement)
        self.assertIn('retained predictions', text)
        self.assertIn('training/search variability on fixed partitions', text)

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
        self.assertNotIn('DTI: TAPB & Dev.', table)
        self.assertIn('DTI development replay is in Appendix A', table)


if __name__ == '__main__':
    unittest.main()
