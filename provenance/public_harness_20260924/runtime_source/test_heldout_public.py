"""Synthetic CPU-only checks of formulas and pre-access production gates."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score, matthews_corrcoef

from broker import dump
from heldout_public import validate_run
from verify_public import assert_metrics, binary_metrics, cell_metrics
from runtime.experiments.drugevolve_transfer.scoring import score_predictions
from extensions.proteomics.scoring import phenotype_scores


class PublicHeldoutTests(unittest.TestCase):
    def test_module_import_does_not_load_torch(self):
        command = "import heldout_public,verify_public,sys; assert 'torch' not in sys.modules"
        subprocess.run([sys.executable, "-B", "-c", command], cwd=Path(__file__).parent, check=True)

    def test_synthetic_development_rejected_before_other_artifact_access(self):
        with tempfile.TemporaryDirectory() as directory:
            dump(Path(directory) / "definition.json", {"execution_kind": "injected-test-fitter"})
            with self.assertRaisesRegex(ValueError, "synthetic/replay"):
                validate_run(directory)

    def test_binary_ties_extremes_and_threshold_match_reference_formulas(self):
        rng = np.random.default_rng(42)
        cases = [([0, 1], [0, 1]), ([0, 1, 0, 1], [.5, .5, .5, .5]),
                 ([0, 1, 1, 0, 1, 0], [.2, .2, .8, .8, 1, 0])]
        for _ in range(10):
            y = np.concatenate(([0, 1], rng.integers(0, 2, 98)))
            p = rng.choice(np.arange(11) / 10, size=100)
            cases.append((y, p))
        for y, p in cases:
            for proteomics in (True, False):
                actual = binary_metrics(y, p, proteomics=proteomics)
                expected = phenotype_scores(y, p) if proteomics else score_predictions(y, p)
                self.assertLessEqual(assert_metrics(actual, expected), 1e-12)
                self.assertAlmostEqual(actual["auroc"], roc_auc_score(y, p), places=14)
                self.assertAlmostEqual(actual["ap" if proteomics else "average_precision"], average_precision_score(y, p), places=14)
                if not proteomics:
                    self.assertAlmostEqual(actual["mcc"], matthews_corrcoef(y, np.asarray(p) >= .5), places=14)

    def test_binary_invalid_and_metric_tampering_rejected(self):
        for y, p in (([1, 1], [.1, .2]), ([0, 1], [0, float("nan")]), ([0, 1], [0, 2])):
            with self.assertRaises(ValueError):
                binary_metrics(y, p)
        with self.assertRaises(ValueError):
            assert_metrics({"ap": .3}, {"ap": .31})

    def test_cell_stable_ties_and_intervention_macro_weighting(self):
        ids = [1, 1, 2]
        choices = [[1, 2, 3, 4, 5], [3, 1, 2, 4, 5], [2, 1, 3, 4, 5]]
        scores = [[0., 0., 0., 0., 0.], [1., 0., 0., 0., 0.], [0., 1., 0., 0., 0.]]
        rows = [dict(original_row_index=i, intervention=identity, choices=option, scores=score, rank=rank)
                for i, (identity, option, score, rank) in enumerate(zip(ids, choices, scores, [1, 2, 2]))]
        actual = cell_metrics(rows, ids, choices)
        self.assertAlmostEqual(actual["accuracy"], 1 / 3)
        self.assertAlmostEqual(actual["macro_accuracy"], .25)
        self.assertAlmostEqual(actual["mrr"], 2 / 3)
        expected_ce = (np.log(5) + 2 * np.log(np.exp(10) + 4)) / 3
        self.assertAlmostEqual(actual["cross_entropy"], expected_ce, places=13)
        rows[0]["rank"] = 2
        with self.assertRaises(AssertionError):
            cell_metrics(rows, ids, choices)

    def test_cell_row_identity_and_choice_order_tampering_rejected(self):
        row = dict(original_row_index=0, intervention=1, choices=[1, 2, 3, 4, 5], scores=[1., 0., 0., 0., 0.], rank=1)
        with self.assertRaises(AssertionError):
            cell_metrics([row], [1], [[2, 1, 3, 4, 5]])
        row["original_row_index"] = 10
        with self.assertRaises(ValueError):
            cell_metrics([row], [1], [[1, 2, 3, 4, 5]])


if __name__ == "__main__":
    unittest.main()
