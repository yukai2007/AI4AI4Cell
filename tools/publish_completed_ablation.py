"""Publish completed sensitivity results from hash-verified snapshots only.

No training, predictions, main-table replacement, or protocol selection occurs.
Outputs are restricted to tables/completed_ablation and assets/completed_*.
"""
from collections import defaultdict
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import statistics

PAPER = Path(__file__).resolve().parents[1]
ROOT = PAPER.parent
OUT = PAPER / 'tables/completed_ablation'
FINAL = ROOT / 'results/tonight_completion_20260923/final_delivery/summary.json'
LEGACY = PAPER / 'tables/core_review/snapshot.json'
CORE = ROOT / 'results/core_ablation_20260922'
TASKS = [('native_tapb', 'DTI', 'AUROC'), ('ptpc_neural', 'PTPC', 'AP'),
         ('vcc_corrected', 'VCC', 'Macro Top-1'), ('norman_double_corrected', 'Norman', 'Macro Top-1'),
         ('tahoe_drug_corrected', 'Tahoe', 'Macro Top-1')]
K_VALUES = (1, 2, 5, 10)
BACKENDS = ('qwen', 'luna')
SOURCE_NAMES = {'cross_target_only': 'Target only', 'cross_plus_biosnap': '+ BioSNAP',
    'cross_plus_davis': '+ Davis', 'cross_plus_human': '+ Human', 'cross_plus_all': '+ All three',
    'target_only': 'Target only', 'plus_replogle': '+ Replogle', 'plus_nadig': '+ Nadig',
    'plus_jiang': '+ Jiang', 'plus_all': '+ All three', 'plus_lin': '+ Lin',
    'plus_ruprecht': '+ Ruprecht', 'plus_both': '+ Both', 'plus_HCC1143': '+ HCC1143',
    'plus_HCC1806': '+ HCC1806', 'plus_MDA-MB-453-1': '+ MDA-MB-453-1'}


def atomic_text(path, content):
    path = Path(path)
    temporary = path.with_name(path.name + '.tmp-' + str(os.getpid()))
    try:
        temporary.write_text(content)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def save_figure(figure, target):
    temporary = target.with_name('.' + target.stem + '.tmp-' + str(os.getpid()) + target.suffix)
    try:
        figure.savefig(temporary, metadata={'Creator': 'AI4AI4Cell verified snapshot publisher'})
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1048576), b''):
            h.update(chunk)
    return h.hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def relative(path):
    return str(Path(path).resolve().relative_to(ROOT))


def bind(path, receipts, expected=None):
    path = Path(path)
    if not path.is_absolute():
        path = ROOT / path
    digest = sha(path)
    require(expected is None or digest == expected, 'Changed verified input: ' + str(path))
    receipts[relative(path)] = digest
    return read(path) if path.suffix == '.json' else None


def escape(value):
    return str(value).replace('\\', r'\textbackslash{}').replace('&', r'\&').replace('%', r'\%').replace('_', r'\_').replace('#', r'\#')


def score(values, bold=False, signed=False):
    values = [100 * float(v) for v in values]
    require(values and all(math.isfinite(v) for v in values), 'Missing or nonfinite published score')
    mean = statistics.mean(values)
    text = format(mean, '+.2f' if signed else '.2f')
    if len(values) > 1:
        text += r' $\pm$ ' + format(statistics.stdev(values), '.2f')
    return r'\textbf{' + text + '}' if bold else text


def best_flags(values):
    # Ties at the displayed precision are all emphasized, not just one row.
    displayed = [round(statistics.mean(x) * 100, 2) for x in values]
    top = max(displayed)
    return [x == top for x in displayed]


def table(filename, header, rows, caption, label, columns, small='small'):
    lines = [r'\begin{table}[htbp]', r'\centering' + '\\' + small, r'\setlength{\tabcolsep}{4pt}',
             r'\begin{tabularx}{\linewidth}{@{}' + columns + '@{}}', r'\toprule',
             ' & '.join(header) + r' \\', r'\midrule']
    for row in rows:
        lines.append(r'\midrule' if row is None else ' & '.join(row) + r' \\')
    lines += [r'\bottomrule', r'\end{tabularx}', r'\caption{' + caption + '}',
              r'\label{' + label + '}', r'\end{table}']
    atomic_text(OUT / filename, '\n'.join(lines) + '\n')


