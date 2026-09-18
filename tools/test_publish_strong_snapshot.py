import tempfile
from pathlib import Path
import unittest
import json
import os

from publish_strong_snapshot import TASKS, ARMS, HELDOUT_ROLE, collect, table, effects, macros, result_path, sha, uncertainty, dti_endpoints


def fixture():
    snapshot=dict(tasks={})
    for task,label,_ in TASKS:
        values={arm:dict(primary=.6 if arm.startswith('federated') else .4) for arm,_,_ in ARMS}
        snapshot['tasks'][task]=dict(label=label,runs={'42':dict(scores=values),'43':None,'44':None})
    snapshot['tasks']['native_tapb']['runs']['42']=None
    return snapshot


class StrongSnapshotTests(unittest.TestCase):
    def test_model_sources_are_distinct_and_have_no_legacy_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory)
            # Even arbitrarily high old-model files must not fill new-model cells.
            old=base/'heldout_v3/ptpc/seed42'; old.mkdir(parents=True)
            (old/'results.json').write_text('{"primary":1.0}')
            snapshot=collect(base)
            self.assertTrue(all(all(r is None for r in t['runs'].values()) for t in snapshot['tasks'].values()))
            self.assertEqual(result_path(base,'ptpc_neural',42),base/'heldout_ptpc_neural/seed42')
            self.assertEqual(result_path(base,'native_tapb',42),base/'heldout_v3/native_tapb/seed42')

    def test_main_rows_all_displayed_ties_and_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory); data=fixture()
            for task,_,_ in TASKS:
                run=data['tasks'][task]['runs']['42']
                if run: run['scores']['single_direct']['primary']=.600001
            table(data,out)
            text=(out/'main.tex').read_text()
            self.assertEqual(text.count(r'\textbf{60.00}'),8)
            self.assertIn('1 & Fixed model & N/A',text)
            self.assertIn('10 & Our harness & N/A',text)
            self.assertIn('ProteinTalks-derived',text)
            self.assertIn('mask-corrected',text)
            self.assertIn('not blind confirmation',text)

    def test_full_ablation_not_hidden_and_signed_effects(self):
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory); data=fixture()
            data['tasks']['norman_double_corrected']['runs']['42']['scores']['single_loop']['primary']=.7
            table(data,out,True); effects(data,out,True); effects(data,out)
            self.assertIn('1 & Our loop', (out/'ablation.tex').read_text())
            self.assertIn('10 $-$ 1 labs (both loop) & N/A & +20.00 & +20.00 & -10.00 & +20.00',
                          (out/'effects_full.tex').read_text())
            self.assertIn('Loop $-$ fixed (10 labs)',(out/'effects.tex').read_text())
            self.assertNotIn('Loop $-$ fixed (1 lab)',(out/'effects.tex').read_text())
            self.assertIn('Loop $-$ fixed (1 lab)',(out/'effects_full.tex').read_text())

    def test_distinct_strong_macros_and_incomplete_seed_estimates(self):
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory); macros(fixture(),out); text=(out/'snapshot_stats.tex').read_text()
            self.assertIn(r'\newcommand{\StrongPTPCHarness}{60.00}',text)
            self.assertIn(r'\newcommand{\StrongPTPCThreeSeedHarness}{N/A}',text)
            self.assertIn(r'\newcommand{\StrongDTIHarness}{N/A}',text)
            self.assertIn(r'\newcommand{\StrongPTPCSearchEffect}{+0.00}',text)
            self.assertNotIn('HeldoutPTPC',text)

    def test_native_tapb_schema_flat_verification_and_missing_bootstrap(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory); study=base/'native_tapb/study_v3_seed42'; study.mkdir(parents=True)
            path=result_path(base,'native_tapb',42); path.mkdir(parents=True)
            definition=dict(task='native_tapb',seed=42,rounds=100,slots=6,test_read=False)
            for name,value in [('definition.json',definition),('selected_development.json',{}),
                               ('status.json',dict(status='DEVELOPMENT_COMPLETE'))]:
                (study/name).write_text(json.dumps(value))
            arms={arm:dict(checkpoint=str(study/(arm+'.pt'))) for arm,_,_ in ARMS}
            seal=dict(task='native_tapb',seed=42,role=HELDOUT_ROLE,feedback_to_controller=False,
                sealed_unix=1,definition=definition,definition_sha256=sha(study/'definition.json'),
                selection_sha256=sha(study/'selected_development.json'),arms=arms,
                source_provenance=dict(repository='https://github.com/GaomingL1n/TAPB',
                                       commit='ac846b1463ecf4a031b84bd6caacb57b25d50d4f'))
            (path/'seal.json').write_text(json.dumps(seal))
            metrics=dict(auroc=.7,average_precision=.6,mcc=.4,log_loss=.3)
            endpoints={endpoint:{arm:dict(primary=.7,metrics=metrics,checkpoint=arms[arm]['checkpoint']) for arm in arms}
                       for endpoint in ['random','unseen_drug','unseen_protein']}
            result=dict(schema='native-tapb-v3-heldout-results-v1',task='native_tapb',seed=42,
                role=HELDOUT_ROLE,feedback_to_controller=False,seal_sha256=sha(path/'seal.json'),
                heldout_decoded_unix=2,completed_unix=3,primary_endpoint='random',primary_metric='auroc',
                endpoints=endpoints,results=endpoints['random'])
            verification=dict(status='PASS',task='native_tapb',seed=42,arms=6,endpoints=3,
                sealed_before_response_access=True,common_original_roster=True,original_scorer=True,
                rescored={f'{endpoint}/{arm}':dict(metrics=metrics) for endpoint in endpoints for arm in arms})
            audit=dict(status='PASS',development_prediction_parity=True,fixed_all_three_endpoints=True,
                six_arms=True,original_scorer=True,test_checkpoint_selection=False,feedback_to_controller=False,dictionary_updated=False)
            for name,value in [('results.json',result),('audit.json',audit),('verification.json',verification)]:
                (path/name).write_text(json.dumps(value))
            data=collect(base)
            self.assertEqual(data['tasks']['native_tapb']['runs']['42']['scores']['federated_loop']['primary'],.7)
            self.assertIsNone(data['tasks']['native_tapb']['runs']['42']['uncertainty'])
            uncertainty(data,base); dti_endpoints(data,base)
            self.assertIn('Bootstrap intervals pending',(base/'uncertainty.tex').read_text())
            self.assertEqual((base/'dti_endpoints.tex').read_text().count(r'\textbf{70.00}'),18)

    def test_relative_result_root_with_registered_neural_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory); study=base/'ptpc_neural/study_v3_seed42'; study.mkdir(parents=True)
            path=result_path(base,'ptpc_neural',42); path.mkdir(parents=True)
            definition=dict(task='ptpc_neural',seed=42,rounds=100,slots=6,test_read=False)
            for name,value in [('definition.json',definition),('selected_development.json',{}),
                               ('status.json',dict(status='DEVELOPMENT_COMPLETE')),('neural_registration.json',{})]:
                (study/name).write_text(json.dumps(value))
            arms={arm:dict(checkpoint=str(study/(arm+'.pt'))) for arm,_,_ in ARMS}
            seal=dict(task='ptpc_neural',seed=42,role=HELDOUT_ROLE,feedback_to_controller=False,
                sealed_unix=1,definition=definition,definition_sha256=sha(study/'definition.json'),
                selection_sha256=sha(study/'selected_development.json'),arms=arms,
                predictor='ProteinTalks-derived observed-response efficacy head (adapted)',
                model_version='ptpc-observed-6h24h-head-v1',registration_sha256=sha(study/'neural_registration.json'))
            (path/'seal.json').write_text(json.dumps(seal))
            result=dict(schema='unified-v3-heldout-results-v1',task='ptpc_neural',seed=42,
                role=HELDOUT_ROLE,feedback_to_controller=False,seal_sha256=sha(path/'seal.json'),
                heldout_decoded_unix=2,completed_unix=3,primary_metric='ap',
                results={arm:dict(primary=.7,metrics=dict(ap=.7),checkpoint=arms[arm]['checkpoint']) for arm in arms})
            verification=dict(status='PASS',task='ptpc_neural',seed=42,seal_before_response_access=True,
                all_checkpoint_hashes_match=True,common_original_roster=True,
                rescored={arm:dict(metrics=dict(ap=.7)) for arm in arms})
            audit=dict(status='PASS',original_scorer=True,common_roster_all_arms=True,
                       no_test_checkpoint_selection=True,no_controller_feedback=True)
            for name,value in [('results.json',result),('audit.json',audit),('verification.json',verification)]:
                (path/name).write_text(json.dumps(value))
            relative=Path(os.path.relpath(base,Path.cwd()))
            data=collect(relative)
            receipt=data['tasks']['ptpc_neural']['runs']['42']['receipts']
            self.assertIn('ptpc_neural/study_v3_seed42/neural_registration.json',receipt)


if __name__=='__main__': unittest.main()
