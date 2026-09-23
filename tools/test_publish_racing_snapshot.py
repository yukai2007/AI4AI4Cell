import copy
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import ExitStack
from unittest.mock import patch

import numpy as np
from publish_racing_snapshot import (PROTOCOL, ROLE, SEEDS, TASKS, collect_racing,
                                     publish_racing, render, sha)

def write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))

def fixture(root):
    base = root/'results'
    full = dict(schema='ai4ai4cell-v6-loop-summary', seeds=SEEDS, equal_compute=True,
                feedback_to_controller=False, independent_rescore='PASS', tasks={},
                heldout_wins=9, heldout_ties=3, heldout_losses=0)
    public = dict(schema='ai4ai4cell-v6-loop-public-summary', protocol=copy.deepcopy(PROTOCOL),
                  independent_rescore='PASS', heldout_loop_minus_direct={}, heldout_wins_ties_losses=[9,3,0])
    for task, public_key, _ in TASKS:
        query = base/task/'query.npz'
        query.parent.mkdir(parents=True)
        if task == 'ptpc_neural':
            np.savez(query, y=np.array([0,1]))
            delta, scores = 0., dict(direct=1., loop=1.)
        else:
            np.savez(query, ids=np.array([0,1]), choices=np.array([[0,1],[0,1]]))
            delta, scores = .5, dict(direct=.5, loop=1.)
        shared = dict(mean=delta, per_seed={str(s):delta for s in SEEDS},
                      hierarchical_paired_bootstrap_ci95=[delta,delta])
        public['heldout_loop_minus_direct'][public_key] = copy.deepcopy(shared)
        full['tasks'][task] = dict(heldout=dict(shared, bootstrap_replicates=5000))
        for seed in SEEDS:
            study = base/task/f'study_v6_seed{seed}'
            directory = base/'heldout_v6'/task/f'seed{seed}'
            definition = dict(schema='ai4ai4cell-racing-v6', task=task, seed=seed,
                clients=list(range(10)), slate=list(map(str,range(10))),
                direct_rounds_per_candidate=80, loop_screen_rounds_per_candidate=20,
                loop_promoted_candidates=6, loop_validation_rounds_per_promoted_candidate=100,
                total_client_epochs_per_arm=8000, development_evaluations_per_arm=160,
                candidate_count_per_arm=10, restart_promoted_candidates_from_common_initialization=True,
                test_read=False)
            write(study/'definition.json', definition)
            write(study/'status.json', dict(status='DEVELOPMENT_COMPLETE'))
            selected, arms, results = {}, {}, {}
            metric = 'ap' if task == 'ptpc_neural' else 'macro_accuracy'
            for arm in ('direct','loop'):
                checkpoint = study/(arm+'.pt')
                checkpoint.write_bytes(b'test checkpoint')
                selected[arm] = dict(checkpoint=str(checkpoint), config={}, best=dict(round=80),
                                     clients=list(range(10)), seed=seed)
                arms[arm] = dict(checkpoint=str(checkpoint), checkpoint_sha256=sha(checkpoint),
                                 config={}, best_round=80)
                results[arm] = dict(checkpoint=str(checkpoint), primary=scores[arm], metrics={metric:scores[arm]})
                directory.mkdir(parents=True,exist_ok=True)
                if task == 'ptpc_neural':
                    np.savez(directory/f'{arm}_predictions.npz', probabilities=np.array([.1,.9]))
                else:
                    second_scores = [.9,.1] if arm == 'direct' else [.1,.9]
                    write(directory/f'{arm}_predictions.json', [
                        dict(intervention=0, choices=[0,1], scores=[.9,.1], rank=1),
                        dict(intervention=1, choices=[0,1], scores=second_scores, rank=2 if arm == 'direct' else 1)])
            write(study/'selected_development.json', selected)
            seal = dict(schema='ai4ai4cell-v6-heldout-seal', task=task, seed=seed, role=ROLE,
                feedback_to_controller=False, development_completed_unix=1, sealed_unix=2,
                definition_sha256=sha(study/'definition.json'), selection_sha256=sha(study/'selected_development.json'),
                heldout_path=str(query), heldout_sha256=sha(query), arms=arms)
            write(directory/'seal.json', seal)
            result = dict(schema='ai4ai4cell-v6-heldout-results', task=task, seed=seed, role=ROLE,
                feedback_to_controller=False, primary_metric=metric, results=results,
                loop_minus_direct=delta, seal_sha256=sha(directory/'seal.json'), heldout_decoded_unix=3, completed_unix=4)
            write(directory/'results.json', result)
    write(base/'v6_loop_summary/summary.json', full)
    public['local_full_summary_sha256'] = sha(base/'v6_loop_summary/summary.json')
    public_path = root/'public.json'
    write(public_path, public)
    return base, public_path

