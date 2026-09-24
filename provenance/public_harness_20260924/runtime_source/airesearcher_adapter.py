"""Versioned task adaptation of HKUDS AI-Researcher's actual InnoFlow source.

The pinned checkout remains unchanged. Core/AgentModule/planning tools execute
upstream code. Agent factory and InnoFlow ASTs are loaded from the checkout with
enumerated resource-import, tool-list, task-prompt and refinement-budget edits.
There is no replacement search loop and model output is never Python-executed.
Full before/after source hashes and transformed AST source are recorded per run.
"""
from __future__ import annotations

import argparse
import ast
import asyncio
from contextlib import ExitStack, redirect_stderr, redirect_stdout
import copy
import hashlib
import importlib
import importlib.util
import inspect
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import threading
import time
import types
import typing


LABEL = "AI-Researcher (task-adapted experimental controller)"
PINNED_COMMIT = "f9a6f8480860c193afff600eeffe3defcee8a978"
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_UPSTREAM = ROOT / "references/public_harness_20260924/AI-Researcher"
CORE_HASHES = {
    "research_agent/run_infer_idea.py": "574abdf972b0681d38437c009ebbcd919a5fa9d2d3f0877f5997a1b23af8e790",
    "research_agent/inno/core.py": "d33aaa15443cd81e0a2e3020b9ef5cb9082240743e62930d79c34efdd296a8ab",
    "research_agent/inno/workflow/flowcache.py": "2ba8a788196a1ba33eaefd66c4089d2b9f1ab3f4b42a846b8fe649a04069d177",
}
DEPENDENCIES = {
    "litellm": "litellm==1.55.0", "openai": "openai", "inquirer": "inquirer",
    "dotenv": "python-dotenv", "tenacity": "tenacity", "rich": "rich",
    "pydantic": "pydantic", "tiktoken": "tiktoken", "torch": "torch",
    "flask": "Flask", "httpx": "httpx", "prompt_toolkit": "prompt-toolkit",
}
RESOURCE_TOOLS = {
    "gen_code_tree_structure", "read_file", "terminal_page_down", "terminal_page_up",
    "terminal_page_to", "list_files", "execute_command", "create_file", "write_file",
    "create_directory", "run_python", "open_local_file", "page_up_markdown",
    "page_down_markdown", "find_on_page_ctrl_f", "find_next", "visualizer",
    "question_answer_on_whole_page", "google_scholar_search", "download_from_pdf_link",
}
FORMAT_ATTEMPTS = 3  # Includes the initial response; at most two repairs.
PLANNING_DESCRIPTIONS = {
    "plan_dataset": "Record the dataset plan as concise natural-language references to the already registered task and trusted pipeline. Every argument is a short phrase (at most 20 words). dataset_location names the trusted broker, not an invented path. No Python, imports, URLs, file names, new preprocessing, or new loaders. This records a plan; it does not load or execute data.",
    "plan_training": "Record the training plan as concise natural-language references to the unchanged trusted fitter. Every argument is a short phrase (at most 20 words). Preserve ten clients, 100 rounds, registered design configuration, native loss and optimizer, and development-only logging. Do not write Python, invent settings, or execute training here.",
    "plan_testing": "Record the development-evaluation plan, not held-out testing. Every argument is a short phrase (at most 20 words). test_metric references the registered primary metric and loss; test_data references the broker's development partition; test_code is a natural-language reference to the trusted evaluator, never Python or a file path.",
}
UNTYPED_TEXT_ARGUMENTS = {
    "case_resolved": "task_response", "case_not_resolved": "failure_reason",
    "transfer_to_code_review_agent": "atomic_idea", "transfer_to_judge_agent": "task_report",
}
_RUN_LOCK = threading.Lock()


class UpstreamUnavailable(RuntimeError):
    """Fail closed instead of supplying an imitation controller."""


class NativeRunIncomplete(RuntimeError):
    """The native controller did not complete the registered budget."""


class NativeBudgetComplete(BaseException):
    """External global budget boundary, not a native tool error or fake result."""


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def _git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                          text=True, check=True, timeout=30).stdout.strip()


def dependency_report():
    return {package: importlib.util.find_spec(module) is not None
            for module, package in DEPENDENCIES.items()}


def load_upstream(repo=DEFAULT_UPSTREAM):
    """Import only the native core, not eager browser/tool discovery packages."""
    repo = Path(repo).resolve()
    if not (repo / ".git").is_dir() or _git(repo, "rev-parse", "HEAD") != PINNED_COMMIT:
        raise UpstreamUnavailable("Missing or wrong AI-Researcher pinned checkout")
    if _git(repo, "diff", "HEAD", "--", "research_agent", "global_state.py", "setup.cfg"):
        raise UpstreamUnavailable("Upstream tracked code differs from pinned HEAD")
    for name, expected in CORE_HASHES.items():
        if not (repo / name).is_file() or _sha(repo / name) != expected:
            raise UpstreamUnavailable("Audited source hash mismatch: " + name)
    missing = [name for name, ready in dependency_report().items() if not ready]
    if missing:
        raise UpstreamUnavailable("Missing lightweight native dependencies: " + ", ".join(missing))
    existing = sys.modules.get("research_agent.inno.core")
    if existing and not Path(existing.__file__).resolve().is_relative_to(repo):
        raise UpstreamUnavailable("A different research_agent package is already imported")
    sys.path.insert(0, str(repo))
    try:
        modules = {name: importlib.import_module("research_agent.inno." + name)
                   for name in ("core", "types", "util", "registry", "workflow.flowcache")}
    except Exception as exc:
        raise UpstreamUnavailable("Native core import failed: " + type(exc).__name__ + ": " + str(exc)) from exc
    finally:
        sys.path.pop(0)
    for module in modules.values():
        if not Path(module.__file__).resolve().is_relative_to(repo):
            raise UpstreamUnavailable("Native module resolved outside pinned checkout")
    modules["repo"] = repo
    return modules


def _control_signature(tree):
    """Record native forward's stage awaits, loops, branches, and state stores."""
    forward = next(n for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef) and n.name == "forward")
    signature = []
    for node in ast.walk(forward):
        if isinstance(node, ast.Await):
            signature.append(["await", ast.dump(node.value, include_attributes=False)])
        elif isinstance(node, (ast.For, ast.If)):
            expression = node.iter if isinstance(node, ast.For) else node.test
            signature.append([type(node).__name__, ast.dump(expression, include_attributes=False)])
        elif isinstance(node, ast.Assign) and any(isinstance(t, ast.Subscript) for t in node.targets):
            signature.append(["state_store", ast.dump(node, include_attributes=False)])
    return signature


class _ResourceToolTransform(ast.NodeTransformer):
    """Only replace explicit resource capability lists inside native factories."""
    def __init__(self, ml=False):
        self.ml = ml
        self.edits = []

    def visit_List(self, node):
        if any(isinstance(item, ast.Name) and item.id in RESOURCE_TOOLS for item in node.elts):
            removed = [item.id for item in node.elts if isinstance(item, ast.Name) and item.id in RESOURCE_TOOLS]
            kept = [item for item in node.elts if not (isinstance(item, ast.Name) and item.id in RESOURCE_TOOLS)]
            kept.append(ast.Name(id="read_task_artifact", ctx=ast.Load()))
            if self.ml:
                kept.append(ast.Name(id="evaluate_design", ctx=ast.Load()))
            self.edits.append({"kind": "resource_tool_list", "line": node.lineno,
                               "removed": removed, "added": ["read_task_artifact"] + (["evaluate_design"] if self.ml else [])})
            node.elts = kept
        return self.generic_visit(node)


