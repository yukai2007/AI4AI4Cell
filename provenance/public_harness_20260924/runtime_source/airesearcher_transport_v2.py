"""One bounded final transport-compatibility batch, after compact-v1 drains.

Accept standard SINGLE native tool-call list envelopes without changing their
selected function or arguments. No fragment extraction or multi-call choice.
All four short tasks are registered afresh, independently of their v1 scores.
"""
from __future__ import annotations
import argparse
import copy
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import airesearcher_adapter as native
import airesearcher_compact as compact
import run_airesearcher_compact as runner
import supervise as frozen
from broker import dump, read, sha

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
VERSION='airesearcher-task-transport-compact-v2'
BASE_ADAPTER=native.AIResearcherAdapter
TASKS=('ptpc_neural','norman_double_corrected','vcc_corrected','tahoe_drug_corrected')


def decode_transport(raw,schema,tool_choice):
    payload=raw.strip()
    prefix=False
    if payload.startswith('Tool calls:'):
        payload=payload[len('Tool calls:'):].strip();prefix=True
    body,wrappers=native._unwrap_transport(payload)
    try:
        # Strict decoder rejects duplicate keys and non-finite constants.
        obj=json.loads(body,object_pairs_hook=lambda pairs:_unique(pairs),
                       parse_constant=lambda x:(_ for _ in ()).throw(ValueError(x)))
    except ValueError:
        return compact.decode_transport(raw,schema,tool_choice)
    shape=None
    if isinstance(obj,list):
        if not prefix and not any(isinstance(item,dict) and set(item)&{'tool','function','arguments'} for item in obj):
            return compact.decode_transport(raw,schema,tool_choice)
        calls=obj;shape='single_native_call_list'
    elif isinstance(obj,dict) and set(obj)=={'tool_calls'}:
        calls=obj['tool_calls'];shape='single_tool_calls_envelope'
    elif isinstance(obj,dict) and set(obj)=={'tool_choice','tools'}:
        if obj['tool_choice'] not in ('auto','required'):
            raise ValueError('Invalid single-call policy metadata')
        calls=obj['tools'];shape='single_tools_policy_envelope'
    else:
        if prefix: raise ValueError('Native Tool calls prefix requires a single-call list')
        return compact.decode_transport(raw,schema,tool_choice)
    if not isinstance(calls,list) or len(calls)!=1 or not isinstance(calls[0],dict):
        raise ValueError('Exactly one complete native call is required; no multi-call selection')
    content,decoded,note=compact.decode_transport(json.dumps(calls[0],ensure_ascii=False),schema,'required')
    if decoded is None: raise ValueError('Single-call envelope must contain a callable function')
    note=dict(note,native_envelope=shape,native_prefix=prefix,envelope_wrappers=wrappers)
    return content,decoded,note


def _unique(pairs):
    out={}
    for key,value in pairs:
        if key in out: raise ValueError('Duplicate JSON key '+key)
        out[key]=value
    return out


class CompatibleAIResearcher(compact.CompactAIResearcher):
    def _provenance(self):
        super()._provenance()
        path=self.output/'provenance.json';record=read(path)
        record['transport_revision'].update(version=VERSION,source_sha256=sha(__file__),
            additional_single_call_envelopes=['Tool calls: [one function call]','[one function call]',
                '{tool_calls: [one function call]}','{tool_choice: policy, tools: [one function call]}'],
            native_call_values_unchanged=True,multi_call_selection=False)
        dump(path,record)

    def run(self):
        previous=native._decode_transport_response
        native._decode_transport_response=decode_transport
        try:return BASE_ADAPTER.run(self)
        finally:native._decode_transport_response=previous


def controller(broker,backend,*,trace_dir,registered_designs,task_description,task_name,seed,upstream_repo):
    adapter=CompatibleAIResearcher(broker,backend,trace_dir,upstream=upstream_repo)
    adapter.task_description=task_description;adapter.task_name=task_name
    adapter.registered_designs=copy.deepcopy(registered_designs);adapter.seed=seed
    return adapter.run()


def train(args):
    # Reuse the unchanged fresh-fit launcher; bind both original and override
    # sources into its immutable experiment definition.
    original_config=runner.BrokerConfig
    def config(**kw):
        kw['adapter_paths']=tuple(kw['adapter_paths'])+(str(Path(__file__).resolve()),)
        return original_config(**kw)
    runner.BrokerConfig=config;runner.run_airesearcher=controller;runner.VERSION=VERSION
    runner.run(args)


def source_pins():
    out=frozen.pinned_sources()
    for name in ('airesearcher_compact.py','run_airesearcher_compact.py','airesearcher_transport_v2.py'):
        out[str(HERE/name)]=sha(HERE/name)
    return out


