"""Literal-boundary tests and a genuine upstream-controller fake-backend smoke."""
import json
import hashlib
import copy
from contextlib import redirect_stdout
import io
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

from aiscientist_adapter import (DEFAULT_UPSTREAM, PINNED_COMMIT, InvalidDesignRequest,
    FUNCTION_FORMAT_MAX_ATTEMPTS, NativeFunctionFormatError,
    adapt_native_prompt, fixed_baseline_evidence,
    dependency_report, load_upstream, parse_design_request, run_aiscientist)


MENU = {f"D{i:02d}": {"design": i} for i in range(12)}


def literal(design_id="D01"):
    return "design = " + repr({"design_id": design_id, "hypothesis": "A component helps.",
        "experiment": "Run the trusted 100-round fitter.", "expected_effect": "Improve development."})


class FakeBroker:
    def __init__(self):
        self.rows = []
        self.incumbent = {"config": MENU["D00"], "development": {"primary": .1, "loss": 1.},
                          "best_round": 100}

    def initialize(self):
        return {"status": "READY", "baseline": self.incumbent, "test_read": False}

    def status(self):
        used = {item["design_id"] for item in self.rows}
        return {"budget": 6, "used_slots": len(self.rows), "remaining_slots": 6 - len(self.rows),
                "incumbent": self.incumbent,
                "available_designs": {k: v for k, v in MENU.items() if k != "D00" and k not in used}}

    def evaluate_design(self, design_id, hypothesis, experiment, expected_effect, **receipts):
        if len(self.rows) >= 6:
            raise RuntimeError("Seventh candidate is prohibited")
        complete = design_id in self.status()["available_designs"]
        evidence = {"primary": .2 + len(self.rows) / 10., "loss": .8} if complete else None
        if evidence and evidence["primary"] > self.incumbent["development"]["primary"]:
            self.incumbent = {"config": MENU[design_id], "development": evidence, "best_round": 100}
        row = {"slot": len(self.rows), "design_id": design_id,
               "status": "COMPLETE" if complete else "INVALID", "accepted": complete,
               "candidate": evidence, "incumbent": self.incumbent,
               "remaining_slots": 5 - len(self.rows), "test_read": False}
        self.rows.append(row)
        return row

    def seal_selection(self):
        assert len(self.rows) == 6
        return {"status": "DEVELOPMENT_SEALED", "incumbent": self.incumbent,
                "seal_sha256": "fake-unit-test-seal", "test_read": False}


class FakeTextBackend:
    def __init__(self, invalid=False):
        self.proposals = 0
        self.calls = []
        self.invalid = invalid

    def __call__(self, messages, *, purpose):
        self.calls.append(purpose)
        text = messages[0]["content"]
        original = text.split("TASK-ADAPTED EXECUTION CONTRACT", 1)[0]
        if purpose == "select_best_implementation":
            ids = re.findall(r"ID: ([0-9a-f]+)", original)
            raw = json.dumps({"selected_id": ids[0], "reasoning": "Choose first for smoke testing."})
        elif purpose == "submit_review":
            raw = json.dumps({"is_bug": False, "summary": "Use only trusted evaluator results."})
        elif purpose == "evaluate_stage_completion":
            raw = json.dumps({"is_complete": False, "reasoning": "More evidence needed.",
                              "missing_criteria": ["No additional dataset or plot evidence"]})
        elif "HYPERPARAM NAME:" in original:
            raw = "HYPERPARAM NAME: registered-design-contrast\nDESCRIPTION: Choose another legal menu item."
        elif "summarizing experimental progress" in original:
            raw = "Previous outcomes are recorded; use only the trusted development metric."
        else:
            self.proposals += 1
            code = "import os\nos.system('touch /tmp/NEVER_EXECUTE_AIS_SMOKE')" if self.invalid else literal(f"D{self.proposals:02d}")
            raw = "Test the next constrained design using the trusted fitter.\n```python\n" + code + "\n```"
        return {"raw_response": raw, "input_tokens": 1, "output_tokens": 1, "seconds": 0.,
                "seed": 42, "model": "fake-backend-not-scientific-evidence", "call_id": len(self.calls)}


