"""A bounded, task-adapted *imported* AI-Scientist-v2 experiment controller.

No generated Python is executed. Native manager/search/generation/history methods
run against a literal-only design broker, with explicitly recorded adaptations.
The upstream checkout is never modified and no replacement tree policy exists.
"""
from __future__ import annotations

import ast
from contextlib import ExitStack, redirect_stdout, redirect_stderr
from concurrent.futures import Future
import copy
import hashlib
import importlib
import importlib.util
import inspect
import json
import math
from pathlib import Path
import random
import subprocess
import sys
import threading
import time
from typing import Any, Callable, Mapping


LABEL = "AI-Scientist-v2 (task-adapted experimental controller)"
PINNED_COMMIT = "96bd51617cfdbb494a9fc283af00fe090edfae48"
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_UPSTREAM = ROOT / "references/public_harness_20260924/AI-Scientist-v2"
IMPORT_DEPENDENCIES = {
    "numpy": "numpy", "pandas": "pandas", "anthropic": "anthropic",
    "openai": "openai", "backoff": "backoff", "funcy": "funcy",
    "rich": "rich", "humanize": "humanize", "dataclasses_json": "dataclasses-json",
    "omegaconf": "omegaconf", "coolname": "coolname", "shutup": "shutup",
    "igraph": "python-igraph", "black": "black", "genson": "genson",
    "jsonschema": "jsonschema",
}
REQUEST_FIELDS = {"design_id", "hypothesis", "experiment", "expected_effect"}
FUNCTION_FORMAT_MAX_ATTEMPTS = 3
PROMPT_ADAPTER_VERSION = "literal-design-fields-v2"
DESIGN_RESPONSE_FORMAT = (
    "Give 2–4 concise natural-language sentences describing the proposed design and rationale, "
    "followed by exactly one python Markdown block containing only "
    "design = {\"design_id\": \"<available design_id>\", \"hypothesis\": \"...\", "
    "\"experiment\": \"...\", \"expected_effect\": \"...\"}. "
    "Use four nonempty literal strings and a currently available registered design ID. "
    "No other statements, imports, calls, data containers, output printing or file writing are allowed."
)
DESIGN_IMPLEMENTATION_GUIDELINE = [
    "Submit one literal-only design request from the currently available registered menu.",
    "The trusted broker alone runs the fixed 100-round, 10-client fitter and returns measured development evidence.",
    "Do not implement training, change datasets or rounds, synthesize results, create arrays, save files or generate plots.",
    "The only Python syntax accepted is one assignment named design with the four required literal string fields.",
]
PROMPT_ADAPTER_RULES = [
    "coding.execution_guideline", "coding.response_format", "coding.environment",
    "coding.draft_introduction", "coding.debug_introduction", "coding.tuning_introduction",
    "coding.ablation_introduction", "coding.synthetic_data_sketch", "coding.concise_sketch",
    "coding.plot_feedback_label", "ideas.fixed_round_budget", "ideas.fixed_dataset",
    "review.broker_execution_boundary", "selection.development_evidence",
    "stage_completion.trusted_evidence_heading", "stage_completion.fixed_task_criteria",
]
_IMPORT_LOCK = threading.Lock()


class InvalidDesignRequest(ValueError):
    """Generated text is outside the literal-only execution interface."""


class UpstreamUnavailable(RuntimeError):
    """The exact, unmodified upstream or its import dependencies are absent."""


class NativeFunctionFormatError(RuntimeError):
    """The real text backend exhausted bounded native FunctionSpec formatting retries."""


class _CandidateBudgetReached(RuntimeError):
    pass


