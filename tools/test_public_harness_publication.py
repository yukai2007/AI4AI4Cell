"""CPU-only preview contracts; injected fixtures are explicitly nonpublishable."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import publish_public_harness as publisher


def reference_snapshot():
    return {"role": publisher.ROLE, "seeds_requested": list(publisher.SEEDS),
            "tasks": {task: {"runs": {str(seed): {"scores": {arm: {"primary": value}
                for arm, value in zip(publisher.ORIGINAL_ARMS, (.4, .5, .6))}}
                for seed in publisher.SEEDS}} for task in publisher.TASKS}}


class PublicHarnessPublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def fixture(self, harness, task, seed, primary):
        folder = self.base / harness / task / f"seed{seed}" / "heldout"
        folder.mkdir(parents=True)
        for filename in publisher.REQUIRED:
            (folder / filename).write_text(json.dumps({"primary": primary, "unit_test_only": True}))
        return folder

    def collect(self):
        return publisher.collect(self.base, _reference_snapshot=reference_snapshot(), _verification_fn=lambda folder: {"unit_test_only": True})

    def test_incomplete_seed_cells_are_na_never_partial_means(self):
        task = publisher.TASKS[0]
        self.fixture("ai_scientist_v2", task, 42, .9)
        self.fixture("ai_scientist_v2", task, 43, .8)
        snapshot = self.collect()
        row = snapshot["tasks"][task]["public_harnesses"]["ai_scientist_v2"]
        self.assertEqual(row["completed_seeds"], [42, 43])
        self.assertIsNone(row["mean"])
        self.assertIsNone(row["sd"])
        self.assertIn("44", row["pending"])
        self.assertFalse(snapshot["matrix_complete"])
        text = publisher.table_text(snapshot)
        self.assertIn("AI-Scientist-v2 (10 labs) & N/A", text)
        self.assertNotIn("completed seeds", text)
        self.assertNotIn("2/3", text)

    def test_complete_three_seed_mean_uses_sample_sd(self):
        task = publisher.TASKS[0]
        for seed, value in zip(publisher.SEEDS, (.7, .8, .9)):
            self.fixture("ai_scientist_v2", task, seed, value)
        row = self.collect()["tasks"][task]["public_harnesses"]["ai_scientist_v2"]
        self.assertAlmostEqual(row["mean"], .8)
        self.assertAlmostEqual(row["sd"], .1)
        self.assertEqual(row["n"], 3)

    def test_rankings_include_both_public_methods_and_ties(self):
        task = publisher.TASKS[0]
        for harness in publisher.HARNESSES:
            for seed in publisher.SEEDS:
                self.fixture(harness, task, seed, .8)
        text = publisher.table_text(self.collect())
        self.assertIn(r"AI-Scientist-v2 (10 labs) & \textbf{80.00}", text)
        self.assertIn(r"AI-Researcher (10 labs) & \textbf{80.00}", text)
        self.assertIn(r"\textbf{BioCoLoop} (10 labs) & \underline{60.00}", text)

    def test_caption_states_adaptation_once_and_keeps_table_clean(self):
        text = publisher.table_text(self.collect())
        self.assertEqual(text.count("task-adapted"), 1)
        self.assertIn("Preview pending manuscript integration", text)
        self.assertNotIn("completed seeds", text)
        for phrase in ("not unrestricted", "not blind", "not a confidence interval", "do not have matched"):
            self.assertNotIn(phrase, text)

    def test_seed42_original_rows_use_seed42_not_the_three_seed_mean(self):
        reference = reference_snapshot()
        task = publisher.TASKS[0]
        for seed, offset in ((42, 0.), (43, .1), (44, .2)):
            for arm in publisher.ORIGINAL_ARMS:
                reference["tasks"][task]["runs"][str(seed)]["scores"][arm]["primary"] += offset
        snapshot = publisher.collect(self.base, _reference_snapshot=reference, _verification_fn=lambda folder: {"unit_test_only": True})
        text = publisher.seed42_table_text(snapshot)
        self.assertIn("TAPB & 40.00", text)
        self.assertIn(r"Qwen direct (1 lab) & \underline{50.00}", text)
        self.assertIn(r"\textbf{BioCoLoop} (10 labs) & \textbf{60.00}", text)
        self.assertNotIn(r"\pm", text)
        self.assertNotIn("sample SD", text)
        self.assertNotIn("42--44", text)
        self.assertIn("same training/search seed 42", text)
        self.assertIn("pilot preview", text)

    def test_seed42_missing_public_result_is_never_filled_from_another_seed(self):
        task = publisher.TASKS[0]
        self.fixture("ai_scientist_v2", task, 43, .91)
        self.fixture("ai_scientist_v2", task, 44, .93)
        snapshot = self.collect()
        self.assertIn("AI-Scientist-v2 (10 labs) & N/A", publisher.seed42_table_text(snapshot))
        self.assertNotIn(task, snapshot["seed42_preview"]["public_completed_tasks"]["ai_scientist_v2"])
        self.assertFalse(snapshot["seed42_preview"]["complete"])

    def test_seed42_public_score_can_appear_while_three_seed_cell_stays_na(self):
        task = publisher.TASKS[0]
        self.fixture("ai_scientist_v2", task, 42, .85)
        snapshot = self.collect()
        self.assertIn(r"AI-Scientist-v2 (10 labs) & \textbf{85.00}", publisher.seed42_table_text(snapshot))
        self.assertIn("AI-Scientist-v2 (10 labs) & N/A", publisher.table_text(snapshot))
        self.assertIn(task, snapshot["seed42_preview"]["public_completed_tasks"]["ai_scientist_v2"])

    def test_no_other_single_seed_can_be_silently_substituted(self):
        with self.assertRaisesRegex(ValueError, "seed42"):
            publisher.table_text(self.collect(), seed=43)

    def test_changed_or_redirected_prediction_is_rejected(self):
        path = self.base / "primary_predictions.json"
        path.write_text("synthetic test predictions")
        result = {"endpoints": {"primary": {"predictions": str(path), "predictions_sha256": publisher.sha(path)}}}
        publisher.check_prediction_hashes(self.base, result)
        path.write_text("changed synthetic test predictions")
        with self.assertRaisesRegex(ValueError, "hash changed"):
            publisher.check_prediction_hashes(self.base, result)

    def test_readonly_rescorer_does_not_rewrite_verification(self):
        import verify_public
        predictions = self.base / "primary_predictions.json"
        predictions.write_text("synthetic unit-test payload")
        result = {"endpoints": {"primary": {"predictions": str(predictions), "predictions_sha256": publisher.sha(predictions)}}}
        (self.base / "results.json").write_text(json.dumps(result))
        receipt = {"status": "UNIT_TEST_ONLY", "verified_unix": 1., "value": .5}
        path = self.base / "verification.json"
        path.write_text(json.dumps(receipt))
        before = path.read_bytes()
        original_dump = verify_public.dump

        def fake_verify(folder):
            recomputed = dict(receipt, verified_unix=2.)
            verify_public.dump(Path(folder) / "verification.json", recomputed)
            return recomputed

        with mock.patch.object(verify_public, "verify", fake_verify):
            publisher.verify_readonly(self.base)
        self.assertEqual(path.read_bytes(), before)
        self.assertIs(verify_public.dump, original_dump)

    def test_synthetic_injected_snapshot_cannot_be_written_as_evidence(self):
        with self.assertRaisesRegex(ValueError, "injected evidence"):
            publisher.write_preview(self.collect(), self.base / "preview")
        self.assertFalse((self.base / "preview").exists())

    def test_complete_matrix_remains_nonintegrated_preview(self):
        for harness in publisher.HARNESSES:
            for task in publisher.TASKS:
                for seed in publisher.SEEDS:
                    self.fixture(harness, task, seed, .7)
        snapshot = self.collect()
        self.assertTrue(snapshot["matrix_complete"])
        self.assertFalse(snapshot["main_table_replaced"])
        self.assertFalse(snapshot["manuscript_modified"])
        self.assertFalse(snapshot["ready_for_explicit_manuscript_integration"])


if __name__ == "__main__":
    unittest.main()
