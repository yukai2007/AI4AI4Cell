"""CPU-only supervisor ownership/accounting tests; never touch live study jobs."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock
import uuid

import supervise
from broker import dump, read


class SupervisorTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='supervisor_owned_test_')
        self.base = Path(self.temporary.name)
        self.owned = []

    def tearDown(self):
        for process, ownership in self.owned:
            supervise.stop_owned_group(process, ownership, grace_seconds=2.)
            process.stdout.close()
            process.stderr.close()
        self.temporary.cleanup()

    def launch(self, script, extra_args=()):
        ownership = dict(token=uuid.uuid4().hex, boot_id=supervise._boot_id())
        environment = dict(os.environ)
        environment[supervise.OWNER_ENV] = ownership['token']
        process = subprocess.Popen([sys.executable, '-B', '-c', script, *extra_args], start_new_session=True,
                                   env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        identity = supervise._process_identity(process.pid)
        ownership.update(pid=process.pid, pgid=process.pid, sid=process.pid,
                         leader_start_ticks=identity['start_ticks'] if identity else None)
        self.owned.append((process, ownership))
        return process, ownership

    def test_exit_of_leader_does_not_leave_owned_grandchild(self):
        script = ("import subprocess,sys; p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(120)'],"
                  "stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); print(p.pid,flush=True)")
        process, ownership = self.launch(script)
        grandchild = int(process.stdout.readline())
        process.wait(timeout=5)
        self.assertTrue(any(p['pid'] == grandchild for p in supervise._token_members(ownership)))
        supervise.stop_owned_group(process, ownership, grace_seconds=2.)
        self.assertFalse(supervise._token_members(ownership))

    def test_detached_owned_descendant_is_also_stopped(self):
        script = ("import subprocess,sys; p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(120)'],"
                  "start_new_session=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); print(p.pid,flush=True)")
        process, ownership = self.launch(script)
        child = int(process.stdout.readline())
        process.wait(timeout=5)
        self.assertTrue(any(p['pid'] == child and p['sid'] != process.pid for p in supervise._token_members(ownership)))
        supervise.stop_owned_group(process, ownership, grace_seconds=2.)
        self.assertFalse(supervise._token_members(ownership))

    def test_wrong_nonce_never_signals_a_live_process(self):
        process, ownership = self.launch("import time; time.sleep(120)")
        wrong = dict(ownership, token=uuid.uuid4().hex)
        with self.assertRaises(supervise.OwnershipUnverified):
            supervise.stop_owned_group(process, wrong, grace_seconds=.1)
        self.assertIsNone(process.poll())

    def test_resume_charges_gap_and_stops_only_verified_orphan(self):
        process, ownership = self.launch("import time; time.sleep(120)")
        now = time.time()
        previous = dict(reserved_gpu_hours=1., reserved_gpus=8, child_started_unix=now-10,
                        child_last_accounted_unix=now-2, updated_unix=now-2,
                        child_ownership=ownership, child_pid=process.pid, child_state='RUNNING')
        with self.assertRaisesRegex(RuntimeError, 'verified orphan'):
            supervise.reconcile_previous_child(self.base, previous, grace_seconds=2.)
        recovered = read(self.base / 'supervisor_status.json')
        self.assertGreaterEqual(recovered['reserved_gpu_hours'], 1. + 16/3600)
        self.assertEqual(recovered['status'], 'STOPPED_AFTER_OWNED_CHILD_RECOVERY')
        self.assertEqual(recovered['child_state'], 'FINISHED')
        self.assertFalse(supervise._token_members(ownership))
        # A second resume cannot double charge the same finished interval.
        self.assertEqual(supervise.reconcile_previous_child(self.base, recovered), recovered)

    def test_crash_between_spawn_and_pid_record_recovers_by_launch_nonce(self):
        process, ownership = self.launch("import time; time.sleep(120)")
        intent = dict(ownership, pid=None, pgid=None, sid=None, leader_start_ticks=None)
        now = time.time()
        previous = dict(reserved_gpu_hours=0., reserved_gpus=1, child_started_unix=now-1,
                        child_last_accounted_unix=now-1, child_state='STARTING', child_ownership=intent)
        with self.assertRaisesRegex(RuntimeError, 'verified orphan'):
            supervise.reconcile_previous_child(self.base, previous, grace_seconds=2.)
        self.assertFalse(supervise._token_members(ownership))

    def test_legacy_unfinished_pid_fails_closed_without_zeroing_budget(self):
        now = time.time()
        previous = dict(reserved_gpu_hours=3., reserved_gpus=8, child_started_unix=now-10,
                        updated_unix=now-2, child_pid=os.getpid())
        with self.assertRaises(supervise.OwnershipUnverified):
            supervise.reconcile_previous_child(self.base, previous)
        recovered = read(self.base / 'supervisor_status.json')
        self.assertGreaterEqual(recovered['reserved_gpu_hours'], 3. + 16/3600)
        self.assertEqual(recovered['status'], 'STOPPED_UNVERIFIED_PREVIOUS_CHILD')

    def test_compute_cap_stops_owned_child_and_persists_final_charge(self):
        state = dict(reserved_gpu_hours=0.)
        with self.assertRaises(TimeoutError):
            supervise.run_child([sys.executable, '-B', '-c', 'import time; time.sleep(120)'],
                self.base/'child.log', self.base, state, reserved_gpus=8,
                max_gpu_hours=1e-9, deadline=time.time()+30)
        saved = read(self.base/'supervisor_status.json')
        self.assertEqual(saved['child_state'], 'FINISHED')
        self.assertGreater(saved['reserved_gpu_hours'], 0.)
        self.assertFalse(supervise._token_members(saved['child_ownership']))

    def test_existing_manifest_missing_ledger_never_resets_accounting(self):
        dump(self.base/'queue_manifest.json', {})
        args = argparse.Namespace(base=self.base, max_gpu_hours=180., max_wall_hours=24.)
        with self.assertRaisesRegex(ValueError, 'accounting ledger'):
            supervise.supervise(args)

    def test_recovery_precedes_changed_source_rejection(self):
        process, ownership = self.launch("import time; time.sleep(120)")
        now = time.time()
        dump(self.base/'queue_manifest.json', dict(source_sha256={'old': 'hash'}))
        dump(self.base/'supervisor_status.json', dict(reserved_gpu_hours=2., reserved_gpus=8,
             child_started_unix=now-10, child_last_accounted_unix=now-2, child_ownership=ownership))
        args = argparse.Namespace(base=self.base, max_gpu_hours=180., max_wall_hours=24.)
        with self.assertRaisesRegex(RuntimeError, 'verified orphan'):
            supervise.supervise(args)
        self.assertFalse(supervise._token_members(ownership))
        self.assertGreater(read(self.base/'supervisor_status.json')['reserved_gpu_hours'], 2.)

    def preview_fixture(self, job=None):
        job = job or dict(harness='ai_researcher', task='ptpc_neural', seed=42)
        run = supervise.job_directory(self.base, job)
        now = time.time()
        dump(run/'run_status.json', dict(**job, status='DEVELOPMENT_COMPLETE', pid=-1,
             started_unix=now-3600, completed_unix=now-1800,
             usage=dict(calls=32, input_tokens=100, output_tokens=100, generation_seconds=1., model='unit-test-only')))
        dump(run/'development/definition.json', dict(execution_kind='fresh-canonical-v3', config=job))
        dump(run/'heldout/results.json', dict(primary=.25, primary_metric='fake-test-only'))
        args = argparse.Namespace(base=self.base, max_gpu_hours=180., max_wall_hours=24.)
        return job, run, args

    def test_verified_preview_is_owned_cpu_child_before_completion(self):
        job, run, args = self.preview_fixture()
        calls = []
        def fake_child(command, log_path, base, state, **kwargs):
            calls.append((command, log_path, state['phase'], kwargs['reserved_gpus'], len(state['completed'])))
        with mock.patch.object(supervise, 'jobs', return_value=[job]), \
             mock.patch.object(supervise, 'pinned_sources', return_value={}), \
             mock.patch.object(supervise, 'run_child', side_effect=fake_child):
            supervise.supervise(args)
        self.assertEqual([call[2] for call in calls], ['INDEPENDENT_RESCORING', 'VERIFIED_PREVIEW_REFRESH'])
        self.assertEqual([call[3] for call in calls], [0, 0])
        self.assertEqual(calls[1][4], 0)
        self.assertEqual(calls[1][0][-4:], ['--base', str(self.base), '--output-dir',
                         str(supervise.ROOT/'paper/tables/public_harness_preview')])
        self.assertEqual(calls[1][1], run/'preview.log')
        saved = read(self.base/'supervisor_status.json')
        self.assertEqual(saved['status'], 'COMPLETE')
        self.assertEqual(len(saved['completed']), 1)

    def test_preview_failure_stops_without_claiming_completion(self):
        job, run, args = self.preview_fixture()
        with mock.patch.object(supervise, 'jobs', return_value=[job]), \
             mock.patch.object(supervise, 'pinned_sources', return_value={}), \
             mock.patch.object(supervise, 'run_child', side_effect=[None, RuntimeError('preview fixture failed')]):
            with self.assertRaisesRegex(RuntimeError, 'preview fixture failed'):
                supervise.supervise(args)
        saved = read(self.base/'supervisor_status.json')
        self.assertEqual(saved['status'], 'STOPPED_ON_FAILURE')
        self.assertEqual(saved['phase'], 'VERIFIED_PREVIEW_REFRESH')
        self.assertEqual(saved['completed'], [])

    def test_completed_prequeue_accounting_and_prior_charge_are_adopted_once(self):
        job, run, args = self.preview_fixture()
        args.prior_reserved_gpu_hours = 1.
        with mock.patch.object(supervise, 'jobs', return_value=[job]), \
             mock.patch.object(supervise, 'pinned_sources', return_value={}), \
             mock.patch.object(supervise, 'run_child'):
            supervise.supervise(args)
            first = read(self.base/'supervisor_status.json')
            supervise.supervise(args)
        manifest = read(self.base/'queue_manifest.json')
        saved = read(self.base/'supervisor_status.json')
        self.assertEqual(manifest['prior_reserved_gpu_hours'], 1.)
        self.assertEqual(manifest['adopted_prequeue_runs'][0]['reserved_gpu_hours'], 4.)
        self.assertEqual(manifest['initial_reserved_gpu_hours'], 5.)
        self.assertEqual(first['reserved_gpu_hours'], 5.)
        self.assertEqual(saved['reserved_gpu_hours'], 5.)
        self.assertEqual(len(manifest['adopted_prequeue_runs']), 1)
        args.prior_reserved_gpu_hours = 0.
        with mock.patch.object(supervise, 'jobs', return_value=[job]), \
             mock.patch.object(supervise, 'pinned_sources', return_value={}):
            with self.assertRaisesRegex(ValueError, 'prior compute accounting'):
                supervise.supervise(args)

    def test_prequeue_and_prior_accounting_are_inside_total_cap(self):
        job, run, args = self.preview_fixture()
        args.prior_reserved_gpu_hours, args.max_gpu_hours = 1., 4.
        with mock.patch.object(supervise, 'jobs', return_value=[job]), \
             mock.patch.object(supervise, 'pinned_sources', return_value={}), \
             mock.patch.object(supervise, 'run_child') as child:
            with self.assertRaises(TimeoutError):
                supervise.supervise(args)
        child.assert_not_called()
        self.assertEqual(read(self.base/'supervisor_status.json')['reserved_gpu_hours'], 5.)

    def test_live_unfinished_prequeue_runner_refuses_creation_without_signaling(self):
        job, run, args = self.preview_fixture()
        process, ownership = self.launch('import time; time.sleep(120)')
        status = read(run/'run_status.json')
        status.update(status='NATIVE_CONTROLLER_RUNNING', pid=process.pid)
        status.pop('completed_unix')
        dump(run/'run_status.json', status)
        with mock.patch.object(supervise, 'jobs', return_value=[job]):
            with self.assertRaisesRegex(ValueError, 'Active or unfinished prequeue'):
                supervise.supervise(args)
        self.assertIsNone(process.poll())
        self.assertFalse((self.base/'queue_manifest.json').exists())

    def test_completed_prequeue_status_still_waits_for_launcher_cleanup(self):
        job, run, args = self.preview_fixture()
        process, ownership = self.launch('import time; time.sleep(120)',
            [str(supervise.HERE/'run_baseline.py'), '--output', str(run)])
        status = read(run/'run_status.json')
        status['pid'] = process.pid
        dump(run/'run_status.json', status)
        with self.assertRaisesRegex(ValueError, 'still cleaning up'):
            supervise.prequeue_accounting(self.base, [job])
        self.assertIsNone(process.poll())

    def test_synthetic_prequeue_run_is_never_adopted(self):
        job, run, args = self.preview_fixture()
        dump(run/'development/definition.json', dict(execution_kind='injected-test-fitter', config=job))
        with self.assertRaisesRegex(ValueError, 'Test/cache execution'):
            supervise.prequeue_accounting(self.base, [job])

    def test_job_order_is_breadth_first_but_same_thirty_jobs(self):
        jobs = supervise.jobs()
        self.assertEqual(len(jobs), 30)
        self.assertEqual([job['seed'] for job in jobs], [42]*10 + [43]*10 + [44]*10)
        self.assertEqual(jobs[0], dict(harness='ai_scientist_v2', task='ptpc_neural', seed=42))
        self.assertEqual({tuple(sorted(job.items())) for job in jobs},
                         {tuple(sorted(dict(harness=h,task=t,seed=s).items()))
                          for h in supervise.HARNESS_ORDER for t in supervise.TASK_ORDER for s in (42,43,44)})

    def failure_fixture(self, *, job=None, error=None, base=None):
        job = job or dict(harness='ai_researcher', task='ptpc_neural', seed=42)
        base = base or self.base
        run = supervise.job_directory(base, job)
        now = time.time()
        status = dict(**job, status='FAILED', pid=-1, started_unix=now-2, completed_unix=now-1,
            error_type='NativeRunIncomplete', test_read=False,
            error=error or 'Error: Tool response remained invalid after 3 format attempts: Return exactly one tool/arguments object or one permitted final object',
            usage=dict(calls=3, input_tokens=100, output_tokens=100, generation_seconds=.2, model='unit-test-only'))
        dump(run/'run_status.json', status)
        dump(run/'development/definition.json', dict(execution_kind='fresh-canonical-v3', config=job))
        args = argparse.Namespace(base=base, max_gpu_hours=180., max_wall_hours=24.,
                                  continue_controller_failures=True)
        return job, run, args

    def test_controller_failure_default_still_stops(self):
        job, run, args = self.failure_fixture()
        del args.continue_controller_failures
        with mock.patch.object(supervise, 'jobs', return_value=[job]), \
             mock.patch.object(supervise, 'pinned_sources', return_value={}), \
             mock.patch.object(supervise, 'run_child') as child:
            with self.assertRaisesRegex(ValueError, 'Incomplete or failed run'):
                supervise.supervise(args)
        child.assert_not_called()
        self.assertFalse(read(self.base/'queue_manifest.json')['continue_controller_failures'])
        self.assertEqual(read(self.base/'supervisor_status.json')['status'], 'STOPPED_ON_FAILURE')

    def test_exact_prefixes_and_single_native_error_wrapper(self):
        for prefix in supervise.CONTROLLER_FAILURE_PREFIXES:
            for wrapper in ('', 'Error: '):
                with self.subTest(prefix=prefix, wrapper=wrapper):
                    job, run, _ = self.failure_fixture(error=wrapper+prefix+' details')
                    self.assertIsNotNone(supervise.controller_failure(run, job, read(run/'run_status.json')))
        for error in ('Trusted evaluator infrastructure failed; native experiment aborted',
                      'Global model-call cap reached', 'Native agent produced no messages',
                      'Error: Error: Tool response remained invalid after 3 attempts',
                      'Infrastructure error: Tool response remained invalid after 3 attempts'):
            job, run, _ = self.failure_fixture(error=error)
            self.assertIsNone(supervise.controller_failure(run, job, read(run/'run_status.json')))
        job, run, _ = self.failure_fixture()
        status = read(run/'run_status.json')
        for field, value in (('error_type', 'RuntimeError'), ('status', 'DEVELOPMENT_COMPLETE')):
            self.assertIsNone(supervise.controller_failure(run, job, dict(status, **{field:value})))
        ais = dict(job, harness='ai_scientist_v2')
        _, run, _ = self.failure_fixture(job=ais)
        self.assertIsNone(supervise.controller_failure(run, ais, read(run/'run_status.json')))

    def test_context_limit_failure_is_adopted_once_without_retry_or_score(self):
        job, run, args = self.failure_fixture(
            error='Error: Native context exceeds declared token limit; no silent truncation.')
        status = read(run/'run_status.json')
        expected = 8 * (status['completed_unix'] - status['started_unix']) / 3600
        args.prior_reserved_gpu_hours = 4.02
        with mock.patch.object(supervise, 'jobs', return_value=[job]), \
             mock.patch.object(supervise, 'pinned_sources', return_value={}), \
             mock.patch.object(supervise, 'run_child') as child:
            supervise.supervise(args)
            supervise.supervise(args)
        child.assert_not_called()
        manifest = read(self.base/'queue_manifest.json')
        saved = read(self.base/'supervisor_status.json')
        self.assertEqual(len(manifest['adopted_prequeue_runs']), 1)
        self.assertEqual(manifest['adopted_prequeue_runs'][0]['reserved_gpu_hours'], expected)
        self.assertEqual(saved['reserved_gpu_hours'], 4.02 + expected)
        self.assertEqual(saved['status'], 'FINISHED_WITH_INCOMPLETE_RUNS')
        self.assertEqual(len(saved['failed']), 1)
        self.assertEqual(saved['completed'], [])
        self.assertNotIn('primary', saved['failed'][0])
        self.assertFalse((run/'heldout').exists())
        dump(run/'run_status.json', dict(status, error='altered receipt'))
        with mock.patch.object(supervise, 'jobs', return_value=[job]), \
             mock.patch.object(supervise, 'pinned_sources', return_value={}):
            with self.assertRaisesRegex(ValueError, 'Adopted prequeue accounting evidence changed'):
                supervise.supervise(args)

    def test_sealed_partial_run_is_not_classified_as_unscorable(self):
        job, run, _ = self.failure_fixture(
            error='Error: Native context exceeds declared token limit; no silent truncation.')
        dump(run/'development/selection_seal.json', dict(status='sealed-test-fixture'))
        with self.assertRaisesRegex(ValueError, 'held-out access/artifacts'):
            supervise.controller_failure(run, job, read(run/'run_status.json'))

    def test_classifier_rejects_identity_nonproduction_and_bad_receipts(self):
        job, run, _ = self.failure_fixture()
        status = read(run/'run_status.json')
        for bad in (dict(status, seed=43), dict(status, usage=None), dict(status, completed_unix=None),
                    dict(status, test_read=True)):
            with self.assertRaises(ValueError):
                supervise.controller_failure(run, job, bad)
        for definition in (dict(execution_kind='injected-test-fitter', config=job),
                           dict(execution_kind='fresh-canonical-v3', config=dict(job, seed=43))):
            dump(run/'development/definition.json', definition)
            with self.assertRaises(ValueError):
                supervise.controller_failure(run, job, status)
        self.failure_fixture()
        dump(run/'heldout/results.json', dict(primary=.4))
        with self.assertRaisesRegex(ValueError, 'held-out'):
            supervise.controller_failure(run, job, status)

    def test_allowed_failure_continues_without_heldout_retry_or_fake_score(self):
        failed, run, args = self.failure_fixture()
        successful, _, _ = self.preview_fixture(dict(harness='ai_scientist_v2', task='ptpc_neural', seed=42))
        with mock.patch.object(supervise, 'jobs', return_value=[failed, successful]), \
             mock.patch.object(supervise, 'pinned_sources', return_value={}), \
             mock.patch.object(supervise, 'run_child') as child:
            supervise.supervise(args)
            first = read(self.base/'supervisor_status.json')
            supervise.supervise(args)
        saved = read(self.base/'supervisor_status.json')
        self.assertEqual(saved['status'], 'FINISHED_WITH_INCOMPLETE_RUNS')
        self.assertEqual(len(saved['failed']), 1)
        self.assertEqual(saved['failed'][0]['job'], failed)
        self.assertEqual(saved['failed'][0]['output'], str(run))
        self.assertNotIn('primary', saved['failed'][0])
        self.assertEqual(saved['failed'], first['failed'])
        self.assertEqual(saved['reserved_gpu_hours'], first['reserved_gpu_hours'])
        self.assertEqual(len(saved['completed']), 1)
        self.assertFalse((run/'heldout').exists())
        self.assertEqual(child.call_count, 4)  # Only successful job: verify + preview, twice.
        self.assertTrue(all('run_baseline.py' not in ' '.join(call.args[0])
                            and 'heldout_public.py' not in ' '.join(call.args[0])
                            for call in child.call_args_list))

    def test_all_failed_final_status_and_flag_pinned_both_directions(self):
        job, _, args = self.failure_fixture()
        with mock.patch.object(supervise, 'jobs', return_value=[job]), \
             mock.patch.object(supervise, 'pinned_sources', return_value={}), \
             mock.patch.object(supervise, 'run_child') as child:
            supervise.supervise(args)
            self.assertEqual(read(self.base/'supervisor_status.json')['status'], 'FINISHED_WITH_INCOMPLETE_RUNS')
            args.continue_controller_failures = False
            with self.assertRaisesRegex(ValueError, 'controller-failure continuation'):
                supervise.supervise(args)
        child.assert_not_called()
        with tempfile.TemporaryDirectory(prefix='supervisor_false_flag_') as other:
            args.base, args.continue_controller_failures = Path(other), False
            with mock.patch.object(supervise, 'jobs', return_value=[]), \
                 mock.patch.object(supervise, 'pinned_sources', return_value={}):
                supervise.supervise(args)
                args.continue_controller_failures = True
                with self.assertRaisesRegex(ValueError, 'controller-failure continuation'):
                    supervise.supervise(args)

    def new_failure_child(self, command, log_path, base, state, **kwargs):
        job = dict(harness='ai_researcher', task='ptpc_neural', seed=42)
        self.failure_fixture(job=job, base=base)
        finish = time.time()
        state.update(child_command=command, child_started_unix=finish-3, child_finished_unix=finish,
                     child_last_accounted_unix=finish, child_state='FINISHED', child_exit_code=1,
                     child_ownership=dict(boot_id='unit-test-no-live-processes', token='fixture'),
                     reserved_gpu_hours=state['reserved_gpu_hours'] + 8*3/3600)
        raise supervise.ChildExitedError(1, log_path)

    def test_new_failed_child_is_cleaned_accounted_then_skipped_without_retry(self):
        job = dict(harness='ai_researcher', task='ptpc_neural', seed=42)
        args = argparse.Namespace(base=self.base, max_gpu_hours=180., max_wall_hours=24.,
                                  continue_controller_failures=True)
        with mock.patch.object(supervise, 'jobs', return_value=[job]), \
             mock.patch.object(supervise, 'pinned_sources', return_value={}), \
             mock.patch.object(supervise, 'run_child', side_effect=self.new_failure_child) as child:
            supervise.supervise(args)
            first = read(self.base/'supervisor_status.json')
            supervise.supervise(args)
        self.assertEqual(child.call_count, 1)
        saved = read(self.base/'supervisor_status.json')
        self.assertEqual(saved['status'], 'FINISHED_WITH_INCOMPLETE_RUNS')
        self.assertGreater(saved['reserved_gpu_hours'], 0.)
        self.assertEqual(saved['reserved_gpu_hours'], first['reserved_gpu_hours'])
        self.assertEqual(saved['failed'][0]['accounting']['kind'], 'finished_owned_child')
        failure_run = supervise.job_directory(self.base, job)
        status = read(failure_run/'run_status.json')
        dump(failure_run/'run_status.json', dict(status, error='Tool response remained invalid after ALTERED'))
        with mock.patch.object(supervise, 'jobs', return_value=[job]), \
             mock.patch.object(supervise, 'pinned_sources', return_value={}):
            with self.assertRaisesRegex(ValueError, 'failed-controller evidence'):
                supervise.supervise(args)

    def test_other_child_failures_never_continue_even_with_matching_status(self):
        errors = [TimeoutError('cap'), OSError('launch'), RuntimeError('cleanup'),
                  supervise.OwnershipUnverified('ownership'), supervise.ChildExitedError(-15, 'signal')]
        for error in errors:
            with self.subTest(error=type(error).__name__), tempfile.TemporaryDirectory(prefix='supervisor_infra_') as tmp:
                args = argparse.Namespace(base=Path(tmp), max_gpu_hours=180., max_wall_hours=24.,
                                          continue_controller_failures=True)
                job = dict(harness='ai_researcher', task='ptpc_neural', seed=42)
                def fail(command, log_path, base, state, **kwargs):
                    try:
                        self.new_failure_child(command, log_path, base, state, **kwargs)
                    except supervise.ChildExitedError:
                        raise error
                with mock.patch.object(supervise, 'jobs', return_value=[job]), \
                     mock.patch.object(supervise, 'pinned_sources', return_value={}), \
                     mock.patch.object(supervise, 'run_child', side_effect=fail):
                    with self.assertRaises(type(error)):
                        supervise.supervise(args)
                self.assertEqual(read(args.base/'supervisor_status.json')['status'], 'STOPPED_ON_FAILURE')

    def test_new_failure_source_drift_stops_before_classification(self):
        job = dict(harness='ai_researcher', task='ptpc_neural', seed=42)
        args = argparse.Namespace(base=self.base, max_gpu_hours=180., max_wall_hours=24.,
                                  continue_controller_failures=True)
        with mock.patch.object(supervise, 'jobs', return_value=[job]), \
             mock.patch.object(supervise, 'pinned_sources', side_effect=[{}, {}, {'changed':'hash'}]), \
             mock.patch.object(supervise, 'run_child', side_effect=self.new_failure_child):
            with self.assertRaisesRegex(ValueError, 'Runtime source changed'):
                supervise.supervise(args)
        self.assertEqual(read(self.base/'supervisor_status.json')['failed'], [])

    def test_unresolved_cleanup_and_unknown_native_reason_stop(self):
        job = dict(harness='ai_researcher', task='ptpc_neural', seed=42)
        for mode in ('unresolved', 'unknown_reason'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory(prefix='supervisor_unresolved_') as tmp:
                args = argparse.Namespace(base=Path(tmp), max_gpu_hours=180., max_wall_hours=24.,
                                          continue_controller_failures=True)
                def fail(command, log_path, base, state, **kwargs):
                    try:
                        self.new_failure_child(command, log_path, base, state, **kwargs)
                    except supervise.ChildExitedError:
                        if mode == 'unresolved':
                            state['child_state'] = 'UNRESOLVED'
                        else:
                            self.failure_fixture(base=base, error='Trusted evaluator infrastructure failed; native experiment aborted')
                        raise
                with mock.patch.object(supervise, 'jobs', return_value=[job]), \
                     mock.patch.object(supervise, 'pinned_sources', return_value={}), \
                     mock.patch.object(supervise, 'run_child', side_effect=fail) as child:
                    with self.assertRaises(supervise.ChildExitedError):
                        supervise.supervise(args)
                self.assertEqual(child.call_count, 1)
                self.assertEqual(read(args.base/'supervisor_status.json')['failed'], [])

    def test_real_cpu_nonzero_child_is_finally_cleaned_and_accounted(self):
        state = dict(reserved_gpu_hours=1.)
        with self.assertRaises(supervise.ChildExitedError) as caught:
            supervise.run_child([sys.executable, '-B', '-c', 'raise SystemExit(7)'],
                self.base/'nonzero.log', self.base, state, reserved_gpus=0,
                max_gpu_hours=180., deadline=time.time()+30)
        self.assertEqual(caught.exception.exit_code, 7)
        self.assertEqual(state['child_state'], 'FINISHED')
        self.assertEqual(state['child_exit_code'], 7)
        self.assertEqual(state['child_finished_unix'], state['child_last_accounted_unix'])
        self.assertEqual(state['reserved_gpu_hours'], 1.)
        self.assertFalse(supervise._token_members(state['child_ownership']))

    def test_unaccounted_failed_run_is_not_skipped(self):
        job, run, _ = self.failure_fixture()
        with self.assertRaisesRegex(ValueError, 'compute accounting'):
            supervise.failure_accounting(run, {}, {})

    def test_detach_forwards_explicit_option(self):
        command = ['supervise.py', '--base', str(self.base), '--detach', '--continue-controller-failures']
        with mock.patch.object(sys, 'argv', command), mock.patch.object(supervise.subprocess, 'Popen') as process:
            process.return_value.pid = 123
            supervise.main()
        self.assertIn('--continue-controller-failures', process.call_args.args[0])


if __name__ == '__main__':
    unittest.main()
