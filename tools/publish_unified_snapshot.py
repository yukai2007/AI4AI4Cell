"""Publish a role-separated manuscript snapshot, never substituting legacy scores.

Reads aggregate result JSON only. Held-out publication requires complete sealed,
independently verified six-arm evaluations; development never fills test cells.
"""
from pathlib import Path
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import statistics

PAPER = Path(__file__).resolve().parents[1]
TASKS = [('native_dti', 'DTI'), ('ptpc', 'Proteomics'), ('vcc_pilot', 'VCC'),
         ('norman_double_pilot', 'Norman'), ('tahoe_drug_pilot', 'Tahoe')]
ARMS = [('single_fixed', '1', 'Fixed model'), ('single_direct', '1', 'Direct'),
        ('single_loop', '1', 'Our loop'), ('federated_fixed', '10', 'Fixed model'),
        ('federated_direct', '10', 'Direct'), ('federated_loop', '10', 'Our loop')]
MAIN_ARMS = [('single_fixed', '1', 'Fixed model'),
             ('single_direct', '1', 'Direct optimize'),
             ('federated_loop', '10', 'Our harness')]
HELDOUT_ROLE = 'retrospective held-out; prior historical exposure; not blind confirmation'
CONTRASTS = [('Loop $-$ direct (1 lab)', 'single_loop', 'single_direct'),
             ('Loop $-$ direct (10 labs)', 'federated_loop', 'federated_direct'),
             ('10 $-$ 1 labs (both fixed)', 'federated_fixed', 'single_fixed'),
             ('10 $-$ 1 labs (both direct)', 'federated_direct', 'single_direct'),
             ('10 $-$ 1 labs (both loop)', 'federated_loop', 'single_loop')]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect(root):
    audit = json.loads((root/'audit_v3.json').read_text())
    snapshot = dict(snapshot_utc=datetime.now(timezone.utc).isoformat(), protocol='unified_v3',
                    seeds=[42, 43, 44], evaluation_role='post-selection common development',
                    final_test_scored=False, tasks={})
    for task, label in TASKS:
        item = dict(label=label, runs={}, final_test=None)
        for seed in snapshot['seeds']:
            path = root/task/f'study_v3_seed{seed}'
            if audit.get(f'{task}/seed{seed}', {}).get('status') != 'PASS':
                item['runs'][str(seed)] = None
                continue
            status = json.loads((path/'status.json').read_text())
            assert status['status'] == 'DEVELOPMENT_COMPLETE'
            report = json.loads((path/'common_development_report.json').read_text())
            definition = json.loads((path/'definition.json').read_text())
            assert definition['rounds'] == 100 and definition['slots'] == 6 and definition['seed'] == seed
            assert definition['test_read'] is False
            scores = {}
            for arm, _, _ in ARMS:
                value = report[arm]
                metrics = value['per_client'][0]['metrics']
                keys = ([k for k in ['auroc', 'average_precision', 'mcc', 'accuracy', 'log_loss'] if k in metrics]
                        if task == 'native_dti' else ['ap', 'auroc', 'bce', 'accuracy_at_0_5'] if task == 'ptpc'
                        else ['macro_accuracy', 'accuracy', 'mrr', 'top3', 'cross_entropy'])
                scores[arm] = dict(primary=value['aggregate']['primary'], loss=value['aggregate']['loss'],
                    secondary={k: statistics.mean(c['metrics'][k] for c in value['per_client']) for k in keys})
            receipts = {f'{task}/study_v3_seed{seed}/{f}': sha(path/f) for f in
                        ['definition.json', 'status.json', 'selected_development.json', 'common_development_report.json', 'effects.json']}
            item['runs'][str(seed)] = dict(scores=scores, receipts=receipts, definition=definition,
                physical_fits=len(list((path/'fits').glob('*/fit.json'))))
        snapshot['tasks'][task] = item
    snapshot['heldout'] = collect_heldout(root/'heldout_v3')
    snapshot['final_test_scored'] = any(heldout_runs(snapshot['heldout'], task) for task, _ in TASKS)
    snapshot['blind_confirmatory_test_scored'] = False
    return snapshot


