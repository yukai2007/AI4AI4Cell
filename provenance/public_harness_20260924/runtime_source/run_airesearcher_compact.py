"""Fresh, explicitly versioned AI-Researcher transport-repair experiment."""
from __future__ import annotations
import argparse
from dataclasses import asdict
import gc
import os
from pathlib import Path
import time
import traceback

from broker import Broker, BrokerConfig, DESIGNS, TASK_DESCRIPTIONS, dump, sha
from qwen_backend import LocalQwenBackend
from airesearcher_compact import run_airesearcher, VERSION

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
COMMIT = 'f9a6f8480860c193afff600eeffe3defcee8a978'


def run(args):
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    upstream = ROOT / 'references/public_harness_20260924/AI-Researcher'
    native = output / 'native_controller'
    config = BrokerConfig(task=args.task, seed=args.seed, harness='ai_researcher',
        output_dir=str(output/'development'), upstream_repo=str(upstream), upstream_commit=COMMIT,
        native_trace_path=str(native/'native_trace.jsonl'),
        gpu_ids=tuple(int(g) for g in args.gpus.split(',')),
        adapter_paths=tuple(str(HERE/p) for p in (
            'airesearcher_adapter.py', 'airesearcher_compact.py', 'qwen_backend.py',
            'run_airesearcher_compact.py')))
    dump(output/'config.json', asdict(config))
    start = time.time()
    identity = dict(task=args.task, seed=args.seed, harness='ai_researcher',
        pid=os.getpid(), started_unix=start, fresh_training=True,
        controller_backend='local Qwen2.5-7B-Instruct', transport_revision=VERSION,
        test_read=False, replaces_frozen_run=False)
    dump(output/'run_status.json', dict(identity, status='STARTING'))
    broker, backend = Broker(config), None
    try:
        backend = LocalQwenBackend(output/'model_calls', seed=args.seed, device=args.model_device)
        dump(output/'run_status.json', dict(identity, status='NATIVE_CONTROLLER_RUNNING'))
        result = run_airesearcher(broker, backend, trace_dir=native, registered_designs=DESIGNS,
            task_description=TASK_DESCRIPTIONS[args.task], task_name=args.task,
            seed=args.seed, upstream_repo=upstream)
        dump(output/'controller_result.json', result)
        dump(output/'run_status.json', dict(identity, status='DEVELOPMENT_COMPLETE',
            completed_unix=time.time(), wall_seconds=time.time()-start, usage=backend.usage(),
            selection_seal_sha256=sha(output/'development/selection_seal.json')))
    except BaseException as exc:
        dump(output/'run_status.json', dict(identity, status='FAILED', completed_unix=time.time(),
            error_type=type(exc).__name__, error=str(exc), traceback=traceback.format_exc(),
            usage=backend.usage() if backend is not None else None))
        raise
    finally:
        broker.close()
        if backend is not None:
            import torch
            del backend
            gc.collect()
            torch.cuda.empty_cache()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task', choices=TASK_DESCRIPTIONS, required=True)
    parser.add_argument('--seed', type=int, choices=[42, 43, 44], default=42)
    parser.add_argument('--gpus', default='0')
    parser.add_argument('--model-device', default='cuda:0')
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args())