def trajectory_summary(curves, slots):
    modes = {}
    for mode in ('direct', 'loop'):
        rows = sorted([r for r in curves if r['mode'] == mode], key=lambda r: r['slot'])
        require([r['slot'] for r in rows] == list(range(slots + 1)), 'Incomplete trajectory')
        improvements = [r['slot'] for p, r in zip(rows, rows[1:])
                        if r['incumbent']['primary'] > p['incumbent']['primary'] + 1e-12]
        modes[mode] = dict(final=rows[-1]['incumbent']['primary'],
            last_primary_improvement=max(improvements, default=0),
            last_retained=max((r['slot'] for r in rows[1:] if r['accepted']), default=0),
            retained=sum(bool(r['accepted']) for r in rows[1:]),
            valid=sum(bool(r.get('design')) for r in rows[1:]),
            trajectory=[dict(slot=r['slot'], primary=r['incumbent']['primary'],
                             loss=r['incumbent'].get('loss'), accepted=r['accepted']) for r in rows])
    target = min(modes[m]['final'] for m in modes)
    higher_target = max(modes[m]['final'] for m in modes)
    for mode in modes:
        modes[mode]['first_common_target'] = next((r['slot'] for r in modes[mode]['trajectory']
                                                  if r['primary'] >= target - 1e-12), None)
        modes[mode]['first_higher_terminal_target'] = next((r['slot'] for r in modes[mode]['trajectory']
                                                           if r['primary'] >= higher_target - 1e-12), None)
    return dict(common_development_target=target, higher_terminal_development_target=higher_target, modes=modes)


def normalized_loop(task, backend, seed, protocol, prefixes, curves, definition, initial):
    slots = 6 if protocol == 'short6' else 24
    menu = definition['menu']
    require(len(menu) == (12 if protocol == 'short6' else 36), 'Design-space mismatch')
    expected = [0, 1, 2, 4, 6] if protocol == 'short6' else [0, 1, 2, 4, 6, 8, 12, 16, 20, 24]
    require([r['budget'] for r in prefixes] == expected, 'Published prefix inventory differs')
    traces = []
    for row in curves:
        if row['slot'] == 0:
            continue
        design = row.get('design') or {}
        config = design.get('config')
        if config is not None:
            require(config == menu[design['design_id']], 'Proposal differs from its registered design')
        changes = {k: dict(initial=initial[k], proposed=v) for k, v in (config or {}).items()
                   if initial.get(k) != v}
        traces.append(dict(task=task, backend=backend, seed=seed, protocol=protocol,
            mode=row['mode'], slot=row['slot'], design_id=design.get('design_id'),
            config=config, changes_from_initial=changes,
            changes_from_prompt_reference=row.get('actual_change_from_prompt_reference'),
            hypothesis=design.get('hypothesis'), expected_effect=design.get('expected_effect'),
            outcome='retained' if row['accepted'] else 'invalid' if row.get('invalid') else 'not retained',
            invalid=row.get('invalid'), candidate_primary=(row.get('candidate') or {}).get('primary'),
            incumbent_primary=row['incumbent']['primary']))
    return dict(task=task, backend=backend, seed=seed, protocol=protocol, slots=slots,
        design_count=len(menu), menu=menu, initial_config=initial, prefixes=prefixes,
        curves=curves, traces=traces, **trajectory_summary(curves, slots))