def collect_heldout(root):
    """Consume verified frozen evaluations, never select on their outcomes."""
    root = Path(root).resolve()
    ledger = root/'summary.json'
    summary = json.loads(ledger.read_text()) if ledger.exists() else {}
    seeds = summary.get('seeds_requested', [42, 43, 44])
    heldout = dict(role=HELDOUT_ROLE, seeds_requested=seeds, tasks={},
                   summary_sha256=sha(ledger) if ledger.exists() else None)
    if summary and summary['role'] != HELDOUT_ROLE:
        raise ValueError('Unexpected held-out role; do not silently relabel evaluation')
    for task, label in TASKS:
        if task == 'native_dti':
            heldout['tasks'][task] = collect_native_dti(root, seeds)
            continue
        item = dict(label='PTPC (linear)' if task == 'ptpc' else label,
                    runs={str(s): None for s in seeds})
        registered = summary.get('tasks', {}).get(task, {})
        for seed in registered.get('completed_seeds', []):
            assert seed in seeds
            path = root/task/f'seed{seed}'
            names = ['results.json', 'verification.json', 'audit.json', 'seal.json']
            if not all((path/f).exists() for f in names):
                continue
            result, verification, audit, seal = [json.loads((path/f).read_text()) for f in names]
            if not all(arm in result.get('results', {}) for arm, _, _ in ARMS):
                continue  # A pending arm keeps the entire paired seed unpublished.
            assert result['schema'] == 'unified-v3-heldout-results-v1'
            assert result['task'] == seal['task'] == verification['task'] == task
            assert result['seed'] == seal['seed'] == verification['seed'] == seed
            assert result['role'] == seal['role'] == HELDOUT_ROLE
            assert result['feedback_to_controller'] is seal['feedback_to_controller'] is False
            assert verification['status'] == audit['status'] == 'PASS'
            assert all(verification[k] is True for k in
                       ['seal_before_response_access', 'all_checkpoint_hashes_match', 'common_original_roster'])
            assert all(audit[k] is True for k in
                       ['original_scorer', 'common_roster_all_arms', 'no_test_checkpoint_selection', 'no_controller_feedback'])
            assert result['seal_sha256'] == sha(path/'seal.json')
            assert seal['sealed_unix'] <= result['heldout_decoded_unix'] <= result['completed_unix']
            definition = seal['definition']
            assert definition['rounds'] == 100 and definition['slots'] == 6
            assert definition['seed'] == seed and definition['test_read'] is False
            if task == 'ptpc':
                assert 'linear' in seal['predictor'] and 'NOT native ProteinTalks' in seal['predictor']
            scores = {}
            for arm, _, _ in ARMS:
                value = result['results'][arm]
                primary = value['primary']
                assert math.isfinite(primary)
                assert abs(primary - registered['arms'][arm]['per_seed'][str(seed)]) < 1e-12
                assert abs(primary - verification['rescored'][arm]['metrics'][result['primary_metric']]) < 1e-12
                assert value['checkpoint'] == seal['arms'][arm]['checkpoint']
                scores[arm] = dict(primary=primary, secondary=value['metrics'],
                                   checkpoint=seal['arms'][arm])
            item['runs'][str(seed)] = dict(scores=scores, predictor=seal['predictor'],
                primary_metric=result['primary_metric'], uncertainty=result['uncertainty'],
                receipts={f'{task}/seed{seed}/{f}': sha(path/f) for f in names})
        heldout['tasks'][task] = item
    return heldout