def parse_design_request(code: str, registered_designs: Mapping[str, Any]) -> dict:
    """Accept exactly one ``design = {four string fields}`` AST statement.

    Syntax is checked without evaluating expressions: calls, imports, attributes,
    comprehensions, f-strings, duplicate keys, and extra statements are rejected.
    Known but unavailable/repeated designs go to the broker to consume a slot.
    """
    if not isinstance(code, str) or len(code) > 32768:
        raise InvalidDesignRequest("Expected at most 32768 characters of literal design syntax")
    try:
        tree = ast.parse(code, mode="exec")
    except (SyntaxError, ValueError, RecursionError) as exc:
        raise InvalidDesignRequest("Malformed design request syntax") from exc
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.Assign):
        raise InvalidDesignRequest("Only one assignment to design is allowed")
    statement = tree.body[0]
    if (len(statement.targets) != 1 or not isinstance(statement.targets[0], ast.Name)
            or statement.targets[0].id != "design" or not isinstance(statement.value, ast.Dict)):
        raise InvalidDesignRequest("Expected design = {literal string fields}")
    values = statement.value
    if len(values.keys) != len(REQUEST_FIELDS):
        raise InvalidDesignRequest("Exactly four design request fields are required")
    request = {}
    for key, value in zip(values.keys, values.values):
        if not (isinstance(key, ast.Constant) and type(key.value) is str
                and isinstance(value, ast.Constant) and type(value.value) is str):
            raise InvalidDesignRequest("Only literal string keys and values are allowed")
        if key.value in request:
            raise InvalidDesignRequest("Duplicate field")
        if not value.value.strip() or len(value.value) > 8000:
            raise InvalidDesignRequest("Fields must be nonempty bounded strings")
        request[key.value] = value.value
    if set(request) != REQUEST_FIELDS:
        raise InvalidDesignRequest("Unknown or missing design request field")
    if request["design_id"] not in registered_designs:
        raise InvalidDesignRequest("Design is outside the registered design menu")
    return request


def dependency_report() -> dict:
    return {package: importlib.util.find_spec(module) is not None
            for module, package in IMPORT_DEPENDENCIES.items()}