def normalize():
    sources = {}
    final, legacy = bind(FINAL, sources), bind(LEGACY, sources)
    require(final['status'] == 'COMPLETE' and all(g['status'] == 'COMPLETE' for g in final['groups'].values()),
            'All final-delivery components must be complete before publication')
    require(final['requested_full_cross_output'].endswith('/native_final_cross_v2'),
            'Publication requires the explicitly finalized full-cross v2 directory')
    verification = bind(PAPER / 'provenance/coauthor_review_20260922/core_verification.json',
                        sources, legacy['verification_sha256'])
    require(verification['status'] == 'PASS', 'Legacy independent verification is not PASS')
    for name, digest in legacy['source_sha256'].items():
        bind(CORE / name, sources, digest)
    for group in final['groups'].values():
        for name, digest in group.get('source_sha256', {}).items():
            bind(name, sources, digest)
    payload = dict(schema='completed-ablation-publication-v1',
        scope='Completed single-seed native studies plus previously verified light-task results; protocols remain separate.',
        source_sha256=sources, laboratory=[], independent_transfer=[], protein_loop=[], context_transfer=[], loops=[])
    labs = [s for s in legacy['studies'] if s['relative_path'].startswith('lab_count/')]
    for family in ('participation', 'partition'):
        for task, label, metric in TASKS:
            if task == 'native_tapb':
                data = {r['case']: r for r in final['groups']['dti_lab_count']['rows']}
                by_k = {str(k): [data[f'{family}_k{k}']['primary']] for k in K_VALUES}
                seeds = [61]
            else:
                runs = sorted([s for s in labs if s['task'] == task], key=lambda s: s['seed'])
                require(len(runs) == 3, 'Expected all three completed legacy lab-count seeds')
                by_k = {str(k): [r['scores'][f'{family}_k{k}']['primary'] for r in runs] for k in K_VALUES}
                seeds = [int(r['seed'][4:]) for r in runs]
            payload['laboratory'].append(dict(task=task, label=label, metric=metric, family=family,
                                               seeds=seeds, by_k=by_k))
    for group_name, label, metric in [('dti_diverse', 'DTI', 'AUROC'), ('cell_diverse', 'VCC', 'Macro Top-1')]:
        groups = defaultdict(list)
        for row in final['groups'][group_name]['rows']:
            groups[row['case']].append(row)
        for name, rows in groups.items():
            rows = sorted(rows, key=lambda r: r['seed'])
            payload['independent_transfer'].append(dict(task=label, case=name, label=SOURCE_NAMES[name], metric=metric,
                seeds=[r['seed'] for r in rows], scores=[r['primary'] for r in rows],
                deltas=[r['delta_pp'] / 100 for r in rows], independent_sources=3))
    protein = final['groups']['protein_diverse']['rows']
    for row in protein:
        source, mode = row['case'].rsplit('_', 1)
        item = dict(task='PTPC auxiliary', case=source, label=SOURCE_NAMES[source], metric='AP',
                    seeds=[row['seed']], scores=[row['primary']], deltas=[row['delta_pp'] / 100],
                    independent_sources=2, mode=mode, loop_minus_fixed_pp=row.get('loop_minus_fixed_pp'))
        payload['protein_loop'].append(item)
        if mode == 'fixed':
            payload['independent_transfer'].append(item)
    context_runs = [s for s in legacy['studies'] if s['relative_path'].startswith('cross_source/proteomics/')]
    require(len(context_runs) == 3, 'Expected verified three-seed within-study contexts')
    for case in context_runs[0]['scores']:
        values = [s['scores'][case]['primary'] for s in context_runs]
        deltas = [s['scores'][case]['primary'] - s['scores']['target_only']['primary'] for s in context_runs]
        ci = legacy['transfer_uncertainty']['proteomics']['intervals'][case]['delta_percentile95']
        payload['context_transfer'].append(dict(case=case, label=SOURCE_NAMES[case], scores=values,
            deltas=deltas, ci_pp=ci, seeds=[int(s['seed'][4:]) for s in context_runs], independent_studies=False))
    for row in final['groups']['loop_light']['rows']:
        folder = ROOT / row['source_folder']
        for name, digest in row['sources_sha256'].items():
            bind(name, sources, digest)
        curves = bind(folder / 'curves.json', sources)
        selected = bind(folder / 'selected_development.json', sources)
        payload['loops'].append(normalized_loop(row['task'], row['backend'], row['seed'], row['protocol'],
            row['fixed_prefix_results'], curves, row['fit_definition'], selected['direct_b0']['config']))
    for backend in BACKENDS:
        group = final['groups']['dti_loop_' + backend]
        folder = ROOT / f'results/budget1day_20260923/native_tapb/seed42/{backend}'
        definition = bind(folder / 'definition.json', sources)
        selected = bind(folder / 'selected_development.json', sources)
        prefixes = [dict(budget=r['budget'], direct_heldout_primary=r['direct_primary'],
                         loop_heldout_primary=r['loop_primary'], loop_minus_direct_pp=r['delta_pp']) for r in group['rows']]
        payload['loops'].append(normalized_loop('native_tapb', backend, 42, 'short6', prefixes,
            group['development_trajectory'], definition, selected['direct_b0']['config']))
    # The old long protocol is independently bound both by the original paper
    # snapshot and by the recent audit; both must contain identical heldout scores.
    for study in legacy['studies']:
        if not study['relative_path'].startswith('model_loop/'):
            continue
        backend = Path(study['relative_path']).parts[3]
        run = next(r for r in payload['loops'] if r['task'] == study['task'] and
                   r['backend'] == backend and r['protocol'] == 'long24')
        for row in run['prefixes']:
            for mode in ('direct', 'loop'):
                require(math.isclose(study['scores'][f'{mode}_b{row["budget"]}']['primary'],
                                     row[mode + '_heldout_primary'], abs_tol=1e-12), 'Legacy long-loop scores differ')
    payload['loops'].sort(key=lambda r: (r['protocol'], [x[0] for x in TASKS].index(r['task']), r['backend']))
    return payload


