import copy
import tempfile
from pathlib import Path
import unittest
import publish_public_harness_repair as repair


class RepairPublicationTests(unittest.TestCase):
    def fixture(self):
        return dict(registered=True,tasks={t:dict(status='Scored',primary=.3,biocoloop_seed42=.3) for t in repair.TASKS})

    def test_unregistered_queue_produces_no_numbers(self):
        with tempfile.TemporaryDirectory() as d:
            s=repair.collect(Path(d)/'absent')
        self.assertFalse(s['registered'])
        self.assertFalse(s['resolved'])
        self.assertNotIn('table',repair.table(s))

    def test_table_marks_equal_scores_and_names_revision(self):
        s=self.fixture();text=repair.table(s)
        self.assertEqual(text.count(r'\textbf{30.00}'),8)
        self.assertIn('AI-Researcher / repaired',text)
        self.assertIn('Original-adapter failures remain',text)
        self.assertIn('seed 42',text)

    def test_failures_and_pending_are_not_scores(self):
        s=self.fixture()
        for task,status in zip(repair.TASKS,['Failed','Pending','Failed','Pending']):
            s['tasks'][task].update(status=status,primary=None)
        text=repair.table(s)
        self.assertIn('Failed & Pending & Failed & Pending',text)
        self.assertNotIn('& 0.00',text)
        self.assertNotIn(r'\textbf{30.00}',text)

    def test_better_score_not_method_identity_gets_bold(self):
        s=self.fixture();s['tasks'][repair.TASKS[0]]['primary']=.4
        text=repair.table(s)
        self.assertIn(r'\textbf{40.00}',text)
        self.assertEqual(text.count(r'\textbf{30.00}'),6)


if __name__=='__main__':unittest.main()