class MalformedReviewBackend(FakeTextBackend):
    """Reproduce the real pilot's fenced JSON followed by narrative prose."""
    def __init__(self, always=False):
        super().__init__()
        self.review_attempts = 0
        self.always = always
        self.review_messages = []

    def __call__(self, messages, *, purpose):
        receipt = super().__call__(messages, purpose=purpose)
        if purpose == "submit_review":
            self.review_attempts += 1
            self.review_messages.append(messages)
            if self.always or self.review_attempts == 1:
                receipt["raw_response"] = '```json\n{"is_bug": false, "summary": ""}\n```\n\nUnexpected trailing explanation.'
        return receipt


class LiteralBoundaryTests(unittest.TestCase):
    def test_exact_literal_request(self):
        self.assertEqual(parse_design_request(literal(), MENU)["design_id"], "D01")

    def test_known_but_unavailable_design_reaches_broker_validation(self):
        self.assertEqual(parse_design_request(literal("D00"), MENU)["design_id"], "D00")

    def test_arbitrary_python_is_never_accepted(self):
        bad = ["import os\n" + literal(), literal() + "\nprint('hi')", "exec('malicious')",
               literal().replace("'D01'", "'D' + '01'"), literal().replace("'D01'", "f'D01'"),
               literal().replace("'D01'", "str('D01')"), literal().replace("'D01'", "'D99'"),
               "other = " + literal(), "design = {}", "design = {'design_id': 'D01'}",
               "design = {'design_id': 'D01', 'design_id': 'D02', 'experiment': 'x', 'expected_effect': 'x'}"]
        for code in bad:
            with self.subTest(code=code), self.assertRaises(InvalidDesignRequest):
                parse_design_request(code, MENU)

    def test_baseline_evidence_has_no_stale_menu_or_budget(self):
        initialized = {"status": "READY", "remaining_slots": 6, "available_designs": MENU,
                       "baseline": {"config": MENU["D00"], "development": {"primary": .5},
                                    "best_round": 25, "training_diagnostics": {"first": {"round": 5}}}}
        evidence = fixed_baseline_evidence(initialized)
        self.assertEqual(set(evidence), {"config", "development", "best_round", "training_diagnostics"})
        self.assertNotIn("remaining_slots", json.dumps(evidence))
        self.assertNotIn("available_designs", json.dumps(evidence))
        initialized["baseline"]["development"]["primary"] = .9
        self.assertEqual(evidence["development"]["primary"], .5)

    def test_prompt_transform_preserves_measurements_memory_and_idea_formats(self):
        prompt = {"Introduction": "Ordinary native introduction", "Memory": "np.save was a prior failed attempt",
                  "Previous solution": {"Code": "recorded old script"},
                  "Instructions": {"Implementation guideline": ["np.save('experiment_data.npy', data)"],
                                   "Response format": "full executable script"}}
        original = copy.deepcopy(prompt)
        effective, changes = adapt_native_prompt(prompt)
        self.assertEqual(prompt, original)
        self.assertEqual(effective["Memory"], original["Memory"])
        self.assertEqual(effective["Previous solution"], original["Previous solution"])
        self.assertNotIn("np.save", json.dumps(effective["Instructions"]))
        self.assertIn("2–4", effective["Instructions"]["Response format"])
        self.assertTrue(changes)
        idea = {"Introduction": "Propose ONE native idea.", "Response format": "HYPERPARAM NAME: ... DESCRIPTION: ...",
                "Instructions": {"Requirements": ["Identify ONE hyperparameter"]}}
        self.assertEqual(adapt_native_prompt(idea)[0], idea)

    def test_stage_completion_maps_criteria_not_measured_evidence_or_verdict(self):
        prompt = ("1. Figure Analysis:\nActual evidence: primary=0.731, clients=10, round=100\n"
                  "1. Training curves should show stable convergence\n"
                  "2. Results should be tested on at least two datasets\n"
                  "3. No major instabilities or issues in the plots")
        effective, changes = adapt_native_prompt(prompt, "evaluate_stage_completion")
        self.assertIn("Actual evidence: primary=0.731, clients=10, round=100", effective)
        self.assertNotIn("at least two datasets", effective)
        self.assertIn("all 10 clients", effective)
        self.assertNotIn('"is_complete"', effective)
        self.assertEqual(len(changes), 4)