def lab_tables(snapshot):
    for family, filename, title in [('participation', 'lab_participation.tex', 'Increasing participation'),
                                    ('partition', 'lab_fixed_pool.tex', 'Fixed data pool')]:
        rows = []
        for row in snapshot['laboratory']:
            if row['family'] != family:
                continue
            cells = [row['by_k'][str(k)] for k in K_VALUES]
            flags = best_flags(cells)
            rows.append([row['label'], row['metric']] + [score(x, b) for x, b in zip(cells, flags)])
        interpretation = ('A nested set of the original ten client partitions participates, so increasing $K$ also adds training data.'
                          if family == 'participation' else
                          'All target data are retained and merged into $K$ clients; only the partition count changes.')
        table(filename, ['Task', 'Metric', '$K=1$', '$K=2$', '$K=5$', '$K=10$'], rows,
              title + '. ' + interpretation + r' The default design and 100-round trainer are fixed. DTI uses seed 61; the four light endpoints report mean $\pm$ sample SD over seeds 61--63. Scores are metric $\times100$; bold denotes the best $K$ within each row, including displayed ties.',
              'tab:completed-' + family, 'lXrrrr')


def transfer_tables(snapshot):
    rows = []
    for task in ('DTI', 'VCC', 'PTPC auxiliary'):
        values = [r for r in snapshot['independent_transfer'] if r['task'] == task]
        flags = best_flags([r['scores'] for r in values])
        for row, bold in zip(values, flags):
            rows.append([task, row['label'], row['metric'], score(row['scores'], bold), score(row['deltas'], signed=True)])
        rows.append(None)
    table('transfer_independent.tex', ['Target', 'Additional source', 'Metric', r'Score $\uparrow$', r'$\Delta$ (pp)'], rows[:-1],
          r'Independent-source transfer on the same target heldout set, including every prespecified source and their combination. DTI (seed 61) adds BioSNAP, Davis or Human; VCC (seeds 61--63, mean $\pm$ SD) adds Replogle, Nadig or Jiang. The PTPC auxiliary multi-task model (seed 61) adds Lin or Ruprecht and is compared only with its matched auxiliary target-only model. PTPC has two independent external studies, not three. Changes are paired against target-only training; bold marks the best score within a target/model block. Scores are multiplied by 100.',
          'tab:completed-independent-transfer', 'lXlrr')
    rows = []
    flags = best_flags([r['scores'] for r in snapshot['context_transfer']])
    for row, bold in zip(snapshot['context_transfer'], flags):
        rows.append([row['label'], score(row['scores'], bold), score(row['deltas'], signed=True),
                     f'[{row["ci_pp"][0]:.2f}, {row["ci_pp"][1]:.2f}]'])
    table('transfer_contexts.tex', ['Additional context', r'AP $\uparrow$', r'$\Delta$ AP (pp)', r'Paired 95\% CI'], rows,
          r'Within-study PTPC context transfer, reported separately from independent-source transfer. HCC1143, HCC1806 and MDA-MB-453-1 belong to the same mtPTDS study. Values are mean $\pm$ sample SD over seeds 61--63, multiplied by 100. Confidence intervals resample target compounds while retaining paired seed predictions. These contexts are not additional independent studies; the original model and results are unchanged.',
          'tab:completed-context-transfer', 'Xrrr')
    rows = []
    values = snapshot['protein_loop']
    flags = best_flags([r['scores'] for r in values])
    for row, bold in zip(values, flags):
        rows.append([row['label'], row['mode'].capitalize(), score(row['scores'], bold),
                     score(row['deltas'], signed=True)])
    table('transfer_protein_loop.tex', ['Training sources', 'Selection', r'AP $\uparrow$', r'$\Delta$ vs target only (pp)'], rows,
          r'Independent-source proteomics auxiliary pilot, seed 61. Fixed design and a two-proposal Luna loop use the same shared-encoder/source-specific-head model and 100-round training allocation. Every source arm and both selection modes are retained. The heldout AP gain from this short loop is zero in all four source conditions; source-transfer gains are a different comparison.',
          'tab:completed-protein-loop', 'Xlrr')


