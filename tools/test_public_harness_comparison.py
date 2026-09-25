"""Fast CPU-only comparison contracts; fixtures can never be published."""
import copy
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest import mock

import publish_public_harness_comparison as comparison
import publish_public_harness as publisher
import supervise


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


def score_snapshot():
    snapshot = {"artifact_role": "unit-test-only", "role": publisher.ROLE,
                "seeds_requested": list(publisher.SEEDS), "reference_complete": True,
                "tasks": {}, "source_sha256": {}}
    for task in publisher.TASKS:
        item = {"original": {}, "public_harnesses": {}}
        for method in publisher.METHODS:
            primary = dict(zip(publisher.ORIGINAL_ARMS, (.4, .5, .6))).get(method)
            runs = {str(seed): {"primary": primary} if primary is not None else None for seed in publisher.SEEDS}
            group = "original" if method in publisher.ORIGINAL_ARMS else "public_harnesses"
            item[group][method] = {"runs": runs, "pending": {}, **publisher.aggregate_seeds(runs)}
        snapshot["tasks"][task] = item
    return snapshot


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.scores = score_snapshot()

    def tearDown(self):
        self.temp.cleanup()

    def collect(self):
        return comparison.collect_comparison(self.base, _verified_snapshot=self.scores)

    def scored(self, harness, task, seed, primary):
        row = publisher._row(self.scores, task, harness)
        row["runs"][str(seed)] = {"primary": primary}
        row.update(publisher.aggregate_seeds(row["runs"]))

    def failure(self, prefix=None, *, task="ptpc_neural", seed=42, accounting="immutable_prequeue_receipt"):
        job = dict(harness="ai_researcher", task=task, seed=seed)
        run = self.base / job["harness"] / task / f"seed{seed}"
        now = time.time()
        status = dict(**job, status="FAILED", pid=-1, started_unix=now-10, completed_unix=now-2,
                      error_type="NativeRunIncomplete", test_read=False,
                      error="Error: " + (prefix or next(iter(comparison.FAILURE_PREFIXES))),
                      usage=dict(calls=3, input_tokens=100, output_tokens=100, generation_seconds=.2, model="unit-test-only"))
        definition = dict(schema="public-harness-development-v1", execution_kind="fresh-canonical-v3",
                          config=job, binding={"source_sha256": {"unit-test-only": "not-production"}})
        write_json(run / "run_status.json", status)
        write_json(run / "development/definition.json", definition)
        receipt = supervise.controller_failure(run, job, status)
        hours = 8 * (status["completed_unix"] - status["started_unix"]) / 3600
        adopted = dict(**job, output=str(run), started_unix=status["started_unix"], completed_unix=status["completed_unix"],
                       usage=status["usage"], reserved_gpus=8, reserved_gpu_hours=hours, evidence_sha256=receipt["evidence_sha256"])
        manifest = dict(schema="public-harness-queue-v1", jobs=supervise.jobs(), source_sha256=supervise.pinned_sources(),
                        continue_controller_failures=True, adopted_prequeue_runs=[adopted], initial_reserved_gpu_hours=hours)
        receipt["accounting"] = dict(kind=accounting, reserved_gpu_hours=hours)
        if accounting == "finished_owned_child":
            manifest.update(adopted_prequeue_runs=[], initial_reserved_gpu_hours=0.)
            receipt["accounting"] = dict(kind=accounting, child_started_unix=now-11, child_finished_unix=now-1,
                                         cumulative_reserved_gpu_hours=8*10/3600)
        state = dict(schema="public-harness-supervisor-v1", failed=[receipt], reserved_gpu_hours=1., status="RUNNING")
        write_json(self.base / "queue_manifest.json", manifest)
        write_json(self.base / "supervisor_status.json", state)
        return run, status, manifest, state

    def validated_fixture(self):
        # Only the expensive source/manifest checks are isolated; ledger hashes,
        # exact prefix, accounting, identity, no-seal, and no-heldout all run.
        with mock.patch.object(comparison, "_validate_definition"):
            return self.collect()

    def test_missing_runs_stay_pending_with_fixed_denominators(self):
        snapshot = self.collect()
        counts = snapshot["completion"]["matrix"]
        self.assertEqual((counts["denominator"], counts["pending"], counts["terminal"], counts["scored"]), (30, 30, 0, 0))
        for method in publisher.METHODS:
            for count in snapshot["completion"]["by_method"][method]["by_seed"].values():
                self.assertEqual(count["denominator"], 5)
        self.assertFalse(snapshot["comparison_resolved"])
        self.assertFalse(snapshot["scores_complete"])

    def test_four_exact_prefixes_and_one_wrapper(self):
        for prefix, expected in comparison.FAILURE_PREFIXES.items():
            with self.subTest(prefix=prefix):
                self.failure(prefix)
                snapshot = self.validated_fixture()
                status = publisher._row(snapshot, "ptpc_neural", "ai_researcher")["statuses"]["42"]
                self.assertEqual(status["status"], expected)
                self.assertIsNone(status["primary"])
                self.assertTrue(status["terminal"])
                self.assertFalse(status["scored"])

    def test_raw_infrastructure_error_is_pending_not_method_failure(self):
        run = self.base / "ai_researcher/ptpc_neural/seed42"
        write_json(run / "run_status.json", {"status": "FAILED", "error": "CUDA out of memory"})
        status = publisher._row(self.collect(), "ptpc_neural", "ai_researcher")["statuses"]["42"]
        self.assertEqual(status["status"], "Pending")

    def rewrite_status_and_receipt(self, run, status, state):
        write_json(run / "run_status.json", status)
        state["failed"][0]["evidence_sha256"][str(run / "run_status.json")] = publisher.sha(run / "run_status.json")
        write_json(self.base / "supervisor_status.json", state)

    def test_untrusted_infrastructure_and_substring_errors_abort(self):
        for message in ("CUDA out of memory", "Infrastructure: Tool response remained invalid after 3 attempts",
                        "Error: Error: Tool response remained invalid after 3 attempts", "Global model-call cap reached"):
            with self.subTest(message=message):
                run, status, _, state = self.failure()
                status["error"] = state["failed"][0]["error"] = message
                self.rewrite_status_and_receipt(run, status, state)
                with self.assertRaisesRegex(ValueError, "Untrusted/infrastructure"):
                    self.validated_fixture()

    def test_changed_receipt_hash_is_rejected(self):
        run, status, _, _ = self.failure()
        status["usage"]["calls"] += 1
        write_json(run / "run_status.json", status)
        with self.assertRaisesRegex(ValueError, "hash changed"):
            self.validated_fixture()

    def test_bad_identity_usage_time_and_test_access_are_rejected(self):
        for field, value in (("seed", 43), ("usage", None), ("completed_unix", None), ("test_read", True)):
            with self.subTest(field=field):
                run, status, _, state = self.failure()
                status[field] = value
                self.rewrite_status_and_receipt(run, status, state)
                with self.assertRaises(ValueError):
                    self.validated_fixture()

    def test_failure_never_accepts_seal_or_heldout_artifacts(self):
        for name in ("development/selection_seal.json", "heldout/results.json"):
            with self.subTest(name=name):
                run, _, _, _ = self.failure()
                write_json(run / name, {"unit_test_only": True})
                with self.assertRaisesRegex(ValueError, "held-out"):
                    self.validated_fixture()
                (run / name).unlink()
                if name.startswith("heldout"):
                    (run / "heldout").rmdir()

    def test_full_definition_protocol_is_not_bypassed_by_production_tag(self):
        run, _, _, _ = self.failure()
        with self.assertRaisesRegex(ValueError, "production development protocol"):
            self.collect()
        definition = publisher.read(run / "development/definition.json")
        definition["execution_kind"] = "injected-test-fitter"
        with self.assertRaisesRegex(ValueError, "production development protocol"):
            comparison._validate_definition(definition, definition["config"])

    def test_source_hash_map_must_not_be_empty_or_changed(self):
        with self.assertRaisesRegex(ValueError, "nonempty"):
            comparison._hashes({})
        path = self.base / "source.py"
        path.write_text("unit test source")
        expected = {str(path): publisher.sha(path)}
        comparison._hashes(expected)
        path.write_text("changed")
        with self.assertRaisesRegex(ValueError, "hash changed"):
            comparison._hashes(expected)

    def test_immutable_accounting_cannot_be_omitted_or_forged(self):
        for change in ("missing", "unregistered", "hours"):
            with self.subTest(change=change):
                _, _, manifest, state = self.failure()
                if change == "missing":
                    state["failed"][0].pop("accounting")
                elif change == "unregistered":
                    manifest["adopted_prequeue_runs"] = []
                else:
                    state["failed"][0]["accounting"]["reserved_gpu_hours"] = 0.
                write_json(self.base / "queue_manifest.json", manifest)
                write_json(self.base / "supervisor_status.json", state)
                with self.assertRaisesRegex(ValueError, "accounting"):
                    self.validated_fixture()

    def test_finished_owned_child_must_be_fully_accounted(self):
        _, _, _, state = self.failure(accounting="finished_owned_child")
        self.assertEqual(self.validated_fixture()["completion"]["matrix"]["failed_tool"], 1)
        state["failed"][0]["accounting"]["child_finished_unix"] = time.time()-20
        write_json(self.base / "supervisor_status.json", state)
        with self.assertRaisesRegex(ValueError, "fully charged"):
            self.validated_fixture()

    def test_duplicate_and_redirected_failures_are_rejected(self):
        for change in ("duplicate", "redirect"):
            with self.subTest(change=change):
                _, _, _, state = self.failure()
                if change == "duplicate":
                    state["failed"].append(copy.deepcopy(state["failed"][0]))
                else:
                    state["failed"][0]["output"] += "/elsewhere"
                write_json(self.base / "supervisor_status.json", state)
                with self.assertRaisesRegex(ValueError, "Duplicate or redirected"):
                    self.validated_fixture()

    def test_changed_queue_source_or_job_matrix_is_rejected(self):
        for field in ("jobs", "source_sha256"):
            with self.subTest(field=field):
                _, _, manifest, _ = self.failure()
                manifest[field] = [] if field == "jobs" else {}
                write_json(self.base / "queue_manifest.json", manifest)
                with self.assertRaisesRegex(ValueError, "Frozen queue"):
                    self.validated_fixture()

    def test_no_partial_mean_and_seed42_never_borrows_another_seed(self):
        task = publisher.TASKS[0]
        self.scored("ai_scientist_v2", task, 43, .99)
        snapshot = self.collect()
        row = publisher._row(snapshot, task, "ai_scientist_v2")
        self.assertIsNone(row["mean"])
        self.assertIsNone(row["sd"])
        self.assertIn("AI-Scientist-v2 (10 labs) & Pending", comparison.table_text(snapshot, seed=42))
        self.assertIn("1S/0F/2P", comparison.table_text(snapshot))
        self.assertNotIn("99.00", comparison.table_text(snapshot, seed=42))

    def test_failure_cells_have_no_numeric_score_and_mixed_counts(self):
        self.failure()
        self.scored("ai_researcher", "ptpc_neural", 43, .9)
        snapshot = self.validated_fixture()
        self.assertIn(r"$F_{\mathrm{tool}}$", comparison.table_text(snapshot, seed=42))
        self.assertIn("1S/1F/1P", comparison.table_text(snapshot))
        self.assertNotIn("90.00", comparison.table_text(snapshot))
        self.assertIsNone(publisher._row(snapshot, "ptpc_neural", "ai_researcher")["mean"])

    def test_best_and_runner_up_ties_use_all_scored_methods(self):
        for harness in publisher.HARNESSES:
            for seed in publisher.SEEDS:
                self.scored(harness, publisher.TASKS[0], seed, .8)
        text = comparison.table_text(self.collect())
        self.assertIn(r"AI-Scientist-v2 (10 labs) & \textbf{80.00}", text)
        self.assertIn(r"AI-Researcher (10 labs) & \textbf{80.00}", text)
        self.assertIn(r"\textbf{BioCoLoop} (10 labs) & \underline{60.00}", text)

    def test_main_table_separates_three_seed_core_from_seed42_public_controllers(self):
        for harness in publisher.HARNESSES:
            for task in publisher.TASKS:
                self.scored(harness, task, 42, .55)
        repair = dict(schema='public-harness-final-adapter-publication-v3',
                      tasks={task:dict(status='Scored',primary=.58) for task in publisher.TASKS})
        text = comparison.main_table_text(self.collect(), repair)
        self.assertIn('A. Core comparison, seeds 42--44', text)
        self.assertIn('B. Matched research-controller comparison, seed 42', text)
        self.assertIn('AI-Scientist-v2 (10 labs)', text)
        self.assertIn('AI-Researcher (10 labs)', text)
        self.assertIn(r'58.00', text)
        self.assertNotIn('S/0F/', text)

    def test_all_terminal_is_distinct_from_all_scored(self):
        failures = {}
        for task in publisher.TASKS:
            for seed in publisher.SEEDS:
                self.scored("ai_scientist_v2", task, seed, .7)
                failures[("ai_researcher", task, seed)] = {"status": "Failed-context", "terminal": True, "scored": False, "primary": None}
        with mock.patch.object(comparison, "verified_failures", return_value=(failures, {})):
            snapshot = self.collect()
        self.assertTrue(snapshot["comparison_resolved"])
        self.assertTrue(snapshot["seed42_comparison_resolved"])
        self.assertFalse(snapshot["scores_complete"])
        self.assertFalse(snapshot["ready_for_explicit_manuscript_integration"])
        self.assertEqual(snapshot["completion"]["matrix"]["terminal"], 30)
        self.assertEqual(snapshot["completion"]["matrix"]["scored"], 15)
        self.assertIn(r"$F_{\mathrm{ctx}}$ $3/3$", comparison.table_text(snapshot))

    def test_injected_snapshot_cannot_be_written(self):
        with self.assertRaisesRegex(ValueError, "injected evidence"):
            comparison.write_comparison(self.collect(), self.base / "publication")
        self.assertFalse((self.base / "publication").exists())

    def test_production_collect_calls_unchanged_full_verifier(self):
        scores = copy.deepcopy(self.scores)
        scores["artifact_role"] = "verified-preview-not-integrated"
        with mock.patch.object(publisher, "collect", return_value=scores) as collector:
            comparison.collect_comparison(self.base)
        collector.assert_called_once_with(self.base, None)

    def test_result_narrative_is_scoped_and_defines_status_macros(self):
        text = comparison.results_text(self.collect())
        self.assertIn(r"\PublicHarnessPending", text)
        self.assertIn("30 remain pending", text)
        self.assertIn("specified task adaptations and local-Qwen backend", text)
        self.assertIn("Failed runs have no predictive score", text)


if __name__ == "__main__":
    unittest.main()
