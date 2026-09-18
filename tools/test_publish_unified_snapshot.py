import tempfile
from pathlib import Path
import unittest
import hashlib
import json
from publish_unified_snapshot import (TASKS, ARMS, MAIN_ARMS, HELDOUT_ROLE,
    score_table, effect_table, collect_heldout, heldout_effect_table,
    heldout_secondary_table, snapshot_macros)


def fixture():
    snapshot = dict(tasks={})
    for task, label in TASKS:
        values = {arm: dict(primary=.6 if arm.startswith('federated') else .4) for arm, _, _ in ARMS}
        snapshot['tasks'][task] = dict(label=label, runs={'42':dict(scores=values), '43':None, '44':None})
    snapshot['tasks']['native_dti']['runs']['42'] = None
    return snapshot


def heldout_fixture():
    heldout = dict(role=HELDOUT_ROLE, seeds_requested=[42, 43, 44], tasks={})
    for task, label in TASKS:
        scores = {arm: dict(primary=.6 if arm.startswith('federated') else .4,
            secondary={key: .4 for key in ['ap', 'auroc', 'bce', 'accuracy_at_0_5',
                'accuracy', 'mrr', 'top3', 'cross_entropy']}) for arm, _, _ in ARMS}
        runs = {'42': dict(scores=scores), '43': None, '44': None}
        if task == 'ptpc':
            runs['43'] = json.loads(json.dumps(runs['42']))
            for value in runs['43']['scores'].values(): value['primary'] += .04
        if task == 'native_dti': runs['42'] = None
        heldout['tasks'][task] = dict(label=label, runs=runs)
    return heldout


def write_receipt_fixture(root):
    path = root/'ptpc/seed42'; path.mkdir(parents=True)
    arms = {arm: dict(checkpoint=f'/checkpoint/{arm}') for arm, _, _ in ARMS}
    seal = dict(task='ptpc', seed=42, role=HELDOUT_ROLE, feedback_to_controller=False,
        sealed_unix=1, definition=dict(rounds=100, slots=6, seed=42, test_read=False),
        predictor='random linear head; NOT native ProteinTalks', arms=arms)
    (path/'seal.json').write_text(json.dumps(seal))
    result = dict(schema='unified-v3-heldout-results-v1', task='ptpc', seed=42,
        role=HELDOUT_ROLE, feedback_to_controller=False, heldout_decoded_unix=2,
        completed_unix=3, primary_metric='ap', uncertainty={},
        seal_sha256=hashlib.sha256((path/'seal.json').read_bytes()).hexdigest(),
        results={arm: dict(primary=.7, metrics=dict(ap=.7), checkpoint=arms[arm]['checkpoint']) for arm in arms})
    (path/'results.json').write_text(json.dumps(result))
    verification = dict(status='PASS', task='ptpc', seed=42, seal_before_response_access=True,
        all_checkpoint_hashes_match=True, common_original_roster=True,
        rescored={arm: dict(metrics=dict(ap=.7)) for arm in arms})
    (path/'verification.json').write_text(json.dumps(verification))
    (path/'audit.json').write_text(json.dumps(dict(status='PASS', original_scorer=True,
        common_roster_all_arms=True, no_test_checkpoint_selection=True, no_controller_feedback=True)))
    (root/'summary.json').write_text(json.dumps(dict(role=HELDOUT_ROLE, seeds_requested=[42,43,44],
        tasks=dict(ptpc=dict(completed_seeds=[42], arms={arm:dict(per_seed={'42':.7}) for arm in arms})))))
    return path


