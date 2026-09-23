"""Check the published sensitivity snapshot without accessing private arrays."""
from pathlib import Path
import hashlib
import json
import unittest

PAPER = Path(__file__).resolve().parents[1]


class CoreReviewTests(unittest.TestCase):
    def test_snapshot_is_bound_to_independent_rescore(self):
        path = PAPER/'provenance/coauthor_review_20260922/core_verification.json'
        summary = json.loads((PAPER/'tables/core_review/snapshot.json').read_text())
        self.assertEqual(summary['verification_sha256'], hashlib.sha256(path.read_bytes()).hexdigest())
        verification = json.loads(path.read_text())
        self.assertEqual(verification['status'], 'PASS')
        self.assertEqual(len(summary['studies']), verification['result_files'])
        self.assertEqual(len(summary['studies']), len(verification['records']))
        self.assertGreaterEqual(len(summary['studies']), 24)
        self.assertTrue(all(r['status'] == 'PASS' for r in verification['records']))

    def test_missing_and_negative_outcomes_are_retained(self):
        tables = PAPER/'tables/core_review'
        snapshot = json.loads((tables/'snapshot.json').read_text())
        labs = [r for r in snapshot['studies'] if r['relative_path'].startswith('lab_count/')]
        if len(labs) < 15:
            self.assertIn('N/A', (tables/'lab_count.tex').read_text())
        self.assertIn('49.63', (tables/'lab_count.tex').read_text())
        self.assertIn('27.33', (tables/'transfer.tex').read_text())
        key = 'model_loop/vcc_corrected/seed61/qwen/heldout/results.json'
        vcc = next(r for r in snapshot['studies'] if r['relative_path'] == key)
        self.assertAlmostEqual(vcc['scores']['loop_b24']['primary']*100, 19.61, places=2)
        direct = [r for r in snapshot['curves'][key] if r['mode'] == 'direct' and r['slot'] > 0]
        self.assertEqual(sum(r['valid'] for r in direct), 11)
        self.assertEqual(len(direct), 24)

    def test_all_twenty_four_comments_have_dispositions(self):
        folder = PAPER/'provenance/coauthor_review_20260922'
        annotations = json.loads((folder/'annotations.json').read_text())['annotations']
        response = (folder/'RESPONSE.zh-CN.md').read_text()
        self.assertEqual(sum(bool(x['comment']) for x in annotations), 24)
        for annot in annotations:
            self.assertIn('x'+str(annot['xref']), response)

    def test_budget_diagnostics_cover_the_same_snapshot(self):
        tables = PAPER/'tables/core_review'
        snapshot = json.loads((tables/'snapshot.json').read_text())
        analysis = json.loads((tables/'budget_analysis.json').read_text())
        self.assertEqual(analysis['snapshot_sha256'], hashlib.sha256((tables/'snapshot.json').read_bytes()).hexdigest())
        self.assertEqual({j['relative_path']+'/heldout/results.json' for j in analysis['jobs']}, set(snapshot['curves']))
        norman = next(j for j in analysis['jobs'] if j['task']=='norman_double_corrected' and j['seed']==61 and j['backend']=='luna')
        self.assertEqual(norman['comparisons']['first_slot_at_common_target'], {'direct':22, 'loop':4})
        self.assertEqual(norman['comparisons']['final_test_delta'], 0)

    def test_method_is_mechanism_not_a_training_recipe(self):
        method = (PAPER/'sections/03_method.tex').read_text()
        self.assertNotIn(r'\begin{enumerate}', method)
        self.assertNotIn('Qwen2.5', method)
        self.assertIn('training allocation', method)
        self.assertIn('proposal revision', method)
        entry = (PAPER/'ai4ai4cell-main.tex').read_text()
        self.assertNotIn('sections/06_discussion', entry)
        self.assertIn('sections/23_appendix_core_sensitivity', entry)


if __name__ == '__main__':
    unittest.main()
