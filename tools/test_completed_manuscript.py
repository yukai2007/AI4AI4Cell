"""Check that manuscript evidence, source scope and figure provenance agree."""
from pathlib import Path
import hashlib
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CompletedManuscriptTests(unittest.TestCase):
    def test_active_appendix_uses_verified_tables_and_external_trace_archive(self):
        text = (ROOT / 'sections/23_appendix_core_sensitivity.tex').read_text()
        for name in ('lab_participation', 'lab_fixed_pool', 'transfer_independent',
                     'transfer_protein_loop', 'short6', 'long24', 'dynamics_long24',
                     'norman_retained_events'):
            self.assertIn(r'\input{tables/completed_ablation/' + name + '}', text)
        for name in ('trace_short6', 'trace_long24'):
            self.assertNotIn(r'\input{tables/completed_ablation/' + name + '}', text)
            self.assertTrue((ROOT / 'tables/completed_ablation' / (name + '.tex')).is_file())
        self.assertTrue((ROOT / 'tables/completed_ablation/proposal_trace.tsv').is_file())
        self.assertIn('504 attempted proposal slots', text)
        self.assertIn('reproducibility archive', text)
        self.assertNotIn(r'\input{tables/core_review/', text)
        self.assertNotIn('completed follow-up', text)

    def test_scope_and_adapter_are_explicit(self):
        text = (ROOT / 'sections/23_appendix_core_sensitivity.tex').read_text()
        for phrase in ('two independent external studies', 'source-specific prediction heads',
                       'not part of this extended protocol', 'DTI seed 42',
                       '100 training rounds', '12-design', '36-design',
                       '124 distinct compounds', '620 dose conditions',
                       'zero proposal slots', 'private continuous-response head'):
            self.assertIn(phrase, text)
        for name in ('source_client_mapping', 'proteomics_three_source'):
            self.assertIn(r'\input{tables/supplemental_20260923/' + name + '}', text)
        mapping = (ROOT / 'tables/supplemental_20260923/source_client_mapping.tex').read_text()
        self.assertIn('Four data collections', mapping)
        self.assertIn('ten PTPC clients remain partitions of one target corpus', mapping)

    def test_new_source_table_uses_verified_fixed_design_scores(self):
        snapshot = json.loads((ROOT / 'provenance/supplemental_proteomics_20260923/snapshot.json').read_text())
        receipt = snapshot['verified_receipt']
        self.assertEqual(receipt['status'], 'COMPLETE_VERIFIED')
        self.assertEqual(receipt['proposal_slots'], 0)
        self.assertEqual(receipt['rounds'], 100)
        self.assertEqual(len(receipt['results']), 4)
        self.assertTrue(all(x['max_absolute_error'] == 0 for x in receipt['results'].values()))
        table = ROOT / snapshot['table_path']
        self.assertEqual(sha(table), snapshot['table_sha256'])
        self.assertIn(r'\textbf{35.68}', table.read_text())
        self.assertIn(r'\textbf{74.75}', table.read_text())

    def test_main_result_narrative_distinguishes_proposal_history_and_allocation(self):
        text = (ROOT / 'sections/05_results.tex').read_text()
        self.assertIn(r'\input{tables/strong_v3/main}', text)
        self.assertIn(r'\input{tables/strong_v3/effects}', text)
        self.assertIn('seven ties and one decrease', text)
        self.assertIn('eight pairs tie', text)
        self.assertIn('800 aggregation rounds', text)
        self.assertIn('4.7 How does feedback change the research trajectory?', text)
        self.assertIn('4.4 Measured trajectories improve training allocation', text)
        self.assertLess(text.index('4.4 Measured trajectories'),
                        text.index('4.5 Learning from different'))
        self.assertNotIn(r'\input{tables/completed_ablation/summary}', text)
        self.assertIn(r'\label{fig:completed-short-dev}', text)
        appendix = (ROOT / 'sections/23_appendix_core_sensitivity.tex').read_text()
        self.assertNotIn(r'\label{fig:completed-short-dev}', appendix)
        self.assertIn(r'\label{fig:completed-long-dev}', appendix)

    def test_active_framework_is_verified_vector_redesign(self):
        stem = 'biocoloop_framework_v2'
        method = (ROOT / 'sections/03_method.tex').read_text()
        self.assertIn('figures/' + stem + '.pdf', method)
        receipt = json.loads((ROOT / 'figures' / (stem + '.provenance.json')).read_text())
        self.assertEqual(receipt['status'], 'STRUCTURAL_AND_VISUAL_CHECKS_PASSED')
        self.assertEqual(receipt['embedded_raster_assets'], [])
        self.assertEqual(receipt['pdf_embedded_images'], 0)
        self.assertEqual(receipt['text_outside_canvas'], [])
        self.assertEqual(receipt['slides_test_returncode'], 0)
        self.assertEqual(receipt['independent_visual_review']['status'], 'PASSED')
        self.assertEqual(sha(ROOT / 'tools/draw_framework_v2.js'), receipt['source_js_sha256'])
        for filename, digest in receipt['artifacts'].items():
            self.assertEqual(sha(ROOT / 'figures' / filename), digest)

    def test_previous_framework_and_user_source_remain_preserved(self):
        old = json.loads((ROOT / 'figures/biocoloop_framework.provenance.json').read_text())
        new = json.loads((ROOT / 'figures/biocoloop_framework_v2.provenance.json').read_text())
        self.assertTrue(new['old_editable_source_unchanged'])
        self.assertEqual(sha(ROOT / 'figures/biocoloop_framework.pptx'), new['old_editable_source_sha256'])
        self.assertEqual(new['old_editable_source_sha256'], old['derived_pptx_sha256'])
        self.assertEqual(sha(ROOT / 'figures/biocoloop_framework.pdf'), old['vector_pdf_sha256'])
        original = Path(old['original_user_source'])
        self.assertTrue(original.is_file())
        self.assertEqual(sha(original), old['original_user_source_sha256'])
        self.assertEqual(old['original_user_source_sha256'],
                         'f708424b3f30ed6f7813d66eeddc86e8adf58940091ac1a672703cf267028f81')


if __name__ == '__main__':
    unittest.main()
