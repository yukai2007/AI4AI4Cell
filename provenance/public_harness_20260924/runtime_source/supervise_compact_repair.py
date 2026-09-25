"""Bounded seed-42 transport repair queue on shared GPU 0; no v6 mutation.

Four short biological endpoints run first. The existing seven-GPU DTI fitter
and its supervisor continue unchanged. The extra conservative two GPU-hour
allowance plus the existing 180-hour cap stays below 8 GPUs x one day.
"""
from __future__ import annotations
import argparse
import fcntl
import json
from pathlib import Path
import signal
import subprocess
import sys
import time

from broker import dump, read, sha
import supervise as frozen

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TASKS = ('ptpc_neural', 'norman_double_corrected', 'vcc_corrected', 'tahoe_drug_corrected')


def source_pins():
    pins = frozen.pinned_sources()
    pins.update({str(HERE/name):sha(HERE/name) for name in (
        'airesearcher_compact.py', 'run_airesearcher_compact.py', 'supervise_compact_repair.py')})
    return pins


def run(base, parent):
    base, parent = base.resolve(), parent.resolve()
    base.mkdir(parents=True, exist_ok=True)
    with (base/'.repair.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # This small queue does not resume an interrupted fit or launch retries.
        if (base/'queue_manifest.json').exists():
            raise ValueError('Repair queue already registered; inspect it rather than duplicating training')
        original = read(parent/'queue_manifest.json')
        if original['max_gpu_hours'] > 180 or original['source_sha256'] != frozen.pinned_sources():
            raise ValueError('Original queue/budget differs from the checked shared-GPU experiment')
        now = time.time()
        deadline = min(now+2*3600, original['created_unix']+original['max_wall_hours']*3600)
        if deadline <= now: raise TimeoutError('Original wall-time window has expired')
        manifest = dict(schema='public-harness-compact-repair-queue-v1', created_unix=now,
            jobs=[dict(harness='ai_researcher',task=t,seed=42) for t in TASKS],
            source_sha256=source_pins(), parent_queue=str(parent),
            parent_manifest_sha256=sha(parent/'queue_manifest.json'),
            max_gpu_hours=2., deadline_unix=deadline, max_combined_reserved_gpu_hours=182.,
            model_gpu=0, fitting_gpus=[0], shared_gpu=True,
            prior_failures_replaced=False, development_retries=False,
            primary_training_queue_mutations=False,
            purpose='Fresh complete six-slot runs after explicit task-prompt/codec repair; score all completed runs regardless of outcome.')
        dump(base/'queue_manifest.json',manifest)
        state = dict(schema='public-harness-compact-repair-status-v1',status='RUNNING',
            pid=__import__('os').getpid(),started_unix=now,updated_unix=now,
            reserved_gpu_hours=0.,completed=[],failed=[])
        def interrupted(signum, frame): raise InterruptedError(f'Repair queue signal {signum}')
        old = {s:signal.signal(s,interrupted) for s in (signal.SIGTERM,signal.SIGINT)}
        def child(command, log, gpu_count):
            if source_pins()!=manifest['source_sha256']: raise ValueError('Registered repair sources changed')
            frozen.run_child(command,log,base,state,reserved_gpus=gpu_count,
                             max_gpu_hours=2.,deadline=deadline)
        try:
            for job in manifest['jobs']:
                run_dir=base/'ai_researcher'/job['task']/'seed42'
                state.update(current_job=job,phase='DEVELOPMENT')
                try:
                    child([str(HERE/'.venv/bin/python'),'-B',str(HERE/'run_airesearcher_compact.py'),
                           '--task',job['task'],'--seed','42','--gpus','0','--model-device','cuda:0',
                           '--output',str(run_dir)],base/'logs'/f"{job['task']}.log",1)
                except frozen.ChildExitedError:
                    failure=frozen.controller_failure(run_dir,job,read(run_dir/'run_status.json'))
                    if failure is None: raise
                    state['failed'].append(failure)
                    dump(base/'supervisor_status.json',state)
                    continue
                if read(run_dir/'run_status.json')['status']!='DEVELOPMENT_COMPLETE':
                    raise ValueError('Candidate selection not completed')
                state['phase']='HELDOUT_EVALUATION'
                child([frozen.LDA,'-B',str(HERE/'heldout_public.py'),'--run-dir',str(run_dir/'development'),
                       '--output',str(run_dir/'heldout'),'--device','cpu'],run_dir/'evaluation.log',0)
                state['phase']='INDEPENDENT_RESCORING'
                child([frozen.LDA,'-B',str(HERE/'verify_public.py'),str(run_dir/'heldout')],run_dir/'verification.log',0)
                result=read(run_dir/'heldout/results.json')
                state['completed'].append(dict(job,primary=result['primary'],metric=result['primary_metric'],output=str(run_dir)))
                dump(base/'supervisor_status.json',state)
                # Separate supplementary output, not an automatic replacement
                # of v6 failures or of either main-table source.
                state['phase']='VERIFIED_REPAIR_TABLE'
                child([frozen.LDA,'-B',str(ROOT/'paper/tools/publish_public_harness.py'),
                       '--base',str(base),'--output-dir',str(ROOT/'paper/tables/public_harness_compact_repair')],
                       run_dir/'publication.log',0)
            state.update(status='COMPLETE' if not state['failed'] else 'FINISHED_WITH_INCOMPLETE_RUNS',
                         phase='TERMINAL',completed_unix=time.time())
        except BaseException as exc:
            state.update(status='STOPPED_ON_FAILURE',error_type=type(exc).__name__,error=str(exc))
            raise
        finally:
            state['updated_unix']=time.time()
            dump(base/'supervisor_status.json',state)
            for s,h in old.items(): signal.signal(s,h)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',type=Path,required=True)
    parser.add_argument('--parent',type=Path,required=True)
    parser.add_argument('--detach',action='store_true')
    args=parser.parse_args()
    if args.detach:
        args.base.mkdir(parents=True,exist_ok=True)
        with (args.base/'supervisor.log').open('ab') as log:
            p=subprocess.Popen([sys.executable,'-B',__file__,'--base',str(args.base.resolve()),
                                '--parent',str(args.parent.resolve())],stdout=log,stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL,start_new_session=True)
        print(json.dumps(dict(pid=p.pid,base=str(args.base.resolve()))))
    else: run(args.base,args.parent)