def collect_native_dti(root, seeds):
    """DrugBAN uses its frozen three-endpoint schema, not the cell/head schema.

    Scan the prespecified seeds directly: the historical generic summary only
    enumerates cell/linear tasks. Never rewrite that ledger to inject results.
    """
    item = dict(label='DTI (DrugBAN)', runs={str(s): None for s in seeds})
    arm_names = {arm for arm, _, _ in ARMS}
    for seed in seeds:
        path = root/'native_dti'/f'seed{seed}'
        names = ['results.json', 'verification.json', 'audit.json', 'seal.json']
        if not all((path/name).is_file() for name in names):
            continue
        result, verification, audit, seal = [json.loads((path/name).read_text()) for name in names]
        if set(result.get('results', {})) != arm_names:
            continue
        assert result['schema'] == 'native-dti-v3-heldout-results-v1'
        assert seal['schema'] == 'native-dti-v3-heldout-seal-v1'
        assert verification['schema'] == 'native-dti-independent-verification-v1'
        assert result['task'] == seal['task'] == verification['task'] == 'native_dti'
        assert result['seed'] == seal['seed'] == verification['seed'] == seed
        assert result['role'] == seal['role'] == HELDOUT_ROLE
        assert verification['status'] == audit['status'] == 'PASS'
        assert result['feedback_to_controller'] is seal['feedback_to_controller'] is False
        assert result['primary_endpoint'] == seal['primary_endpoint'] == 'random'
        assert result['primary_metric'] == seal['primary_metric'] == 'auroc'
        assert verification['arms'] == 6 and verification['endpoints'] == 3
        assert all(verification[k] is True for k in ['sealed_before_response_access',
            'all_checkpoint_hashes_match', 'common_original_roster', 'original_scorer'])
        assert all(audit[k] is True for k in ['sealed_before_response_decode',
            'fixed_all_three_endpoints', 'six_arms', 'original_scorer', 'all_inputs_matched_official_featurizer'])
        assert audit['test_checkpoint_selection'] is audit['feedback_to_controller'] is False
        assert verification['feedback_to_controller'] is False
        assert result['seal_sha256'] == verification['seal_sha256'] == sha(path/'seal.json')
        assert verification['results_sha256'] == sha(path/'results.json')
        assert seal['development_completed_unix'] <= seal['sealed_unix'] <= result['heldout_decoded_unix'] <= result['completed_unix']
        definition = seal['definition']
        assert definition['rounds'] == 100 and definition['slots'] == 6
        assert definition['seed'] == seed and definition['test_read'] is False
        assert result['results'] == result['endpoints']['random']
        assert set(result['endpoints']) == {'random', 'unseen_drug', 'unseen_protein'}
        for endpoint, records in result['endpoints'].items():
            assert set(records) == arm_names
            for arm, record in records.items():
                actual = verification['rescored'][f'{endpoint}/{arm}']['metrics']
                assert all(math.isfinite(v) for v in actual.values())
                assert all(abs(actual[k] - record['metrics'][k]) <= 1e-12 for k in actual)
                assert abs(record['primary'] - actual['auroc']) <= 1e-12
                source_arm = record.get('reused_identical_checkpoint', arm)
                assert record['checkpoint'] == seal['arms'][source_arm]['checkpoint']
                assert seal['arms'][source_arm]['checkpoint_sha256'] == seal['arms'][arm]['checkpoint_sha256']
        scores = {arm: dict(primary=record['primary'], secondary=record['metrics'],
                  checkpoint=seal['arms'][arm]) for arm, record in result['results'].items()}
        supplement, supplement_path = None, None
        if (root.parent/'uncertainty_native_dti_v1'/f'seed{seed}.json').exists():
            # Lazy import avoids a module initialization cycle: strong exports
            # share our arm definitions and the same strict sidecar validator.
            from publish_strong_snapshot import tapb_uncertainty
            supplement, supplement_path = tapb_uncertainty(
                root.parent, seed, path, result, seal, task='native_dti')
        receipts = {f'native_dti/seed{seed}/{name}': sha(path/name) for name in names}
        if supplement_path is not None:
            receipts[str(supplement_path)] = sha(supplement_path)
        item['runs'][str(seed)] = dict(scores=scores, predictor='Native DrugBAN; task-trained from random initialization',
            primary_metric='auroc', primary_endpoint='random', endpoints=result['endpoints'],
            uncertainty=supplement['endpoints']['random']['metrics']['auroc'] if supplement else {},
            endpoint_uncertainty=supplement, receipts=receipts)
    return item


def heldout_runs(heldout, task):
    return [r for r in heldout.get('tasks', {}).get(task, {}).get('runs', {}).values() if r is not None]


def metric_stats(runs, arm, key=None):
    values = [r['scores'][arm]['primary'] if key is None else r['scores'][arm]['secondary'][key] for r in runs]
    return (statistics.mean(values), statistics.stdev(values) if len(values) > 1 else None)


def heldout_score_table(heldout, out, full=False):
    arms = ARMS if full else MAIN_ARMS
    lines = [r'\begin{table}[t]', r'\centering\small', r'\setlength{\tabcolsep}{3pt}',
             r'\begin{tabular}{clrrrrr}', r'\toprule',
             r' & & DTI & PTPC (linear) & \multicolumn{3}{c}{Cell perturbation} \\',
             r'\cmidrule(lr){5-7}',
             r'Labs & Method & AUROC & AP & VCC & Norman & Tahoe \\',
             r' & & $\uparrow$ & $\uparrow$ & Top-1 $\uparrow$ & Top-1 $\uparrow$ & Top-1 $\uparrow$ \\',
             r'\midrule']
    for arm, labs, name in arms:
        cells = []
        for task, _ in TASKS:
            runs = heldout_runs(heldout, task)
            if not runs:
                cells.append('N/A'); continue
            mean, sd = metric_stats(runs, arm)
            value = round(100*mean, 2)
            best = max(round(100*metric_stats(runs, a)[0], 2) for a, _, _ in arms)
            text = f'{value:.2f}'
            if value == best:
                text = r'\textbf{'+text+'}'
            if full and sd is not None:
                text += r'{\scriptsize$\pm'+f'{100*sd:.2f}'+r'$}'
            cells.append(text)
        if arm == 'federated_fixed':
            lines.append(r'\midrule')
        lines.append(f'{labs} & {name} & '+' & '.join(cells)+r' \\')
    lines += [r'\midrule', r'\multicolumn{2}{l}{Completed seeds ($n/3$)} & '+' & '.join(
        f'{len(heldout_runs(heldout, t))}/3' for t, _ in TASKS)+r' \\', r'\bottomrule', r'\end{tabular}']
    prefix = ('Six-arm retrospective held-out ablation: mean and sample SD over completed seeds; '
              'no SD is estimated for a single seed. ' if full else
              'Diagnostic comparison of the earlier model versions: retrospective held-out means over completed seeds ($n$ shown). '
              'Fixed and harness-free direct optimization use one laboratory; our harness uses ten. ')
    caption = (prefix+'Scores are multiplied by 100; bold marks all displayed maxima. '
               'PTPC uses the linear comparator, not native ProteinTalks. '
               'These historically exposed endpoints are not blind confirmation. '
               'N/A denotes incomplete paired evaluation; unrun seeds are never imputed.')
    label = 'tab:unified-heldout-ablation' if full else 'tab:unified-final'
    filename = 'heldout_ablation.tex' if full else 'final.tex'
    lines += [r'\caption{'+caption+'}', r'\label{'+label+'}', r'\end{table}']
    (out/filename).write_text('\n'.join(lines)+'\n')