class RacingPublisherTests(unittest.TestCase):
    def test_main_routes_only_main_effects_to_racing(self):
        import publish_strong_snapshot as strong
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory)
            snapshot = dict(tasks={task:dict(runs={}) for task,_,_ in strong.TASKS})
            stack.enter_context(patch.object(strong,'PAPER',root))
            stack.enter_context(patch.object(strong,'collect',return_value=snapshot))
            stack.enter_context(patch('sys.argv',['publisher','--results',str(root)]))
            mocks = {name:stack.enter_context(patch.object(strong,name)) for name in
                     ('table','effects','secondary','uncertainty','macros','dti_endpoints','dti_uncertainty')}
            racing = stack.enter_context(patch('publish_racing_snapshot.publish_racing'))
            stack.enter_context(patch('builtins.print'))
            strong.main()
            racing.assert_called_once_with(root,root/'tables/strong_v3')
            mocks['effects'].assert_called_once_with(snapshot,root/'tables/strong_v3',True)

    def test_scores_are_rescored_and_four_rows_exclude_dti(self):
        with tempfile.TemporaryDirectory() as directory:
            base, public = fixture(Path(directory))
            snapshot = collect_racing(base, public)
            self.assertEqual(snapshot['tasks']['norman_double_corrected']['direct'], .5)
            self.assertEqual(snapshot['tasks']['norman_double_corrected']['loop'], 1.)
            self.assertEqual(len(snapshot['result_bindings']),12)
            text = render(snapshot)
            self.assertIn('50.00 & \\textbf{100.00} & \\textbf{+50.00}', text)
            self.assertEqual(text.count('Cell:'),3)
            self.assertNotIn('DTI:',text)
            self.assertIn('DTI development replay is in Appendix A',text)

    def test_missing_evidence_rejects_without_overwriting_table(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base, public = fixture(root)
            out = root/'table'; out.mkdir()
            target = out/'effects.tex'; target.write_text('existing racing table')
            (base/'heldout_v6/vcc_corrected/seed53/results.json').unlink()
            with self.assertRaisesRegex(ValueError,'Missing racing'):
                publish_racing(base,out,public)
            self.assertEqual(target.read_text(),'existing racing table')

    def test_stale_summary_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            base, public = fixture(Path(directory))
            source = base/'v6_loop_summary/summary.json'
            source.write_text(source.read_text()+'\n')
            with self.assertRaisesRegex(ValueError,'Stale racing public'):
                collect_racing(base,public)

    def test_wrong_public_protocol_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            base, public = fixture(Path(directory))
            data = json.loads(public.read_text()); data['protocol']['candidate_count_per_arm']=12
            write(public,data)
            with self.assertRaisesRegex(ValueError,'Wrong racing public protocol'):
                collect_racing(base,public)

    def test_wrong_run_protocol_rejected_even_after_resealing(self):
        with tempfile.TemporaryDirectory() as directory:
            base, public = fixture(Path(directory))
            study = base/'vcc_corrected/study_v6_seed53'
            heldout = base/'heldout_v6/vcc_corrected/seed53'
            definition = json.loads((study/'definition.json').read_text())
            definition['direct_rounds_per_candidate']=81
            write(study/'definition.json',definition)
            seal = json.loads((heldout/'seal.json').read_text())
            seal['definition_sha256']=sha(study/'definition.json'); write(heldout/'seal.json',seal)
            result = json.loads((heldout/'results.json').read_text())
            result['seal_sha256']=sha(heldout/'seal.json'); write(heldout/'results.json',result)
            with self.assertRaisesRegex(ValueError,'Wrong racing run protocol'):
                collect_racing(base,public)

    def test_changed_predictions_fail_independent_rescore(self):
        with tempfile.TemporaryDirectory() as directory:
            base, public = fixture(Path(directory))
            np.savez(base/'heldout_v6/ptpc_neural/seed53/direct_predictions.npz', probabilities=np.array([.9,.1]))
            with self.assertRaisesRegex(ValueError,'independent re-score mismatch'):
                collect_racing(base,public)

if __name__ == '__main__':
    unittest.main()
