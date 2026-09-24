"""Bounded, restart-aware supervisor for the public-harness comparison.

Only owned child process groups are stopped. Failed development runs are kept;
an immutable opt-in may skip narrowly identified, unscorable controller failures.
Scientific duplicates/failures are handled by the controller, never retried by
the supervisor. This tool never pushes a manuscript.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid

from broker import HERE, ROOT, dump, read, sha

HARNESS_ORDER = ('ai_scientist_v2', 'ai_researcher')
TASK_ORDER = ('ptpc_neural', 'norman_double_corrected', 'vcc_corrected',
              'tahoe_drug_corrected', 'native_tapb')
LDA = '/opt/conda/envs/LDA/bin/python'
OWNER_ENV = 'BIOCOLOOP_PUBLIC_HARNESS_OWNER'


class OwnershipUnverified(RuntimeError):
    """Never signal a PID/group whose ownership cannot be established."""


class ChildExitedError(RuntimeError):
    """An ordinary nonzero child exit, distinct from cleanup/budget failures."""

    def __init__(self, exit_code, log_path):
        self.exit_code = exit_code
        super().__init__(f'Child exited {exit_code}: {log_path}')


CONTROLLER_FAILURE_PREFIXES = (
    'Tool response remained invalid after',
    'Native required-tool stage ended',
    'Native stage exhausted with a failed completion/tool receipt',
    'Native context exceeds declared token limit; no silent truncation.',
)


def _assert_launcher_exited(run, status):
    # FAILED/COMPLETE is written before launcher cleanup. Never treat that file
    # alone as proof that a launcher with this exact output has finished.
    identity = _process_identity(status.get('pid', -1))
    if identity is None or identity['state'] == 'Z':
        return
    try:
        command = Path(f'/proc/{identity["pid"]}/cmdline').read_bytes().split(b'\0')
    except (FileNotFoundError, ProcessLookupError):
        return
    except PermissionError as exc:
        raise OwnershipUnverified('Cannot confirm prequeue launcher has exited') from exc
    command = [part.decode(errors='replace') for part in command if part]
    if (str(HERE / 'run_baseline.py') in command and '--output' in command
            and command.index('--output') + 1 < len(command)
            and Path(command[command.index('--output') + 1]).resolve() == run.resolve()):
        raise ValueError(f'Active prequeue runner is still cleaning up: {run}')


def controller_failure(run, job, status):
    """Classify only production, identity-bound AIRE declared native failures.

    This does not authorize continuing: the immutable queue option and, for a
    newly launched child, successful cleanup/final accounting are also required.
    No score, selection, retry, or held-out result is manufactured.
    """
    if any(status.get(key) != value for key, value in job.items()):
        raise ValueError(f'Run identity differs from registered queue job: {run}')
    definition_path = run / 'development/definition.json'
    definition = read(definition_path)
    if definition.get('execution_kind') != 'fresh-canonical-v3':
        raise ValueError(f'Nonproduction execution cannot be classified: {run}')
    if any(definition.get('config', {}).get(key) != value for key, value in job.items()):
        raise ValueError(f'Production definition identity differs from queue job: {run}')
    error = status.get('error')
    # The native agent wraps some tool exceptions with exactly one "Error: ".
    # Do not use substring matching: infrastructure text must not qualify.
    native_error = error.removeprefix('Error: ') if isinstance(error, str) else None
    if not (job['harness'] == 'ai_researcher' and status.get('status') == 'FAILED'
            and status.get('error_type') == 'NativeRunIncomplete'
            and isinstance(native_error, str) and native_error.startswith(CONTROLLER_FAILURE_PREFIXES)):
        return None
    _assert_launcher_exited(run, status)
    start, finish = status.get('started_unix'), status.get('completed_unix')
    usage = status.get('usage')
    if (any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
            for value in (start, finish)) or not 0 <= start <= finish <= time.time() + 1):
        raise ValueError(f'Invalid failed-run wall-time receipt: {run}')
    if (not isinstance(usage, dict) or not {'calls', 'input_tokens', 'output_tokens', 'generation_seconds', 'model'}.issubset(usage)
            or any(isinstance(usage[key], bool) or not isinstance(usage[key], (int, float))
                   or not math.isfinite(usage[key]) or usage[key] < 0
                   for key in ('calls', 'input_tokens', 'output_tokens', 'generation_seconds'))):
        raise ValueError(f'Failed run has no complete backend usage receipt: {run}')
    if (status.get('test_read') is not False or (run / 'heldout').exists()
            or (run / 'development/selection_seal.json').exists()):
        raise ValueError(f'Unscorable controller failure has unexpected held-out access/artifacts: {run}')
    return dict(job=dict(job), output=str(run), status='UNSCORABLE_CONTROLLER_FAILURE',
                error_type=status['error_type'], error=error, test_read=False,
                evidence_sha256={str(path): sha(path) for path in
                                 (run / 'run_status.json', definition_path)})


def failure_accounting(run, manifest, previous):
    """Do not skip externally added failed runs whose compute was never charged."""
    for receipt in previous.get('failed', []):
        if receipt['output'] == str(run):
            return receipt['accounting']
    for receipt in manifest.get('adopted_prequeue_runs', []):
        if receipt['output'] == str(run):
            return dict(kind='immutable_prequeue_receipt', reserved_gpu_hours=receipt['reserved_gpu_hours'])
    command = previous.get('child_command', [])
    if (previous.get('child_state') == 'FINISHED' and '--output' in command
            and command.index('--output') + 1 < len(command)
            and Path(command[command.index('--output') + 1]).resolve() == run.resolve()
            and previous.get('child_exit_code', 0) is not None
            and previous.get('child_exit_code', 0) > 0
            and previous.get('child_finished_unix', -1) >= previous.get('child_started_unix', 0)
            and previous.get('child_last_accounted_unix', -1) >= previous.get('child_finished_unix', 0)):
        if _token_members(previous['child_ownership']):
            raise OwnershipUnverified('Accounted failed child still has live owned descendants')
        return dict(kind='finished_owned_child',
                    child_started_unix=previous['child_started_unix'],
                    child_finished_unix=previous['child_finished_unix'],
                    cumulative_reserved_gpu_hours=previous['reserved_gpu_hours'])
    raise ValueError(f'Failed run lacks adopted or finished-child compute accounting: {run}')


def jobs():
    # Breadth first: all task/harness seed-42 pilots, then seeds 43 and 44.
    # The same 30 jobs and three-seed scientific protocol are retained.
    return [dict(harness=h, task=t, seed=s) for s in (42, 43, 44)
            for t in TASK_ORDER for h in HARNESS_ORDER]


def job_directory(base, job):
    return base / job['harness'] / job['task'] / f"seed{job['seed']}"


def prequeue_accounting(base, matrix):
    """Adopt completed production development runs once; never adopt live work.

    The registered allocation is always eight reserved GPUs, including model
    loading and development idle time. These receipts are accounting evidence,
    not a substitute for the independent scientific verifier.
    """
    receipts = []
    now = time.time()
    expected = {job_directory(base, job) for job in matrix}
    if any(path.parent not in expected for path in base.glob('*/*/seed*/run_status.json')):
        raise ValueError('Unregistered prequeue run requires explicit accounting before queue creation')
    for job in matrix:
        run = job_directory(base, job)
        if not run.exists():
            continue
        status_path = run / 'run_status.json'
        if not status_path.is_file():
            raise ValueError(f'Existing prequeue directory has no accounting status: {run}')
        status = read(status_path)
        if status.get('status') not in {'DEVELOPMENT_COMPLETE', 'FAILED'} or 'completed_unix' not in status:
            raise ValueError(f'Active or unfinished prequeue runner cannot be adopted: {run}')
        if any(status.get(key) != value for key, value in job.items()):
            raise ValueError(f'Prequeue run identity differs from registered matrix: {run}')
        # Completion is written before model/broker cleanup. Do not begin a
        # competing queue until that launcher has actually exited. PID reuse is
        # disambiguated with its exact launcher/output command, never signaled.
        _assert_launcher_exited(run, status)
        start, finish = status.get('started_unix'), status.get('completed_unix')
        if (any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
                for value in (start, finish)) or not 0 <= start <= finish <= now + 1):
            raise ValueError(f'Invalid prequeue wall-time receipt: {run}')
        usage = status.get('usage')
        if (not isinstance(usage, dict) or not {'calls', 'input_tokens', 'output_tokens', 'generation_seconds', 'model'}.issubset(usage)
                or any(isinstance(usage[key], bool) or not isinstance(usage[key], (int, float))
                       or not math.isfinite(usage[key]) or usage[key] < 0
                       for key in ('calls', 'input_tokens', 'output_tokens', 'generation_seconds'))):
            raise ValueError(f'Prequeue run has no complete real-backend usage receipt: {run}')
        definition_path = run / 'development/definition.json'
        definition = read(definition_path)
        if definition.get('execution_kind') != 'fresh-canonical-v3':
            raise ValueError(f'Test/cache execution cannot be adopted as production work: {run}')
        if any(definition.get('config', {}).get(key) != value for key, value in job.items()):
            raise ValueError(f'Prequeue production definition identity mismatch: {run}')
        receipts.append(dict(**job, output=str(run), started_unix=start, completed_unix=finish,
            reserved_gpus=8, reserved_gpu_hours=8 * (finish-start) / 3600, usage=usage,
            evidence_sha256={str(path): sha(path) for path in (status_path, definition_path)}))
    return receipts


def pinned_sources():
    names = ('broker.py', 'runtime_worker.py', 'qwen_backend.py', 'run_baseline.py',
             'aiscientist_adapter.py', 'airesearcher_adapter.py', 'heldout_public.py',
             'verify_public.py', 'supervise.py')
    sources = {str(HERE / name): sha(HERE / name) for name in names}
    publisher = ROOT / 'paper/tools/publish_public_harness.py'
    sources[str(publisher)] = sha(publisher)
    return sources


def _boot_id():
    return Path('/proc/sys/kernel/random/boot_id').read_text().strip()


def _process_identity(pid):
    try:
        fields = Path(f'/proc/{pid}/stat').read_text().rsplit(') ', 1)[1].split()
        return dict(pid=int(pid), state=fields[0], ppid=int(fields[1]), pgid=int(fields[2]),
                    sid=int(fields[3]), start_ticks=int(fields[19]))
    except (FileNotFoundError, ProcessLookupError, PermissionError, IndexError, ValueError):
        return None


def _token_members(ownership):
    """Return only live processes carrying this launch's inherited nonce.

    Environment contents are never logged or returned. The nonce is an ownership
    marker, not a credential. Boot ID and process start ticks are also retained
    to disambiguate crash recovery from PID reuse. Zombies consume no GPU time.
    """
    if ownership.get('boot_id') != _boot_id():
        return []
    token = ownership.get('token')
    if not isinstance(token, str) or not token:
        raise OwnershipUnverified('No persisted child ownership token')
    marker = (OWNER_ENV + '=' + token).encode()
    members = []
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():
            continue
        identity = _process_identity(entry.name)
        if identity is None or identity['state'] == 'Z':
            continue
        try:
            owned = marker in (entry / 'environ').read_bytes().split(b'\0')
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
        if owned:
            members.append(identity)
    return members


def _signal_owned_groups(ownership, signum):
    # Re-scan immediately before every signal; never rely on a saved PID alone.
    groups = {(item['pgid'], item['sid']) for item in _token_members(ownership)}
    for pgid, sid in groups:
        if pgid == os.getpgrp() or sid == os.getsid(0):
            raise OwnershipUnverified('Refusing to signal supervisor/shared session')
        verified = [item for item in _token_members(ownership) if item['pgid'] == pgid and item['sid'] == sid]
        if not verified:
            continue
        try:
            os.killpg(pgid, signum)
        except ProcessLookupError:
            pass


def _stop_owned_descendants(ownership, process=None, *, grace_seconds=15.):
    # A reaped leader is not evidence that its fitter descendants have stopped.
    if process is not None:
        process.poll()
    if not _token_members(ownership):
        if process is not None and process.poll() is None:
            raise OwnershipUnverified('Live child does not carry its registered ownership token')
        return
    _signal_owned_groups(ownership, signal.SIGTERM)
    deadline = time.monotonic() + grace_seconds
    while _token_members(ownership) and time.monotonic() < deadline:
        if process is not None:
            process.poll()
        time.sleep(.05)
    if _token_members(ownership):
        _signal_owned_groups(ownership, signal.SIGKILL)
        deadline = time.monotonic() + grace_seconds
        while _token_members(ownership) and time.monotonic() < deadline:
            if process is not None:
                process.poll()
            time.sleep(.05)
    if _token_members(ownership):
        raise OwnershipUnverified('Owned descendants remain alive after bounded termination')
    if process is not None:
        process.wait(timeout=grace_seconds)


def stop_owned_group(process, ownership=None, *, grace_seconds=15.):
    ownership = ownership or getattr(process, '_public_harness_ownership', None)
    if ownership is None:
        raise OwnershipUnverified('Directly owned child metadata is required')
    _stop_owned_descendants(ownership, process, grace_seconds=grace_seconds)


def reconcile_previous_child(base, previous, *, grace_seconds=15.):
    """Conservatively charge gaps and clean only nonce-verified orphan children.

    Cleanup never retries development. A recovered live child stops this resume
    for investigation. Lost accounting is not reset to zero; unknown legacy
    ownership fails closed without signaling arbitrary processes.
    """
    started = previous.get('child_started_unix')
    if started is None or previous.get('child_finished_unix', 0.) >= started:
        return previous
    recovered = dict(previous)
    last = max(started, previous.get('child_last_accounted_unix', previous.get('updated_unix', started)))
    now = time.time()
    recovered['reserved_gpu_hours'] = previous.get('reserved_gpu_hours', 0.) + previous.get('reserved_gpus', 0) * max(0., now-last) / 3600
    recovered.update(updated_unix=now, child_last_accounted_unix=now,
                     crash_gap_accounting='Conservative reserved-GPU time through recovery, including uncertain downtime')
    dump(base / 'supervisor_status.json', recovered)
    ownership = previous.get('child_ownership')
    if not ownership:
        recovered.update(status='STOPPED_UNVERIFIED_PREVIOUS_CHILD', child_state='UNVERIFIED')
        dump(base / 'supervisor_status.json', recovered)
        raise OwnershipUnverified('Previous unfinished child lacks nonce ownership; investigate without PID-only termination')
    members = _token_members(ownership)
    if members:
        _stop_owned_descendants(ownership, grace_seconds=grace_seconds)
    finished = time.time()
    recovered['reserved_gpu_hours'] += previous.get('reserved_gpus', 0) * max(0., finished-now) / 3600
    recovered.update(child_state='FINISHED', child_finished_unix=finished,
                     child_last_accounted_unix=finished, updated_unix=finished,
                     recovered_owned_children=[item['pid'] for item in members])
    if members:
        recovered['status'] = 'STOPPED_AFTER_OWNED_CHILD_RECOVERY'
    dump(base / 'supervisor_status.json', recovered)
    if members:
        raise RuntimeError('Stopped verified orphan children and preserved full accounting; inspect incomplete run before resuming')
    return recovered


def run_child(command, log_path, base, state, *, reserved_gpus, max_gpu_hours, deadline):
    start = time.time()
    monotonic_start = time.monotonic()
    prior = state.get('reserved_gpu_hours', 0.)
    if prior >= max_gpu_hours or start >= deadline:
        raise TimeoutError('No remaining registered compute/wall-time budget')
    ownership = dict(token=uuid.uuid4().hex, boot_id=_boot_id(), pid=None, pgid=None,
                     sid=None, leader_start_ticks=None)
    for key in ('child_finished_unix', 'child_exit_code'):
        state.pop(key, None)
    # Persist launch intent before Popen: recovery can find the inherited nonce
    # even if the supervisor dies before the new PID is durably recorded.
    state.update(child_command=command, child_started_unix=start, child_state='STARTING',
                 child_ownership=ownership, reserved_gpus=reserved_gpus,
                 child_log=str(log_path), child_last_accounted_unix=start, updated_unix=start)
    dump(base / 'supervisor_status.json', state)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open('ab') as log:
        process = None
        try:
            environment = dict(os.environ, PYTHONUNBUFFERED='1', OMP_NUM_THREADS='2', MKL_NUM_THREADS='2')
            environment[OWNER_ENV] = ownership['token']
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                       cwd=ROOT, start_new_session=True, env=environment)
            identity = _process_identity(process.pid)
            ownership.update(pid=process.pid, pgid=process.pid, sid=process.pid,
                             leader_start_ticks=identity['start_ticks'] if identity else None)
            process._public_harness_ownership = ownership
            state.update(child_pid=process.pid, child_state='RUNNING', child_ownership=ownership)
            dump(base / 'supervisor_status.json', state)
            while process.poll() is None:
                elapsed = time.monotonic() - monotonic_start
                state['reserved_gpu_hours'] = prior + reserved_gpus * elapsed / 3600
                state['updated_unix'] = time.time()
                state['child_last_accounted_unix'] = state['updated_unix']
                dump(base / 'supervisor_status.json', state)
                if state['reserved_gpu_hours'] >= max_gpu_hours or time.time() >= deadline:
                    stop_owned_group(process)
                    raise TimeoutError('Reserved GPU-hour or wall-time cap reached; only owned job stopped')
                time.sleep(5)
            if process.returncode:
                raise ChildExitedError(process.returncode, log_path)
        finally:
            cleaned = False
            try:
                if process is not None:
                    stop_owned_group(process, ownership)
                cleaned = True
            finally:
                state['reserved_gpu_hours'] = prior + reserved_gpus * (time.monotonic() - monotonic_start) / 3600
                state['child_exit_code'] = process.returncode if process is not None else None
                state['child_last_accounted_unix'] = time.time()
                state['updated_unix'] = state['child_last_accounted_unix']
                state['child_state'] = 'FINISHED' if cleaned else 'UNRESOLVED'
                if cleaned:
                    state['child_finished_unix'] = state['updated_unix']
                dump(base / 'supervisor_status.json', state)


def supervise(args):
    base = args.base.resolve()
    base.mkdir(parents=True, exist_ok=True)
    with (base / '.supervisor.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            return _supervise_locked(args, base)
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def _supervise_locked(args, base):
    manifest_path = base / 'queue_manifest.json'
    prior_hours = getattr(args, 'prior_reserved_gpu_hours', 0.)
    continue_failures = getattr(args, 'continue_controller_failures', False)
    if not math.isfinite(prior_hours) or not 0 <= prior_hours < args.max_gpu_hours:
        raise ValueError('Prior reserved GPU hours must be finite, nonnegative and below the inclusive cap')
    previous = read(base / 'supervisor_status.json') if (base / 'supervisor_status.json').exists() else {}
    # Recover ownership/accounting even if source drift will subsequently reject
    # this resume. A validation failure must not leave an orphan unaccounted for.
    previous = reconcile_previous_child(base, previous)
    if manifest_path.exists():
        manifest = read(manifest_path)
        if not (base / 'supervisor_status.json').exists():
            raise ValueError('Existing queue has no accounting ledger; never reset consumed GPU hours to zero')
        if manifest['source_sha256'] != pinned_sources() or manifest['jobs'] != jobs():
            raise ValueError('Frozen queue source or job matrix changed; investigate before a new version')
        if manifest['max_gpu_hours'] != args.max_gpu_hours or manifest['max_wall_hours'] != args.max_wall_hours:
            raise ValueError('Do not silently extend the registered compute budget on resume')
        if manifest.get('prior_reserved_gpu_hours', 0.) != prior_hours:
            raise ValueError('Do not change registered prior compute accounting on resume')
        if manifest.get('continue_controller_failures', False) != continue_failures:
            raise ValueError('Do not change registered controller-failure continuation on resume')
        for receipt in manifest.get('adopted_prequeue_runs', []):
            if any(sha(Path(path)) != digest for path, digest in receipt['evidence_sha256'].items()):
                raise ValueError('Adopted prequeue accounting evidence changed')
        for receipt in previous.get('failed', []):
            if (receipt.get('job') not in manifest['jobs'] or not receipt.get('accounting')
                    or receipt.get('output') != str(job_directory(base, receipt['job']))
                    or any(sha(Path(path)) != digest for path, digest in receipt['evidence_sha256'].items())):
                raise ValueError('Recorded failed-controller evidence or accounting changed')
        if previous.get('reserved_gpu_hours', -1.) < manifest.get('initial_reserved_gpu_hours', 0.):
            raise ValueError('Consumed GPU hours fell below immutable initial accounting')
    else:
        if previous:
            raise ValueError('Accounting ledger exists without a queue manifest; investigate rather than resetting it')
        adopted = prequeue_accounting(base, jobs())
        initial_hours = prior_hours + sum(receipt['reserved_gpu_hours'] for receipt in adopted)
        manifest = dict(schema='public-harness-queue-v1', created_unix=time.time(),
                        source_sha256=pinned_sources(), jobs=jobs(), max_gpu_hours=args.max_gpu_hours,
                        max_wall_hours=args.max_wall_hours, model_gpu=0, fitting_gpus=list(range(1, 8)),
                        prior_reserved_gpu_hours=prior_hours, adopted_prequeue_runs=adopted,
                        initial_reserved_gpu_hours=initial_hours,
                        continue_controller_failures=continue_failures,
                        accounting='Reserved GPU count times monotonic child duration; crash gaps conservatively charged through recovery',
                        automatic_development_retries=False, automatic_git_push=False)
        dump(manifest_path, manifest)
        previous = dict(reserved_gpu_hours=initial_hours)
    state = dict(schema='public-harness-supervisor-v1', status='RUNNING', pid=os.getpid(),
                 started_unix=manifest['created_unix'], updated_unix=time.time(),
                 reserved_gpu_hours=previous.get('reserved_gpu_hours', 0.), completed=[],
                 failed=list(previous.get('failed', [])))
    deadline = manifest['created_unix'] + args.max_wall_hours * 3600
    dump(base / 'supervisor_status.json', state)
    def interrupted(signum, frame):
        raise InterruptedError(f'Supervisor received signal {signum}')
    original_signals = {signum: signal.signal(signum, interrupted)
                        for signum in (signal.SIGTERM, signal.SIGINT)}
    def record_failure(failure, accounting_state):
        failure['accounting'] = failure_accounting(Path(failure['output']), manifest, accounting_state)
        if not any(item['output'] == failure['output'] for item in state['failed']):
            state['failed'].append(failure)
        state.update(phase='UNSCORABLE_CONTROLLER_FAILURE', updated_unix=time.time())
        dump(base / 'supervisor_status.json', state)
        print(json.dumps(failure), flush=True)
    try:
        for job in manifest['jobs']:
            if pinned_sources() != manifest['source_sha256']:
                raise ValueError('Runtime source changed after the queue was frozen')
            if time.time() >= deadline or state['reserved_gpu_hours'] >= args.max_gpu_hours:
                raise TimeoutError('No remaining registered compute/wall-time budget')
            run = job_directory(base, job)
            state.update(current_job=job, status='RUNNING')
            if not run.exists():
                command = [str(HERE / '.venv/bin/python'), '-B', str(HERE / 'run_baseline.py'),
                           '--harness', job['harness'], '--task', job['task'], '--seed', str(job['seed']),
                           '--gpus', '1,2,3,4,5,6,7', '--model-device', 'cuda:0', '--output', str(run)]
                name = f"{job['harness']}_{job['task']}_seed{job['seed']}"
                state['phase'] = 'DEVELOPMENT'
                try:
                    run_child(command, base / 'logs' / (name + '.log'), base, state,
                              reserved_gpus=8, max_gpu_hours=args.max_gpu_hours, deadline=deadline)
                except ChildExitedError as exc:
                    # run_child's finally must have cleaned descendants and
                    # charged the complete interval before any classification.
                    if (not continue_failures or exc.exit_code <= 0
                            or state.get('child_state') != 'FINISHED'
                            or state.get('child_exit_code') != exc.exit_code
                            or state.get('child_finished_unix', -1) < state.get('child_started_unix', 0)
                            or state.get('child_last_accounted_unix', -1) < state.get('child_finished_unix', 0)):
                        raise
                    if pinned_sources() != manifest['source_sha256']:
                        raise ValueError('Runtime source changed after the queue was frozen') from exc
                    status = read(run / 'run_status.json')
                    failure = controller_failure(run, job, status)
                    if failure is None:
                        raise
                    record_failure(failure, state)
                    continue
            status = read(run / 'run_status.json')
            if continue_failures:
                failure = controller_failure(run, job, status)
                if failure is not None:
                    record_failure(failure, previous)
                    continue
            if status.get('status') != 'DEVELOPMENT_COMPLETE':
                raise ValueError(f'Incomplete or failed run preserved for investigation: {run}')
            evaluation = run / 'heldout'
            python, device = LDA, 'cpu'
            if job['task'] == 'native_tapb':
                registration = ROOT / 'results/unified_bio_20260918/native_tapb/data/manifest.json'
                python, device = read(registration)['worker_python'], 'cuda:1'
            if not (evaluation / 'results.json').exists():
                state['phase'] = 'HELDOUT_EVALUATION'
                command = [python, '-B', str(HERE / 'heldout_public.py'), '--run-dir', str(run / 'development'),
                           '--output', str(evaluation), '--device', device]
                run_child(command, run / 'evaluation.log', base, state, reserved_gpus=int(device != 'cpu'),
                          max_gpu_hours=args.max_gpu_hours, deadline=deadline)
            # Independently rescore even when resuming a previously completed job.
            state['phase'] = 'INDEPENDENT_RESCORING'
            command = [LDA, '-B', str(HERE / 'verify_public.py'), str(evaluation)]
            run_child(command, run / 'verification.log', base, state, reserved_gpus=0,
                      max_gpu_hours=args.max_gpu_hours, deadline=deadline)
            result = read(evaluation / 'results.json')
            # Separate verified preview only: never edit the manuscript or push.
            state['phase'] = 'VERIFIED_PREVIEW_REFRESH'
            command = [LDA, '-B', str(ROOT / 'paper/tools/publish_public_harness.py'),
                       '--base', str(base), '--output-dir', str(ROOT / 'paper/tables/public_harness_preview')]
            run_child(command, run / 'preview.log', base, state, reserved_gpus=0,
                      max_gpu_hours=args.max_gpu_hours, deadline=deadline)
            state['completed'].append(dict(**job, primary=result['primary'],
                                           metric=result['primary_metric'], output=str(run)))
            dump(base / 'supervisor_status.json', state)
            print(json.dumps(state['completed'][-1]), flush=True)
        state.update(status='FINISHED_WITH_INCOMPLETE_RUNS' if state['failed'] else 'COMPLETE',
                     phase='FINISHED_WITH_UNSCORABLE_RUNS' if state['failed'] else 'VERIFIED',
                     completed_unix=time.time())
    except BaseException as exc:
        state.update(status='STOPPED_ON_FAILURE', error_type=type(exc).__name__, error=str(exc),
                     stopped_unix=time.time())
        dump(base / 'supervisor_status.json', state)
        raise
    finally:
        state['updated_unix'] = time.time()
        dump(base / 'supervisor_status.json', state)
        for signum, handler in original_signals.items():
            signal.signal(signum, handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--max-gpu-hours', type=float, default=180.)
    parser.add_argument('--max-wall-hours', type=float, default=24.)
    parser.add_argument('--prior-reserved-gpu-hours', type=float, default=0.,
                        help='Fixed earlier engineering allocation, counted inside --max-gpu-hours (must match on resume)')
    parser.add_argument('--continue-controller-failures', action='store_true',
                        help='Skip only registered unscorable AIRE native failures; immutable on resume')
    parser.add_argument('--detach', action='store_true')
    parser.add_argument('--status', action='store_true')
    args = parser.parse_args()
    if not 0 < args.max_gpu_hours <= 192 or not 0 < args.max_wall_hours <= 24:
        parser.error('Budget must be positive and no greater than 8 GPUs x one day')
    if not math.isfinite(args.prior_reserved_gpu_hours) or not 0 <= args.prior_reserved_gpu_hours < args.max_gpu_hours:
        parser.error('Prior reserved GPU hours must be finite, nonnegative and below the inclusive cap')
    if args.status:
        print(json.dumps(read(args.base / 'supervisor_status.json'), indent=2))
    elif args.detach:
        args.base.mkdir(parents=True, exist_ok=True)
        command = [sys.executable, '-B', str(Path(__file__).resolve()), '--base', str(args.base.resolve()),
                   '--max-gpu-hours', str(args.max_gpu_hours), '--max-wall-hours', str(args.max_wall_hours)]
        command += ['--prior-reserved-gpu-hours', str(args.prior_reserved_gpu_hours)]
        if args.continue_controller_failures:
            command.append('--continue-controller-failures')
        with (args.base / 'supervisor.log').open('ab') as log:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                       start_new_session=True, stdin=subprocess.DEVNULL)
        print(json.dumps(dict(supervisor_pid=process.pid, output=str(args.base.resolve()))))
    else:
        supervise(args)


if __name__ == '__main__':
    main()