def heldout_effect_table(heldout, out):
    lines = [r'\begin{table}[t]', r'\centering\small', r'\setlength{\tabcolsep}{3pt}',
             r'\begin{tabular}{lrrrrr}', r'\toprule',
             r'Held-out contrast & DTI & PTPC (linear) & VCC & Norman & Tahoe \\', r'\midrule']
    for label, a, b in CONTRASTS:
        cells = []
        for task, _ in TASKS:
            runs = heldout_runs(heldout, task)
            values = [100*(r['scores'][a]['primary']-r['scores'][b]['primary']) for r in runs]
            cells.append(f'{statistics.mean(values):+.2f}' if values else 'N/A')
        lines.append(label+' & '+' & '.join(cells)+r' \\')
    lines += [r'\midrule', 'Completed seeds ($n/3$) & '+' & '.join(
        f'{len(heldout_runs(heldout, t))}/3' for t, _ in TASKS)+r' \\', r'\bottomrule', r'\end{tabular}',
        r'\caption{Separate loop and laboratory-participation effects on held-out data. Entries are mean paired differences in percentage points over the completed seeds shown. Loop versus direct holds participation and search budget fixed; ten versus one laboratory adds locally held data with research mode fixed. Per-seed cluster-bootstrap intervals accompany the current uniform-protocol tables.}',
        r'\label{tab:unified-heldout-effects}', r'\end{table}']
    (out/'heldout_effects.tex').write_text('\n'.join(lines)+'\n')


def heldout_secondary_table(heldout, out):
    lines = [r'\begin{longtable}{llrrrr}',
        r'\caption{Retrospective held-out secondary metrics: means over completed seeds, on each task\textquotesingle s common held-out roster. PTPC is the linear comparator, not native ProteinTalks. Bold marks all displayed maxima, or minima for loss.}\label{tab:unified-heldout-secondary}\\',
        r'\toprule Method & Labs & Metric 1 & Metric 2 & Metric 3 & Metric 4 \\ \midrule\endfirsthead',
        r'\toprule Method & Labs & Metric 1 & Metric 2 & Metric 3 & Metric 4 \\ \midrule\endhead']
    for task, label in TASKS:
        runs = heldout_runs(heldout, task)
        if task == 'ptpc':
            label = 'PTPC (linear)'
            keys = ['ap', 'auroc', 'bce', 'accuracy_at_0_5']; names = ['AP', 'AUROC', 'BCE', 'Acc.']
        elif task == 'native_dti':
            keys = ['auroc', 'average_precision', 'mcc', 'log_loss']; names = ['AUROC', 'AP', 'MCC', 'BCE']
        else:
            keys = ['accuracy', 'mrr', 'top3', 'cross_entropy']; names = ['Micro Top-1', 'MRR', 'Top-3', 'CE']
        lines.append(r'\multicolumn{2}{l}{\textbf{'+label+f' ($n={len(runs)}$)'+r'}} & '+' & '.join(names)+r' \\')
        for arm, labs, name in ARMS:
            cells = []
            for key in keys:
                if not runs:
                    cells.append('N/A'); continue
                value = round(metric_stats(runs, arm, key)[0], 4)
                values = [round(metric_stats(runs, a, key)[0], 4) for a, _, _ in ARMS]
                best = min(values) if key in ['bce', 'log_loss', 'cross_entropy'] else max(values)
                text = f'{value:.4f}'
                cells.append(r'\textbf{'+text+'}' if value == best else text)
            lines.append(f'{name} & {labs} & '+' & '.join(cells)+r' \\')
        lines.append(r'\midrule')
    lines += [r'\bottomrule', r'\end{longtable}']
    (out/'heldout_secondary.tex').write_text('\n'.join(lines)+'\n')


