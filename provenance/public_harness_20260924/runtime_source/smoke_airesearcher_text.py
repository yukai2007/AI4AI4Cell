"""One real-Qwen/native-flow smoke with an injected fake fitter: NOT a benchmark."""
import argparse
import gc
from pathlib import Path
import time

from airesearcher_adapter import DEFAULT_UPSTREAM, PINNED_COMMIT, run_airesearcher
from broker import Broker, BrokerConfig, DESIGNS, TASK_DESCRIPTIONS, dump
from qwen_backend import LocalQwenBackend
from test_broker import FakeFitter


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--model-device', default='cuda:7')
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    started = time.time()
    native = output/'native_controller'
    task = 'ptpc_neural'
    config = BrokerConfig(task=task, seed=42, harness='REAL_LLM_FAKE_FITTER_TRANSPORT_TEST_ONLY',
        output_dir=str(output/'development'), upstream_repo=str(DEFAULT_UPSTREAM),
        upstream_commit=PINNED_COMMIT, native_trace_path=str(native/'native_trace.jsonl'), gpu_ids=(7,))
    fitter = FakeFitter([(0.5+i/100, 1.-i/100) for i in range(7)])
    broker = Broker(config, fitter=fitter, test_binding={'test_only': True, 'real_llm': True, 'real_training': False})
    backend = None
    dump(output/'smoke_status.json', dict(status='RUNNING', real_llm=True, real_training=False,
         publishable=False, started_unix=started, model_device=args.model_device))
    try:
        import torch
        free, total = torch.cuda.mem_get_info(torch.device(args.model_device))
        if free < 20 * 1024**3:
            raise RuntimeError('Less than 20 GiB free; do not pressure the ongoing production fitting')
        backend = LocalQwenBackend(output/'model_calls', seed=42, device=args.model_device)
        result = run_airesearcher(broker, backend, trace_dir=native, registered_designs=DESIGNS,
            task_description=TASK_DESCRIPTIONS[task], task_name=task, seed=42, upstream_repo=DEFAULT_UPSTREAM)
        dump(output/'smoke_status.json', dict(status='REAL_LLM_NATIVE_FLOW_FAKE_FITTER_PASS',
            real_llm=True, real_training=False, publishable=False, started_unix=started,
            completed_unix=time.time(), wall_seconds=time.time()-started,
            reserved_model_gpu_hours=(time.time()-started)/3600,
            fake_fitter_calls=len(fitter.calls), proposal_slots=broker.status()['used_slots'],
            usage=backend.usage(), native_status=result['status'], model_device=args.model_device))
    except BaseException as exc:
        dump(output/'smoke_status.json', dict(status='REAL_LLM_FAKE_FITTER_SMOKE_FAILED',
            real_llm=True, real_training=False, publishable=False, started_unix=started,
            completed_unix=time.time(), wall_seconds=time.time()-started,
            reserved_model_gpu_hours=(time.time()-started)/3600,
            error_type=type(exc).__name__, error=str(exc), fake_fitter_calls=len(fitter.calls),
            usage=backend.usage() if backend is not None else None, model_device=args.model_device))
        raise
    finally:
        broker.close()
        if backend is not None:
            del backend
            gc.collect()
            torch.cuda.empty_cache()


if __name__ == '__main__':
    main()
