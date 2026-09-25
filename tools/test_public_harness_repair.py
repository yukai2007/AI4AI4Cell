import copy
import json
import tempfile
from pathlib import Path
import unittest
import publish_public_harness_repair as repair


class RepairPublicationTests(unittest.TestCase):
    def fixture(self):
        return dict(schema='public-harness-final-adapter-publication-v3',registered=True,
                    tasks={t:dict(status='Scored',primary=.3,biocoloop_seed42=.3) for t in repair.TASKS})

    def test_unregistered_queue_produces_no_numbers(self):
        with tempfile.TemporaryDirectory() as d:
            s=repair.collect(Path(d)/'absent')
        self.assertFalse(s['registered'])
        self.assertFalse(s['resolved'])
        self.assertNotIn('table',repair.table(s))

    def test_table_marks_equal_scores_and_names_revision(self):
        s=self.fixture();text=repair.table(s)
        self.assertEqual(text.count(r'\textbf{30.00}'),10)
        self.assertIn('AI-Researcher / final adapter',text)
        self.assertIn('Original-adapter outcomes remain',text)
        self.assertIn('seed 42',text)

    def test_failures_and_pending_are_not_scores(self):
        s=self.fixture()
        for task,status in zip(repair.TASKS,['Failed','Pending','Failed','Pending','Failed']):
            s['tasks'][task].update(status=status,primary=None)
        text=repair.table(s)
        self.assertIn('Failed & Pending & Failed & Pending & Failed',text)
        self.assertNotIn('& 0.00',text)
        self.assertNotIn(r'\textbf{30.00}',text)

    def test_better_score_not_method_identity_gets_bold(self):
        s=self.fixture();s['tasks'][repair.TASKS[0]]['primary']=.4
        text=repair.table(s)
        self.assertIn(r'\textbf{40.00}',text)
        self.assertEqual(text.count(r'\textbf{30.00}'),8)

    def test_balanced_direct_dti_registration_is_explicitly_validated(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);run=root/'ai_researcher'/'native_tapb'/'seed42'
            (run/'development').mkdir(parents=True)
            adapter=str(repair.original.EXTENSION/'airesearcher_budget_cap_v4.py')
            config=dict(harness='ai_researcher',task='native_tapb',seed=42,
                        upstream_commit=repair.original.HARNESSES['ai_researcher']['commit'],
                        adapter_paths=[adapter],gpu_ids=[4,5,6,7,0,1,2,3])
            definition=dict(config=dict(task='native_tapb',seed=42,harness='ai_researcher'),
                            rounds=100,slots=6)
            (run/'config.json').write_text(json.dumps(config))
            (run/'development'/'definition.json').write_text(json.dumps(definition))
            receipt=repair._validate_direct_dti_registration(root)
            self.assertEqual(receipt['gpu_ids'],[4,5,6,7,0,1,2,3])
            definition['rounds']=99
            (run/'development'/'definition.json').write_text(json.dumps(definition))
            with self.assertRaises(ValueError):
                repair._validate_direct_dti_registration(root)

    def test_repeated_multi_tool_response_is_displayed_as_tool_failure(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);run=base/'ai_researcher'/'native_tapb'/'seed42'
            run.mkdir(parents=True)
            status=dict(status='FAILED',error='Error: Tool response remained invalid after 3 format attempts: Extra data')
            (run/'run_status.json').write_text(json.dumps(status))
            snapshot={'tasks':{'native_tapb':{'public_harnesses':{
                'ai_researcher':{'runs':{'42':None}}}}}}
            item=repair._run_item(snapshot,base,'native_tapb',repair.VERSION,'airesearcher_budget_cap_v4.py')
            self.assertEqual(item['failure_type'],'tool')
            self.assertEqual(item['display'],r'$F_{\mathrm{tool}}$')


if __name__=='__main__':unittest.main()
