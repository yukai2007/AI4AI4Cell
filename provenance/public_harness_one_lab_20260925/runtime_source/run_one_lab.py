"""Run a task-adapted public controller with access to lab 0 only.

Both controllers retain their pinned upstream workflow, local
Qwen2.5-7B-Instruct backend, twelve-design menu, six-candidate cap and
100-round candidate schedule.  Prompt text is changed only where the previous
transport explicitly said ten clients, so the controller is accurately told
that the trusted fitter uses lab 0.
"""
from __future__ import annotations

import argparse
import copy
from pathlib import Path
import sys
import types

HERE = Path(__file__).resolve().parent
ORIGINAL = HERE.parent / "public_harness_20260924"
ROOT = HERE.parents[1]
if str(ORIGINAL) not in sys.path:
    sys.path.insert(1, str(ORIGINAL))

import broker


def _replace_code(code, replacements):
    constants = []
    for value in code.co_consts:
        if isinstance(value, types.CodeType):
            value = _replace_code(value, replacements)
        elif isinstance(value, str):
            for old, new in replacements:
                value = value.replace(old, new)
        constants.append(value)
    return code.replace(co_consts=tuple(constants))


def _patched_function(function, replacements):
    patched = types.FunctionType(
        _replace_code(function.__code__, replacements), function.__globals__,
        function.__name__, function.__defaults__, function.__closure__)
    patched.__kwdefaults__ = copy.deepcopy(function.__kwdefaults__)
    patched.__annotations__ = dict(function.__annotations__)
    patched.__dict__.update(function.__dict__)
    patched.__doc__ = function.__doc__
    patched.__module__ = function.__module__
    patched.__qualname__ = function.__qualname__
    return patched


def _patch_ai_scientist():
    import aiscientist_adapter as native
    replacements = (
        ("all 10 clients", "lab 0 only"),
        ("10-client", "single-client lab-0"),
        ("10 clients", "lab 0 only"),
    )
    native.DESIGN_IMPLEMENTATION_GUIDELINE[:] = [
        value.replace("10-client", "single-client lab-0")
        for value in native.DESIGN_IMPLEMENTATION_GUIDELINE]
    native.adapt_native_prompt = _patched_function(native.adapt_native_prompt, replacements)
    native._run_locked = _patched_function(native._run_locked, replacements)
    return native


def _patch_ai_researcher():
    import airesearcher_adapter as native
    replacements = (
        ("fixed ten-client registered task", "fixed lab-0 registered task"),
        ("10 original clients", "one original client (lab 0)"),
        ("trusted ten-client", "trusted single-client lab-0"),
        ("Preserve ten clients", "Preserve lab 0 only"),
        ("ten clients", "lab 0 only"),
        ("ten-client", "single-client lab-0"),
    )
    native.PLANNING_DESCRIPTIONS = {
        key: next((value.replace(old, new) for old, new in replacements if old in value), value)
        for key, value in native.PLANNING_DESCRIPTIONS.items()
    }
    native.AIResearcherAdapter._public_task = _patched_function(
        native.AIResearcherAdapter._public_task, replacements)
    native.AIResearcherAdapter._build = _patched_function(
        native.AIResearcherAdapter._build, replacements)
    return native


def _tracked_config(original):
    def config(**kwargs):
        kwargs["adapter_paths"] = tuple(kwargs["adapter_paths"]) + (
            str(Path(broker.__file__).resolve()), str(Path(__file__).resolve()))
        return original(**kwargs)
    return config


def run(args):
    if broker.CLIENTS != [0]:
        raise RuntimeError("Single-laboratory broker did not bind exactly lab 0")
    if args.harness == "ai_scientist_v2":
        _patch_ai_scientist()
        import run_baseline as runner
        runner.BrokerConfig = _tracked_config(runner.BrokerConfig)
        runner.run(args)
        return

    _patch_ai_researcher()
    import run_airesearcher_compact as runner
    runner.BrokerConfig = _tracked_config(runner.BrokerConfig)
    import airesearcher_budget_cap_v4 as final_adapter
    final_adapter.train(args)


def check():
    ais = _patch_ai_scientist()
    aire = _patch_ai_researcher()
    ais_text = " ".join(ais.DESIGN_IMPLEMENTATION_GUIDELINE)
    aire_text = " ".join(aire.PLANNING_DESCRIPTIONS.values())
    probe = object.__new__(aire.AIResearcherAdapter)
    probe.broker = type("ProbeBroker", (), {"status": lambda self: {
        "task": "probe", "available_designs": {}, "used_slots": 0}})()
    probe.task_description = "probe"
    probe.registered_designs = {}
    probe.evidence = []
    public = aire.AIResearcherAdapter._public_task(probe)
    assert broker.CLIENTS == [0]
    assert "10-client" not in ais_text and "all 10 clients" not in ais_text
    assert "ten clients" not in aire_text and "10 original clients" not in public["protocol"]
    assert "lab-0" in ais_text and "lab 0" in aire_text and "lab 0" in public["protocol"]
    print({"status": "PASS", "clients": broker.CLIENTS,
           "protocol": broker.SINGLE_LAB_PROTOCOL,
           "research_model": "Qwen2.5-7B-Instruct"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--harness", choices=("ai_scientist_v2", "ai_researcher"))
    parser.add_argument("--task", choices=tuple(broker.TASK_DESCRIPTIONS))
    parser.add_argument("--seed", type=int, choices=(42,), default=42)
    parser.add_argument("--gpus", default="0")
    parser.add_argument("--model-device", default="cuda:0")
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    if arguments.check_only:
        check()
    else:
        if not arguments.harness or not arguments.task or arguments.output is None:
            parser.error("--harness, --task and --output are required for a run")
        run(arguments)
