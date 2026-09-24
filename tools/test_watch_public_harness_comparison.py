"""CPU-only watcher tests: no live queue launches, Git commits, or pushes."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest import mock

import watch_public_harness_comparison as watch


class WatcherTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='comparison_watch_test_')
        self.root = Path(self.temporary.name)
        self.paper = self.root/'paper'
        self.base = self.root/'queue'
        self.paper.mkdir()
        self.base.mkdir()
        self.args = argparse.Namespace(paper=self.paper, base=self.base, tectonic=Path('/fixture/tectonic'),
            fontconfig=Path('/fixture/fonts'), poll_seconds=60., once=False, deliver=False, detach=False)
        self.watcher = watch.Watcher(self.args)
        self.watcher.folder.mkdir()
        self.job = dict(harness='ai_researcher', task='ptpc_neural', seed=42)
        self.manifest = dict(created_unix=time.time()-10, max_gpu_hours=180., max_wall_hours=24., jobs=[self.job])
        self.supervisor = dict(status='RUNNING', pid=123, updated_unix=time.time(), phase='DEVELOPMENT',
                               current_job=self.job, reserved_gpu_hours=1.)
        self.write(self.base/'queue_manifest.json', self.manifest)
        self.write(self.base/'supervisor_status.json', self.supervisor)
        self.watcher.state = dict(base=str(self.base), paper=str(self.paper), origin='fixture-origin',
            queue_manifest_sha256=watch.digest(self.base/'queue_manifest.json'), source_sha256={},
            owned_sha256={name:None for name in watch.ALLOWLIST}, last_fingerprint=None,
            last_snapshot=None, delivered_milestones=[], pending_push=None, deliver_enabled=False)

    def tearDown(self):
        self.temporary.cleanup()

    def write(self, path, value):
        watch.atomic_write(path, watch.json_bytes(value))

    def snapshot(self, resolved=False, seed42=False):
        return dict(comparison_resolved=resolved, scores_complete=False,
                    seed42_comparison_resolved=seed42, seed42_scores_complete=False,
                    completion=dict(matrix=dict(denominator=30, terminal=30 if resolved else 0)))

    def test_branch_guard_refuses_main_or_other_branch(self):
        for branch in ('main', 'master', 'unrelated'):
            with self.subTest(branch=branch), mock.patch.object(watch, 'git', side_effect=[str(self.paper), branch]):
                with self.assertRaisesRegex(RuntimeError, 'outside'):
                    watch.branch_guard(self.paper)
        with mock.patch.object(watch, 'git', side_effect=[str(self.paper), watch.BRANCH, '']) as git:
            watch.branch_guard(self.paper)
        self.assertEqual(git.call_args.args[1:], ('merge-base', '--is-ancestor', watch.ANCHOR, 'HEAD'))

    def test_exact_allowlist_excludes_manuscript_and_old_preview(self):
        self.assertIn(str(watch.MANUSCRIPT_PDF), watch.ALLOWLIST)
        for path in ('main.tex', 'manuscript.pdf', 'sections/05-experiments.tex',
                     'tables/public_harness_preview/snapshot_public_harness.json', '../outside'):
            with self.assertRaises(RuntimeError):
                watch.safe_artifact(self.paper, path)

    def test_symlink_output_is_never_overwritten(self):
        target = self.root/'user.tex'
        target.write_text('user content')
        (self.paper/watch.REPORT_TEX).symlink_to(target)
        with self.assertRaisesRegex(RuntimeError, 'symlink'):
            watch.safe_artifact(self.paper, str(watch.REPORT_TEX))
        self.assertEqual(target.read_text(), 'user content')

    def test_ownership_guard_detects_user_edits(self):
        path = self.paper/watch.REPORT_TEX
        path.write_text('owned')
        self.watcher.state['owned_sha256'][str(watch.REPORT_TEX)] = watch.digest(path)
        path.write_text('user edit')
        with mock.patch.object(watch, 'branch_guard'), mock.patch.object(watch, 'git', return_value='fixture-origin'):
            with self.assertRaisesRegex(RuntimeError, 'User/unowned edit'):
                self.watcher.guard(sources=False)
        self.assertEqual(path.read_text(), 'user edit')

    def test_initialize_rejects_untracked_existing_artifact(self):
        self.watcher.state = {}
        (self.paper/watch.REPORT_TEX).write_text('user untracked draft')
        def fake_git(paper, *args):
            if args[0] == 'diff':
                return ''
            if args[0] == 'rev-parse':
                raise subprocess.CalledProcessError(128, ['git'])
            return ''
        with mock.patch.object(watch, 'branch_guard'), mock.patch.object(watch, 'git', side_effect=fake_git):
            with self.assertRaisesRegex(RuntimeError, 'Untracked artifact collision'):
                self.watcher.initialize()

    def test_initialize_rejects_user_staging(self):
        self.watcher.state = {}
        with mock.patch.object(watch, 'branch_guard'), mock.patch.object(watch, 'git', return_value='main.tex'):
            with self.assertRaisesRegex(RuntimeError, 'User-staged'):
                self.watcher.initialize()

    def test_lock_excludes_second_watcher(self):
        with watch.watcher_lock(self.watcher.folder):
            with self.assertRaises(BlockingIOError):
                with watch.watcher_lock(self.watcher.folder):
                    self.fail('Second watcher entered lock')

    def test_terminal_fingerprint_ignores_training_progress(self):
        before = watch.terminal_fingerprint(self.base, [self.job], self.supervisor)
        run = self.base/'ai_researcher/ptpc_neural/seed42'
        self.write(run/'run_status.json', dict(status='NATIVE_CONTROLLER_RUNNING'))
        self.write(run/'development/fits/D00/progress.json', dict(round=20))
        self.assertEqual(before, watch.terminal_fingerprint(self.base, [self.job], self.supervisor))
        self.write(run/'run_status.json', dict(status='FAILED', error='declared failure'))
        after = watch.terminal_fingerprint(self.base, [self.job], self.supervisor)
        self.assertNotEqual(before, after)

    def test_observation_distinguishes_budget_infra_dead_and_progress(self):
        progress = self.base/'ai_researcher/ptpc_neural/seed42/development/fits/D01/progress.json'
        self.write(progress, dict(round=45, rounds=100))
        with mock.patch.object(watch, 'supervisor_alive', return_value=True):
            observation = watch.queue_observation(self.base, self.manifest, self.supervisor)
        self.assertEqual(observation['status'], 'PENDING')
        self.assertEqual(observation['current_fit']['receipt']['round'], 45)
        for error, expected in [('TimeoutError', 'BUDGET_EXHAUSTED'), ('ChildExitedError', 'STOPPED_INFRASTRUCTURE_OR_UNEXPECTED')]:
            stopped = dict(self.supervisor, status='STOPPED_ON_FAILURE', error_type=error)
            observation = watch.queue_observation(self.base, self.manifest, stopped)
            self.assertEqual(observation['status'], expected)
            self.assertTrue(observation['action_needed'])
        with mock.patch.object(watch, 'supervisor_alive', return_value=False):
            self.assertEqual(watch.queue_observation(self.base, self.manifest, self.supervisor)['status'], 'SUPERVISOR_NOT_RUNNING')

    def test_no_full_publication_on_unchanged_poll(self):
        snapshot = self.snapshot()
        def fake_publish(observation):
            self.watcher.state['last_snapshot'] = snapshot
            return snapshot
        with mock.patch.object(self.watcher, 'guard'), \
             mock.patch.object(self.watcher, 'publish', side_effect=fake_publish) as publish, \
             mock.patch.object(self.watcher, 'delivery'), \
             mock.patch.object(watch, 'supervisor_alive', return_value=True):
            self.assertIsNone(self.watcher.tick())
            self.assertIsNone(self.watcher.tick())
        self.assertEqual(publish.call_count, 1)
        self.assertFalse(watch.read(self.watcher.folder/'heartbeat.json')['training_mutations'])

    def test_unexpected_stop_records_stopped_milestone_and_nonzero(self):
        self.write(self.base/'supervisor_status.json', dict(self.supervisor, status='STOPPED_ON_FAILURE', error_type='RuntimeError'))
        with mock.patch.object(self.watcher, 'guard'), \
             mock.patch.object(self.watcher, 'publish', return_value=self.snapshot()), \
             mock.patch.object(self.watcher, 'delivery') as delivery:
            self.assertEqual(self.watcher.tick(), 1)
        self.assertIn('stopped_terminal', delivery.call_args.args[0])
        self.assertTrue(watch.read(self.watcher.folder/'heartbeat.json')['action_needed'])

    def test_finished_supervisor_with_pending_jobs_is_not_success(self):
        self.write(self.base/'supervisor_status.json', dict(self.supervisor, status='COMPLETE'))
        with mock.patch.object(self.watcher, 'guard'), \
             mock.patch.object(self.watcher, 'publish', return_value=self.snapshot()), \
             mock.patch.object(self.watcher, 'delivery') as delivery:
            self.assertEqual(self.watcher.tick(), 1)
        self.assertIn('stopped_terminal', delivery.call_args.args[0])

    def test_all_resolved_is_distinct_from_all_scored(self):
        self.write(self.base/'supervisor_status.json', dict(self.supervisor, status='FINISHED_WITH_INCOMPLETE_RUNS'))
        with mock.patch.object(self.watcher, 'guard'), \
             mock.patch.object(self.watcher, 'publish', return_value=self.snapshot(resolved=True, seed42=True)), \
             mock.patch.object(self.watcher, 'delivery'):
            self.assertEqual(self.watcher.tick(), 0)
        heartbeat = watch.read(self.watcher.folder/'heartbeat.json')
        self.assertTrue(heartbeat['comparison_resolved'])
        self.assertFalse(heartbeat['scores_complete'])

    def test_delivery_is_opt_in_and_milestone_only(self):
        with mock.patch.object(watch, 'git') as git:
            self.watcher.delivery(['seed42_resolved'], {})
            self.args.deliver = True
            self.watcher.delivery([], {})
        git.assert_not_called()

    def test_delivery_never_stages_existing_user_index(self):
        self.args.deliver = True
        with mock.patch.object(self.watcher, 'guard'), mock.patch.object(watch, 'git', return_value='main.tex') as git:
            with self.assertRaisesRegex(RuntimeError, 'User-staged'):
                self.watcher.delivery(['seed42_resolved'], {})
        self.assertEqual(git.call_count, 1)

    def test_mock_delivery_commands_are_scoped_and_nonforce(self):
        self.args.deliver = True
        self.watcher.state['last_snapshot'] = self.snapshot(seed42=True)
        calls = []
        def fake_git(paper, *args):
            calls.append(args)
            if args[:2] == ('rev-parse', 'HEAD'):
                return 'fixture-checkpoint'
            return ''
        with mock.patch.object(self.watcher, 'guard'), mock.patch.object(watch, 'git', side_effect=fake_git):
            self.watcher.delivery(['seed42_resolved'], dict(status='PENDING'))
        added = next(args for args in calls if args[0] == 'add')
        self.assertTrue(set(added[3:]) <= set(watch.ALLOWLIST))
        committed = next(args for args in calls if args[0] == 'commit')
        self.assertEqual(committed[1], '--only')
        pushed = next(args for args in calls if args[0] == 'push')
        self.assertEqual(pushed, ('push', 'origin', 'HEAD:refs/heads/'+watch.BRANCH))
        self.assertFalse(any(arg in ('--force', 'checkout', 'reset') for args in calls for arg in args))
        self.assertEqual(self.watcher.state['delivered_milestones'], ['seed42_resolved'])

    def test_mock_publish_writes_only_dedicated_outputs_and_cpu_commands(self):
        (self.paper/'fonts').mkdir()
        snapshot = self.snapshot()
        calls = []
        def fake_command(argv, **kwargs):
            calls.append((argv, kwargs))
            output = Path(argv[argv.index('--output-dir')+1])
            for name in watch.TABLE_NAMES:
                watch.atomic_write(output/name, watch.json_bytes(snapshot) if name.endswith('.json') else b'% fixture\n')
            return 'fixture publisher'
        with mock.patch.object(self.watcher, 'guard'), mock.patch.object(watch, 'command', side_effect=fake_command), \
             mock.patch.object(self.watcher, 'compile', return_value=(b'fixture-pdf', dict(visual_review=watch.VISUAL_REVIEW))) as compile:
            result = self.watcher.publish(dict(action_needed=False))
        self.assertEqual(result, snapshot)
        self.assertEqual(compile.call_count, 1)
        self.assertEqual(calls[0][1]['env']['CUDA_VISIBLE_DEVICES'], '')
        self.assertTrue((self.paper/watch.REPORT_PDF).exists())
        self.assertFalse((self.paper/'manuscript.pdf').exists())
        self.assertFalse((self.paper/'tables/public_harness_preview').exists())

    def test_milestone_builds_manuscript_without_editing_source(self):
        (self.paper/'fonts').mkdir()
        (self.paper/'main.tex').write_text('reviewed manuscript source')
        snapshot = self.snapshot(seed42=True)
        def fake_command(argv, **kwargs):
            output = Path(argv[argv.index('--output-dir')+1])
            for name in watch.TABLE_NAMES:
                watch.atomic_write(output/name, watch.json_bytes(snapshot) if name.endswith('.json') else b'% fixture\n')
            return ''
        with mock.patch.object(self.watcher, 'guard'), mock.patch.object(watch, 'command', side_effect=fake_command), \
             mock.patch.object(self.watcher, 'compile', return_value=(b'fixture-pdf', dict(visual_review=watch.VISUAL_REVIEW))) as compile:
            self.watcher.publish(dict(action_needed=False))
        self.assertEqual(compile.call_count, 2)
        self.assertTrue(compile.call_args.kwargs['manuscript'])
        self.assertTrue((self.paper/watch.MANUSCRIPT_PDF).exists())
        self.assertEqual((self.paper/'main.tex').read_text(), 'reviewed manuscript source')

    def test_source_guard_rejects_reviewed_source_drift(self):
        with mock.patch.object(watch, 'branch_guard'), mock.patch.object(watch, 'git', return_value='fixture-origin'), \
             mock.patch.object(watch, 'source_snapshot', return_value={'main.tex':'changed'}):
            with self.assertRaisesRegex(RuntimeError, 'sources changed'):
                self.watcher.guard()

    def test_pdf_validation_records_pending_visual_review_and_main_pages(self):
        import fitz
        source, output = self.root/'fixture.pdf', self.root/'validated.pdf'
        with fitz.open() as document:
            document.new_page().insert_text((72,72), 'CONCLUSION\nFixture main text')
            document.new_page().insert_text((72,72), 'REPRODUCIBILITY STATEMENT\nFixture appendix')
            document.save(source)
        receipt = watch.validate_pdf(source, output, manuscript=True)
        self.assertEqual(receipt['pages'], 2)
        self.assertEqual(receipt['main_text_pages'], 1)
        self.assertEqual(receipt['visual_review'], watch.VISUAL_REVIEW)
        self.assertFalse(receipt['submission_ready'])
        with fitz.open(output) as document:
            self.assertIn(watch.VISUAL_REVIEW, document.metadata['subject'])

    def test_cpu_build_uses_frozen_compiler_and_fontconfig(self):
        source = Path('fixture.tex')
        (self.paper/source).write_text('fixture')
        out = self.root/'build'
        def fake_command(argv, **kwargs):
            if '--version' in argv:
                return 'Tectonic 0.16.0'
            out.mkdir(exist_ok=True)
            (out/'validated.pdf').write_bytes(b'fixture')
            return 'fixture compilation'
        real_digest = watch.digest
        def fixture_digest(path):
            return watch.TECTONIC_SHA256 if path == self.args.tectonic else real_digest(path)
        with mock.patch.object(watch, 'command', side_effect=fake_command) as run, \
             mock.patch.object(watch, 'digest', side_effect=fixture_digest), \
             mock.patch.object(watch, 'validate_pdf', return_value={'visual_review':watch.VISUAL_REVIEW}):
            self.watcher.compile(source, self.paper, out)
        env = run.call_args.kwargs['env']
        self.assertEqual(env['CUDA_VISIBLE_DEVICES'], '')
        self.assertEqual(env['FONTCONFIG_FILE'], str(self.args.fontconfig/'fonts.conf'))
        self.assertIn('--only-cached', run.call_args.args[0])


if __name__ == '__main__':
    unittest.main()