def adapt_native_prompt(prompt: Any, purpose: str = "native_text") -> tuple[Any, list[dict]]:
    """Replace only audited task-incompatible instruction fields, never evidence.

    Native proposal/selection/transition code and memory are not rewritten. The
    before/after records make this task-domain transformation inspectable per query.
    """
    adapted = copy.deepcopy(prompt)
    changes = []

    def replace(container, key, value, path, rule):
        old = container[key]
        if old != value:
            container[key] = value
            changes.append({"rule": rule, "path": path, "before": old, "after": value})

    if isinstance(adapted, dict):
        instructions = adapted.get("Instructions")
        coding = isinstance(instructions, dict) and "Response format" in instructions
        if coding:
            if "Implementation guideline" in instructions:
                replace(instructions, "Implementation guideline", DESIGN_IMPLEMENTATION_GUIDELINE.copy(),
                        "Instructions.Implementation guideline", "coding.execution_guideline")
            replace(instructions, "Response format", DESIGN_RESPONSE_FORMAT,
                    "Instructions.Response format", "coding.response_format")
            if "Installed Packages" in instructions:
                replace(instructions, "Installed Packages",
                        "No generated Python is executed; all task fitting is performed by the trusted broker.",
                        "Instructions.Installed Packages", "coding.environment")
            sketch = instructions.get("Experiment design sketch guideline")
            if isinstance(sketch, list):
                for index, text in enumerate(sketch):
                    if "Make sure to create synthetic data" in text:
                        replace(sketch, index, "Use only the existing registered task data through the trusted fitter.",
                                f"Instructions.Experiment design sketch guideline[{index}]", "coding.synthetic_data_sketch")
                    elif "The solution sketch should be 6-10 sentences" in text:
                        replace(sketch, index, "The solution sketch should be 2–4 concise sentences.",
                                f"Instructions.Experiment design sketch guideline[{index}]", "coding.concise_sketch")
            sketch = instructions.get("Bugfix improvement sketch guideline")
            if isinstance(sketch, list):
                for index, text in enumerate(sketch):
                    if "(3-5 sentences)" in text:
                        replace(sketch, index, text.replace("(3-5 sentences)", "(2–4 concise sentences)"),
                                f"Instructions.Bugfix improvement sketch guideline[{index}]", "coding.concise_sketch")
            intro = adapted.get("Introduction", "")
            if "Your first task is to write a python code" in intro:
                replacement = (
                    "You are an AI researcher investigating the research idea below. Your first task is to propose "
                    "one simple registered design as a literal request to the trusted evaluator. "
                    "Focus on obtaining a valid working evaluation before sophisticated improvements; "
                    "later native stages can investigate other registered designs."
                )
                replace(adapted, "Introduction", replacement, "Introduction", "coding.draft_introduction")
            elif "Your previous code for research experiment had a bug" in intro:
                replace(adapted, "Introduction",
                        "You are an experienced AI researcher. The previous design request or evaluation failed. "
                        "Use the recorded feedback to repair the literal-only design request, keeping within the "
                        "registered menu and the trusted execution interface.",
                        "Introduction", "coding.debug_introduction")
            elif "implement hyperparameter tuning for the following idea:" in intro:
                replace(adapted, "Introduction", intro.replace(
                    "implement hyperparameter tuning for the following idea:",
                    "select one available registered design expressing the following hyperparameter-tuning idea:"),
                    "Introduction", "coding.tuning_introduction")
            elif "implement the ablation study for the following idea:" in intro:
                replace(adapted, "Introduction", intro.replace(
                    "implement the ablation study for the following idea:",
                    "select one available registered design expressing the following component-ablation idea:"),
                    "Introduction", "coding.ablation_introduction")
            if "Feedback based on generated plots" in adapted:
                old = adapted.pop("Feedback based on generated plots")
                adapted["Feedback from trusted development evaluation"] = old
                changes.append({"rule": "coding.plot_feedback_label", "path": "Feedback based on generated plots",
                                "before": "Feedback based on generated plots",
                                "after": "Feedback from trusted development evaluation", "evidence_preserved": True})
        # Idea-format keywords are left intact; only impossible training/data requests change.
        intro = adapted.get("Introduction", "")
        longer = ("You should first check if simply training longer (more epochs) improves the performance."
                  "Then try tuning common hyperparameters such as learning rate, batch size, etc."
                  "Only propose algorithm-specific and/or model-specific hyperparameters after you have tried the above.")
        if longer in intro:
            replace(adapted, "Introduction", intro.replace(longer,
                    "Choose one hyperparameter contrast represented in the available registered designs. "
                    "The number of rounds and all nonregistered training settings are fixed; do not tune them."),
                    "Introduction", "ideas.fixed_round_budget")
        if isinstance(instructions, dict) and isinstance(instructions.get("Requirements"), list):
            requirements = instructions["Requirements"]
            for index, requirement in enumerate(requirements):
                if "one of your ablations should be to use multiple synthetic datasets" in requirement:
                    replace(requirements, index,
                            "4. Use only the fixed registered task and component contrasts available in the design menu.",
                            f"Instructions.Requirements[{index}]", "ideas.fixed_dataset")
        if purpose == "submit_review" and "Introduction" in adapted:
            replace(adapted, "Introduction",
                    "You are an experienced AI researcher reviewing a trusted broker's response to a literal design "
                    "request. Determine whether the request/evaluation failed from its actual status and error "
                    "evidence, and summarize the findings. Generated Python was not executed. "
                    "Do not infer successful training from proposed code or confuse within-run improvement with "
                    "improvement over the fixed reference.",
                    "Introduction", "review.broker_execution_boundary")
        if purpose == "select_best_implementation" and "Introduction" in adapted:
            replace(adapted, "Introduction", adapted["Introduction"].replace(
                    "generated plots quality", "trusted development diagnostics"),
                    "Introduction", "selection.development_evidence")
    elif isinstance(adapted, str) and purpose == "evaluate_stage_completion":
        replacements = {
            "1. Figure Analysis:": ("1. Trusted development evidence (plotting is not used):", "stage_completion.trusted_evidence_heading"),
            "1. Training curves should show stable convergence":
                ("1. The trusted 100-round fit should have finite measured development results and usable training diagnostics", "stage_completion.fixed_task_criteria"),
            "2. Results should be tested on at least two datasets":
                ("2. Results should cover the one registered task with all 10 clients; no new datasets are permitted", "stage_completion.fixed_task_criteria"),
            "3. No major instabilities or issues in the plots":
                ("3. No unresolved numerical failure or invalid execution request should affect the selected result", "stage_completion.fixed_task_criteria"),
        }
        for old, (new, rule) in replacements.items():
            if old in adapted:
                adapted = adapted.replace(old, new)
                changes.append({"rule": rule, "path": "system_message.known_clause", "before": old, "after": new})
    return adapted, changes


def fixed_baseline_evidence(initialized: Mapping[str, Any]) -> dict:
    """Exclude initial availability/budget/status snapshots from fixed evidence."""
    baseline = initialized["baseline"]
    return {key: copy.deepcopy(baseline[key])
            for key in ("config", "development", "best_round", "training_diagnostics") if key in baseline}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                            text=True, check=True, timeout=20)
    return result.stdout.strip()


