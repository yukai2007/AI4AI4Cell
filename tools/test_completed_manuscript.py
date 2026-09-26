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
        appendix_text = (ROOT / 'sections/23_appendix_core_sensitivity.tex').read_text()
        self.assertIn(r'\input{tables/public_harness_comparison/main_public_harness_three_seed}', text)
        self.assertIn(r'\input{tables/strong_v3/effects}', text)
        self.assertIn('eight pairs tie', text + appendix_text)
        self.assertNotIn('seven ties and one decrease', text + appendix_text)
        self.assertIn('800 training rounds and 160 development evaluations', text)
        self.assertIn('4.7 How previous evaluation results affect subsequent proposals', text)
        self.assertIn('4.4 Early evaluation results guide further training', text)
        self.assertLess(text.index('4.4 Early evaluation'),
                        text.index('4.5 Learning from different'))
        self.assertNotIn(r'\input{tables/completed_ablation/summary}', text)
        self.assertNotIn(r'\label{fig:completed-short-dev}', text)
        self.assertIn(r'Figure~\ref{fig:completed-short-dev}', text)
        appendix = (ROOT / 'sections/23_appendix_core_sensitivity.tex').read_text()
        self.assertIn(r'\label{fig:completed-short-dev}', appendix)
        self.assertIn(r'\label{fig:completed-long-dev}', appendix)

    def test_active_framework_is_the_repaired_author_deck(self):
        method = (ROOT / 'sections/03_method.tex').read_text()
        self.assertIn('figures/biocoloop_framework_v3.pdf', method)
        receipt = json.loads((ROOT / 'figures/biocoloop_framework_v3.provenance.json').read_text())
        self.assertEqual(receipt['status'],
                         'STRUCTURAL_CHECKS_PASSED_VISUAL_REVIEW_REQUIRED')
        self.assertEqual(receipt['text_outside_canvas'], [])
        self.assertEqual(receipt['slides_test_returncode'], 0)
        self.assertEqual(receipt['aspect_ratio'], '4:3')
        self.assertTrue(receipt['source_deck_unchanged'])
        self.assertEqual(receipt['source_deck'],
                         str(Path('/liziqing/yukai/AI4AI4Cell/0925_repaired_v3.pptx')))
        self.assertEqual(sha(Path(receipt['source_deck'])), receipt['source_deck_sha256'])
        repairs = {item['id'] for item in receipt['declared_repairs']}
        self.assertEqual(repairs, {'flatten_alternate_content', 'math_run_to_text',
                                   'propose_card_fit', 'fixed_model_label_contrast',
                                   'drop_local_data_note', 'update_figure_terms',
                                   'candidate_configuration_label',
                                   'development_evidence_label',
                                   'aggregated_evidence_label'})
        for label in ['model design and training hyperparameters',
                      'evidence ℰₜ', '(one card per trial)',
                      '(configuration, dev score, decision)']:
            self.assertIn(label, receipt['required_labels_present'])
        self.assertNotIn('Candidate design', receipt['required_labels_present'])
        self.assertEqual(receipt['embedded_raster_assets'],
                         sorted(receipt['embedded_raster_assets']))
        self.assertEqual(receipt['pdf_embedded_images'],
                         len(receipt['placed_raster_assets']))
        self.assertEqual(sorted(receipt['placed_raster_assets']),
                         sorted(set(receipt['placed_raster_assets'])))
        dropped = set(receipt['embedded_raster_assets']) - set(receipt['placed_raster_assets'])
        self.assertEqual(len(dropped), 2)
        for filename, digest in receipt['artifacts'].items():
            self.assertEqual(sha(ROOT / 'figures' / filename), digest)
        adapter = (ROOT / 'tools/adapt_framework_v3.py').read_text()
        self.assertIn('mc:AlternateContent', adapter)
        self.assertIn('design_id', adapter)

    def test_active_paradigm_figure_is_the_author_deck(self):
        intro = (ROOT / 'sections/01_introduction.tex').read_text()
        self.assertIn('assets/paradigm_comparison_v3.pdf', intro)
        receipt = json.loads((ROOT / 'assets/paradigm_comparison_v3.provenance.json').read_text())
        self.assertEqual(receipt['status'],
                         'STRUCTURAL_CHECKS_PASSED_VISUAL_REVIEW_REQUIRED')
        repairs = {item['id']: item for item in receipt['declared_repairs']}
        self.assertEqual(set(repairs), {'trim_canvas'})
        self.assertIn('7045325 -> 5136739 EMU', repairs['trim_canvas']['change'])
        self.assertTrue(receipt['source_deck_unchanged'])
        self.assertEqual(receipt['source_deck'],
                         str(Path('/liziqing/yukai/AI4AI4Cell/try/paradigm_comparison_editable.pptx')))
        self.assertEqual(sha(Path(receipt['source_deck'])), receipt['source_deck_sha256'])
        copied = ROOT / 'assets/paradigm_comparison_v3.pptx'
        self.assertEqual(sha(copied), receipt['artifacts']['paradigm_comparison_v3.pptx'])
        self.assertEqual(receipt['text_outside_canvas'], [])
        self.assertEqual(receipt['slides_test_returncode'], 0)
        self.assertAlmostEqual(float(receipt['aspect_ratio']), 12192000 / 5136739, places=3)
        for filename, digest in receipt['artifacts'].items():
            self.assertEqual(sha(ROOT / 'assets' / filename), digest)
        adapter = (ROOT / 'tools/adapt_paradigm_v3.py').read_text()
        self.assertIn('paradigm_comparison_editable.pptx', adapter)
        self.assertIn('Centralized bio-agent', adapter)

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