class _FlowTaskTransform(ast.NodeTransformer):
    """Task-prompt/resource expressions only; never create a controller loop."""
    PROMPTS = {"query", "idea_query", "code_survey_query", "plan_query", "ml_dev_query",
               "ml_submit_query", "exp_planner_query", "refine_query"}

    def __init__(self, refinements):
        self.refinements = refinements
        self.in_forward = False
        self.edits = []

    def visit_AsyncFunctionDef(self, node):
        old = self.in_forward
        self.in_forward = node.name == "forward"
        node = self.generic_visit(node)
        self.in_forward = old
        return node

    def visit_Expr(self, node):
        call = node.value
        if (self.in_forward and isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                and isinstance(call.func.value, ast.Name) and call.func.value.id == "messages"
                and call.func.attr == "extend" and len(call.args) == 1
                and isinstance(call.args[0], ast.Name) and call.args[0].id == "survey_messages"):
            # Native AgentModule returns the same input list after extending it.
            # Re-appending that alias doubles all existing history each idea.
            # Keep distinct returned messages, but never append a list to itself.
            call.args[0] = ast.IfExp(
                test=ast.Compare(left=ast.Name(id="survey_messages", ctx=ast.Load()),
                    ops=[ast.Is()], comparators=[ast.Name(id="messages", ctx=ast.Load())]),
                body=ast.List(elts=[], ctx=ast.Load()),
                orelse=ast.Name(id="survey_messages", ctx=ast.Load()))
            self.edits.append({"kind": "native_alias_duplication_correction", "line": node.lineno,
                "upstream": "messages.extend(survey_messages)",
                "adapted": "messages.extend([] if survey_messages is messages else survey_messages)",
                "reason": "AgentModule returns its input list; prevent self-duplication without truncating or dropping unique messages"})
        return self.generic_visit(node)

    def visit_Assign(self, node):
        if not self.in_forward:
            return self.generic_visit(node)
        names = [t.id for t in node.targets if isinstance(t, ast.Name)]
        if any(name in self.PROMPTS for name in names) and isinstance(node.value, ast.JoinedStr):
            stage = names[0] + "@" + str(node.lineno)
            node.value = ast.Call(func=ast.Name(id="_task_prompt", ctx=ast.Load()),
                                  args=[ast.Constant(stage), ast.Call(func=ast.Name(id="locals", ctx=ast.Load()), args=[], keywords=[])], keywords=[])
            self.edits.append({"kind": "task_prompt", "stage": stage, "line": node.lineno})
        elif names == ["data_module"]:
            node.value = ast.Name(id="_task_data", ctx=ast.Load())
            self.edits.append({"kind": "fixed_task_metadata", "line": node.lineno})
        elif names == ["EXP_ITER_TIMES"]:
            if not isinstance(node.value, ast.Constant) or node.value.value != 2:
                raise UpstreamUnavailable("Unexpected native refinement count")
            node.value = ast.Constant(self.refinements)
            self.edits.append({"kind": "budget_parameter", "line": node.lineno,
                               "name": "EXP_ITER_TIMES", "upstream": 2, "adapted": self.refinements})
        elif names == ["messages"] and "You have generated" in ast.unparse(node.value):
            node.value = ast.List(elts=[ast.Dict(keys=[ast.Constant("role"), ast.Constant("content")],
                values=[ast.Constant("user"), ast.Call(func=ast.Name(id="_task_prompt", ctx=ast.Load()),
                    args=[ast.Constant("idea_selection"), ast.Call(func=ast.Name(id="locals", ctx=ast.Load()), args=[], keywords=[])], keywords=[])])], ctx=ast.Load())
            self.edits.append({"kind": "task_prompt", "stage": "idea_selection", "line": node.lineno})
        return self.generic_visit(node)


def _source_module(repo, relative, bindings, *, transform=None, keep=None):
    """Execute audited source definitions, not copied replacement functions.

    Import discovery and executable top-level demos are outside the experiment
    scope. Definitions keep their original code filename/line numbers. This is
    explicitly source-adapted loading, not an assertion of unmodified import.
    """
    path = repo / relative
    source = path.read_text()
    if source != subprocess.run(["git", "-C", str(repo), "show", "HEAD:" + relative],
                                capture_output=True, text=True, check=True, timeout=30).stdout:
        raise UpstreamUnavailable("Source file differs from pinned blob: " + relative)
    tree = ast.parse(source, filename=str(path))
    excluded = [{"kind": "excluded_top_level", "node": type(n).__name__, "line": n.lineno}
                for n in tree.body if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
    tree.body = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                 and (keep is None or n.name in keep)]
    before = _control_signature(tree) if relative.endswith("run_infer_idea.py") else None
    if transform:
        tree = transform.visit(tree)
    ast.fix_missing_locations(tree)
    after = _control_signature(tree) if before is not None else None
    if before is not None and before != after:
        raise UpstreamUnavailable("Adapter unexpectedly changed native stage/loop/branch/state structure")
    module_name = "biocoloop_airesearcher_sourceadapted." + path.stem
    module = types.ModuleType(module_name)
    module.__file__ = str(path)
    module.__dict__.update(bindings)
    # Trusted, hash-verified upstream source only. Never compile LLM output.
    exec(compile(tree, str(path), "exec", dont_inherit=True), module.__dict__)
    adapted_source = ast.unparse(tree)
    record = {"path": relative, "sha256": _sha(path), "loading": "source_definitions_with_explicit_task_transforms",
              "excluded_top_level": excluded, "edits": getattr(transform, "edits", []),
              "transformed_source": adapted_source,
              "transformed_source_sha256": hashlib.sha256(adapted_source.encode()).hexdigest(), "control_signature": before,
              "control_signature_preserved": before == after if before is not None else None}
    return module, record


def _json_object(raw):
    raw = raw.strip()
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result
    def invalid_constant(value):
        raise ValueError("Non-finite JSON constant: " + value)
    value = json.loads(raw, object_pairs_hook=unique, parse_constant=invalid_constant)
    if not isinstance(value, dict):
        raise ValueError("Tool response must be an object")
    return value


def _unwrap_transport(raw):
    """Strip only complete serialization wrappers, never surrounding prose."""
    payload, wrappers = raw.strip(), []
    # A fence and a tool_call tag may each wrap the whole object once. Repeated
    # wrappers, multiple calls and surrounding prose remain invalid JSON.
    for _ in range(2):
        fence = re.fullmatch(r"```(?:json)?\s*\n?(.*?)\s*```", payload, re.DOTALL)
        tagged = re.fullmatch(r"<tool_call>\s*(.*?)\s*</tool_call>", payload, re.DOTALL)
        if fence is not None and "json_fence" not in wrappers:
            payload, shape = fence.group(1), "json_fence"
        elif tagged is not None and "tool_call_wrapper" not in wrappers:
            payload, shape = tagged.group(1), "tool_call_wrapper"
        else:
            break
        wrappers.append(shape)
        payload = payload.strip()
    return payload, wrappers