def load_upstream(repo: str | Path = DEFAULT_UPSTREAM) -> dict:
    """Verify provenance, then import actual native modules (no experiments)."""
    repo = Path(repo).resolve()
    if not (repo / ".git").exists():
        raise UpstreamUnavailable(f"Missing pinned upstream checkout: {repo}")
    if _git(repo, "rev-parse", "HEAD") != PINNED_COMMIT:
        raise UpstreamUnavailable("AI-Scientist-v2 checkout is not at the audited commit")
    if _git(repo, "diff", "HEAD", "--", "ai_scientist", "bfts_config.yaml", "LICENSE"):
        raise UpstreamUnavailable("Audited upstream source has local modifications")
    missing = [name for name, available in dependency_report().items() if not available]
    if missing:
        raise UpstreamUnavailable("Missing native import dependencies: " + ", ".join(missing))
    existing = sys.modules.get("ai_scientist")
    if existing is not None and not Path(existing.__file__).resolve().is_relative_to(repo):
        raise UpstreamUnavailable("Another ai_scientist package is already imported")
    sys.path.insert(0, str(repo))
    try:
        modules = {
            key: importlib.import_module("ai_scientist.treesearch." + name)
            for key, name in {
                "manager": "agent_manager", "parallel": "parallel_agent",
                "journal": "journal", "metric": "utils.metric",
                "interpreter": "interpreter", "backend": "backend",
            }.items()
        }
    finally:
        sys.path.pop(0)
    for module in modules.values():
        if not Path(module.__file__).resolve().is_relative_to(repo):
            raise UpstreamUnavailable("Native module resolved outside pinned checkout")
    modules["repo"] = repo
    return modules


def provenance(modules: dict) -> dict:
    """Record real defining-module hashes and method source/line locators."""
    methods = {
        "AgentManager.run": modules["manager"].AgentManager.run,
        "AgentManager._create_agent_for_stage": modules["manager"].AgentManager._create_agent_for_stage,
        "AgentManager._check_stage_completion": modules["manager"].AgentManager._check_stage_completion,
        "AgentManager._check_substage_completion": modules["manager"].AgentManager._check_substage_completion,
        "AgentManager._create_next_main_stage": modules["manager"].AgentManager._create_next_main_stage,
        "AgentManager._create_next_substage": modules["manager"].AgentManager._create_next_substage,
        "ParallelAgent.step": modules["parallel"].ParallelAgent.step,
        "ParallelAgent._select_parallel_nodes": modules["parallel"].ParallelAgent._select_parallel_nodes,
        "ParallelAgent._generate_hyperparam_tuning_idea": modules["parallel"].ParallelAgent._generate_hyperparam_tuning_idea,
        "ParallelAgent._generate_ablation_idea": modules["parallel"].ParallelAgent._generate_ablation_idea,
        "MinimalAgent._draft": modules["parallel"].MinimalAgent._draft,
        "MinimalAgent._debug": modules["parallel"].MinimalAgent._debug,
        "MinimalAgent._improve": modules["parallel"].MinimalAgent._improve,
        "MinimalAgent._generate_hyperparam_tuning_node": modules["parallel"].MinimalAgent._generate_hyperparam_tuning_node,
        "MinimalAgent._generate_ablation_node": modules["parallel"].MinimalAgent._generate_ablation_node,
        "MinimalAgent.plan_and_code_query": modules["parallel"].MinimalAgent.plan_and_code_query,
        "MinimalAgent.parse_exec_result": modules["parallel"].MinimalAgent.parse_exec_result,
        "Journal.get_best_node": modules["journal"].Journal.get_best_node,
        "Journal.generate_summary": modules["journal"].Journal.generate_summary,
        "Journal.append": modules["journal"].Journal.append,
        "Node.to_dict": modules["journal"].Node.to_dict,
        "Node.from_dict": modules["journal"].Node.from_dict,
    }
    details = {}
    for name, method in methods.items():
        source, line = inspect.getsourcelines(method)
        path = Path(inspect.getsourcefile(method)).resolve()
        details[name] = {"module": method.__module__, "qualname": method.__qualname__,
                         "path": str(path.relative_to(modules["repo"])), "line": line,
                         "module_sha256": _sha(path),
                         "function_sha256": hashlib.sha256("".join(source).encode()).hexdigest()}
    imported_modules = {}
    for name, module in tuple(sys.modules.items()):
        path = getattr(module, "__file__", None)
        if name.startswith("ai_scientist") and path:
            path = Path(path).resolve()
            if path.is_relative_to(modules["repo"]):
                imported_modules[name] = {"path": str(path.relative_to(modules["repo"])),
                                          "sha256": _sha(path)}
    return {"label": LABEL, "upstream_commit": PINNED_COMMIT,
            "upstream_url": "https://github.com/SakanaAI/AI-Scientist-v2",
            "license_sha256": _sha(modules["repo"] / "LICENSE"),
            "native_config_sha256": _sha(modules["repo"] / "bfts_config.yaml"),
            "adapter_sha256": _sha(Path(__file__)), "native_methods": details,
            "imported_modules": imported_modules,
            "prompt_adapter": {"version": PROMPT_ADAPTER_VERSION, "rules": PROMPT_ADAPTER_RULES}}