def loop_tables(snapshot):
    labels = {t: (name, metric) for t, name, metric in TASKS}
    short = {(r['task'], r['backend']): r for r in snapshot['loops'] if r['protocol'] == 'short6'}
    rows = []
    for backend in BACKENDS:
        values = []
        for task, _, _ in TASKS:
            run = short[(task, backend)]
            values.append([[run['prefixes'][0]['direct_heldout_primary']],
                           [run['prefixes'][-1]['direct_heldout_primary']], [run['prefixes'][-1]['loop_heldout_primary']]])
        flags = [best_flags(v[1:]) for v in values]
        for i, method in ((1, 'Direct@6'), (2, 'Loop@6')):
            rows.append([('Qwen' if backend == 'qwen' else 'Luna') + ': ' + method] +
                        [score(v[i], b[i - 1]) for v, b in zip(values, flags)])
        rows.append(None)
    table('summary.tex', ['Research model / method', 'DTI', 'PTPC', 'VCC', 'Norman', 'Tahoe'], rows[:-1],
          r'Completed research-model and feedback ablation in the original 12-design, six-slot protocol. DTI uses AUROC and seed 42; PTPC uses AP and the cell endpoints use macro Top-1, all at seed 61. Each candidate receives 100 rounds on the same ten clients. The common initial design is reported in the full protocol table. Scores are multiplied by 100; bold denotes the best method within each task/backend block, including displayed ties. This table does not mix metrics across tasks or substitute the separate 36-design protocol.',
          'tab:completed-short-summary', 'Xrrrrr')
    for protocol in ('short6', 'long24'):
        runs = [r for r in snapshot['loops'] if r['protocol'] == protocol]
        rows, dynamics = [], []
        for run in runs:
            ps = {p['budget']: p for p in run['prefixes']}
            budgets = [0, 6] if protocol == 'short6' else [0, 6, 24]
            values = [[ps[0]['direct_heldout_primary']]] + [[ps[b][mode + '_heldout_primary']]
                for b in budgets[1:] for mode in ('direct', 'loop')]
            flags = best_flags(values)
            rows.append([labels[run['task']][0], run['backend'].capitalize()] +
                         [score(v, flag) for v, flag in zip(values, flags)])
            d, l = (run['modes'][m] for m in ('direct', 'loop'))
            pair = lambda field: '/'.join('--' if x[field] is None else str(x[field]) for x in (d, l))
            dynamics.append([labels[run['task']][0], run['backend'].capitalize(),
                             score([run['common_development_target']]), pair('first_common_target'),
                             pair('last_primary_improvement'), pair('last_retained'), pair('valid')])
        title = ('Original 12-design/six-slot' if protocol == 'short6' else 'Extended 36-design/24-slot')
        seeds = ('DTI seed 42; four light endpoints seed 61.' if protocol == 'short6' else
                 'Four light endpoints, seed 61; no native DTI 24-slot result is implied.')
        header = ['Task', 'Proposer', 'Fixed', 'Direct@6', 'Loop@6']
        if protocol == 'long24':
            header += ['Direct@24', 'Loop@24']
        table(protocol + '.tex', header, rows, title + r' heldout results. ' + seeds +
              r' All displayed budgets are prefixes of this single protocol; they are not selected by test performance. Every candidate uses 100 rounds. Scores use each original task metric $\times100$; bold marks the best displayed score within a row, including ties.',
              'tab:completed-' + protocol, 'Xl' + 'r' * (len(header) - 2))
        table('dynamics_' + protocol + '.tex', ['Task', 'Proposer', 'Dev. target', 'First D/L', 'Last gain D/L', 'Last retain D/L', 'Valid D/L'],
              dynamics, title + r' search dynamics. ' + seeds +
              r' D/L means direct/loop. The common target is the lower of the two terminal development primary scores, so it is attainable by both runs; first records its earliest attainment. Last gain is the last strictly improving primary-score slot; last retain also includes loss-tiebreak selections. These are retrospective diagnostics, not stopping rules. Slot 0 is initialization.',
              'tab:completed-dynamics-' + protocol, 'Xlrrrrr', 'small')