def _transport_schema(tools):
    """Task descriptions plus explicit repair of four untyped text schemas."""
    schema = copy.deepcopy(tools)
    for entry in schema:
        function = entry["function"]
        text_argument = UNTYPED_TEXT_ARGUMENTS.get(function["name"])
        properties = function.get("parameters", {}).get("properties", {})
        if text_argument in properties:
            parameter = properties[text_argument]
            # Native get_type_info mistakes inspect._empty.__annotations__={}
            # for a typed dictionary. Actual source signatures have NO type
            # annotation and their documented report/handoff argument is text.
            if parameter.get("type") == "object" and parameter.get("properties") == {}:
                properties[text_argument] = {"type": "string",
                    "description": "Concise natural-language report; no code or invented evidence."}
        if function["name"] in PLANNING_DESCRIPTIONS:
            function["description"] = PLANNING_DESCRIPTIONS[function["name"]]
            for name, parameter in function.get("parameters", {}).get("properties", {}).items():
                parameter["description"] = f"{name}: concise natural-language reference to the unchanged trusted pipeline, at most 20 words; no code or invented paths."
    return schema


def _transport_response(raw, schema, tool_choice):
    """Public test helper retaining the content/call pair interface."""
    content, decoded, _ = _decode_transport_response(raw, schema, tool_choice)
    return content, decoded


def _decode_transport_response(raw, schema, tool_choice):
    """Single-call text codec; native dispatch still owns argument semantics."""
    functions = {item["function"]["name"]: item["function"] for item in schema}
    claims_structured_call = any(marker in raw for marker in (
        '"tool"', '"arguments"', '"tool_choice"', '"tools"', '"function"', '"tool_calls"',
        "'tool'", "'arguments'", "'tool_choice'", "'tools'", "'function'", "'tool_calls'",
        "<tool_call>", "</tool_call>"))
    claims_structured_call = claims_structured_call or any(
        re.search(r'["\']' + re.escape(name) + r'["\']\s*:', raw) for name in functions)
    payload, wrappers = _unwrap_transport(raw)
    if tool_choice != "required" and not claims_structured_call:
        # Native AUTO agents may finish with ordinary assistant text. Preserve
        # that text exactly, INCLUDING JSON-shaped prose such as {"design_id":
        # "D07"}. Braces do not claim a tool call. The optional final envelope
        # is transport sugar; no other no-tool content requires a schema.
        try:
            optional_final = _json_object(payload)
        except ValueError:
            optional_final = None
        if (optional_final is not None and set(optional_final) == {"final"}
                and isinstance(optional_final["final"], str)):
            return optional_final["final"], None, {"shape": "final", "wrappers": wrappers}
        return raw, None, None
    decoded = _json_object(payload)
    if set(decoded) == {"final"} and isinstance(decoded["final"], str):
        if tool_choice == "required":
            raise ValueError("This native stage requires a tool call, not a final answer")
        return decoded["final"], None, {"shape": "final", "wrappers": wrappers}
    normalization = {"shape": None, "wrappers": wrappers, "arguments_encoding": "object"}
    if set(decoded) == {"tool"} and isinstance(decoded["tool"], str) and decoded["tool"] in functions:
        parameters = functions[decoded["tool"]].get("parameters", {})
        if parameters.get("properties") == {} and parameters.get("required") == []:
            # An explicitly selected zero-arity tool needs no argument values.
            # Canonicalize its absent empty object; never fill a data-bearing or
            # optional parameter, and leave native context injection untouched.
            decoded = {**decoded, "arguments": {}}
            normalization["shape"] = "zero_arity_omitted_arguments"
    if set(decoded) == {"tool", "arguments"}:
        name, arguments = decoded["tool"], decoded["arguments"]
        normalization["shape"] = normalization["shape"] or "tool_arguments"
    elif set(decoded) == {"name", "arguments"}:
        name, arguments = decoded["name"], decoded["arguments"]
        normalization["shape"] = "name_arguments"
    elif "function" in decoded and set(decoded) <= {"function", "type", "id"}:
        function = decoded["function"]
        if (not isinstance(function, dict) or set(function) != {"name", "arguments"}
                or ("type" in decoded and decoded["type"] != "function")
                or ("id" in decoded and not isinstance(decoded["id"], str))):
            raise ValueError("A function wrapper requires exactly name/arguments and valid id/type metadata")
        name, arguments = function["name"], function["arguments"]
        normalization["shape"] = "function_wrapper"
    elif len(decoded) == 1 and next(iter(decoded)) in functions:
        name, arguments = next(iter(decoded.items()))
        normalization["shape"] = "exposed_tool_key"
    else:
        raise ValueError("Return exactly one explicit single-tool object or one permitted final object")
    if not isinstance(name, str):
        raise ValueError("Tool name must be an explicit string")
    if name not in functions:
        raise ValueError("Unknown tool " + name + "; auto/required are calling policies, never tool names")
    if isinstance(arguments, str) and normalization["shape"] in {"name_arguments", "function_wrapper"}:
        # Standard function calls serialize arguments as JSON text. Decode once
        # as one strict object; no recursive decoding, fence or fragment repair.
        arguments = _json_object(arguments)
        normalization["arguments_encoding"] = "json_string"
    if not isinstance(arguments, dict):
        raise ValueError("Tool arguments must be one JSON object")
    # Original MetaChain.handle_tool_calls does json.loads -> func(**args),
    # with owned context injection and its own caught invocation errors. JSON
    # schema is model-facing documentation, not a runtime type validator.
    # Preserve missing/extra arguments, null and all other JSON values exactly;
    # native functions (and the trusted evaluator) decide their validity.
    return None, {"tool": name, "arguments": arguments}, normalization


