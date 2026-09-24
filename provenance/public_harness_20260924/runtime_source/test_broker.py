"""CPU-only contract tests: injected fits are marked as test-only artifacts."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from broker import Broker, BrokerConfig, BudgetExhausted, DESIGNS, InfrastructureFailure, dump, read


class FakeFitter:
    def __init__(self, outcomes):
        self.outcomes = iter(outcomes)
        self.calls = []

    def fit(self, config, clients, out, seed, rounds):
        self.calls.append((config, clients, out, seed, rounds))
        outcome = next(self.outcomes)
        if isinstance(outcome, BaseException):
            raise outcome
        primary, loss = outcome
        out.mkdir(parents=True, exist_ok=False)
        (out / "best.pt").write_bytes(b"synthetic checkpoint; not a trained model")
        development = dict(primary=primary, loss=loss, worst_client=primary, clients=10)
        history = [dict(round=i, train_loss=loss, **({"development": development} if i % 5 == 0 else {})) for i in range(1, 101)]
        record = dict(config=config, clients=clients, seed=seed, rounds=rounds, best=history[4], history=history,
                      training_seconds=0.01, model_update_bytes=1234, test_read=False)
        dump(out / "fit.json", record)
        return record


class BrokerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        self.trace = self.directory / "native_trace.jsonl"
        self.trace.write_text('{"native_controller":"test-only"}\n')
        self.config = BrokerConfig(task="vcc_corrected", seed=42, harness="unit-test-not-a-baseline",
            output_dir=str(self.directory / "run"), upstream_repo=str(self.directory / "upstream"),
            upstream_commit="synthetic", native_trace_path=str(self.trace), gpu_ids=(0,))

    def tearDown(self):
        self.temporary.cleanup()

    def broker(self, outcomes):
        fitter = FakeFitter(outcomes)
        broker = Broker(self.config, fitter=fitter, test_binding={"test_only": True})
        broker.initialize()
        return broker, fitter

    def request(self, broker, design="D01"):
        return broker.evaluate_design(design, "test hypothesis", "controlled test experiment", "testable expected effect")

    def test_menu_is_exact_v3_not_ablation_grid_and_import_is_gpu_free(self):
        self.assertEqual(list(DESIGNS), [f"D{i:02d}" for i in range(12)])
        self.assertEqual(DESIGNS["D00"], dict(lr=.001, weight_decay=.001, prox_mu=0., server_momentum=0., residual=False))
        self.assertEqual(DESIGNS["D09"]["server_momentum"], .9)
        script = "import broker,sys; assert 'torch' not in sys.modules; assert 'proposer' not in sys.modules"
        subprocess.run([sys.executable, "-B", "-c", script], cwd=Path(__file__).parent, check=True)

    def test_budget_invalid_duplicate_numerical_failure_all_charge_slots(self):
        broker, fitter = self.broker([(0.5, 1.), (0.6, 1.), ValueError("Non-finite training objective")])
        replies = [broker.evaluate({}), self.request(broker), self.request(broker), self.request(broker, "D02"),
                   self.request(broker, "D00"), broker.evaluate({"design_id": "D99"})]
        self.assertEqual([r["status"] for r in replies], ["INVALID", "COMPLETE", "DUPLICATE", "NUMERICAL_FAILURE", "DUPLICATE", "INVALID"])
        self.assertEqual([r["remaining_slots"] for r in replies], [5, 4, 3, 2, 1, 0])
        with self.assertRaises(BudgetExhausted):
            self.request(broker, "D03")
        self.assertEqual(len(fitter.calls), 3)  # Fixed + novel success + numerical failure.
        self.assertNotIn("D02", broker.status()["available_designs"])

    def test_selection_primary_then_lower_loss_strict_ties_reject(self):
        broker, _ = self.broker([(0.5, 1.), (0.5, .9), (0.5, .9), (.6, 2.), (.59, .01)])
        replies = [self.request(broker, key) for key in ("D01", "D02", "D03", "D04")]
        self.assertEqual([r["accepted"] for r in replies], [True, False, True, False])
        self.assertEqual(broker.status()["incumbent"]["config"], DESIGNS["D03"])

    def test_outputs_are_development_only_and_no_generated_text_executes(self):
        broker, _ = self.broker([(0.5, 1.), (0.6, .9)])
        marker = self.directory / "MUST_NOT_EXIST"
        payload = dict(design_id="D01", hypothesis=f"__import__('pathlib').Path({str(marker)!r}).touch()",
                       experiment="generated text is data", expected_effect="never executed")
        response = broker.evaluate(payload, model_receipts=[dict(model="test", input_tokens=20, output_tokens=8)])
        text = json.dumps([response, broker.status()])
        for forbidden in ("checkpoint", "best.pt", "heldout_path", "test/query", "secret_test_score"):
            self.assertNotIn(forbidden, text)
        self.assertFalse(marker.exists())
        self.assertFalse(response["test_read"])
        receipt = read(Path(self.config.output_dir) / "requests/slot_01.json")
        self.assertEqual(receipt["model_receipts"][0]["output_tokens"], 8)
        self.assertIn("sha256", receipt["native_trace"])

    def test_seal_requires_six_requests_and_preserves_best_checkpoint(self):
        broker, _ = self.broker([(0.5, 1.), (.7, 1.)])
        with self.assertRaises(ValueError):
            broker.seal_selection()
        self.request(broker, "D01")
        for _ in range(5):
            broker.evaluate({})
        response = broker.seal_selection()
        self.assertEqual(response["status"], "DEVELOPMENT_SEALED")
        root = Path(self.config.output_dir)
        selected, seal = read(root / "selected_development.json"), read(root / "selection_seal.json")
        self.assertEqual(selected["record"]["config"], DESIGNS["D01"])
        self.assertFalse(seal["heldout_evaluation_performed"])
        self.assertEqual(seal["execution_kind"], "injected-test-fitter")
        self.assertEqual(broker.seal_selection()["seal_sha256"], response["seal_sha256"])
        with self.assertRaises(BudgetExhausted):
            self.request(broker, "D02")

    def test_no_implicit_cache_reuse_and_infrastructure_errors_abort(self):
        broker, fitter = self.broker([(0.5, 1.)])
        root = Path(self.config.output_dir)
        (root / "fits/slot_01_D01").mkdir()
        with self.assertRaises(InfrastructureFailure):
            self.request(broker, "D01")
        self.assertEqual(len(fitter.calls), 1)
        self.assertEqual(broker.status()["used_slots"], 1)
        self.assertEqual(broker.status()["status"], "INFRASTRUCTURE_FAILURE")
        with self.assertRaises(InfrastructureFailure):
            self.request(broker, "D02")

    def test_test_artifacts_cannot_be_resumed_as_production(self):
        self.broker([(0.5, 1.)])
        with self.assertRaises(ValueError):
            Broker(self.config).initialize()

    def test_trace_paths_cannot_request_arbitrary_file_reads(self):
        broker, fitter = self.broker([(0.5, 1.)])
        reply = broker.evaluate_design("D01", "h", "e", "effect", native_trace_path="/not/a/native/trace")
        self.assertEqual(reply["status"], "INVALID")
        self.assertEqual(reply["remaining_slots"], 5)
        self.assertEqual(len(fitter.calls), 1)

    def test_selected_checkpoint_tampering_is_detected_before_sealing(self):
        broker, _ = self.broker([(0.5, 1.)])
        for _ in range(6):
            broker.evaluate({})
        checkpoint = Path(self.config.output_dir) / "fits/fixed_D00/best.pt"
        checkpoint.write_bytes(b"changed checkpoint")
        with self.assertRaises(ValueError):
            broker.seal_selection()


if __name__ == "__main__":
    unittest.main()