def heldout_uncertainty_table(heldout, out):
    lines = [r'\begin{longtable}{llrrl}',
        r'\caption{Per-seed paired effects on retrospective held-out data (percentage points). Percentile 95\% intervals use the recorded 1,000-replicate paired cluster bootstrap with fixed trained models, not independent-cell resampling or confidence intervals over training seeds. DrugBAN intervals are a post-hoc supplement over frozen random-endpoint predictions, clustered by drug.}\label{tab:unified-heldout-uncertainty}\\',
        r'\toprule Task & Contrast & Seed & Difference & 95\% interval \\ \midrule\endfirsthead',
        r'\toprule Task & Contrast & Seed & Difference & 95\% interval \\ \midrule\endhead']
    effect_keys = ['loop_single', 'loop_federated', 'federation_fixed', 'federation_direct', 'federation_loop']
    for task, label in TASKS:
        if task == 'ptpc': label = 'PTPC (linear)'
        for seed, run in heldout.get('tasks', {}).get(task, {}).get('runs', {}).items():
            if run is None: continue
            if not run.get('uncertainty', {}).get('effects'):
                lines.append(f'{label} & Bootstrap intervals not yet computed & {seed} & N/A & N/A'+r' \\')
                continue
            for (contrast, _, _), key in zip(CONTRASTS, effect_keys):
                effect = run['uncertainty']['effects'][key]
                lo, hi = effect['ci95']
                lines.append(f"{label} & {contrast} & {seed} & {100*effect['difference']:+.2f} & [{100*lo:+.2f}, {100*hi:+.2f}]"+r' \\')
            lines.append(r'\midrule')
    lines += [r'\bottomrule', r'\end{longtable}']
    (out/'heldout_uncertainty.tex').write_text('\n'.join(lines)+'\n')


def snapshot_macros(heldout, out):
    lines = ['% Generated only from verified held-out measurements; never from development scores.',
             '% PTPC macros describe the linear comparator, NOT native ProteinTalks.']
    for task, prefix in [('native_dti', 'DTI'), ('ptpc', 'PTPC'), ('vcc_pilot', 'VCC'),
                         ('norman_double_pilot', 'Norman'), ('tahoe_drug_pilot', 'Tahoe')]:
        runs = heldout_runs(heldout, task)
        values = {'Seeds': str(len(runs))}
        for suffix, arm in [('Fixed', 'single_fixed'), ('Direct', 'single_direct'), ('Harness', 'federated_loop')]:
            values[suffix] = f'{100*metric_stats(runs, arm)[0]:.2f}' if runs else 'N/A'
        for suffix, a, b in [('DeltaDirect', 'federated_loop', 'single_direct'),
                             ('DeltaFixed', 'federated_loop', 'single_fixed'),
                             ('LoopEffect', 'federated_loop', 'federated_direct'),
                             ('FederationEffect', 'federated_loop', 'single_loop')]:
            values[suffix] = (f"{100*statistics.mean(r['scores'][a]['primary']-r['scores'][b]['primary'] for r in runs):+.2f}"
                              if runs else 'N/A')
        values['ThreeSeedHarness'] = values['Harness'] if len(runs) == 3 else 'N/A'
        for suffix, value in values.items():
            lines.append(r'\newcommand{\Heldout'+prefix+suffix+'}{'+value+'}')
    lines.append(r'\newcommand{\NativeProteinTalksThreeSeedResult}{N/A}')
    (out/'snapshot_stats.tex').write_text('\n'.join(lines)+'\n')


def score_table(snapshot, out, final=False, full=False):
    """Main view is a deployment comparison; full=True preserves all controls.

    Maxima are computed among the rows actually displayed. Missing test results
    never inherit development scores, even when all development runs finish.
    """
    if final:
        return heldout_score_table(snapshot.get('heldout', {}), out, full=full)
    arms = ARMS if full else MAIN_ARMS
    lines = [r'\begin{table}[t]', r'\centering\small', r'\setlength{\tabcolsep}{4pt}',
             r'\begin{tabular}{clrrrrr}', r'\toprule',
             r' & & DTI & Proteomics & \multicolumn{3}{c}{Cell perturbation} \\',
             r'\cmidrule(lr){5-7}',
             r'Labs & Method & AUROC & AP & VCC & Norman & Tahoe \\',
             r' & & $\uparrow$ & $\uparrow$ & Top-1 $\uparrow$ & Top-1 $\uparrow$ & Top-1 $\uparrow$ \\', r'\midrule']
    for arm, labs, name in arms:
        values = []
        for task, _ in TASKS:
            run = snapshot['tasks'][task]['runs']['42']
            if run is None:
                values.append('N/A'); continue
            score = round(100*run['scores'][arm]['primary'], 2)
            best = max(round(100*run['scores'][a]['primary'], 2) for a, _, _ in arms)
            cell = f'{score:.2f}'
            values.append(r'\textbf{'+cell+'}' if score == best else cell)
        if arm == 'federated_fixed':
            lines.append(r'\midrule')
        lines.append(f'{labs} & {name} & '+' & '.join(values)+r' \\')
    lines.extend([r'\bottomrule', r'\end{tabular}'])
    if full:
        caption = ('Full six-arm ablation on the common development panel (seed 42). '
                   'Laboratory participation (1 or 10) is crossed with fixed training, feedback-free direct '
                   'optimization and feedback-guided loop research. All primary metrics are multiplied by 100; '
                   'higher is better. Bold marks all displayed column maxima, including ties. '
                   'Missing studies are N/A. These are development measurements, not final-test results.')
        label = 'tab:unified-ablation'
    else:
        caption = ('Diagnostic deployment comparison on common development data (seed 42; scores multiplied by 100, higher is better). '
                   'Fixed and harness-free direct use one laboratory; our harness combines loop research with ten-laboratory participation. '
                   'AUROC/AP are equal-client means; cell scores are intervention-macro Top-1. '
                   'Bold marks all displayed maxima; N/A denotes unfinished evaluation. These are not final-test results.')
        label = 'tab:unified-development'
    lines.extend([r'\caption{'+caption+'}', r'\label{'+label+'}', r'\end{table}'])
    filename = 'final.tex' if final else 'ablation.tex' if full else 'development.tex'
    (out/filename).write_text('\n'.join(lines)+'\n')