class AIResearcherAdapter:
    """Run actual source InnoFlow against a trusted fixed-task broker."""
    def __init__(self, broker, text_backend, output_dir, *, upstream=DEFAULT_UPSTREAM,
                 refinements=5, max_model_calls=160, max_stage_messages=48):
        if refinements != 5:
            raise ValueError("Registered six-slot protocol uses one implementation plus five refinements")
        self.broker, self.backend = broker, text_backend
        self.output = Path(output_dir).resolve()
        self.repo = Path(upstream).resolve()
        self.refinements = refinements
        self.max_model_calls, self.max_stage_messages = max_model_calls, max_stage_messages
        self.receipts, self.source_records, self.stage_events = [], [], []
        self.evidence = []
        self.stage = {"agent": "not_started", "iteration": None}
        self.trace_path = self.output / "native_trace.jsonl"
        self.last_context = {}
        self.initialized = False
        self.sealed = False
        self.infrastructure_failure = None

    def _trace(self, event, **fields):
        record = {"event": event, "unix": time.time(), "stage": dict(self.stage), **fields}
        with self.trace_path.open("a") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")

    def _check_budget_boundary(self):
        if self.infrastructure_failure is not None:
            raise NativeRunIncomplete("Trusted evaluator infrastructure failed; native experiment aborted") from self.infrastructure_failure
        status = self.broker.status()
        if status["used_slots"] >= 6 and status.get("status", "READY") in {"READY", "DEVELOPMENT_SEALED"}:
            raise NativeBudgetComplete()

    def _public_task(self):
        status = self.broker.status()
        return {"task": status.get("task", getattr(getattr(self.broker, "config", None), "task", "registered task")),
                "task_description": getattr(self, "task_description", "Synthetic integration task; no real biological performance"),
                "registered_designs": getattr(self, "registered_designs", status.get("available_designs", {})),
                "protocol": "10 original clients; fixed D00 reference; six proposal slots; 100 rounds per fit; development evidence only",
                "development_status": status,
                "completed_candidate_evidence": copy.deepcopy(self.evidence),
                "constraints": "Choose only a registered design ID. No Python, shell, file access, downloads, data changes, fit-budget changes, or held-out access."}

    def _instructions(self, agent, context=None):
        role = agent.name
        rules = {
            "Paper Survey Agent": "Generate a distinct feasible design idea by naming ONE exact registered design ID and its unchanged parameters, or select and enhance the most novel of the five native draft ideas when requested. No new IDs or parameter combinations. Be concise. This is design ideation; do not evaluate candidates yet.",
            "Code Survey Agent": "Map the idea to ONE exact registered design ID and its unchanged parameters; no invented IDs or parameter combinations. If a prior draft is infeasible, explain that and choose the nearest feasible registered design yourself. No code is written or read.",
            "Coding Plan Agent": "Use plan_dataset, plan_training, plan_testing in separate calls to record the fixed task, unchanged 100-round fitter and development evaluation plan. Each argument is a concise natural-language phrase (at most 20 words) referring to the existing trusted pipeline, never Python or an invented file path. test_code also means a natural-language evaluator reference. Never invent data access or change fitting. Finish with case_resolved only after those three native plans exist; a plan merely written in prose was NOT recorded.",
            "Machine Learning Agent": "Implement the plan by requesting exactly ONE registered candidate through evaluate_design during implementation/refinement. Inspect actual returned development evidence, then call case_resolved(task_response=your report). For the submit stage, report the existing evaluated candidate WITHOUT another evaluation. Never invent metrics. If the six-slot budget is exhausted, only report existing evidence.",
            "Judge Agent": "Review whether the registered candidate implements the selected idea and obeys the fixed protocol. Use the native transfer_to_code_review_agent handoff when useful. Finish with case_resolved(fully_correct=boolean, suggestion=object). Judge correctness, not held-out performance.",
            "Code Review Agent": "Review the registered design/evidence via read_task_artifact; no code/file access. Return the implementation-fidelity review through transfer_to_judge_agent(task_report=report).",
            "Experiment Analysis Agent": "Analyze actual development-only evidence and propose the next refinement of the existing idea. Finish with case_resolved(analysis_report=text, further_plan={experiment: description}); do not run evaluations yourself.",
            "Prepare Agent": "External resource collection is disabled; the fixed benchmark supplies all public resources.",
        }
        planning_state = ""
        if role == "Coding Plan Agent":
            context = context or {}
            planning_state = "\nNative planning state: " + json.dumps({key: "recorded" if key in context else "MISSING"
                for key in ("dataset_plan", "training_plan", "testing_plan")})
        return (f"You are the upstream AI-Researcher {role}, task-adapted to a fixed BioCoLoop experiment. "
                + rules.get(role, "Use only the registered task tools.") + "\n"
                + json.dumps(self._public_task(), ensure_ascii=False)
                + planning_state + "\nThe tool interface below is the complete capability set. No other actions are available.")

    def _task_prompt(self, stage, state):
        # Preserve native feedback values without the unrelated GPU/code/paper prose.
        keys = ("ideas", "survey_res", "code_survey_res", "plan_res", "ml_dev_res",
                "judge_res", "submit_res", "analysis_report", "further_plan", "i")
        inherited = {key: state[key] for key in keys if key in state}
        actions = {
            "idea_query": "Propose one feasible innovative idea within the registered design menu; do not evaluate it.",
            "idea_selection": "Compare the five native draft ideas; select and enhance the most novel feasible idea without an evaluation.",
            "code_survey_query": "Map the selected idea's components to the fixed registered implementation menu and report implementation fidelity.",
            "plan_query": "Record dataset, training and development-evaluation plans using the unchanged trusted execution protocol.",
            "ml_dev_query": "Implement the selected idea by evaluating exactly one registered design; report actual returned evidence.",
            "ml_submit_query": "SUBMISSION REPORT ONLY: Report the existing evaluated candidate and its actual evidence. Do NOT request another fit.",
            "exp_planner_query": "Analyze the existing actual development evidence and formulate a further experiment/refinement plan.",
            "refine_query": "Refine the existing idea according to the native experiment analysis by evaluating exactly one registered design.",
            "query": "Perform your assigned native role using the inherited idea, plan, implementation and judgment evidence.",
        }
        return json.dumps({"native_prompt_stage": stage, "stage_action": actions[stage.split("@")[0]], "task": self._public_task(),
                           "native_stage_inputs": inherited}, ensure_ascii=False)

    def _adapt_agent(self, agent, seen=None):
        seen = set() if seen is None else seen
        if id(agent) in seen:
            return agent
        seen.add(id(agent))
        agent.instructions = lambda context, a=agent: self._instructions(a, context)
        agent.model = "biocoloop/shared-text-backend"
        # Native experiment analysis builds two resource lists; deduplicate only
        # the single replacement read tool, preserving all native control tools.
        unique = {}
        for function in agent.functions:
            if function.__name__ in RESOURCE_TOOLS:
                raise UpstreamUnavailable("Unsafe resource capability survived adaptation")
            unique.setdefault(function.__name__, function)
            for cell in function.__closure__ or ():
                try:
                    value = cell.cell_contents
                except ValueError:
                    continue
                if isinstance(value, self.native["types"].Agent):
                    self._adapt_agent(value, seen)
        agent.functions = list(unique.values())
        return agent

    async def _completion(self, **kwargs):
        """Text transport only: preserve the native tool selection and runner."""
        self._check_budget_boundary()
        if len(self.receipts) >= self.max_model_calls:
            raise NativeRunIncomplete("Global model-call cap reached")
        if self.infrastructure_failure is not None:
            raise NativeRunIncomplete("Trusted evaluator infrastructure failed; native experiment aborted") from self.infrastructure_failure
        text_messages = []
        for message in kwargs["messages"]:
            role = message["role"]
            if role not in {"system", "user", "assistant", "tool"}:
                raise NativeRunIncomplete("Unexpected native history role")
            content = message.get("content") or ""
            if not isinstance(content, str):
                raise NativeRunIncomplete("Only text messages are enabled")
            if message.get("tool_calls"):
                content += "\nTool calls: " + json.dumps(message["tool_calls"], ensure_ascii=False)
            if role == "tool":
                content = "Tool " + str(message.get("name", "")) + " returned: " + content
            text_messages.append({"role": role, "content": content})
        original_schema = kwargs.get("tools") or []
        schema = _transport_schema(original_schema)
        if schema != original_schema:
            self._trace("tool_schema_metadata_adaptation", before=original_schema, after=schema,
                reason="Concise task planning descriptions; exact four native-unannotated text report/handoff schema corrections only")
        final_rule = ("This native stage REQUIRES a tool call; plain text and final answers are not permitted. "
                      if kwargs.get("tool_choice") == "required" else
                      "This native AUTO stage may finish with ordinary plain assistant text: provide your idea/report directly. "
                      "No tool call is needed for a final answer. An optional {\"final\":\"answer\"} object is also allowed. ")
        grammar = ("\nTEXT TOOL TRANSPORT: " + final_rule + "To invoke exactly one available tool return ONLY JSON "
                   "{\"tool\":\"tool_name\",\"arguments\":{...}}. Use the supplied parameter types. "
                   "auto and required are calling policies, NEVER tool names. "
                   "For a tool call return ONE object only, not a list, multiple objects, markdown, or surrounding prose. "
                   "Keep it short enough to close the JSON within 512 output tokens. "
                   "If planning tools are available, call each separately using short natural-language phrases, not code. "
                   "Do not invent tool output, metrics, file paths, or parameter values. "
                   + json.dumps({"tool_choice": kwargs.get("tool_choice"), "tools": schema}, ensure_ascii=False))
        text_messages[0]["content"] += grammar
        purpose = "airesearcher/" + self.stage["agent"] + "/" + str(self.stage["iteration"])
        for format_attempt in range(FORMAT_ATTEMPTS):
            if len(self.receipts) >= self.max_model_calls:
                raise NativeRunIncomplete("Global model-call cap reached during tool-format repair")
            receipt = self.backend(text_messages, purpose=purpose)
            if inspect.isawaitable(receipt):
                receipt = await receipt
            required = {"raw_response", "input_tokens", "output_tokens", "seconds", "seed", "model", "call_id"}
            if not isinstance(receipt, dict) or not required.issubset(receipt) or not isinstance(receipt["raw_response"], str):
                raise NativeRunIncomplete("Text backend returned an incomplete receipt")
            self.receipts.append(copy.deepcopy(receipt))
            raw = receipt["raw_response"]
            try:
                content, decoded, normalization = _decode_transport_response(raw, schema, kwargs.get("tool_choice"))
                error = None
            except (ValueError, json.JSONDecodeError) as exc:
                error = str(exc)
                normalization = None
            self._trace("model_completion", call_id=receipt["call_id"], input_tokens=receipt["input_tokens"],
                        output_tokens=receipt["output_tokens"], model=receipt["model"], raw_response=raw,
                        format_attempt=format_attempt, transport_accepted=error is None, format_error=error,
                        normalization_shape=normalization,
                        transport_normalization=("omitted_empty_argument_object_for_zero_arity_tool"
                            if normalization and normalization["shape"] == "zero_arity_omitted_arguments" else None))
            if error is None:
                break
            if format_attempt == FORMAT_ATTEMPTS - 1:
                raise NativeRunIncomplete(f"Tool response remained invalid after {FORMAT_ATTEMPTS} format attempts: {error}")
            # No invalid fragment reaches native dispatch or updates native state.
            # Ask the same backend to express its own intended action correctly;
            # never select a tool, design, argument value, or result on its behalf.
            text_messages.extend([{"role": "assistant", "content": raw}, {"role": "user", "content":
                "FORMAT REPAIR ONLY. Your preceding response was not dispatched; no plan or action in it was recorded. "
                + error + ". Return exactly ONE complete JSON object for your intended next action, using only listed tool names "
                "and their required arguments, or one final object only if permitted. No prose, multiple objects, or Python. "
                "Use concise natural-language planning arguments (at most 20 words each), not invented paths/code. "
                "Do not fabricate results. Preserve your own intended decision; do not assume omitted tools already ran."}])
        tool_calls = None
        if decoded is not None:
            tool_calls = [{"id": "native_" + str(receipt["call_id"]), "type": "function",
                           "function": {"name": decoded["tool"], "arguments": json.dumps(decoded["arguments"])}}]
        from litellm import ModelResponse
        return ModelResponse(model=receipt["model"], choices=[{"index": 0,
            "message": {"role": "assistant", "content": content, "tool_calls": tool_calls},
            "finish_reason": "tool_calls" if tool_calls else "stop"}],
            usage={"prompt_tokens": receipt["input_tokens"], "completion_tokens": receipt["output_tokens"],
                   "total_tokens": receipt["input_tokens"] + receipt["output_tokens"]})

    def _build(self):
        self.native = load_upstream(self.repo)
        native_types = self.native["types"]
        core, flowcache = self.native["core"], self.native["workflow.flowcache"]
        owner = self

        def read_task_artifact():
            """Read the fixed public task/menu and actual development-only receipts; no file path is accepted."""
            return json.dumps(owner._public_task(), ensure_ascii=False)

        def evaluate_design(design_id, hypothesis, experiment, expected_effect):
            """Evaluate one registered design through the trusted ten-client, 100-round broker. All four arguments are nonempty strings. Duplicates and malformed requests consume proposal slots."""
            owner._check_budget_boundary()  # No seventh dispatch, receipt, or charged proposal.
            if owner.stage["agent"] != "Machine Learning Agent" or owner.stage["iteration"] == "submit":
                raise ValueError("Evaluation is unavailable outside native implementation/refinement")
            request = dict(design_id=design_id, hypothesis=hypothesis, experiment=experiment, expected_effect=expected_effect)
            owner._trace("design_request", request=request)
            try:
                reply = owner.broker.evaluate(request, native_trace_path=str(owner.trace_path), model_receipts=owner.receipts)
            except Exception as exc:
                # Native tool errors are normally visible to the agent, but a
                # fitter infrastructure failure must abort before another call.
                if type(exc).__name__ == "InfrastructureFailure":
                    owner.infrastructure_failure = exc
                raise
            owner._trace("design_evidence", reply=reply)
            owner.evidence.append(copy.deepcopy(reply))
            return native_types.Result(value=json.dumps(reply, ensure_ascii=False), context_variables={"latest_development_evidence": reply})

        # Native signature conversion reads runtime types rather than postponed hints.
        evaluate_design.__annotations__ = {name: str for name in ("design_id", "hypothesis", "experiment", "expected_effect")}
        bindings = {"json": json, "os": __import__("os"), "signature": inspect.signature,
                    "Agent": native_types.Agent, "Result": native_types.Result,
                    "register_agent": self.native["registry"].register_agent,
                    "register_tool": self.native["registry"].register_tool,
                    "function_to_json": self.native["util"].function_to_json,
                    "read_task_artifact": read_task_artifact, "evaluate_design": evaluate_design,
                    "DockerEnv": typing.Any, "BrowserEnv": typing.Any, "RequestsMarkdownBrowser": typing.Any,
                    "MetaChainLogger": core.MetaChainLogger,
                    **{name: getattr(typing, name) for name in ("Any", "Union", "List", "Dict", "Callable")}}
        planning, record = _source_module(self.repo, "research_agent/inno/tools/inno_tools/planning_tools.py", bindings)
        self.source_records.append(record)
        for name in ("plan_dataset", "plan_model", "plan_training", "plan_testing"):
            bindings[name] = getattr(planning, name)
        factories = {}
        for filename, names in {
            "prepare_agent": ["get_prepare_agent"], "idea_agent": ["get_idea_agent", "get_code_survey_agent"],
            "plan_agent": ["get_coding_plan_agent"], "ml_agent": ["get_ml_agent"],
            "judge_agent": ["get_judge_agent"], "exp_analyser": ["get_exp_analyser_agent"],
        }.items():
            module, record = _source_module(self.repo, "research_agent/inno/agents/inno_agent/" + filename + ".py",
                                            bindings, transform=_ResourceToolTransform(ml=filename == "ml_agent"))
            self.source_records.append(record)
            for name in names:
                original = getattr(module, name)
                def factory(*args, _original=original, **kwargs):
                    return owner._adapt_agent(_original(*args, **kwargs))
                factories[name] = factory

        class TracedAgentModule(flowcache.AgentModule):
            async def __call__(self, messages, context_variables, iter_times=None, *args, **kwargs):
                owner.stage = {"agent": self.agent.name, "iteration": iter_times}
                event = dict(owner.stage)
                owner.stage_events.append(event)
                before_slots = owner.broker.status()["used_slots"]
                owner._trace("stage_start", agent_module="research_agent.inno.workflow.flowcache.AgentModule")
                result = await super().__call__(messages, context_variables, iter_times=iter_times, *args, **kwargs)
                owner.last_context = copy.deepcopy(result[1])
                after_slots = owner.broker.status()["used_slots"]
                owner._trace("stage_end", context_variables=result[1], charged_slots=after_slots - before_slots)
                return result

        class BoundedMetaChain(core.MetaChain):
            async def run_async(self, *args, **kwargs):
                kwargs["max_turns"] = owner.max_stage_messages
                response = await super().run_async(*args, **kwargs)
                owner._check_budget_boundary()
                if not response.messages:
                    raise NativeRunIncomplete("Native agent produced no messages")
                if response.messages[-1].get("role") == "error":
                    raise NativeRunIncomplete(response.messages[-1].get("content", "Native agent error"))
                if (response.messages[-1].get("role") == "tool"
                        and str(response.messages[-1].get("content", "")).startswith("[Tool Call Error]")):
                    raise NativeRunIncomplete("Native stage exhausted with a failed completion/tool receipt")
                entry_agent = args[0] if args else kwargs["agent"]
                if entry_agent.tool_choice == "required" and response.messages[-1].get("name") not in {"case_resolved", "case_not_resolved"}:
                    raise NativeRunIncomplete("Native required-tool stage ended without its own completion tool")
                return response

        def load_instance(instance_path, task_level):
            return {"date_limit": "2026-09-24", "task_instructions": json.dumps(owner._public_task()), "source_papers": []}

        def github_search(metadata):
            return "External literature/repository collection disabled; fixed registered task resources supplied."

        def download_arxiv_source_by_title(paper_list, local_root, workplace_name):
            return "No paper downloads in the fixed-task experiment."

        flow_bindings = {**bindings, **factories, "FlowModule": flowcache.FlowModule,
                         "ToolModule": flowcache.ToolModule, "AgentModule": TracedAgentModule,
                         "load_instance": load_instance, "github_search": github_search,
                         "download_arxiv_source_by_title": download_arxiv_source_by_title,
                         "CHEEP_MODEL": "biocoloop/shared-text-backend", "COMPLETION_MODEL": "biocoloop/shared-text-backend",
                         "_task_prompt": self._task_prompt,
                         "_task_data": types.SimpleNamespace(TASK=json.dumps(self._public_task()), DATASET="fixed ten-client registered task",
                             BASELINE="D00", COMPARISON="development-only trusted evaluator", EVALUATION="unchanged primary metric and loss", REF="fixed task schema")}
        flow_module, record = _source_module(self.repo, "research_agent/run_infer_idea.py", flow_bindings,
            transform=_FlowTaskTransform(self.refinements), keep={"extract_json_from_output", "InnoFlow"})
        self.source_records.append(record)
        descriptor = types.SimpleNamespace(docker_workplace="/public_task", workplace_name="public_task")
        flow = flow_module.InnoFlow(cache_path=str(self.output / "native_cache"), log_path=str(self.output / "native.log"),
                                   code_env=descriptor, file_env=descriptor, web_env=None, model="biocoloop/shared-text-backend")
        client = BoundedMetaChain(log_path=str(self.output / "native.log"))
        flow.client = client
        for value in vars(flow).values():
            if isinstance(value, flowcache.AgentModule):
                value.client = client

        class FixedResources:
            async def __call__(self, messages, context_variables, **kwargs):
                owner._trace("resource_stage_disabled", stage_name="Prepare Agent", reason="fixed benchmark inputs; no literature/search")
                response = {"reference_papers": [], "reference_codebases": [], "reference_paths": []}
                return messages + [{"role": "assistant", "content": json.dumps(response)}], context_variables
        flow.prepare_agent = FixedResources()
        self.flow = flow
        self._provenance()

    def _provenance(self):
        imported = {}
        for name, module in list(sys.modules.items()):
            filename = getattr(module, "__file__", None)
            if name.startswith("research_agent") and filename and Path(filename).is_file():
                path = Path(filename).resolve()
                if path.is_relative_to(self.repo):
                    imported[name] = {"path": str(path.relative_to(self.repo)), "sha256": _sha(path)}
        _dump(self.output / "provenance.json", {
            "label": LABEL, "upstream": "https://github.com/HKUDS/AI-Researcher", "commit": PINNED_COMMIT,
            "upstream_worktree_modified": False, "source_loading": "native imports plus explicitly transformed upstream definitions",
            "native_imported_modules": imported, "source_transforms": self.source_records,
            "adapter_sha256": _sha(__file__), "python": sys.version,
            "upstream_python_metadata": ">=3.11; this exact source adaptation is smoke-tested in the recorded interpreter",
            "license": "setup.cfg declares MIT; no tracked LICENSE/COPYING file at this commit",
            "exclusions": ["literature retrieval", "paper writing", "browser", "Docker", "arbitrary generated code", "filesystem tools", "held-out feedback"],
            "budget_adaptation": {"IDEA_NUM": 5, "MAX_ITER_TIMES": 0, "EXP_ITER_TIMES": {"upstream": 2, "adapted": 5},
                "proposal_slots": 6, "budget_scope": "GLOBAL across all native stages; invalid and duplicate requests consume slots",
                "per_stage_slot_requirement": None, "fixed_reference": "D00", "rounds_per_fit": 100,
                "max_model_calls": self.max_model_calls, "max_stage_history_messages": self.max_stage_messages},
            "tool_transport": {"format_retries": FORMAT_ATTEMPTS - 1, "initial_plus_repair_attempts": FORMAT_ATTEMPTS,
                "all_raw_receipts_count_against_global_call_cap": True,
                "schema_changes": "Planning descriptions plus four unannotated textual report/handoff parameters misclassified as empty objects by native inspect._empty handling; native Python signatures/functions/state unchanged",
                "planning_descriptions": PLANNING_DESCRIPTIONS,
                "untyped_text_schema_compatibility": UNTYPED_TEXT_ARGUMENTS,
                "schema_change_receipts": "Exact before/after live native tool metadata is retained in native_trace.jsonl",
                "native_auto_final_semantics": "Ordinary assistant text is a legal final response, preserved without repair; claimed structured calls still require validation",
                "zero_arity_normalization": "Only an explicitly named available tool with zero model-visible properties and zero required parameters may omit its empty arguments object; trace records normalization, no argument values or native context synthesized",
                "single_call_codec": "Text transport adaptation, not an unchanged native API: canonical tool/arguments, name/arguments, standard function wrapper with optional id/type, or exactly one exposed-tool-name key with object arguments; whole-response JSON fence/tool_call tags accepted; standard name/function arguments may be one JSON-encoded object; raw and normalization_shape retained; no prose/fragment/multi-call extraction or inferred action/argument values",
                "invalid_payload_policy": "Required stages/claimed calls need one complete envelope, exposed tool name and JSON-object arguments; malformed envelopes get bounded same-model format repair; never select fragments or fill argument values",
                "argument_semantics": "Pass missing/extra arguments and all JSON values including null unchanged to original MetaChain.handle_tool_calls -> func(**args); native context injection and genuine native tool errors retained; no adapter JSON-schema argument validation"},
            "native_control": "InnoFlow.forward stage calls, loops, branches and context stores AST-equivalent after allowed task expressions",
            "model_transport": "Original MetaChain.get_chat_completion_async and run_async; only module acompletion transport replaced",
            "runtime_adaptations": [
                "Native agent factories use task system instructions and the shared text model for both cheap/completion roles",
                "Resource capability lists become read_task_artifact; native ML list additionally gets evaluate_design",
                "Native plan_dataset/plan_training/plan_testing, Judge/Code Review handoffs and case completion functions retained",
                "Preparation/search/download stages return fixed task resources without model/browser/file activity",
                "TracedAgentModule delegates to native AgentModule without imposing a per-stage slot count; all native attempts count against the same global six-slot budget",
                "Global budget exhaustion stops further completion/evaluator calls and seals the best valid incumbent (including D00); incomplete later native stages are not fabricated",
                "Native submission stage reports its already evaluated candidate without another fit; every fit remains 100 rounds",
                "BoundedMetaChain delegates to native run_async with finite history-message cap; no interactive cache resume",
                "Safe environment descriptors satisfy factory resource-directory labels only; no environment capability is instantiated",
                "Native idea-loop self-extension is identity-guarded: preserve distinct returned messages, but do not append a history list to itself; no context truncation",
            ],
            "generated_code_executed": False,
        })

    def run(self):
        if self.output.exists() and any(self.output.iterdir()):
            raise ValueError("Use a fresh isolated native output directory; do not overwrite/resume caches")
        self.output.mkdir(parents=True, exist_ok=True)
        with _RUN_LOCK:
            self._trace("controller_start", label=LABEL, commit=PINNED_COMMIT)
            # Validate/import/build before any D00 fit; missing source/deps fail free.
            try:
                with (self.output / "adapter_stdout.log").open("w") as log, redirect_stdout(log), redirect_stderr(log):
                    self._build()
                    baseline = self.broker.initialize()
                    self.initialized = True
                    self._trace("fixed_reference", reply=baseline)
                    core = self.native["core"]
                    with ExitStack() as stack:
                        old = core.acompletion
                        core.acompletion = self._completion
                        stack.callback(setattr, core, "acompletion", old)
                        termination = "native_return"
                        try:
                            asyncio.run(self.flow(instance_path="fixed_task_input", task_level="task2", local_root=str(self.output),
                                workplace_name="public_task", max_iter_times=0, category="registered_fixed_task", references="Fixed public task/menu only."))
                        except NativeBudgetComplete:
                            termination = "global_proposal_budget_exhausted"
                            self._trace("global_budget_exhausted", status=self.broker.status(),
                                next_native_stage_not_fabricated=True)
                status = self.broker.status()
                if status["used_slots"] != 6:
                    raise NativeRunIncomplete("Native controller ended before exactly six proposal slots were consumed")
                self._trace("native_controller_complete", status=status, context_variables=self.last_context,
                            stage_events=self.stage_events, termination_reason=termination,
                            context_snapshot="last fully completed native stage; broker is authoritative for candidate evidence")
                sealed = self.broker.seal_selection()
                self.sealed = True
                result = {"status": "SOURCE_NATIVE_DEVELOPMENT_COMPLETE", "label": LABEL,
                          "selection": sealed, "usage": self.usage(), "native_trace": str(self.trace_path),
                          "termination_reason": termination,
                          "generated_code_executed": False, "heldout_evaluated": False}
                _dump(self.output / "result.json", result)
                return result
            except Exception as exc:
                if not self.sealed:
                    self._trace("controller_failed", exception=type(exc).__name__, message=str(exc), usage=self.usage())
                _dump(self.output / "failure.json", {"status": "BLOCKED" if isinstance(exc, UpstreamUnavailable) else "INCOMPLETE",
                    "exception": type(exc).__name__, "reason": str(exc), "usage": self.usage(),
                    "baseline_initialized": self.initialized, "generated_code_executed": False})
                raise

    def usage(self):
        return {"calls": len(self.receipts), "input_tokens": sum(r["input_tokens"] for r in self.receipts),
                "output_tokens": sum(r["output_tokens"] for r in self.receipts),
                "generation_seconds": sum(r["seconds"] for r in self.receipts)}


