"""Validate the completed publication snapshot without training or private arrays."""
import csv
import hashlib
import json
from pathlib import Path
import unittest

import publish_completed_ablation as pub


class CompletedPublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot = pub.read(pub.OUT / 'snapshot.json')
        cls.provenance = pub.read(pub.OUT / 'provenance.json')
        cls.final = pub.read(pub.FINAL)
        cls.legacy = pub.read(pub.LEGACY)

    def test_verified_inputs_and_generated_outputs_are_bound(self):
        self.assertEqual(self.final['status'], 'COMPLETE')
        for relative, expected in self.provenance['input_sha256'].items():
            self.assertEqual(pub.sha(pub.ROOT / relative), expected, relative)
        for relative, expected in self.provenance['outputs_sha256'].items():
            self.assertEqual(pub.sha(pub.ROOT / relative), expected, relative)

    def test_lab_matrix_has_two_separate_complete_settings(self):
        rows = self.snapshot['laboratory']
        self.assertEqual(len(rows), 10)
        self.assertEqual({r['family'] for r in rows}, {'participation', 'partition'})
        native = {r['case']: r['primary'] for r in self.final['groups']['dti_lab_count']['rows']}
        for row in rows:
            self.assertEqual(set(row['by_k']), {'1', '2', '5', '10'})
            self.assertEqual(row['seeds'], [61] if row['task'] == 'native_tapb' else [61, 62, 63])
            if row['task'] == 'native_tapb':
                for k in pub.K_VALUES:
                    self.assertEqual(row['by_k'][str(k)], [native[f'{row["family"]}_k{k}']])
            else:
                legacy = sorted([s for s in self.legacy['studies'] if s['task'] == row['task'] and
                                 s['relative_path'].startswith('lab_count/')], key=lambda s: s['seed'])
                for k in pub.K_VALUES:
                    self.assertEqual(row['by_k'][str(k)], [s['scores'][f'{row["family"]}_k{k}']['primary'] for s in legacy])

    def test_independent_sources_retain_combination_and_negative_results(self):
        rows = self.snapshot['independent_transfer']
        self.assertEqual(len(rows), 14)
        self.assertEqual([r['independent_sources'] for r in rows if r['task'] == 'PTPC auxiliary'], [2] * 4)
        self.assertEqual(sum(r['task'] == 'DTI' for r in rows), 5)
        self.assertEqual(sum(r['task'] == 'VCC' for r in rows), 5)
        self.assertLess(next(r for r in rows if r['case'] == 'cross_plus_all')['deltas'][0], 0)
        self.assertLess(next(r for r in rows if r['case'] == 'cross_plus_biosnap')['deltas'][0], 0)
        self.assertTrue(all(d < 0 for r in rows if r['case'] in ('plus_replogle', 'plus_nadig', 'plus_all') for d in r['deltas']))

    def test_contexts_are_separate_and_unchanged(self):
        self.assertEqual(len(self.snapshot['context_transfer']), 5)
        self.assertTrue(all(not row['independent_studies'] for row in self.snapshot['context_transfer']))
        self.assertFalse(self.snapshot['publication_notes']['contexts_counted_as_independent'])
        self.assertNotIn('HCC1143', (pub.OUT / 'transfer_independent.tex').read_text())
        self.assertIn('HCC1143', (pub.OUT / 'transfer_contexts.tex').read_text())

    def test_all_short_and_long_protocols_are_separate(self):
        short = [r for r in self.snapshot['loops'] if r['protocol'] == 'short6']
        long = [r for r in self.snapshot['loops'] if r['protocol'] == 'long24']
        self.assertEqual((len(short), len(long)), (10, 8))
        self.assertTrue(all(r['design_count'] == 12 and r['slots'] == 6 for r in short))
        self.assertTrue(all(r['design_count'] == 36 and r['slots'] == 24 for r in long))
        self.assertFalse(any(r['task'] == 'native_tapb' for r in long))
        for row in short:
            self.assertEqual(row['seed'], 42 if row['task'] == 'native_tapb' else 61)
            self.assertEqual([p['budget'] for p in row['prefixes']], [0, 1, 2, 4, 6])
        for row in long:
            self.assertEqual([p['budget'] for p in row['prefixes']], [0, 1, 2, 4, 6, 8, 12, 16, 20, 24])

    def test_native_luna_negative_endpoint_is_visible(self):
        row = next(r for r in self.snapshot['loops'] if r['task'] == 'native_tapb' and r['backend'] == 'luna')
        last = row['prefixes'][-1]
        self.assertAlmostEqual(last['loop_minus_direct_pp'], -.33210984948508493)
        table = (pub.OUT / 'summary.tex').read_text()
        self.assertIn('94.60', table)
        self.assertIn('94.27', table)

    def test_all_attempted_proposals_have_machine_readable_trace(self):
        rows = [t for r in self.snapshot['loops'] for t in r['traces']]
        self.assertEqual(len(rows), 504)
        with (pub.OUT / 'proposal_trace.tsv').open() as handle:
            saved = list(csv.DictReader(handle, delimiter='\t'))
        self.assertEqual(len(saved), 504)
        self.assertGreater(sum(r['outcome'] == 'invalid' for r in rows), 0)
        for run in self.snapshot['loops']:
            for mode in ('direct', 'loop'):
                self.assertEqual([r['slot'] for r in run['traces'] if r['mode'] == mode], list(range(1, run['slots'] + 1)))

    def test_common_target_diagnostic_distinguishes_speed_from_final_score(self):
        row = next(r for r in self.snapshot['loops'] if r['task'] == 'norman_double_corrected' and
                   r['backend'] == 'luna' and r['protocol'] == 'long24')
        self.assertEqual(row['modes']['direct']['first_common_target'], 22)
        self.assertEqual(row['modes']['loop']['first_common_target'], 4)
        self.assertAlmostEqual(row['prefixes'][-1]['loop_minus_direct_pp'], 0)

    def test_common_target_matches_final_audit_for_every_light_run(self):
        for audited in self.final['groups']['loop_light']['rows']:
            row = next(r for r in self.snapshot['loops'] if r['task'] == audited['task'] and
                       r['backend'] == audited['backend'] and r['protocol'] == audited['protocol'])
            self.assertAlmostEqual(row['common_development_target'], audited['common_development_target'])
            for mode in ('direct', 'loop'):
                self.assertEqual(row['modes'][mode]['first_common_target'],
                                 audited['first_slot_at_common_development_target'][mode])
        vcc = next(r for r in self.snapshot['loops'] if r['task'] == 'vcc_corrected' and
                   r['backend'] == 'luna' and r['protocol'] == 'long24')
        self.assertEqual(vcc['modes']['direct']['first_common_target'], 16)
        self.assertEqual(vcc['modes']['loop']['first_common_target'], 9)
        self.assertIsNone(vcc['modes']['direct']['first_higher_terminal_target'])
        self.assertEqual(vcc['modes']['loop']['first_higher_terminal_target'], 10)

    def test_bold_display_ties_and_no_pending_placeholders(self):
        self.assertEqual(pub.best_flags([[.90], [.90], [.80]]), [True, True, False])
        self.assertEqual(pub.best_flags([[.900001], [.900002]]), [True, True])
        for file in pub.OUT.glob('*.tex'):
            text = file.read_text()
            self.assertNotIn('0/3', text)
            self.assertNotIn('N/A', text)
        text = (pub.OUT / 'summary.tex').read_text()
        self.assertEqual(text.count('Qwen:'), 2)
        self.assertEqual(text.count('Luna:'), 2)
        self.assertIn(r'\textbf{94.27}', text)
        self.assertFalse(self.snapshot['publication_notes']['cross_metric_average'])

    def test_pdf_figures_are_vector_and_text_stays_inside_canvas(self):
        import fitz
        files = sorted((pub.PAPER / 'assets').glob('completed_*.pdf'))
        self.assertEqual(len(files), 5)
        for file in files:
            with fitz.open(file) as doc:
                self.assertEqual(len(doc), 1)
                page = doc[0]
                self.assertFalse(page.get_images())
                self.assertAlmostEqual(page.rect.width, 5.5 * 72, places=2)
                bounds = page.rect + (-1, -1, 1, 1)
                for block in page.get_text('dict')['blocks']:
                    for line in block.get('lines', []):
                        for span in line['spans']:
                            self.assertTrue(bounds.contains(fitz.Rect(span['bbox'])), (file.name, span['text'], span['bbox']))


if __name__ == '__main__':
    unittest.main()