class _SerialExecutor:
    """Executor API preserving the upstream submit/result flow, without exec."""
    _processes = None

    def __init__(self, max_workers=1):
        if max_workers != 1:
            raise ValueError("This budget-serial adapter requires exactly one worker")

    def submit(self, function, *args, **kwargs):
        future = Future()
        try:
            future.set_result(function(*args, **kwargs))
        except Exception as exc:
            future.set_exception(exc)
        return future

    def shutdown(self, **kwargs):
        pass


def _patch(stack: ExitStack, target, name: str, value):
    original = getattr(target, name)
    setattr(target, name, value)
    stack.callback(setattr, target, name, original)


def _json_response(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```") and text.endswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1])
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("Native FunctionSpec response must be a JSON object")
    return value


def run_aiscientist(
    broker,
    text_backend: Callable[..., Mapping[str, Any]],
    *,
    trace_dir: str | Path,
    registered_designs: Mapping[str, Any],
    task_description: str,
    task_name: str,
    seed: int,
    upstream_repo: str | Path = DEFAULT_UPSTREAM,
) -> dict:
    """Run the actual manager until six broker candidate slots are consumed.

    ``text_backend(messages, *, purpose)`` returns a serializable receipt with
    ``raw_response``. Broker owns fitting, budget validation, and final selection.
    This process-global native query binding intentionally disallows concurrent
    in-process runs; launch independent OS processes for separate experiments.
    """
    if not _IMPORT_LOCK.acquire(blocking=False):
        raise RuntimeError("AI-Scientist native module bindings are already in use")
    try:
        return _run_locked(broker, text_backend, Path(trace_dir), registered_designs,
                           task_description, task_name, seed, Path(upstream_repo))
    finally:
        _IMPORT_LOCK.release()


def _run_locked(broker, text_backend, trace_dir, registered_designs, task_description,
                task_name, seed, upstream_repo):
    modules = load_upstream(upstream_repo)
    from omegaconf import OmegaConf
    import jsonschema

    trace_dir.mkdir(parents=True, exist_ok=True)
    trace_path = trace_dir / "native_trace.jsonl"
    if trace_path.exists():
        raise FileExistsError("Refusing to overwrite an existing native experiment trace")
    NativeManager = modules["manager"].AgentManager
    NativeParallel = modules["parallel"].ParallelAgent
    NativeMinimal = modules["parallel"].MinimalAgent
    Node = modules["journal"].Node
    MetricValue = modules["metric"].MetricValue
    WorstMetricValue = modules["metric"].WorstMetricValue
    ExecutionResult = modules["interpreter"].ExecutionResult
    compile_prompt = modules["backend"].compile_prompt_to_md
    source_record = provenance(modules)
    state = {"model_receipts": [], "receipt_cursor": 0, "events": 0, "queries": 0}

    def record(kind, **payload):
        entry = {"event": state["events"], "kind": kind, **payload}
        with trace_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(entry, ensure_ascii=False, allow_nan=False) + "\n")
            stream.flush()
        state["events"] += 1

    adaptations = {
        "generated_python_execution": "disabled; one literal-only design request -> trusted broker",
        "candidate_slots": 6, "num_workers": 1, "executor": "synchronous Future API",
        "domain": "12 registered designs; fixed trusted fitter; 100 rounds per valid candidate",
        "literature_and_writeup": "not invoked",
        "plotting_and_vlm": "removed; plot validity is not applicable (False bug flag)",
        "num_seeds": 0, "multi_seed_reason": "external formal seed repetitions only",
        "metric": "broker candidate development primary; higher is better",
        "stage_goals": "domain-adapted, native completion methods retained",
        "stage_completion_criteria": "native queries task-mapped to trusted 100-round, 10-client evidence; no forced verdict",
        "final_selection": "broker development-best checkpoint, not native LLM preference",
        "checkpoint": "JSON trace snapshot instead of native pickle",
        "function_format_max_attempts": FUNCTION_FORMAT_MAX_ATTEMPTS,
        "function_format_retry": "same backend, original context and raw failed response; no invented reviews",
        "prompt_adapter_version": PROMPT_ADAPTER_VERSION,
    }
    record("provenance", **source_record, adaptations=adaptations)
    baseline = fixed_baseline_evidence(broker.initialize())
    if broker.status()["used_slots"] != 0 or broker.status()["remaining_slots"] != 6:
        raise ValueError("This adapter requires a fresh broker with exactly six candidate slots")
    record("baseline", evidence=baseline)

    def domain_contract():
        public = broker.status()
        return (
            "TASK-ADAPTED EXECUTION CONTRACT (overrides incompatible generic ML implementation suggestions):\n"
            + task_description + "\n"
            "Choose one registered design; the trusted evaluator alone trains for exactly 100 rounds. "
            "Never generate imports, functions, calls, file access, training loops or synthetic results. "
            "A code-generating response MUST have 2–4 concise natural-language sentences and ONE python block containing only "
            "design = {\"design_id\": \"<available design_id>\", \"hypothesis\": \"...\", "
            "\"experiment\": \"...\", \"expected_effect\": \"...\"}. "
            "All four values must be nonempty literal strings. Use actual available design IDs. "
            "Interpret tuning/creative/ablation ideas as choosing among these fixed designs; do not change rounds, "
            "datasets, training code, or the registry. Missing datasets and plots remain missing evidence: "
            "never claim they exist to satisfy a native stage-completion request. "
            "There are no VLM plots; use only the trusted development evidence. "
            "FunctionSpec JSON replies and named hyperparameter/ablation idea replies retain their requested formats.\n"
            + "Public baseline: " + json.dumps(baseline, ensure_ascii=False) + "\n"
            + "Current broker state: " + json.dumps(public, ensure_ascii=False)
        )

    def query(system_message=None, user_message=None, model=None, temperature=None,
              max_tokens=None, func_spec=None, **kwargs):
        query_id = state["queries"]
        state["queries"] += 1
        purpose = func_spec.name if func_spec is not None else "native_text"
        effective_system, transformations = adapt_native_prompt(system_message, purpose)
        record("prompt_transformation", query_id=query_id, purpose=purpose,
               version=PROMPT_ADAPTER_VERSION, transformations=transformations,
               original_sha256=hashlib.sha256(json.dumps(system_message, sort_keys=True).encode()).hexdigest(),
               effective_sha256=hashlib.sha256(json.dumps(effective_system, sort_keys=True).encode()).hexdigest())
        messages = []
        system = compile_prompt(effective_system) if effective_system else ""
        if not isinstance(system, str):
            raise TypeError("Visual inputs are not supported by this text-only adapter")
        system += "\n\n" + domain_contract()
        if func_spec is not None:
            system += ("\nReturn only a JSON object matching this native FunctionSpec: "
                       + json.dumps(func_spec.json_schema, ensure_ascii=False))
        messages.append({"role": "system", "content": system})
        if user_message:
            user = compile_prompt(user_message)
            if not isinstance(user, str):
                raise TypeError("Visual inputs are disabled")
            messages.append({"role": "user", "content": user})
        max_attempts = FUNCTION_FORMAT_MAX_ATTEMPTS if func_spec is not None else 1
        for attempt in range(1, max_attempts + 1):
            record("model_request", purpose=purpose, messages=messages, query_id=query_id,
                   function_attempt=attempt, function_max_attempts=max_attempts,
                   native_model_setting=model, native_temperature=temperature)
            receipt = dict(text_backend(messages, purpose=purpose))
            raw = receipt.get("raw_response")
            if not isinstance(raw, str):
                raise TypeError("Text backend receipt must contain string raw_response")
            state["model_receipts"].append(receipt)
            record("model_response", purpose=purpose, receipt=receipt, query_id=query_id,
                   function_attempt=attempt, function_max_attempts=max_attempts)
            if func_spec is None:
                return raw
            try:
                parsed = _json_response(raw)
                jsonschema.validate(parsed, func_spec.json_schema)
                return parsed
            except (ValueError, jsonschema.ValidationError) as exc:
                record("function_format_error", purpose=purpose, query_id=query_id,
                       function_attempt=attempt, function_max_attempts=max_attempts,
                       error_type=type(exc).__name__, error=str(exc)[:2000],
                       will_retry=attempt < max_attempts)
                if attempt == max_attempts:
                    raise NativeFunctionFormatError(
                        f"Native FunctionSpec {purpose} failed JSON/schema validation after "
                        f"{max_attempts} real backend attempts; no replacement verdict was generated"
                    ) from exc
                # Retry only output formatting, not an experiment. Preserve the
                # native prompt/evidence and the actual failed response verbatim.
                messages = messages + [{"role": "assistant", "content": raw}, {
                    "role": "user", "content": (
                        f"Formatting attempt {attempt + 1} of {max_attempts} for native function {purpose}. "
                        "Your previous response failed strict JSON/schema validation: "
                        + str(exc)[:1200] + ". Return ONLY one valid JSON object matching the "
                        "FunctionSpec below. Do not use Markdown fences or append explanations. "
                        "Use only the original trusted evidence; do not rerun an experiment or invent a verdict. "
                        "Schema: " + json.dumps(func_spec.json_schema, ensure_ascii=False)
                    )}]

    class BrokerParallel(NativeParallel):
        def _define_global_metrics(self):
            return "Trusted candidate development primary, maximize=true; evaluator metric is fixed."

        def _run_plot_aggregation(self, node, seed_nodes):
            record("disabled_plot_aggregation", node_id=node.id, seed_node_count=len(seed_nodes))
            return node

        @staticmethod
        def _process_node_wrapper(node_data, task_desc, cfg, gpu_id=None, memory_summary=None,
                                  evaluation_metrics=None, stage_name=None, new_ablation_idea=None,
                                  new_hyperparam_idea=None, *unused_plot_args, **kwargs):
            if broker.status()["remaining_slots"] <= 0:
                raise _CandidateBudgetReached()
            worker = NativeMinimal(task_desc, cfg, memory_summary=memory_summary,
                                   evaluation_metrics=evaluation_metrics, stage_name=stage_name)
            parent = Node.from_dict(copy.deepcopy(node_data), journal=None) if node_data else None
            record("native_generation_start", stage=stage_name,
                   parent_id=parent.id if parent else None,
                   action=("draft" if parent is None else "debug" if parent.is_buggy
                           else "tuning" if new_hyperparam_idea is not None
                           else "ablation" if new_ablation_idea is not None else "improve"))
            if parent is None:
                child = worker._draft()
            elif parent.is_buggy:
                child = worker._debug(parent)
            elif new_hyperparam_idea is not None:
                child = worker._generate_hyperparam_tuning_node(parent, new_hyperparam_idea)
            elif new_ablation_idea is not None:
                child = worker._generate_ablation_node(parent, new_ablation_idea)
            else:
                child = worker._improve(parent)
            record("native_proposal", node_id=child.id, parent_id=parent.id if parent else None,
                   stage=stage_name, plan=child.plan, literal_request=child.code)
            receipts = state["model_receipts"][state["receipt_cursor"]:]
            state["receipt_cursor"] = len(state["model_receipts"])
            started = time.monotonic()
            parse_error = None
            try:
                proposal = parse_design_request(child.code, registered_designs)
            except InvalidDesignRequest as exc:
                parse_error = str(exc)
                # Invalid proposals consume one broker slot but never reach the fitter.
                proposal = {"design_id": "__INVALID_LITERAL_REQUEST__", "hypothesis": parse_error,
                            "experiment": "Rejected by literal-only execution boundary",
                            "expected_effect": "No training or code execution"}
            result = broker.evaluate_design(**proposal, native_trace_path=str(trace_path),
                                            model_receipts=receipts)
            record("broker_result", node_id=child.id, result=result, parse_error=parse_error)
            success = result["status"] == "COMPLETE"
            terminal = json.dumps(result, ensure_ascii=False, allow_nan=False)
            execution = ExecutionResult(term_out=[terminal], exec_time=time.monotonic() - started,
                                        exc_type=None if success else result["status"],
                                        exc_info=None, exc_stack=None)
            # Native output review is retained, but cannot invent or override the trusted score.
            worker.parse_exec_result(child, execution, str(trace_dir))
            if success:
                score = float(result["candidate"]["primary"])
                if not math.isfinite(score):
                    raise ValueError("Broker returned a non-finite COMPLETE development score")
                child.metric = MetricValue(score, maximize=True, name="development_primary")
            else:
                child.metric = WorstMetricValue()
                child.is_buggy = True
            child.is_buggy_plots = False  # Explicitly disabled/non-applicable, not fabricated VLM evidence.
            child.vlm_feedback_summary = ["Plotting/VLM disabled. Trusted evidence: " + terminal]
            child.datasets_successfully_tested = [task_name] if success else []
            child.analysis = (child.analysis or "") + "\nTrusted evaluator evidence: " + terminal
            record("native_node_result", node=child.to_dict())
            return child.to_dict()

    class DomainManager(NativeManager):
        def _save_checkpoint(self):
            snapshot(self, "checkpoint")

    def snapshot(manager, reason):
        record("native_state", reason=reason,
               current_stage=manager.current_stage.name if manager.current_stage else None,
               stages=[{"name": stage.name, "stage_number": stage.stage_number,
                        "goals": stage.goals, "max_iterations": stage.max_iterations}
                       for stage in manager.stages],
               stage_history=[vars(item) for item in manager.stage_history],
               journals={name: [node.to_dict() for node in journal.nodes]
                         for name, journal in manager.journals.items()}, broker=broker.status())

    cfg = OmegaConf.load(modules["repo"] / "bfts_config.yaml")
    cfg.agent.num_workers = 1
    cfg.agent.multi_seed_eval.num_seeds = 0
    cfg.workspace_dir = str(trace_dir / "native_workspace")
    cfg.log_dir = str(trace_dir)
    cfg.generate_report = False
    for role in ("code", "feedback", "vlm_feedback"):
        cfg.agent[role].model = "shared-text-backend"
    cfg.agent.summary = {"model": "shared-text-backend", "temp": .3}
    cfg.agent.select_node = {"model": "shared-text-backend", "temp": .3}
    task = {"Title": task_name, "Abstract": task_description,
            "Short Hypothesis": "One registered design may improve trusted development performance.",
            "Experiments": "Propose designs from the registered menu within six candidate slots.",
            "Risk Factors and Limitations": "Fixed design space, fixed 100 rounds, no new datasets or generated code."}
    previous_random = random.getstate()
    manager = None
    termination = "native_manager_completed"
    with ExitStack() as stack, (trace_dir / "native_stdout.log").open("w") as log:
        stack.callback(random.setstate, previous_random)
        random.seed(seed)
        for module in (modules["manager"], modules["parallel"], modules["journal"], modules["backend"]):
            _patch(stack, module, "query", query)
        _patch(stack, modules["manager"], "ParallelAgent", BrokerParallel)
        _patch(stack, modules["parallel"], "ProcessPoolExecutor", _SerialExecutor)
        _patch(stack, modules["parallel"], "get_gpu_count", lambda: 0)
        # Defensive: no upstream Interpreter.run may become reachable through this adapter.
        def forbidden_execution(*args, **kwargs):
            raise RuntimeError("Generated Python execution is forbidden in this adapter")
        _patch(stack, modules["interpreter"].Interpreter, "run", forbidden_execution)
        with redirect_stdout(log), redirect_stderr(log):
            manager = DomainManager(json.dumps(task), cfg, trace_dir / "native_workspace")
            manager.main_stage_goals = {
                1: "Obtain a valid design evaluation from the fixed registered menu.",
                2: "Tune by choosing a different registered design; all candidates use 100 trusted rounds.",
                3: "Explore scientifically motivated registered designs using development evidence.",
                4: "Analyze component contrasts among registered designs without altering the trusted fitter.",
            }
            manager.current_stage.goals = manager.main_stage_goals[1]

            def step_callback(stage, journal):
                snapshot(manager, "step_completed")
                if broker.status()["remaining_slots"] == 0:
                    raise _CandidateBudgetReached()

            try:
                manager.run(exec_callback=forbidden_execution, step_callback=step_callback)
            except _CandidateBudgetReached:
                termination = "candidate_budget_exhausted"
            except Exception as exc:
                record("controller_error", error_type=type(exc).__name__, error=str(exc))
                snapshot(manager, "error")
                raise
            snapshot(manager, termination)
    if broker.status()["remaining_slots"] != 0:
        record("incomplete", reason="Native manager stopped before using the shared candidate budget")
        raise RuntimeError("Native manager stopped early; refusing to fabricate remaining candidates")
    # This is the final native trace write: the broker hashes it when sealing.
    # Never append a post-seal summary to a sealed trace (or trace directory).
    record("controller_finished", termination=termination,
           native_stage_at_stop=manager.current_stage.name if manager.current_stage else None,
           model_calls=len(state["model_receipts"]))
    seal = broker.seal_selection()
    result = {"label": LABEL, "termination": termination, "seal": seal,
              "upstream_commit": PINNED_COMMIT, "native_trace_path": str(trace_path),
              "native_stage_at_stop": manager.current_stage.name if manager.current_stage else None,
              "native_stage_history": [vars(item) for item in manager.stage_history],
              "model_calls": len(state["model_receipts"]), "adaptations": adaptations}
    return result