class SnapshotTests(unittest.TestCase):
    def test_development_ties_bold_and_pending_not_zero(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            score_table(fixture(), out)
            text = (out/'development.tex').read_text()
            self.assertEqual(text.count(r'\textbf{60.00}'), 4)
            self.assertIn('N/A', text)
            self.assertNotIn('0.00', text.replace('60.00', '').replace('40.00', ''))
            self.assertIn('Direct optimize', text)
            self.assertIn('harness-free direct', text)
            self.assertIn('10 & Our harness', text)
            self.assertNotIn('Our loop', text)
            self.assertNotIn('Cosine reference', text)

    def test_main_bolds_all_displayed_ties_not_hidden_controls(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            data = fixture()
            for task, _ in TASKS:
                run = data['tasks'][task]['runs']['42']
                if run is None:
                    continue
                for arm, _, _ in MAIN_ARMS:
                    run['scores'][arm]['primary'] = .5
                # An ablation-only score must not suppress displayed maxima.
                run['scores']['federated_direct']['primary'] = .8
            score_table(data, out)
            text = (out/'development.tex').read_text()
            self.assertEqual(text.count(r'\textbf{50.00}'), 12)
            self.assertNotIn('80.00', text)

    def test_full_ablation_keeps_every_control_and_bolds_ties(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            score_table(fixture(), out, full=True)
            text = (out/'ablation.tex').read_text()
            self.assertEqual(text.count(r'\textbf{60.00}'), 12)
            self.assertIn('1 & Our loop', text)
            self.assertIn('10 & Direct', text)
            self.assertIn('tab:unified-ablation', text)

    def test_final_not_filled_from_development(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            score_table(fixture(), out, final=True)
            text = (out/'final.tex').read_text()
            self.assertNotIn('60.00', text)
            self.assertNotIn('40.00', text)
            self.assertEqual(text.count('N/A'), 16)  # 3 x 5 cells and caption

    def test_attribution_and_incomplete_seed_summary(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            effect_table(fixture(), out)
            text = (out/'effects.tex').read_text()
            self.assertIn('Loop $-$ direct (10 labs) & N/A & +0.00 & +0.00 & +0.00 & +0.00', text)
            self.assertIn('Loop $-$ direct (1 lab) & N/A & +0.00', text)
            self.assertIn('10 $-$ 1 labs (both fixed) & N/A & +20.00', text)
            self.assertIn('10 $-$ 1 labs (both direct) & N/A & +20.00', text)
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

    def test_heldout_actual_means_seed_counts_and_role(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory); data = fixture(); data['heldout'] = heldout_fixture()
            score_table(data, out, final=True)
            text = (out/'final.tex').read_text()
            self.assertIn(r'\textbf{62.00}', text)
            self.assertIn(r'Completed seeds ($n/3$)} & 0/3 & 2/3 & 1/3 & 1/3 & 1/3', text)
            self.assertIn('retrospective held-out', text)
            self.assertIn('not blind confirmation', text)
            self.assertIn('PTPC (linear)', text)
            self.assertIn('not native ProteinTalks', text)
            self.assertIn('1 & Fixed model & N/A & 42.00', text)
            self.assertNotIn('three-seed mean', text)

    def test_heldout_all_rounded_ties_and_secondary_loss_direction(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory); heldout = heldout_fixture(); data = dict(heldout=heldout)
            for run in heldout['tasks']['ptpc']['runs'].values():
                if run is not None:
                    run['scores']['single_direct']['primary'] = run['scores']['federated_loop']['primary']+.000001
                    run['scores']['federated_loop']['secondary']['bce'] = .2
            score_table(data, out, final=True)
            self.assertEqual((out/'final.tex').read_text().count(r'\textbf{62.00}'), 2)
            score_table(data, out, final=True, full=True)
            text = (out/'heldout_ablation.tex').read_text()
            self.assertEqual(text.count(r'\textbf{62.00}'), 4)
            self.assertIn(r'\pm2.83', text)
            self.assertIn('no SD is estimated for a single seed', text)
            heldout_secondary_table(heldout, out)
            text = (out/'heldout_secondary.tex').read_text()
            self.assertIn(r'\textbf{0.2000}', text)

    def test_heldout_effects_and_macros_preserve_negative_and_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory); heldout = heldout_fixture()
            heldout['tasks']['norman_double_pilot']['runs']['42']['scores']['single_loop']['primary'] = .7
            heldout_effect_table(heldout, out); snapshot_macros(heldout, out)
            self.assertIn('10 $-$ 1 labs (both loop) & N/A & +20.00 & +20.00 & -10.00 & +20.00',
                          (out/'heldout_effects.tex').read_text())
            text = (out/'snapshot_stats.tex').read_text()
            self.assertIn(r'\newcommand{\HeldoutPTPCSeeds}{2}', text)
            self.assertIn(r'\newcommand{\HeldoutPTPCHarness}{62.00}', text)
            self.assertIn(r'\newcommand{\HeldoutPTPCThreeSeedHarness}{N/A}', text)
            self.assertIn(r'\newcommand{\HeldoutDTIHarness}{N/A}', text)
            self.assertIn(r'\newcommand{\HeldoutNormanFederationEffect}{-10.00}', text)

    def test_heldout_receipts_required_and_complete_six_arms(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); path = write_receipt_fixture(root)
            result = collect_heldout(root)
            self.assertEqual(result['tasks']['ptpc']['runs']['42']['scores']['single_fixed']['primary'], .7)
            self.assertIsNone(result['tasks']['native_dti']['runs']['42'])
            payload = json.loads((path/'results.json').read_text())
            del payload['results']['federated_loop']
            (path/'results.json').write_text(json.dumps(payload))
            self.assertIsNone(collect_heldout(root)['tasks']['ptpc']['runs']['42'])

    def test_heldout_refuses_unverified_or_changed_seal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); path = write_receipt_fixture(root)
            payload = json.loads((path/'verification.json').read_text())
            payload['status'] = 'FAIL'; (path/'verification.json').write_text(json.dumps(payload))
            with self.assertRaises(AssertionError): collect_heldout(root)
            payload['status'] = 'PASS'; (path/'verification.json').write_text(json.dumps(payload))
            (path/'seal.json').write_text((path/'seal.json').read_text()+' ')
            with self.assertRaises(AssertionError): collect_heldout(root)


if __name__ == '__main__':
    unittest.main()