def effect_table(snapshot, out):
    lines = [r'\begin{table}[t]', r'\centering\footnotesize', r'\setlength{\tabcolsep}{2.5pt}',
             r'\begin{tabular}{lrrrrr}', r'\toprule',
             r'Development contrast & DTI & Proteomics & VCC & Norman & Tahoe \\', r'\midrule']
    comparisons = [('Loop $-$ direct (1 lab)', 'single_loop', 'single_direct'),
                   ('Loop $-$ direct (10 labs)', 'federated_loop', 'federated_direct'),
                   ('10 $-$ 1 labs (both fixed)', 'federated_fixed', 'single_fixed'),
                   ('10 $-$ 1 labs (both direct)', 'federated_direct', 'single_direct'),
                   ('10 $-$ 1 labs (both loop)', 'federated_loop', 'single_loop')]
    for label, a, b in comparisons:
        cells = []
        for task, _ in TASKS:
            run = snapshot['tasks'][task]['runs']['42']
            cells.append('N/A' if run is None else f"{100*(run['scores'][a]['primary']-run['scores'][b]['primary']):+.2f}")
        lines.append(label+' & '+' & '.join(cells)+r' \\')
    lines.extend([r'\midrule', r'Completed seeds ($n/3$) & '+' & '.join(
        f"{sum(r is not None for r in snapshot['tasks'][t]['runs'].values())}/3" for t, _ in TASKS)+r' \\'])
    for label, a, b in [('3-seed loop $-$ direct', 'federated_loop', 'federated_direct'),
                         ('3-seed access (loop)', 'federated_loop', 'single_loop')]:
        cells = []
        for task, _ in TASKS:
            runs = list(snapshot['tasks'][task]['runs'].values())
            if any(r is None for r in runs):
                cells.append('N/A'); continue
            values = [100*(r['scores'][a]['primary']-r['scores'][b]['primary']) for r in runs]
            cells.append(f'${statistics.mean(values):+.2f}\\pm{statistics.stdev(values):.2f}$')
        lines.append(label+' & '+' & '.join(cells)+r' \\')
    lines.extend([r'\bottomrule', r'\end{tabular}',
        r'\caption{Separate contributions of loop engineering and access to additional laboratory data, in percentage points on the primary metric. Loop versus direct holds participation, candidate budget and selection fixed. Ten versus one laboratory holds the research mode fixed while increasing training data, development evidence and computation; it is not a matched-data optimizer comparison. First-seed development only; zero means a measured tie. Three-seed effects remain N/A until all prespecified runs finish.}',
        r'\label{tab:unified-effects}', r'\end{table}'])
    (out/'effects.tex').write_text('\n'.join(lines)+'\n')


