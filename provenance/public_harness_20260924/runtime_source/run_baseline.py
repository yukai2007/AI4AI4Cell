"""Run one genuine task-adapted public controller against the fixed main protocol.

No external API is used. Native LLM calls use local Qwen; all fits are fresh.
Development selection and held-out scoring run in separate processes.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict
import gc
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

from broker import Broker, BrokerConfig, DESIGNS, TASK_DESCRIPTIONS, dump, sha
from qwen_backend import LocalQwenBackend

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PINS = {
    'ai_scientist_v2': ('AI-Scientist-v2', '96bd51617cfdbb494a9fc283af00fe090edfae48', 'aiscientist_adapter.py'),
    'ai_researcher': ('AI-Researcher', 'f9a6f8480860c193afff600eeffe3defcee8a978', 'airesearcher_adapter.py'),
}


def run(args):
    name, commit, adapter_name = PINS[args.harness]
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    upstream = ROOT / 'references/public_harness_20260924' / name
    native = output / 'native_controller'
    config = BrokerConfig(task=args.task, seed=args.seed, harness=args.harness,
        output_dir=str(output/'development'), upstream_repo=str(upstream), upstream_commit=commit,
        native_trace_path=str(native/'native_trace.jsonl'),
        gpu_ids=tuple(int(g) for g in args.gpus.split(',')),
        adapter_paths=tuple(str(HERE/p) for p in [adapter_name, 'qwen_backend.py', 'run_baseline.py']))
    dump(output/'config.json', asdict(config))
    start = time.time()
    dump(output/'run_status.json', dict(status='STARTING', task=args.task, seed=args.seed,
         harness=args.harness, pid=os.getpid(), started_unix=start, fresh_training=True,
         controller_backend='local Qwen2.5-7B-Instruct', test_read=False))
    broker = Broker(config)
    backend = None
    try:
        # Upstream provenance/import validation precedes any paid fitting.
        if args.harness == 'ai_scientist_v2':
            from aiscientist_adapter import load_upstream, run_aiscientist
            load_upstream(upstream)
            controller = run_aiscientist
        else:
            from airesearcher_adapter import run_airesearcher
            controller = run_airesearcher
        backend = LocalQwenBackend(output/'model_calls', seed=args.seed, device=args.model_device)
        dump(output/'run_status.json', dict(status='NATIVE_CONTROLLER_RUNNING', task=args.task,
             seed=args.seed, harness=args.harness, pid=os.getpid(), started_unix=start, test_read=False))
        result = controller(broker, backend, trace_dir=native, registered_designs=DESIGNS,
            task_description=TASK_DESCRIPTIONS[args.task], task_name=args.task,
            seed=args.seed, upstream_repo=upstream)
        dump(output/'controller_result.json', result)
        dump(output/'run_status.json', dict(status='DEVELOPMENT_COMPLETE', task=args.task,
             seed=args.seed, harness=args.harness, pid=os.getpid(), started_unix=start,
             completed_unix=time.time(), wall_seconds=time.time()-start, usage=backend.usage(),
             selection_seal_sha256=sha(output/'development/selection_seal.json'), test_read=False))
        print(json.dumps(dict(status='DEVELOPMENT_COMPLETE', task=args.task, harness=args.harness,
                              seed=args.seed, output=str(output), usage=backend.usage())), flush=True)
    except BaseException as exc:
        dump(output/'run_status.json', dict(status='FAILED', task=args.task, seed=args.seed,
             harness=args.harness, pid=os.getpid(), started_unix=start, completed_unix=time.time(),
             error_type=type(exc).__name__, error=str(exc), traceback=traceback.format_exc(),
             usage=backend.usage() if backend is not None else None, test_read=False))
        raise
    finally:
        broker.close()
        if backend is not None:
            import torch
            del backend
            gc.collect()
            torch.cuda.empty_cache()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--harness', choices=PINS, required=True)
    parser.add_argument('--task', choices=TASK_DESCRIPTIONS, required=True)
    parser.add_argument('--seed', type=int, choices=[42, 43, 44], default=42)
    parser.add_argument('--gpus', default='1,2,3,4,5,6,7')
    parser.add_argument('--model-device', default='cuda:0')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args)


if __name__ == '__main__':
    main()