def trace_tables(snapshot):
    traces = [t for r in snapshot['loops'] for t in r['traces']]
    fields = ['protocol', 'task', 'backend', 'seed', 'mode', 'slot', 'design_id', 'outcome',
              'candidate_primary', 'incumbent_primary', 'changes_from_initial', 'hypothesis']
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=fields, delimiter='\t', extrasaction='ignore')
    writer.writeheader()
    for trace in traces:
        writer.writerow({k: json.dumps(v, sort_keys=True) if isinstance(v, dict) else v for k, v in trace.items()})
    atomic_text(OUT / 'proposal_trace.tsv', stream.getvalue())
    for protocol in ('short6', 'long24'):
        runs = [r for r in snapshot['loops'] if r['protocol'] == protocol]
        menu = runs[0]['menu']
        require(all(r['menu'] == menu for r in runs), 'Menus differ across task/backend in one protocol')
        rows = [[escape(name), f'{config["lr"]:g}', f'{config["weight_decay"]:g}',
                 f'{config["server_momentum"]:g}', 'Yes' if config['residual'] else 'No']
                for name, config in menu.items()]
        table('menu_' + protocol + '.tex', ['Design', 'Learning rate', 'Weight decay', 'Server momentum', 'Residual head'], rows,
              ('Twelve' if protocol == 'short6' else 'Thirty-six') + r' executable configurations for the ' + protocol +
              r' protocol. Every design has proximal coefficient zero. A trace design ID uniquely identifies these parameter changes; the task-specific prediction interface remains fixed.',
              'tab:completed-menu-' + protocol, 'Xrrrr', 'small')
        lines = [r'\begingroup\small', r'\setlength{\tabcolsep}{3pt}',
                 r'\begin{longtable}{@{}p{0.10\linewidth}p{0.08\linewidth}p{0.08\linewidth}>{\raggedright\arraybackslash}p{0.66\linewidth}@{}}',
                 r'\caption{Complete proposal trace for ' + escape(protocol) +
                 r'. Each token is slot:design:decision, with A=retained, R=not retained, I=invalid. Design configurations are decoded in Table~\ref{tab:completed-menu-' + protocol +
                 r'}. All proposed slots, including failures, are retained. Full configuration deltas and development scores are in the accompanying snapshot and TSV.}\label{tab:completed-trace-' + protocol + r'}\\',
                 r'\toprule Task & Proposer & Mode & Slot:design:decision \\ \midrule\endfirsthead',
                 r'\toprule Task & Proposer & Mode & Slot:design:decision \\ \midrule\endhead',
                 r'\bottomrule\endfoot']
        for run in runs:
            for mode in ('direct', 'loop'):
                tokens = []
                for row in run['traces']:
                    if row['mode'] != mode:
                        continue
                    decision = {'retained': 'A', 'not retained': 'R', 'invalid': 'I'}[row['outcome']]
                    tokens.append(str(row['slot']) + ':' + (row['design_id'] or '--') + ':' + decision)
                label = next(x[1] for x in TASKS if x[0] == run['task'])
                lines.append(' & '.join([label, run['backend'].capitalize(), mode.capitalize(),
                                       '; '.join(escape(t) for t in tokens)]) + r' \\[3pt]')
        lines += [r'\end{longtable}', r'\endgroup']
        atomic_text(OUT / ('trace_' + protocol + '.tex'), '\n'.join(lines) + '\n')


def accepted_event_table(snapshot):
    run = next(r for r in snapshot['loops'] if r['task'] == 'norman_double_corrected'
               and r['backend'] == 'luna' and r['protocol'] == 'long24')
    rows = []
    for mode in ('direct', 'loop'):
        rows.append([mode.capitalize(), '0', 'Initial', 'Common initial design',
                     score([run['modes'][mode]['trajectory'][0]['primary']])])
        for trace in run['traces']:
            if trace['mode'] != mode or trace['outcome'] != 'retained':
                continue
            config = trace['config']
            change = ', '.join([f'lr={config["lr"]:g}', f'wd={config["weight_decay"]:g}',
                               f'm={config["server_momentum"]:g}', 'R=' + str(int(config['residual']))])
            rows.append([mode.capitalize(), str(trace['slot']), escape(trace['design_id']), change,
                         score([trace['incumbent_primary']])])
    table('norman_retained_events.tex', ['Mode', 'Slot', 'Design', 'Retained configuration', 'Dev. Top-1'], rows,
          r'All retained proposals for the Norman/Luna extended 36-design, 24-slot study, seed 61. The two modes share initialization and first proposal. lr, wd, m and R denote learning rate, weight decay, server momentum and residual-head indicator. Development selection is followed by evaluation at every prespecified heldout prefix; the full attempted-slot trace is retained separately.',
          'tab:completed-norman-events', 'llXlr', 'small')