def secondary_table(snapshot, out):
    lines = [r'\begin{longtable}{llrrrr}', r'\caption{Uniform seed-42 common-development secondary metrics. Client means, not pooled predictions. Rankings and uncertainty are not inferred from unrun seeds.}\label{tab:unified-secondary}\\',
             r'\toprule', r'Task / method & Labs & Metric 1 & Metric 2 & Metric 3 & Metric 4 \\', r'\midrule\endfirsthead',
             r'\toprule Task / method & Labs & Metric 1 & Metric 2 & Metric 3 & Metric 4 \\ \midrule\endhead']
    for task, label in TASKS:
        run = snapshot['tasks'][task]['runs']['42']
        if task == 'ptpc':
            keys = ['ap', 'auroc', 'bce', 'accuracy_at_0_5']; names = ['AP', 'AUROC', 'BCE', 'Acc.']
        elif task == 'native_dti':
            keys = ['auroc', 'average_precision', 'mcc', 'log_loss']; names = ['AUROC', 'AP', 'MCC', 'BCE']
        else:
            keys = ['accuracy', 'mrr', 'top3', 'cross_entropy']; names = ['Micro Top-1', 'MRR', 'Top-3', 'CE']
        lines.append(r'\multicolumn{2}{l}{\textbf{'+label+r'}} & '+' & '.join(names)+r' \\')
        for arm, labs, name in ARMS:
            cells = []
            for key in keys:
                if run is None:
                    cells.append('N/A'); continue
                value = round(run['scores'][arm]['secondary'][key], 4)
                values = [round(r['secondary'][key], 4) for r in run['scores'].values()]
                best = min(values) if key in ['bce', 'log_loss', 'cross_entropy'] else max(values)
                cell = f'{value:.4f}'
                cells.append(r'\textbf{'+cell+'}' if value == best else cell)
            lines.append(name+' & '+labs+' & '+' & '.join(cells)+r' \\')
        lines.append(r'\midrule')
    lines.extend([r'\bottomrule', r'\end{longtable}'])
    (out/'secondary.tex').write_text('\n'.join(lines)+'\n')