@unittest.skipUnless(DEFAULT_UPSTREAM.exists() and all(dependency_report().values()),
                     "Pinned upstream/native dependencies are required; no stub controller is substituted")
class NativeControllerSmokeTests(unittest.TestCase):
    def run_native(self, invalid=False, backend=None):
        broker, backend = FakeBroker(), backend or FakeTextBackend(invalid)
        with tempfile.TemporaryDirectory() as directory:
            calls = set()
            def profile(frame, event, arg):
                if event == "call" and str(DEFAULT_UPSTREAM) in frame.f_code.co_filename:
                    calls.add((Path(frame.f_code.co_filename).name, frame.f_code.co_name))
            previous = sys.getprofile()
            sys.setprofile(profile)
            try:
                result = run_aiscientist(broker, backend, trace_dir=directory,
                    registered_designs=MENU, task_description="A synthetic integration test, not a real experiment.",
                    task_name="fake_task", seed=42)
            finally:
                sys.setprofile(previous)
            events = [json.loads(line) for line in Path(result["native_trace_path"]).read_text().splitlines()]
        return result, broker, backend, events, calls

    def test_genuine_native_controller_calls_and_budget(self):
        result, broker, backend, events, calls = self.run_native()
        self.assertEqual(len(broker.rows), 6)
        self.assertEqual(backend.proposals, 6)
        self.assertEqual(result["termination"], "candidate_budget_exhausted")
        self.assertEqual(result["upstream_commit"], PINNED_COMMIT)
        self.assertTrue(result["native_stage_at_stop"].startswith("2_"))
        self.assertEqual(result["seal"]["incumbent"]["config"], MENU["D06"])
        expected = {("agent_manager.py", "run"), ("parallel_agent.py", "step"),
                    ("parallel_agent.py", "_select_parallel_nodes"), ("journal.py", "get_best_node"),
                    ("journal.py", "generate_summary"), ("parallel_agent.py", "_draft"),
                    ("parallel_agent.py", "plan_and_code_query"), ("parallel_agent.py", "parse_exec_result"),
                    ("parallel_agent.py", "_generate_hyperparam_tuning_idea"),
                    ("parallel_agent.py", "_generate_hyperparam_tuning_node")}
        self.assertTrue(expected <= calls, expected - calls)
        self.assertNotIn(("interpreter.py", "run"), calls)
        self.assertIn("select_best_implementation", backend.calls)
        sources = events[0]["native_methods"]
        self.assertEqual(sources["ParallelAgent.step"]["module"], "ai_scientist.treesearch.parallel_agent")
        self.assertEqual(len(sources["ParallelAgent.step"]["module_sha256"]), 64)
        self.assertEqual(sum(e["kind"] == "broker_result" for e in events), 6)
        transforms = [event for event in events if event["kind"] == "prompt_transformation"]
        self.assertTrue(any(item["rule"] == "coding.execution_guideline"
                            for event in transforms for item in event["transformations"]))
        for event in events:
            if event["kind"] == "broker_result":
                self.assertFalse(event["result"]["test_read"])

    def test_invalid_generated_code_consumes_slots_and_native_debugs(self):
        result, broker, backend, events, calls = self.run_native(invalid=True)
        self.assertEqual(len(broker.rows), 6)
        self.assertTrue(all(row["status"] == "INVALID" for row in broker.rows))
        self.assertEqual(result["seal"]["incumbent"]["config"], MENU["D00"])
        self.assertEqual(result["native_stage_history"], [])
        self.assertTrue(result["native_stage_at_stop"].startswith("1_"))
        self.assertIn(("parallel_agent.py", "_debug"), calls)
        self.assertNotIn(("interpreter.py", "run"), calls)

    def test_module_bindings_restore_after_run(self):
        modules = load_upstream()
        query = modules["parallel"].query
        executor = modules["parallel"].ProcessPoolExecutor
        original_interpreter = modules["interpreter"].Interpreter.run
        self.run_native()
        self.assertIs(modules["parallel"].query, query)
        self.assertIs(modules["parallel"].ProcessPoolExecutor, executor)
        self.assertIs(modules["interpreter"].Interpreter.run, original_interpreter)

    def test_native_function_format_retry_preserves_real_failed_response(self):
        backend = MalformedReviewBackend()
        result, broker, _, events, _ = self.run_native(backend=backend)
        self.assertEqual(len(broker.rows), 6)
        self.assertEqual(backend.proposals, 6)  # Formatting retries never re-evaluate a design.
        self.assertEqual(backend.review_attempts, 7)
        errors = [event for event in events if event["kind"] == "function_format_error"]
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0]["will_retry"])
        self.assertEqual(errors[0]["function_attempt"], 1)
        self.assertEqual(errors[0]["function_max_attempts"], FUNCTION_FORMAT_MAX_ATTEMPTS)
        repaired = backend.review_messages[1]
        self.assertEqual(repaired[-2]["role"], "assistant")
        self.assertIn("Unexpected trailing explanation.", repaired[-2]["content"])
        self.assertIn("Formatting attempt 2 of 3", repaired[-1]["content"])
        replies = [event for event in events if event["kind"] == "model_response"
                   and event["query_id"] == errors[0]["query_id"]]
        self.assertEqual([event["function_attempt"] for event in replies], [1, 2])
        self.assertIn("Unexpected trailing explanation.", replies[0]["receipt"]["raw_response"])

    def test_exhausted_native_function_retry_aborts_without_invented_review(self):
        broker, backend = FakeBroker(), MalformedReviewBackend(always=True)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(NativeFunctionFormatError):
                run_aiscientist(broker, backend, trace_dir=directory, registered_designs=MENU,
                    task_description="Fake format failure test.", task_name="fake_task", seed=42)
            events = [json.loads(line) for line in (Path(directory) / "native_trace.jsonl").read_text().splitlines()]
        self.assertEqual(backend.review_attempts, FUNCTION_FORMAT_MAX_ATTEMPTS)
        self.assertEqual(len(broker.rows), 1)
        self.assertFalse(any(event["kind"] == "native_node_result" for event in events))
        errors = [event for event in events if event["kind"] == "function_format_error"]
        self.assertEqual(len(errors), FUNCTION_FORMAT_MAX_ATTEMPTS)
        self.assertFalse(errors[-1]["will_retry"])

    def test_real_broker_fake_fitter_and_native_trace_seal(self):
        from broker import Broker, BrokerConfig, DESIGNS, TASK_DESCRIPTIONS, read
        from test_broker import FakeFitter
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            trace = root / "native/native_trace.jsonl"
            config = BrokerConfig(task="vcc_corrected", seed=42,
                harness="AI-Scientist-v2 task-adapted TEST ONLY", output_dir=str(root / "broker"),
                upstream_repo=str(DEFAULT_UPSTREAM), upstream_commit=PINNED_COMMIT,
                native_trace_path=str(trace), gpu_ids=(0,))
            fitter = FakeFitter([(.1 + .1 * i, 1.) for i in range(7)])
            broker = Broker(config, fitter=fitter, test_binding={"test_only": True})
            result = run_aiscientist(broker, FakeTextBackend(), trace_dir=trace.parent,
                registered_designs=DESIGNS, task_description=TASK_DESCRIPTIONS[config.task],
                task_name=config.task, seed=config.seed)
            self.assertEqual(len(fitter.calls), 7)  # Fixed D00 plus six candidates, all fake fits.
            self.assertEqual(result["seal"]["status"], "DEVELOPMENT_SEALED")
            seal = read(root / "broker/selection_seal.json")
            self.assertEqual(seal["execution_kind"], "injected-test-fitter")
            trace_hash = hashlib.sha256(trace.read_bytes()).hexdigest()
            self.assertIn(trace_hash, json.dumps(seal["native_trace"]))
            self.assertFalse(seal["heldout_evaluation_performed"])

    def test_actual_native_draft_debug_improve_tuning_ablation_prompt_fields(self):
        modules = load_upstream()
        from omegaconf import OmegaConf
        native = modules["parallel"]
        cfg = OmegaConf.load(DEFAULT_UPSTREAM / "bfts_config.yaml")
        worker = native.MinimalAgent("One fixed task", cfg, memory_summary="measured history is unchanged",
                                     evaluation_metrics="trusted development primary")
        node = modules["journal"].Node(code=literal(), plan="original plan", _term_out=["actual failure"],
                                      is_buggy=False, is_buggy_plots=False)
        captured = []
        def capture(self, prompt, retries=3):
            captured.append((copy.deepcopy(prompt), *adapt_native_prompt(prompt)))
            return "Test native prompt", literal()
        with patch.object(native.MinimalAgent, "plan_and_code_query", capture), redirect_stdout(io.StringIO()):
            worker._draft()
            worker._debug(node)
            worker._improve(node)
            worker._generate_hyperparam_tuning_node(node, native.HyperparamTuningIdea("momentum", "Use D05"))
            worker._generate_ablation_node(node, native.AblationIdea("residual", "Contrast D06"))
        self.assertEqual(len(captured), 5)
        for original, effective, changes in captured:
            instruction_text = json.dumps(effective["Instructions"])
            self.assertNotIn("np.save", instruction_text)
            self.assertNotIn("experiment_data", instruction_text)
            self.assertNotIn("create synthetic data", instruction_text)
            self.assertNotIn("7-10 sentences", instruction_text)
            self.assertNotIn("6-10 sentences", instruction_text)
            self.assertNotIn("complete and executable", instruction_text)
            self.assertIn("2–4", effective["Instructions"]["Response format"])
            for field in ("Memory", "Previous solution", "Previous (buggy) implementation", "Base code you are working on", "Execution output"):
                if field in original:
                    self.assertEqual(effective[field], original[field])
            self.assertTrue(changes)
        # These are the exact hardcoded upstream fields that caused formal_v1's invalid third slot.
        for original, effective, changes in captured[-2:]:
            self.assertIn("experiment_data.npy", json.dumps(original["Instructions"]))
            self.assertNotIn("experiment_data.npy", json.dumps(effective["Instructions"]))

    def test_actual_native_tuning_ablation_idea_formats_survive_domain_mapping(self):
        modules = load_upstream()
        from omegaconf import OmegaConf
        native = modules["parallel"]
        agent = native.ParallelAgent.__new__(native.ParallelAgent)
        agent.cfg = OmegaConf.load(DEFAULT_UPSTREAM / "bfts_config.yaml")
        agent.best_stage1_node = agent.best_stage3_node = modules["journal"].Node(code=literal())
        agent._hyperparam_tuning_state = {"tried_hyperparams": set()}
        agent._ablation_state = {"completed_ablations": set()}
        captured = []
        def query(system_message, **kwargs):
            effective, changes = adapt_native_prompt(system_message)
            captured.append((system_message, effective, changes))
            if "HYPERPARAM NAME:" in system_message["Response format"]:
                return "HYPERPARAM NAME: momentum\nDESCRIPTION: Use a registered contrast."
            return "ABLATION NAME: residual\nABLATION DESCRIPTION: Use a registered contrast."
        with patch.object(native, "query", query):
            agent._generate_hyperparam_tuning_idea()
            agent._generate_ablation_idea()
        for original, effective, changes in captured:
            self.assertEqual(original["Response format"], effective["Response format"])
            self.assertEqual(original["Base code you are working on"], effective["Base code you are working on"])
            self.assertTrue(changes)
            self.assertNotIn("first check if simply training longer", json.dumps(effective))
            self.assertNotIn("use multiple synthetic datasets", json.dumps(effective))


if __name__ == "__main__":
    unittest.main()