def self_test(upstream=DEFAULT_UPSTREAM, *, broker_integration=False):
    """CPU-only fake transport + fake evaluator; real native source/control loop."""
    class FakeBroker:
        def __init__(self):
            self.used = 0
            self.initializations = 0
            self.requests = []
        def status(self):
            return {"task": "synthetic_integration_test", "used_slots": self.used, "remaining_slots": 6-self.used,
                    "available_designs": {f"D{i:02d}": {"test": True} for i in range(1, 12)}, "test_read": False}
        def initialize(self):
            self.initializations += 1
            return self.status()
        def evaluate(self, request, **kwargs):
            assert self.used < 6
            assert set(request) == {"design_id", "hypothesis", "experiment", "expected_effect"}
            assert request["design_id"] == f"D{self.used+1:02d}"
            assert Path(kwargs["native_trace_path"]).is_file() and kwargs["model_receipts"]
            self.requests.append(request)
            self.used += 1
            return {"slot": self.used, "remaining_slots": 6-self.used, "candidate": {"primary": self.used/10, "loss": 1-self.used/10}, "test_read": False}
        def seal_selection(self):
            assert self.used == 6
            return {"test_only": True, "design_id": "D06"}

    class FakeBackend:
        def __init__(self):
            self.counts, self.calls = {}, []
            self.designs = 0
        def __call__(self, messages, *, purpose):
            count = self.counts.get(purpose, 0)
            self.counts[purpose] = count+1
            agent, iteration = purpose.split("/")[1:]
            def tool(name, **arguments):
                return {"tool": name, "arguments": arguments}
            if agent in {"Paper Survey Agent", "Code Survey Agent"}:
                payload = {"final": "Test-only native-stage design reasoning over the fixed menu."}
            elif agent == "Coding Plan Agent":
                payloads = [tool("plan_dataset", dataset_description="fixed task", dataset_location="trusted evaluator", task_definition="test", read_data_step="broker only", data_preprocessing_step="unchanged", data_dataloader_step="ten clients"),
                    tool("plan_training", training_pipeline="trusted fitter", loss_function="unchanged", optimizer="registered", training_configurations="100 rounds", monitor_and_logging="development only"),
                    tool("plan_testing", test_metric="development primary", test_data="no heldout", test_code="trusted evaluator"), tool("case_resolved")]
                payload = payloads[count]
            elif agent == "Machine Learning Agent":
                if iteration == "submit" or count:
                    payload = tool("case_resolved", task_response="Actual synthetic development evidence was inspected; no real training in this smoke test.")
                else:
                    self.designs += 1
                    payload = tool("evaluate_design", design_id=f"D{self.designs:02d}", hypothesis="synthetic hypothesis", experiment="synthetic experiment", expected_effect="synthetic effect")
            elif agent == "Judge Agent":
                # Purpose remains the outer native stage during actual handoffs.
                payloads = [tool("transfer_to_code_review_agent", atomic_idea="fixed menu fidelity"),
                            tool("transfer_to_judge_agent", task_report="native handoff review complete"),
                            tool("case_resolved", fully_correct=True, suggestion={})]
                payload = payloads[count]
            elif agent == "Experiment Analysis Agent":
                payload = tool("case_resolved", analysis_report="Actual synthetic development evidence inspected.", further_plan={"refinement": "Evaluate another registered design."})
            else:
                raise AssertionError("Unexpected source-native stage: " + purpose)
            receipt = {"raw_response": json.dumps(payload), "input_tokens": 11, "output_tokens": 7, "seconds": 0.0,
                       "seed": 42, "model": "FAKE_TEST_ONLY", "call_id": len(self.calls)}
            self.calls.append(receipt)
            return receipt

    with tempfile.TemporaryDirectory(prefix="airesearcher_native_smoke_") as folder:
        broker, backend = FakeBroker(), FakeBackend()
        fitter = None
        if broker_integration:
            from broker import Broker, BrokerConfig, DESIGNS, TASK_DESCRIPTIONS, read, sha
            from test_broker import FakeFitter
            native_path = Path(folder) / "native"
            config = BrokerConfig(task="vcc_corrected", seed=42, harness="native-source-integration-test-not-a-baseline",
                output_dir=str(Path(folder) / "development"), upstream_repo=str(Path(upstream).resolve()),
                upstream_commit=PINNED_COMMIT, native_trace_path=str(native_path / "native_trace.jsonl"), gpu_ids=(0,))
            fitter = FakeFitter([(0.5 + i/100, 1.0 - i/100) for i in range(7)])
            broker = Broker(config, fitter=fitter, test_binding={"test_only": True})
        adapter = AIResearcherAdapter(broker, backend, Path(folder) / "native", upstream=upstream)
        if broker_integration:
            adapter.task_description = TASK_DESCRIPTIONS["vcc_corrected"]
            adapter.registered_designs = DESIGNS
        result = adapter.run()
        expected = [("Paper Survey Agent", None)] + [("Paper Survey Agent", i) for i in range(1, 5)] + [
            ("Paper Survey Agent", "select"), ("Code Survey Agent", None), ("Coding Plan Agent", None),
            ("Machine Learning Agent", None), ("Judge Agent", None), ("Machine Learning Agent", "submit")]
        for i in range(1, 6):
            expected += [("Experiment Analysis Agent", f"refine_{i}"), ("Machine Learning Agent", f"refine_{i}")]
        assert [(e["agent"], e["iteration"]) for e in adapter.stage_events] == expected
        if broker_integration:
            assert len(fitter.calls) == 7
            assert broker.status()["used_slots"] == 6
            seal = read(Path(folder) / "development" / "selection_seal.json")
            assert seal["execution_kind"] == "injected-test-fitter"
            assert seal["native_trace"]["sha256"] == sha(adapter.trace_path)
            assert broker.seal_selection()["seal_sha256"] == result["selection"]["seal_sha256"]
        else:
            assert broker.initializations == 1 and len(broker.requests) == 6
        assert result["usage"]["calls"] == 31  # Sixth proposal reaches the external global budget boundary.
        assert adapter.source_records[-1]["control_signature_preserved"] is True
        alias_edits = [entry for entry in adapter.source_records[-1]["edits"]
                       if entry["kind"] == "native_alias_duplication_correction"]
        assert len(alias_edits) == 1
        corrected = compile(ast.parse(alias_edits[0]["adapted"]), "trusted_alias_regression", "exec")
        original_messages = [{"role": "user", "content": "fixed task"}]
        state = {"messages": original_messages, "survey_messages": original_messages}
        for _ in range(4):
            exec(corrected, {}, state)
            assert len(original_messages) == 1  # Four repeated ideas no longer double the original input.
        separate = [{"role": "assistant", "content": "new unique response"}]
        exec(corrected, {}, {"messages": original_messages, "survey_messages": separate})
        assert original_messages[-1] == separate[0] and len(original_messages) == 2
        assert len(adapter.last_context["experiment_report"]) == 5
        assert "dataset_plan" in adapter.last_context and "training_plan" in adapter.last_context and "testing_plan" in adapter.last_context
        # Transport parser never accepts expression syntax as executable actions.
        for malicious in ("__import__('os').system('echo unsafe')", '{"tool":"x","tool":"y","arguments":{}}'):
            try:
                _json_object(malicious)
            except ValueError:
                pass
            else:
                raise AssertionError("Unsafe or ambiguous syntax accepted")
        return {"status": "NATIVE_SOURCE_BROKER_INTEGRATION_PASS" if broker_integration else "NATIVE_SOURCE_FAKE_BACKEND_SMOKE_PASS", "real_training": False,
                "native_stages": len(adapter.stage_events), "model_calls": len(backend.calls),
                "broker_requests": 6, "native_control_signature_preserved": True,
                "commit": PINNED_COMMIT, "generated_code_executed": False}


def run_airesearcher(broker, text_backend, *, trace_dir, registered_designs, task_description,
                     task_name, seed, upstream_repo=DEFAULT_UPSTREAM):
    """Shared launcher contract; trusted metadata does not add a proposal policy."""
    adapter = AIResearcherAdapter(broker, text_backend, trace_dir, upstream=upstream_repo)
    adapter.task_description = task_description
    adapter.task_name = task_name
    adapter.registered_designs = copy.deepcopy(registered_designs)
    adapter.seed = seed
    return adapter.run()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--upstream", type=Path, default=DEFAULT_UPSTREAM)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--broker-integration", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps(self_test(args.upstream, broker_integration=args.broker_integration), indent=2))
    elif args.preflight:
        native = load_upstream(args.upstream)
        print(json.dumps({"status": "NATIVE_CORE_IMPORT_PASS", "commit": PINNED_COMMIT,
                          "repository": str(native["repo"]), "dependencies": dependency_report()}, indent=2))
    else:
        parser.error("Use --preflight/--self-test, or import AIResearcherAdapter with the trusted broker and shared backend")


if __name__ == "__main__":
    main()