def figures(snapshot):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    plt.rcParams.update({'font.size': 8, 'axes.titlesize': 8.5, 'axes.labelsize': 7.7,
                         'pdf.fonttype': 42, 'svg.fonttype': 'none', 'font.family': 'DejaVu Sans'})
    colors = {'qwen': '#2166AC', 'luna': '#B35806'}
    rendered = []
    for protocol in ('short6', 'long24'):
        tasks = TASKS if protocol == 'short6' else TASKS[1:]
        for roles in (('development', 'heldout'), ('heldout',)):
            height = 6.5 if len(roles) == 2 else 3.35
            fig, axes = plt.subplots(2 * len(roles), 3, figsize=(5.5, height), squeeze=False)
            for ax in axes.flat:
                ax.set_visible(False)
            for role_index, role in enumerate(roles):
                for task_index, (task, label, metric) in enumerate(tasks):
                    ax = axes[2 * role_index + task_index // 3, task_index % 3]
                    ax.set_visible(True)
                    for backend in BACKENDS:
                        run = next(r for r in snapshot['loops'] if r['task'] == task
                                   and r['backend'] == backend and r['protocol'] == protocol)
                        for mode in ('loop', 'direct'):
                            if role == 'development':
                                data = run['modes'][mode]['trajectory']
                                xs, ys = [r['slot'] for r in data], [100 * r['primary'] for r in data]
                            else:
                                xs = [r['budget'] for r in run['prefixes']]
                                ys = [100 * r[mode + '_heldout_primary'] for r in run['prefixes']]
                            ax.plot(xs, ys, '--' if mode == 'direct' else '-', color=colors[backend],
                                    linewidth=1.05 if mode == 'direct' else 1.65,
                                    marker='x' if mode == 'direct' else 'o', markersize=2.8,
                                    markerfacecolor='none', alpha=.95,
                                    zorder=4 if mode == 'direct' else 3)
                    ax.set_title(label + (' / dev.' if role == 'development' else ' / heldout'))
                    ax.set_xlabel('Proposal slots')
                    ax.set_ylabel(metric + r' $\times100$')
                    ticks = [0, 2, 4, 6] if protocol == 'short6' else [0, 6, 12, 18, 24]
                    ax.set_xticks(ticks)
                    ax.set_xlim(-.25, run['slots'] + .25)
                    ax.tick_params(labelsize=7.2, pad=1)
                    ax.yaxis.set_major_locator(plt.MaxNLocator(4))
                    ax.grid(color='#D9DEE5', linewidth=.55)
                    ax.spines[['top', 'right']].set_visible(False)
                    ax.margins(y=.12)
            handles = [Line2D([0], [0], color=colors[b], linestyle='--' if m == 'direct' else '-',
                              marker='x' if m == 'direct' else 'o', markersize=3, markerfacecolor='none',
                              label=b.capitalize() + ' ' + m) for b in BACKENDS for m in ('direct', 'loop')]
            fig.legend(handles=handles, loc='upper center', ncol=4, frameon=False,
                       bbox_to_anchor=(.53, 1.0), columnspacing=1.05, handlelength=2.0)
            fig.subplots_adjust(left=.105, right=.975, bottom=.13 if len(roles) == 1 else .068,
                                top=.86 if len(roles) == 1 else .929, wspace=.59, hspace=.76)
            stem = 'completed_' + protocol + ('_search' if len(roles) == 2 else '_heldout')
            for extension in ('pdf', 'svg'):
                target = PAPER / 'assets' / (stem + '.' + extension)
                save_figure(fig, target)
                rendered.append(relative(target))
            plt.close(fig)
    return rendered


def main_examples(snapshot):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    fig, axes = plt.subplots(1, 2, figsize=(5.5, 2.1))
    colors = {'qwen': '#2166AC', 'luna': '#B35806'}
    for ax, task, label in zip(axes, ('norman_double_corrected', 'vcc_corrected'), ('Norman', 'VCC')):
        for backend in BACKENDS:
            run = next(r for r in snapshot['loops'] if r['task'] == task and
                       r['backend'] == backend and r['protocol'] == 'long24')
            for mode in ('loop', 'direct'):
                data = run['modes'][mode]['trajectory']
                ax.plot([r['slot'] for r in data], [100 * r['primary'] for r in data],
                        '--' if mode == 'direct' else '-', color=colors[backend],
                        linewidth=1.1 if mode == 'direct' else 1.8,
                        marker='x' if mode == 'direct' else 'o', markersize=2.7,
                        markerfacecolor='none', zorder=4 if mode == 'direct' else 3)
        ax.set(title=label + ' (36 designs)', xlabel='Proposal slots', ylabel='Dev. macro Top-1')
        ax.set_xticks([0, 6, 12, 18, 24])
        ax.set_xlim(-.25, 24.25)
        ax.yaxis.set_major_locator(plt.MaxNLocator(4))
        ax.grid(color='#D9DEE5', linewidth=.55)
        ax.spines[['top', 'right']].set_visible(False)
    handles = [Line2D([0], [0], color=colors[b], linestyle='--' if m == 'direct' else '-',
                     label=b.capitalize() + ' ' + m) for b in BACKENDS for m in ('direct', 'loop')]
    fig.legend(handles=handles, loc='upper center', ncol=4, frameon=False, bbox_to_anchor=(.52, 1.015))
    fig.subplots_adjust(left=.105, right=.965, bottom=.215, top=.77, wspace=.37)
    outputs = []
    for extension in ('pdf', 'svg'):
        target = PAPER / 'assets' / ('completed_budget_examples.' + extension)
        save_figure(fig, target)
        outputs.append(relative(target))
    plt.close(fig)
    return outputs


def review_document():
    tables = ['summary', 'lab_participation', 'lab_fixed_pool', 'transfer_independent', 'transfer_contexts',
              'transfer_protein_loop', 'short6', 'dynamics_short6', 'long24', 'dynamics_long24',
              'norman_retained_events', 'menu_short6', 'menu_long24', 'trace_short6', 'trace_long24']
    lines = [r'\documentclass{article}', r'\usepackage[textwidth=5.5in,textheight=9in]{geometry}',
             r'\usepackage{booktabs,tabularx,longtable,graphicx,amsmath,amssymb,fontspec}',
             r'\setmainfont{texgyretermes-regular.otf}[Path=../../fonts/,BoldFont=texgyretermes-bold.otf,ItalicFont=texgyretermes-italic.otf,BoldItalicFont=texgyretermes-bolditalic.otf]',
             r'\begin{document}',
             r'\section*{Completed ablation publication check}']
    for name in tables:
        lines += [r'\input{' + name + '}', r'\clearpage']
    for name in ('short6_search', 'short6_heldout', 'long24_search', 'long24_heldout', 'budget_examples'):
        lines += [r'\noindent\includegraphics[width=\linewidth]{../../assets/completed_' + name + '.pdf}', r'\clearpage']
    lines += [r'\end{document}']
    atomic_text(OUT / 'publication_review.tex', '\n'.join(lines) + '\n')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    payload = normalize()
    lab_tables(payload)
    transfer_tables(payload)
    loop_tables(payload)
    trace_tables(payload)
    accepted_event_table(payload)
    figures_written = figures(payload) + main_examples(payload)
    review_document()
    payload['publication_notes'] = dict(
        bold='Within the same task/metric/protocol comparison, all best displayed values including ties.',
        independent_protein_studies=['Lin', 'Ruprecht'], contexts_counted_as_independent=False,
        dti_long24_run=False, cross_metric_average=False, trace_reference='Configuration changes relative to common initialization; recorded prompt-relative deltas additionally preserved.')
    atomic_text(OUT / 'snapshot.json', json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    generated = sorted(OUT.glob('*.tex')) + [OUT / 'snapshot.json', OUT / 'proposal_trace.tsv']
    generated += [ROOT / p for p in figures_written]
    manifest = dict(schema='completed-ablation-publication-receipt-v1', generator=relative(__file__),
        generator_sha256=sha(__file__), input_sha256=payload['source_sha256'],
        outputs_sha256={relative(p): sha(p) for p in generated},
        counts=dict(lab_rows=len(payload['laboratory']), independent_transfer_rows=len(payload['independent_transfer']),
                    context_rows=len(payload['context_transfer']), paired_short_runs=10, paired_long_runs=8,
                    proposal_slots=sum(len(r['traces']) for r in payload['loops'])),
        figure_dimensions_inches={'search': [5.5, 6.5], 'heldout': [5.5, 3.35], 'budget_examples': [5.5, 2.1]})
    atomic_text(OUT / 'provenance.json', json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(manifest['counts']))


if __name__ == '__main__':
    main()