def pipeline():
    """Draw the framework only; do not publish or modify any score tables."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'pdf.fonttype': 42, 'svg.fonttype': 'none'})
    fig, ax = plt.subplots(figsize=(11.4, 7.9))
    ax.set(xlim=(0, 12), ylim=(0, 8.8)); ax.axis('off')
    ink = '#172B3A'
    palette = {
        'data': ('#238B7B', '#E7F5F2'),
        'model': ('#356FA3', '#E8F1F8'),
        'harness': ('#76539A', '#F1EAF7'),
        'gate': ('#D97732', '#FBEDE3'),
    }
    text_bounds = []

    def text(x, y, value, size=12, color=ink, weight='normal', ha='center'):
        return ax.text(x, y, value, ha=ha, va='center', fontsize=size,
                       color=color, fontweight=weight, linespacing=1.22, zorder=5)

    def box(x, y, w, h, title, body, role, title_size=12.4, body_size=11.3):
        color, fill = palette[role]
        ax.add_patch(FancyBboxPatch((x, y), w, h,
                     boxstyle='round,pad=0.015,rounding_size=0.08',
                     linewidth=1.4, edgecolor=color, facecolor=fill, zorder=3))
        for artist in [text(x+w/2, y+h-.23, title, title_size, color, 'bold'),
                       text(x+w/2, y+.33, body, body_size, ink)]:
            text_bounds.append((artist, (x, y, w, h)))

    def arrow(a, b, role, both=False):
        ax.add_patch(FancyArrowPatch(a, b, arrowstyle='<|-|>' if both else '-|>',
                     mutation_scale=12, color=palette[role][0], linewidth=1.4,
                     shrinkA=2, shrinkB=2, zorder=2))

    # The feedback route sits above the boxes, apart from execution/evidence lanes.
    text(.25, 8.58, 'OUTER RESEARCH LOOP', 15, palette['harness'][0], 'bold', ha='left')
    text(8.88, 8.58, 'shared research model + persistent history', 11.3, ink)
    for x, title, body, role in [
        (.25, '1  Hypothesize', 'focused revision\nexpected effect', 'harness'),
        (3.25, '2  Instantiate', 'validate proposal\ncompile executable design', 'model'),
        (6.25, '3  Fit + evaluate', 'invoke shared trainer\ncollect local evidence', 'model'),
        (9.25, '4  Retain + record', 'compare with incumbent\nappend evidence card', 'gate'),
    ]:
        box(x, 6.77, 2.5, 1.10, title, body, role)
    for x in (2.75, 5.75, 8.75):
        arrow((x, 7.32), (x+.5, 7.32), 'harness')
    ax.plot([10.5, 10.5, 1.5], [7.88, 8.18, 8.18],
            color=palette['harness'][0], linewidth=1.4, zorder=2)
    arrow((1.5, 8.18), (1.5, 7.88), 'harness')
    text(6, 8.18, 'selected design + experiment history', 10.8,
         palette['harness'][0]).set_bbox(dict(facecolor='white', edgecolor='none', pad=2))

    # Separate downward execution and upward evidence avoid crossing the history loop.
    arrow((7.5, 6.75), (7.5, 6.09), 'model')
    text(6.70, 6.42, 'candidate', 10.5, palette['model'][0])
    arrow((10.5, 6.09), (10.5, 6.75), 'gate')
    text(9.32, 6.42, 'aggregate diagnostics', 10.5, palette['gate'][0])

    box(.30, 5.03, 11.35, 1.04,
        'INNER COLLABORATIVE TRAINING  |  shared coordinator',
        'Distribute predictor  /  aggregate local model updates  /  summarize development evidence',
        'gate', title_size=13.7, body_size=11.9)

    # A laboratory is a data boundary, not a model or an aggregation operation.
    for x, name in [(.30, 'Laboratory 1'), (4.225, 'Laboratory 2'), (8.15, 'Laboratory K')]:
        ax.add_patch(FancyBboxPatch((x, 2.99), 3.5, 1.45,
                     boxstyle='round,pad=0.02,rounding_size=0.08',
                     linewidth=1.2, edgecolor='#CBD6DD', facecolor='#FCFDFE', zorder=1))
        text(x+1.75, 4.20, name, 13, ink, 'bold')
        for offset, value, role in [(.13, 'Local train\n+ development', 'data'),
                                    (1.94, 'Fit predictor\nScore candidate', 'model')]:
            edge, fill = palette[role]
            ax.add_patch(FancyBboxPatch((x+offset, 3.15), 1.43, .70,
                         boxstyle='round,pad=0.015,rounding_size=0.06',
                         linewidth=1.2, edgecolor=edge, facecolor=fill, zorder=3))
            artist = text(x+offset+.715, 3.5, value, 10.5, edge)
            text_bounds.append((artist, (x+offset, 3.15, 1.43, .70)))
        arrow((x+1.58, 3.5), (x+1.91, 3.5), 'data')
        arrow((x+1.75, 5.01), (x+1.75, 4.47), 'model', both=True)
    text(7.94, 3.65, '...', 14, ink)
    text(6, 2.66, 'Local measurements train the predictor and evaluate each proposed design', 11.9, ink)

    ax.plot([.3, 11.65], [2.38, 2.38], color='#D9E0E5', linewidth=1)
    text(6, 2.13, 'ONE RESEARCH INTERFACE  |  THREE BIOLOGICAL TASK FAMILIES', 12.1, ink, 'bold')
    for x, title, body in [
        (.30, 'Drug-target interaction', 'molecule + protein\ninteraction prediction'),
        (4.225, 'Proteomic efficacy', 'observed protein response\nefficacy classification'),
        (8.15, 'Cell perturbation', 'single-gene / double-gene / drug\nfive-option identification'),
    ]:
        box(x, .63, 3.5, 1.13, title, body, 'model', title_size=12.7, body_size=11.2)

    for x, name, role in [(.65, 'Local data', 'data'), (3.02, 'Predictive model', 'model'),
                           (5.89, 'Research harness', 'harness'), (8.87, 'Aggregation / gate', 'gate')]:
        edge, fill = palette[role]
        ax.add_patch(FancyBboxPatch((x, .13), .22, .20,
                     boxstyle='round,pad=0.01,rounding_size=0.03',
                     linewidth=1.1, edgecolor=edge, facecolor=fill, zorder=3))
        text(x+.35, .23, name, 10.7, ink, ha='left')

    fig.subplots_adjust(left=.005, right=.995, bottom=.005, top=.995)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    for artist, (x, y, w, h) in text_bounds:
        bounds = artist.get_window_extent(renderer).transformed(ax.transData.inverted())
        assert bounds.x0 >= x and bounds.x1 <= x+w, f'Text overflows box: {artist.get_text()}'
        assert bounds.y0 >= y and bounds.y1 <= y+h, f'Text overflows box: {artist.get_text()}'
    for suffix in ['pdf', 'svg']:
        fig.savefig(PAPER/f'assets/unified_pipeline.{suffix}')
    svg = PAPER/'assets/unified_pipeline.svg'
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--results', type=Path, default=PAPER.parent/'results/unified_bio_20260918')
    parser.add_argument('--pipeline', action='store_true', help='Explicitly regenerate the existing pipeline asset')
    args = parser.parse_args()
    snapshot = collect(args.results)
    out = PAPER/'tables/unified_v3'; out.mkdir(parents=True, exist_ok=True)
    (out/'snapshot.json').write_text(json.dumps(snapshot, indent=2, allow_nan=False)+'\n')
    score_table(snapshot, out); score_table(snapshot, out, final=True)
    score_table(snapshot, out, full=True)
    effect_table(snapshot, out); secondary_table(snapshot, out)
    heldout_score_table(snapshot['heldout'], out, full=True)
    heldout_effect_table(snapshot['heldout'], out)
    heldout_secondary_table(snapshot['heldout'], out)
    heldout_uncertainty_table(snapshot['heldout'], out)
    snapshot_macros(snapshot['heldout'], out)
    if args.pipeline:
        pipeline()
    print(json.dumps(dict(snapshot=snapshot['snapshot_utc'], completed={t: sum(x is not None for x in v['runs'].values()) for t,v in snapshot['tasks'].items()})))


if __name__ == '__main__':
    main()
