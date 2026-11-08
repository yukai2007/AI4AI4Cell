import copy
import json
from pathlib import Path
import unittest

import publish_rebuttal_allocation as publication


class AllocationPublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((publication.SOURCE / 'allocation_public.json').read_text())
        cls.provenance = json.loads((publication.SOURCE / 'provenance.json').read_text())

    def test_complete_evidence_and_deterministic_export(self):
        publication.validate(self.data, self.provenance)
        for name, text in publication.export().items():
            self.assertEqual((publication.OUT / name).read_text(), text)

    def test_incomplete_fit_counts_rejected(self):
        value = copy.deepcopy(self.data)
        value['cost']['new_fits']['r100'] = 119
        with self.assertRaises(AssertionError):
            publication.validate(value, self.provenance)

    def test_stale_summary_rejected(self):
        value = copy.deepcopy(self.data)
        value['summary']['ptpc_neural']['uniform_80']['mean'] += 0.01
        with self.assertRaises(AssertionError):
            publication.validate(value, self.provenance)

    def test_changed_budget_rejected(self):
        value = copy.deepcopy(self.data)
        value['cost']['per_policy_aggregation_rounds'] = 1000
        with self.assertRaises(AssertionError):
            publication.validate(value, self.provenance)

    def test_changed_wtl_rejected(self):
        value = copy.deepcopy(self.data)
        value['twelve_pair_wtl']['uniform_80']['wins'] += 1
        with self.assertRaises(AssertionError):
            publication.validate(value, self.provenance)

    def test_private_paths_rejected(self):
        value = copy.deepcopy(self.provenance)
        value['unintended_private_path'] = '/liziqing/private/example.npz'
        with self.assertRaises(AssertionError):
            publication.validate(self.data, value)


if __name__ == '__main__':
    unittest.main()