def queue(args):
    base=args.base.resolve();base.mkdir(parents=True,exist_ok=True)
    with (base/'.repair.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (base/'queue_manifest.json').exists():raise ValueError('Versioned queue already registered')
        parent=read(args.parent/'queue_manifest.json')
        if parent['max_gpu_hours']>180 or parent['source_sha256']!=frozen.pinned_sources():
            raise ValueError('Original queue/budget changed')
        deadline=parent['created_unix']+parent['max_wall_hours']*3600
        now=time.time()
        manifest=dict(schema='public-harness-compact-repair-queue-v2',created_unix=now,
            jobs=[dict(harness='ai_researcher',task=t,seed=42) for t in TASKS],
            source_sha256=source_pins(),max_gpu_hours=2.,deadline_unix=deadline,
            fitting_gpus=[0],model_gpu=0,shared_gpu=True,max_combined_reserved_gpu_hours=184.,
            wait_for=str(args.wait_for.resolve()),parent_queue=str(args.parent.resolve()),
            protocol_version=VERSION,select_tasks_by_test_score=False,development_retries=False)
        dump(base/'queue_manifest.json',manifest)
        state=dict(status='WAITING_FOR_COMPACT_V1',pid=os.getpid(),started_unix=now,
            updated_unix=now,reserved_gpu_hours=0.,completed=[],failed=[])
        dump(base/'supervisor_status.json',state)
        def interrupted(s,f):raise InterruptedError(f'Version-2 supervisor signal {s}')
        for s in (signal.SIGINT,signal.SIGTERM):signal.signal(s,interrupted)
        def child(cmd,log,gpus):
            if source_pins()!=manifest['source_sha256']:raise ValueError('Versioned runtime changed')
            frozen.run_child(cmd,log,base,state,reserved_gpus=gpus,max_gpu_hours=2.,deadline=deadline)
        try:
            while True:
                prior=read(args.wait_for/'supervisor_status.json')
                if prior['status'] in ('COMPLETE','FINISHED_WITH_INCOMPLETE_RUNS'):
                    if prior.get('child_ownership') and frozen._token_members(prior['child_ownership']):
                        raise RuntimeError('Previous repair still has active owned children')
                    break
                if prior['status']!='RUNNING':raise RuntimeError('Previous repair stopped unexpectedly')
                if time.time()>=deadline:raise TimeoutError('Registered original deadline expired')
                state['updated_unix']=time.time();dump(base/'supervisor_status.json',state)
                time.sleep(60)
            deadline=min(deadline,time.time()+2*3600)
            state['status']='RUNNING'
            for job in manifest['jobs']:
                run=base/'ai_researcher'/job['task']/'seed42'
                state.update(current_job=job,phase='DEVELOPMENT')
                try:
                    child([str(HERE/'.venv/bin/python'),'-B',str(Path(__file__).resolve()),'--train',
                           '--task',job['task'],'--output',str(run)],base/'logs'/f"{job['task']}.log",1)
                except frozen.ChildExitedError:
                    failure=frozen.controller_failure(run,job,read(run/'run_status.json'))
                    if failure is None:raise
                    state['failed'].append(failure);dump(base/'supervisor_status.json',state);continue
                state['phase']='HELDOUT_EVALUATION'
                child([frozen.LDA,'-B',str(HERE/'heldout_public.py'),'--run-dir',str(run/'development'),
                       '--output',str(run/'heldout'),'--device','cpu'],run/'evaluation.log',0)
                state['phase']='INDEPENDENT_RESCORING'
                child([frozen.LDA,'-B',str(HERE/'verify_public.py'),str(run/'heldout')],run/'verification.log',0)
                result=read(run/'heldout/results.json')
                state['completed'].append(dict(job,primary=result['primary'],metric=result['primary_metric'],output=str(run)))
                dump(base/'supervisor_status.json',state)
            state.update(status='FINISHED_WITH_INCOMPLETE_RUNS' if state['failed'] else 'COMPLETE',phase='TERMINAL')
        except BaseException as exc:
            state.update(status='STOPPED_ON_FAILURE',error_type=type(exc).__name__,error=str(exc));raise
        finally:
            state['updated_unix']=time.time();dump(base/'supervisor_status.json',state)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--train',action='store_true');p.add_argument('--task',choices=TASKS)
    p.add_argument('--output',type=Path);p.add_argument('--seed',type=int,default=42)
    p.add_argument('--gpus',default='0');p.add_argument('--model-device',default='cuda:0')
    p.add_argument('--base',type=Path);p.add_argument('--parent',type=Path);p.add_argument('--wait-for',type=Path)
    p.add_argument('--detach',action='store_true');a=p.parse_args()
    if a.train:train(a)
    elif a.detach:
        a.base.mkdir(parents=True,exist_ok=True)
        with (a.base/'supervisor.log').open('ab') as log:
            proc=subprocess.Popen([sys.executable,'-B',__file__,'--base',str(a.base.resolve()),
                '--parent',str(a.parent.resolve()),'--wait-for',str(a.wait_for.resolve())],
                stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
        print(json.dumps(dict(pid=proc.pid,base=str(a.base.resolve()))))
    else:queue(a)
