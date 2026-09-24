"""Read-only training watcher and opt-in comparison-branch artifact delivery.

This program never launches, retries, repairs, or stops training/evaluation. It
reads the existing queue, invokes only the separate read-only comparison
publisher, and builds CPU-only branch drafts. Run --once for an initial manual
review; commit reviewed sources/artifacts before starting --detach --deliver.
Live heartbeat/ownership state stays in BASE/.comparison_watch, outside Git.
Only explicitly listed generated comparison artifacts may be committed/pushed.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

PAPER = Path(__file__).resolve().parents[1]
BRANCH = 'comparison/public-harness-20260924'
ANCHOR = '676660d'
TECTONIC = Path('/liziqing/yukai/project_collab_auto_research_cell_federated/.tools/tectonic-0.16.0/tectonic')
TECTONIC_SHA256 = 'a6e1ebaba90536e527f2ecd47775a608d9a56bd584efa9f7eee25c1bc7b86349'
FONTCONFIG = Path('/liziqing/yukai/.local/opt/fontconfig/etc/fonts')
FONT_CACHE = Path('/liziqing/yukai/.cache/tectonic/bundles/data/6ffe055852f8faf66c0acbe1a7fb27f87b869a90bad1204f3bf4d9683f597c7c')
TABLE_DIR = Path('tables/public_harness_comparison')
TABLE_NAMES = ('main_public_harness_seed42.tex', 'main_public_harness_three_seed.tex',
               'completion_public_harness.tex', 'results_public_harness.tex', 'snapshot_comparison.json',
               'compact_repair_seed42.tex', 'snapshot_compact_repair.json')
REPORT_TEX = Path('public-harness-comparison.tex')
REPORT_PDF = Path('output/pdf/public-harness-comparison.pdf')
REPORT_RECEIPT = Path('output/pdf/public-harness-comparison.build.json')
MANUSCRIPT_PDF = Path('output/pdf/BioCoLoop_public_harness_branch.pdf')
MANUSCRIPT_RECEIPT = Path('output/pdf/BioCoLoop_public_harness_branch.build.json')
MILESTONE_RECEIPT = Path('provenance/public_harness_comparison/delivery_status.json')
ALLOWLIST = tuple(str(TABLE_DIR / name) for name in TABLE_NAMES) + tuple(map(str, (
    REPORT_TEX, REPORT_PDF, REPORT_RECEIPT, MANUSCRIPT_PDF, MANUSCRIPT_RECEIPT, MILESTONE_RECEIPT)))
VISUAL_REVIEW = 'VISUAL_REVIEW_PENDING'


def read(path):
    return json.loads(Path(path).read_text())


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def atomic_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def command(argv, *, cwd, env=None, timeout=300):
    return subprocess.run(list(map(str, argv)), cwd=cwd, env=env, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          check=True, timeout=timeout).stdout


def git(paper, *args):
    return command(['git', *args], cwd=paper, timeout=120).strip()


def branch_guard(paper):
    if Path(git(paper, 'rev-parse', '--show-toplevel')).resolve() != paper.resolve():
        raise RuntimeError('Expected the paper repository itself, not a parent repository')
    if git(paper, 'branch', '--show-current') != BRANCH:
        raise RuntimeError('Refusing to write or deliver outside ' + BRANCH)
    git(paper, 'merge-base', '--is-ancestor', ANCHOR, 'HEAD')


def safe_artifact(paper, relative):
    if relative not in ALLOWLIST:
        raise RuntimeError('Artifact is not in the dedicated comparison allowlist: ' + relative)
    path = paper / relative
    if path.is_symlink() or any(p.is_symlink() for p in path.parents if p != paper and paper in p.parents):
        raise RuntimeError('Generated artifact path is a symlink: ' + relative)
    if not path.resolve().is_relative_to(paper.resolve()):
        raise RuntimeError('Artifact escapes the paper repository')
    return path


def source_snapshot(paper):
    """Pin reviewed static manuscript and watcher/publisher sources, not previews."""
    names = git(paper, 'ls-files', '-z').split('\0')
    paths = []
    for name in names:
        if not name or name in ALLOWLIST or name.startswith(('tables/public_harness_preview/', 'tmp/', 'output/')):
            continue
        path = paper / name
        if path.suffix in {'.tex', '.bib', '.sty', '.cls', '.otf', '.ttf'} or name.startswith('assets/'):
            paths.append(path)
    paths += [paper / 'tools' / name for name in
              ('watch_public_harness_comparison.py', 'publish_public_harness_comparison.py',
               'publish_public_harness_repair.py')]
    return {str(path.relative_to(paper)): digest(path) for path in sorted(set(paths))}


@contextmanager
def watcher_lock(folder):
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / 'watch.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def terminal_fingerprint(base, matrix, supervisor):
    """Hash only terminal receipts, never every fit/model call on each poll."""
    receipts = {}
    for job in matrix:
        run = base / job['harness'] / job['task'] / ('seed' + str(job['seed']))
        status_path = run / 'run_status.json'
        status = read(status_path) if status_path.exists() else {}
        if status.get('status') in {'FAILED', 'DEVELOPMENT_COMPLETE'}:
            receipts[str(status_path)] = digest(status_path)
            definition = run / 'development/definition.json'
            if definition.exists():
                receipts[str(definition)] = digest(definition)
        verification = run / 'heldout/verification.json'
        if verification.exists() and read(verification).get('status') == 'PASS':
            for name in ('verification.json', 'results.json', 'seal.json', 'audit.json'):
                path = run / 'heldout' / name
                receipts[str(path)] = digest(path)
    terminal_queue = None
    if supervisor.get('status') != 'RUNNING':
        terminal_queue = {key: supervisor.get(key) for key in ('status', 'current_job', 'error_type', 'error')}
    for repair in (base.parent/'compact_repair_v1',base.parent/'compact_repair_v2'):
        manifest_path=repair/'queue_manifest.json'
        if manifest_path.exists():receipts[str(manifest_path)]=digest(manifest_path)
        for path in repair.glob('ai_researcher/*/seed42/heldout/verification.json'):
            receipts[str(path)] = digest(path)
        for path in repair.glob('ai_researcher/*/seed42/run_status.json'):
            if read(path).get('status') in {'FAILED','DEVELOPMENT_COMPLETE'}:
                receipts[str(path)] = digest(path)
    return hashlib.sha256(json_bytes(dict(receipts=receipts, terminal_queue=terminal_queue))).hexdigest()


def repair_base(base):
    # Version choice is fixed by registration, never by held-out performance.
    v2=base.parent/'compact_repair_v2'
    return v2 if (v2/'queue_manifest.json').exists() else base.parent/'compact_repair_v1'


def supervisor_alive(supervisor, base):
    """Read /proc only; never signal a supervisor or child."""
    pid = supervisor.get('pid')
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        stat = Path(f'/proc/{pid}/stat').read_text().rsplit(') ', 1)[1].split()
        argv = [v.decode(errors='replace') for v in Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0') if v]
    except (FileNotFoundError, ProcessLookupError):
        return False
    if stat[0] == 'Z' or not any(Path(arg).name == 'supervise.py' for arg in argv):
        return False
    return '--base' in argv and argv.index('--base') + 1 < len(argv) and Path(argv[argv.index('--base')+1]).resolve() == base.resolve()


def queue_observation(base, manifest, supervisor, *, now=None):
    now = time.time() if now is None else now
    deadline = manifest['created_unix'] + manifest['max_wall_hours'] * 3600
    state = supervisor.get('status')
    outcome, action_needed = 'PENDING', False
    if state in {'COMPLETE', 'FINISHED_WITH_INCOMPLETE_RUNS'}:
        outcome = 'SUPERVISOR_FINISHED'
    elif state != 'RUNNING':
        if supervisor.get('error_type') == 'TimeoutError':
            outcome = 'BUDGET_EXHAUSTED'
        else:
            outcome = 'STOPPED_INFRASTRUCTURE_OR_UNEXPECTED'
        action_needed = True
    elif not supervisor_alive(supervisor, base):
        outcome, action_needed = 'SUPERVISOR_NOT_RUNNING', True
    elif now - supervisor.get('updated_unix', 0) > 300:
        outcome, action_needed = 'SUPERVISOR_HEARTBEAT_STALE', True
    job = supervisor.get('current_job')
    progress = None
    if job:
        run = base / job['harness'] / job['task'] / ('seed' + str(job['seed']))
        candidates = list((run / 'development/fits').glob('*/progress.json'))
        if candidates:
            path = max(candidates, key=lambda p: p.stat().st_mtime)
            progress = dict(path=str(path), modified_unix=path.stat().st_mtime, receipt=read(path))
    return dict(schema='public-harness-comparison-heartbeat-v1', watcher_pid=os.getpid(),
                updated_unix=now, status=outcome, action_needed=action_needed,
                supervisor_status=state, supervisor_pid=supervisor.get('pid'),
                current_job=job, phase=supervisor.get('phase'), current_fit=progress,
                reserved_gpu_hours=supervisor.get('reserved_gpu_hours'),
                max_gpu_hours=manifest['max_gpu_hours'], deadline_unix=deadline,
                remaining_wall_seconds=max(0., deadline-now),
                supervisor_error_type=supervisor.get('error_type'), supervisor_error=supervisor.get('error'),
                training_mutations=False)


def milestone_names(snapshot, observation):
    names = []
    if snapshot.get('seed42_comparison_resolved'):
        names.append('seed42_resolved')
    if snapshot.get('comparison_resolved'):
        names.append('all30_resolved')
    if observation['action_needed']:
        names.append('stopped_terminal')
    return names


def report_source():
    return r'''% Dedicated comparison report; not a replacement for the manuscript.
\documentclass{article}
\usepackage{iclr2027_conference}
\usepackage{amsmath,booktabs,tabularx,array,fontspec}
\setmainfont{texgyretermes-regular.otf}[Path=fonts/,BoldFont=texgyretermes-bold.otf,ItalicFont=texgyretermes-italic.otf,BoldItalicFont=texgyretermes-bolditalic.otf]
\title{BioCoLoop: Public-Harness Comparison}
\author{}
\date{}
\begin{document}
\maketitle
\noindent\textbf{Comparison branch draft.} Public frameworks use task-adapted
native experimental controllers and the common biological fitting interface.
The tables distinguish verified prediction scores, execution failures and
pending runs. Automatic updates await visual review before mainline delivery.
\input{tables/public_harness_comparison/results_public_harness.tex}
\input{tables/public_harness_comparison/completion_public_harness.tex}
\clearpage
\input{tables/public_harness_comparison/main_public_harness_seed42.tex}
\clearpage
\input{tables/public_harness_comparison/main_public_harness_three_seed.tex}
\clearpage
\section*{Task-transport repair}
This separate study removes repeated task packets from stage prompts and
accepts compatible single-tool envelopes. Scientific budgets are unchanged.
\input{tables/public_harness_comparison/compact_repair_seed42.tex}
\end{document}
'''.encode()


def validate_pdf(path, output, *, manuscript=False):
    import fitz
    with fitz.open(path) as document:
        if document.page_count < 1 or document.is_encrypted:
            raise RuntimeError('Missing or encrypted compiled PDF')
        texts = []
        for page in document:
            text = page.get_text()
            if not text.strip() or '\ufffd' in text:
                raise RuntimeError('Empty page or replacement glyph in compiled PDF')
            if list(page.annots() or []):
                raise RuntimeError('Unexpected PDF review annotations')
            pixmap = page.get_pixmap(matrix=fitz.Matrix(1, 1), alpha=False)
            if pixmap.width <= 0 or pixmap.height <= 0:
                raise RuntimeError('PDF page failed CPU raster validation')
            texts.append(text)
        main_pages = None
        if manuscript:
            reproducibility = [i+1 for i, text in enumerate(texts) if re.search(r'REPRODUCIBILITY\s+STATEMENT', text, re.I)]
            conclusion = [i+1 for i, text in enumerate(texts) if re.search(r'\bCONCLUSION\b', text)]
            main_pages = min(reproducibility)-1 if reproducibility else max(conclusion, default=None)
        metadata = dict(document.metadata)
        metadata.update(author='', subject='Comparison branch draft; ' + VISUAL_REVIEW,
                        keywords=VISUAL_REVIEW + '; NOT_SUBMISSION_READY')
        document.set_metadata(metadata)
        document.save(output, garbage=4, deflate=True)
        return dict(pdf_sha256=digest(output), pages=len(texts), text_characters=sum(map(len, texts)),
                    cpu_raster_pages=len(texts), main_text_pages=main_pages,
                    main_text_page_check=('UNKNOWN' if main_pages is None else
                        'OVER_9_DRAFT_WARNING' if main_pages > 9 else 'WITHIN_9'),
                    visual_review=VISUAL_REVIEW, submission_ready=False)


class Watcher:
    def __init__(self, args):
        self.args = args
        self.paper = args.paper.resolve()
        self.base = args.base.resolve()
        self.folder = self.base / '.comparison_watch'
        self.state_path = self.folder / 'state.json'
        self.state = {}

    def save(self):
        atomic_write(self.state_path, json_bytes(self.state))

    def guard(self, *, sources=True):
        branch_guard(self.paper)
        if self.state and git(self.paper, 'remote', 'get-url', 'origin') != self.state['origin']:
            raise RuntimeError('Registered delivery remote changed')
        if self.state and digest(self.base / 'queue_manifest.json') != self.state['queue_manifest_sha256']:
            raise RuntimeError('Frozen queue manifest changed')
        if sources and self.state and source_snapshot(self.paper) != self.state['source_sha256']:
            raise RuntimeError('Reviewed manuscript or monitor/publisher sources changed')
        for relative, expected in self.state.get('owned_sha256', {}).items():
            path = safe_artifact(self.paper, relative)
            actual = digest(path) if path.exists() else None
            if actual != expected:
                raise RuntimeError('User/unowned edit detected; refusing overwrite/staging: ' + relative)

    def initialize(self):
        branch_guard(self.paper)
        if self.state_path.exists():
            self.state = read(self.state_path)
            if self.state['base'] != str(self.base) or self.state['paper'] != str(self.paper):
                raise RuntimeError('Watcher identity changed')
            if self.state['deliver_enabled'] != self.args.deliver:
                raise RuntimeError('Delivery authorization must match the watcher registration on resume')
            self.guard()
            return
        if git(self.paper, 'diff', '--cached', '--name-only'):
            raise RuntimeError('User-staged changes exist; refusing ownership registration')
        owned = {}
        for relative in ALLOWLIST:
            path = safe_artifact(self.paper, relative)
            if path.exists():
                try:
                    expected = git(self.paper, 'rev-parse', 'HEAD:' + relative)
                except subprocess.CalledProcessError as exc:
                    raise RuntimeError('Untracked artifact collision; review/commit it first: ' + relative) from exc
                if git(self.paper, 'hash-object', '--', relative) != expected:
                    raise RuntimeError('Dirty artifact collision; review/commit it first: ' + relative)
            owned[relative] = digest(path) if path.exists() else None
        self.state = dict(schema='public-harness-comparison-watch-v1', base=str(self.base), paper=str(self.paper),
            branch=BRANCH, origin=git(self.paper, 'remote', 'get-url', 'origin'),
            queue_manifest_sha256=digest(self.base/'queue_manifest.json'), source_sha256=source_snapshot(self.paper),
            owned_sha256=owned, deliver_enabled=self.args.deliver, delivered_milestones=[],
            last_fingerprint=None, last_snapshot=None, pending_push=None, created_unix=time.time())
        self.save()

    def install(self, relative, data):
        self.guard(sources=False)
        path = safe_artifact(self.paper, relative)
        atomic_write(path, data)
        self.state['owned_sha256'][relative] = digest(path)
        self.save()

    def compile(self, source, cwd, output_dir, *, manuscript=False):
        # This registered legacy CLI has no --version flag. Pin the actual
        # executable instead of relying on an unsupported CLI version query.
        if digest(self.args.tectonic) != TECTONIC_SHA256:
            raise RuntimeError('Expected the registered Tectonic executable hash')
        version = 'Tectonic 0.16.0; sha256=' + TECTONIC_SHA256
        env = dict(os.environ, FONTCONFIG_FILE=str(self.args.fontconfig/'fonts.conf'),
                   FONTCONFIG_PATH=str(self.args.fontconfig), CUDA_VISIBLE_DEVICES='')
        output_dir.mkdir(parents=True, exist_ok=True)
        try:
            log = command([self.args.tectonic, '--only-cached', '-Z', 'search-path=' + str(FONT_CACHE),
                           '--keep-logs', '--outdir', output_dir, source],
                          cwd=cwd, env=env, timeout=600)
        except subprocess.CalledProcessError as exc:
            atomic_write(output_dir/'watch_build.log', (exc.stdout or '').encode())
            raise
        atomic_write(output_dir/'watch_build.log', log.encode())
        validated = output_dir/'validated.pdf'
        receipt = validate_pdf(output_dir/(Path(source).stem + '.pdf'), validated, manuscript=manuscript)
        receipt.update(built_unix=time.time(), compiler=version.strip(), source_sha256=digest(cwd/source),
                       warnings=re.findall(r'^.*(?:Overfull|Underfull|undefined|Missing character).*$', log, re.M),
                       manuscript_sources=self.state['source_sha256'] if manuscript else None)
        return validated.read_bytes(), receipt

    def publish(self, observation):
        self.guard()
        staging = Path(tempfile.mkdtemp(prefix='publication_', dir=self.folder))
        output = staging/TABLE_DIR
        env = dict(os.environ, CUDA_VISIBLE_DEVICES='')
        log = command([sys.executable, '-B', self.paper/'tools/publish_public_harness_comparison.py',
                       '--base', self.base, '--output-dir', output], cwd=self.paper, env=env, timeout=600)
        atomic_write(staging/'publisher.log', log.encode())
        repair_log = command([sys.executable, '-B', self.paper/'tools/publish_public_harness_repair.py',
                              '--base', repair_base(self.base), '--output-dir', output],
                             cwd=self.paper, env=env, timeout=600)
        atomic_write(staging/'repair_publisher.log', repair_log.encode())
        if {path.name for path in output.iterdir()} != set(TABLE_NAMES):
            raise RuntimeError('Unexpected comparison publisher output set')
        snapshot = read(output/'snapshot_comparison.json')
        repair_snapshot = read(output/'snapshot_compact_repair.json')
        for key in ('comparison_resolved', 'scores_complete', 'seed42_comparison_resolved', 'seed42_scores_complete'):
            if not isinstance(snapshot.get(key), bool):
                raise RuntimeError('Missing typed publisher completion flag: ' + key)
        (staging/'fonts').symlink_to(self.paper/'fonts', target_is_directory=True)
        (staging/'iclr2027_conference.sty').symlink_to(self.paper/'iclr2027_conference.sty')
        atomic_write(staging/REPORT_TEX, report_source())
        pdf, receipt = self.compile(REPORT_TEX, staging, staging/'build')
        receipt.update(snapshot_sha256=digest(output/'snapshot_comparison.json'),
                       comparison_resolved=snapshot['comparison_resolved'], scores_complete=snapshot['scores_complete'])
        self.guard()
        for name in TABLE_NAMES:
            self.install(str(TABLE_DIR/name), (output/name).read_bytes())
        self.install(str(REPORT_TEX), report_source())
        self.install(str(REPORT_PDF), pdf)
        self.install(str(REPORT_RECEIPT), json_bytes(receipt))
        milestones = milestone_names(snapshot, observation)
        if repair_snapshot.get('resolved'):
            milestones.append('compact_repair_resolved')
        if any(name in milestones and name not in self.state['delivered_milestones']
               for name in ('seed42_resolved', 'all30_resolved', 'compact_repair_resolved')):
            self.guard()
            build_parent = self.paper/'tmp/pdfs/public_harness_manuscript'
            build_parent.mkdir(parents=True, exist_ok=True)
            build_dir = Path(tempfile.mkdtemp(prefix='watch_', dir=build_parent))
            main_pdf, main_receipt = self.compile(Path('main.tex'), self.paper, build_dir, manuscript=True)
            main_receipt.update(snapshot_sha256=digest(self.paper/TABLE_DIR/'snapshot_comparison.json'))
            self.install(str(MANUSCRIPT_PDF), main_pdf)
            self.install(str(MANUSCRIPT_RECEIPT), json_bytes(main_receipt))
        self.state['last_snapshot'] = {key:snapshot[key] for key in
            ('comparison_resolved', 'scores_complete', 'seed42_comparison_resolved', 'seed42_scores_complete')}
        self.state['last_snapshot']['completion'] = snapshot.get('completion')
        self.state['last_snapshot']['repair_resolved'] = repair_snapshot.get('resolved',False)
        self.state['last_snapshot']['repair_scored'] = repair_snapshot.get('scored',0)
        self.save()
        return snapshot

    def delivery(self, milestones, observation):
        todo = [name for name in milestones if name not in self.state['delivered_milestones']]
        if not todo or not self.args.deliver:
            return
        self.guard()
        if git(self.paper, 'diff', '--cached', '--name-only'):
            raise RuntimeError('User-staged changes exist; refusing checkpoint staging')
        if self.state.get('pending_push'):
            pending = self.state['pending_push']
            if git(self.paper, 'rev-parse', 'HEAD') != pending['commit']:
                raise RuntimeError('Branch moved after an unpushed watcher checkpoint')
            git(self.paper, 'push', 'origin', 'HEAD:refs/heads/' + BRANCH)
            self.state['delivered_milestones'] += pending['milestones']
            self.state['pending_push'] = None
            self.save()
            return
        receipt = dict(schema='public-harness-comparison-delivery-v1', milestones=todo,
                       observation=observation, snapshot=self.state['last_snapshot'], visual_review=VISUAL_REVIEW,
                       submission_ready=False, branch=BRANCH,
                       artifact_sha256={p:h for p,h in self.state['owned_sha256'].items() if h and p != str(MILESTONE_RECEIPT)})
        self.install(str(MILESTONE_RECEIPT), json_bytes(receipt))
        self.guard()
        if git(self.paper, 'diff', '--cached', '--name-only'):
            raise RuntimeError('Index changed before checkpoint staging')
        paths = [p for p in ALLOWLIST if self.state['owned_sha256'][p] is not None]
        git(self.paper, 'add', '-f', '--', *paths)
        staged = set(git(self.paper, 'diff', '--cached', '--name-only').splitlines())
        if not staged <= set(paths):
            raise RuntimeError('Concurrent user staging detected; do not commit or unstage their changes')
        self.guard()
        git(self.paper, 'commit', '--only', '-m', 'Checkpoint public-harness comparison: ' + ', '.join(todo), '--', *paths)
        self.state['pending_push'] = dict(commit=git(self.paper, 'rev-parse', 'HEAD'), milestones=todo)
        self.save()
        self.guard()
        git(self.paper, 'push', 'origin', 'HEAD:refs/heads/' + BRANCH)
        self.state['delivered_milestones'] += todo
        self.state['pending_push'] = None
        self.save()

    def tick(self):
        self.guard(sources=False)
        manifest = read(self.base/'queue_manifest.json')
        supervisor = read(self.base/'supervisor_status.json')
        observation = queue_observation(self.base, manifest, supervisor)
        repair_status_path = repair_base(self.base)/'supervisor_status.json'
        if repair_status_path.exists():
            repair_status = read(repair_status_path)
            observation['compact_repair'] = {key:repair_status.get(key) for key in
                ('status','phase','current_job','reserved_gpu_hours','completed','failed','error')}
        atomic_write(self.folder/'heartbeat.json', json_bytes(observation))
        fingerprint = terminal_fingerprint(self.base, manifest['jobs'], supervisor)
        # A dead/stale RUNNING supervisor is terminal to this read-only monitor.
        fingerprint += ':' + observation['status'] if observation['action_needed'] else ''
        if fingerprint != self.state['last_fingerprint']:
            snapshot = self.publish(observation)
            self.state['last_fingerprint'] = fingerprint
            self.save()
        else:
            snapshot = self.state['last_snapshot']
        if observation['status'] == 'SUPERVISOR_FINISHED' and not snapshot['comparison_resolved']:
            observation.update(status='SUPERVISOR_FINISHED_WITH_PENDING_JOBS', action_needed=True)
        milestones = milestone_names(snapshot, observation)
        if (self.state.get('last_snapshot') or {}).get('repair_resolved'):
            milestones.append('compact_repair_resolved')
        self.delivery(milestones, observation)
        observation.update(comparison_resolved=snapshot['comparison_resolved'], scores_complete=snapshot['scores_complete'],
                           last_terminal_fingerprint=self.state['last_fingerprint'],
                           delivered_milestones=self.state['delivered_milestones'])
        atomic_write(self.folder/'heartbeat.json', json_bytes(observation))
        if observation['action_needed']:
            return 2 if observation['status'] == 'BUDGET_EXHAUSTED' else 1
        if snapshot['comparison_resolved'] and supervisor.get('status') in {'COMPLETE', 'FINISHED_WITH_INCOMPLETE_RUNS'}:
            return 0
        return None

    def run(self):
        with watcher_lock(self.folder):
            try:
                self.initialize()
                while True:
                    result = self.tick()
                    if result is not None or self.args.once:
                        return result or 0
                    time.sleep(self.args.poll_seconds)
            except Exception as exc:
                atomic_write(self.folder/'heartbeat.json', json_bytes(dict(
                    schema='public-harness-comparison-heartbeat-v1', watcher_pid=os.getpid(), updated_unix=time.time(),
                    status='ACTION_NEEDED', action_needed=True, error_type=type(exc).__name__, error=str(exc),
                    training_mutations=False)))
                raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--paper', type=Path, default=PAPER)
    parser.add_argument('--tectonic', type=Path, default=TECTONIC)
    parser.add_argument('--fontconfig', type=Path, default=FONTCONFIG)
    parser.add_argument('--poll-seconds', type=float, default=60.)
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--deliver', action='store_true', help='Authorize exact allowlisted milestone commits and non-force branch pushes')
    parser.add_argument('--detach', action='store_true')
    args = parser.parse_args()
    if args.poll_seconds < 60:
        parser.error('Polling interval must be at least 60 seconds')
    if args.once and args.detach:
        parser.error('--once and --detach are mutually exclusive')
    if args.detach:
        folder = args.base.resolve()/'.comparison_watch'
        folder.mkdir(parents=True, exist_ok=True)
        argv = [sys.executable, '-B', str(Path(__file__).resolve()), '--base', str(args.base.resolve()),
                '--paper', str(args.paper.resolve()), '--tectonic', str(args.tectonic),
                '--fontconfig', str(args.fontconfig), '--poll-seconds', str(args.poll_seconds)]
        if args.deliver:
            argv.append('--deliver')
        with (folder/'watch.log').open('ab') as log:
            process = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT,
                                       stdin=subprocess.DEVNULL, start_new_session=True)
        print(json.dumps(dict(watcher_pid=process.pid, heartbeat=str(folder/'heartbeat.json'))))
        return 0
    return Watcher(args).run()


if __name__ == '__main__':
    raise SystemExit(main())
