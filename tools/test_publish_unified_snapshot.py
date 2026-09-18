import tempfile
from pathlib import Path
import unittest
from publish_unified_snapshot import TASKS, ARMS, score_table, effect_table


def fixture():
    snapshot = dict(tasks={})
    for task, label in TASKS:
        values = {arm: dict(primary=.6 if arm.startswith('federated') else .4) for arm, _, _ in ARMS}
        snapshot['tasks'][task] = dict(label=label, runs={'42':dict(scores=values), '43':None, '44':None})
    snapshot['tasks']['native_dti']['runs']['42'] = None
    return snapshot


class SnapshotTests(unittest.TestCase):
    def test_development_ties_bold_and_pending_not_zero(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            score_table(fixture(), out)
            text = (out/'development.tex').read_text()
            self.assertEqual(text.count(r'\textbf{60.00}'), 12)
            self.assertIn('N/A', text)
            self.assertNotIn('0.00', text.replace('60.00', '').replace('40.00', ''))

    def test_final_not_filled_from_development(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            score_table(fixture(), out, final=True)
            text = (out/'final.tex').read_text()
            self.assertNotIn('60.00', text)
            self.assertNotIn('40.00', text)
            self.assertEqual(text.count('N/A'), 36)  # 7 x 5 cells and caption

    def test_attribution_and_incomplete_seed_summary(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            effect_table(fixture(), out)
            text = (out/'effects.tex').read_text()
            self.assertIn('Loop $-$ direct (10 labs) & N/A & +0.00 & +0.00 & +0.00 & +0.00', text)
            self.assertIn('10 $-$ 1 labs (both loop) & N/A & +20.00', text)
            self.assertIn('3-seed loop $-$ direct & N/A & N/A & N/A & N/A & N/A', text)

    def test_three_seed_summary_only_when_complete(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            data = fixture()
            for task, _ in TASKS:
                run = data['tasks'][task]['runs']['42']
                data['tasks'][task]['runs'] = {str(seed):run for seed in [42,43,44]}
            effect_table(data, out)
            text = (out/'effects.tex').read_text()
            self.assertIn('3-seed FL $-$ single (loop) & N/A & $+20.00\\pm0.00$', text)


if __name__ == '__main__':
    unittest.main()
