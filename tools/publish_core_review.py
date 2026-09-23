"""Publish only independently rescored completed core studies, never estimates."""
from pathlib import Path
from collections import defaultdict
import hashlib
import json
import statistics

PAPER = Path(__file__).resolve().parents[1]
ROOT = PAPER.parent
BASE = ROOT / 'results/core_ablation_20260922'
REVIEW = PAPER / 'provenance/coauthor_review_20260922'
TASKS = [('native_tapb', 'DTI'), ('ptpc_neural', 'PTPC'), ('vcc_corrected', 'VCC'),
         ('norman_double_corrected', 'Norman'), ('tahoe_drug_corrected', 'Tahoe')]


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stat(values):
    if not values:
        return 'N/A'
    value = f'{statistics.mean(values):.2f}'
    return value + (r' $\pm$ ' + f'{statistics.stdev(values):.2f}' if len(values) > 1 else '')


def make_table(path, header, rows, caption, label, columns):
    lines = [r'\begin{table}[htbp]', r'\centering\small', r'\setlength{\tabcolsep}{4pt}',
             r'\begin{tabularx}{\linewidth}{@{}' + columns + r'@{}}',
             r'\toprule', header + r' \\', r'\midrule']
    lines += [r'\midrule' if row is None else ' & '.join(map(str, row)) + r' \\' for row in rows]
    lines += [r'\bottomrule', r'\end{tabularx}', r'\caption{' + caption + '}',
              r'\label{' + label + '}', r'\end{table}']
    path.write_text('\n'.join(lines) + '\n')


def main():
    verification = read(REVIEW / 'core_verification.json')
    if verification['status'] != 'PASS':
        raise ValueError('Independent core-study verification must pass first')
    out = PAPER / 'tables/core_review'
    out.mkdir(parents=True, exist_ok=True)
    payload = {'verification_sha256': sha(REVIEW / 'core_verification.json'),
               'studies': [], 'curves': {}, 'source_sha256': {}}
    grouped = defaultdict(list)
    for entry in verification['records']:
        path = Path(entry['result_path'])
        if sha(path) != entry['result_sha256']:
            raise ValueError('Completed result changed after verification: ' + str(path))
        result = read(path)
        if result['seal_sha256'] != sha(path.parent / 'seal.json'):
            raise ValueError('Result seal mismatch')
        relative = path.relative_to(BASE)
        key = relative.parts[:2]
        seed = next(p for p in relative.parts if p.startswith('seed'))
        if relative.parts[0] == 'model_loop':
            key += (relative.parts[3],)
        grouped[key].append(result['results'])
        payload['studies'].append({'relative_path': str(relative), 'seed': seed,
                                  'task': result['task'], 'scores': result['results']})
        payload['source_sha256'][str(relative)] = sha(path)
        if key[0] == 'model_loop':
            curvepath = path.parent.parent / 'curves.json'
            curves = read(curvepath)
            payload['source_sha256'][str(curvepath.relative_to(BASE))] = sha(curvepath)
            payload['curves'][str(relative)] = [
                {k: v for k, v in row.items() if k in ('mode', 'slot', 'accepted', 'invalid')} |
                {'primary': row['incumbent']['primary'], 'valid': bool(row.get('design'))}
                for row in curves]
    (out / 'snapshot.json').write_text(json.dumps(payload, indent=2) + '\n')

    rows = []
    for task, label in TASKS:
        runs = grouped[('lab_count', task)]
        for family, name in [('participation', 'More data'), ('partition', 'Fixed pool')]:
            rows.append([label, name, f'{len(runs)}/3'] +
                        [stat([100*r[f'{family}_k{k}']['primary'] for r in runs]) for k in (1, 2, 5, 10)])
        rows.append(None)
    make_table(out/'lab_count.tex', r'Task & Comparison & $n$ & $K=1$ & $K=2$ & $K=5$ & $K=10$', rows[:-1],
               r'Laboratory-count sensitivity with the fixed default recipe. More data adds a nested set of original clients; fixed pool retains all data and merges clients. Scores are mean $\pm$ sample SD times 100. $n$ is completed versus specified seeds. N/A indicates an incomplete evaluation, not a zero.',
               'tab:core-labs', 'Xlcrrrr')

    intervals = read(BASE/'analysis/transfer_uncertainty.json')
    payload['transfer_uncertainty'] = intervals
    payload['source_sha256']['analysis/transfer_uncertainty.json'] = sha(BASE/'analysis/transfer_uncertainty.json')
    rows = []
    names = {'target_only': 'Target only', 'plus_replogle': '+ Replogle', 'plus_nadig': '+ Nadig',
             'plus_jiang': '+ Jiang', 'plus_all': '+ All sources', 'plus_HCC1143': '+ HCC1143',
             'plus_HCC1806': '+ HCC1806', 'plus_MDA-MB-453-1': '+ MDA-MB-453-1'}
    for family, label in [('cell', 'VCC'), ('proteomics', 'PTPC'), ('dti', 'DTI')]:
        runs = grouped[('cross_source', family)]
        if not runs:
            rows.append([label, 'Source comparisons', '0/3', 'N/A', 'N/A', 'N/A'])
            continue
        for case in runs[0]:
            score = stat([r[case]['primary']*100 for r in runs])
            delta = stat([(r[case]['primary']-r['target_only']['primary'])*100 for r in runs])
            ci = intervals.get(family, {}).get('intervals', {}).get(case, {}).get('delta_percentile95')
            ci_text = f'[{ci[0]:.2f}, {ci[1]:.2f}]' if ci is not None else 'N/A'
            rows.append([label, names.get(case, case.replace('_', ' ')), f'{len(runs)}/3', score, delta, ci_text])
        rows.append(None)
    make_table(out/'transfer.tex', r'Target & Source & $n$ & Score & Change & 95\% CI', rows,
               r'External-source transfer on a fixed target test set. Change is paired against target-only training. Scores and changes are mean $\pm$ sample SD, in percentage points. Confidence intervals resample target interventions (VCC) or compounds (PTPC), retaining all paired seed predictions. VCC sources are independent studies; PTPC sources are contexts within the same mtPTDS study.',
               'tab:core-transfer', 'lXcrrr')

    rows, valid_rows = [], []
    for task, label in TASKS:
        for backend, name in [('qwen', 'Qwen'), ('luna', 'Luna')]:
            runs = grouped[('model_loop', task, backend)]
            keys = ['direct_b0', 'direct_b6', 'loop_b6', 'direct_b24', 'loop_b24']
            rows.append([label, name, f'{len(runs)}/3'] + [stat([r[k]['primary']*100 for r in runs]) for k in keys])
            curves = [v for p, v in payload['curves'].items()
                      if Path(p).parts[1] == task and Path(p).parts[3] == backend]
            counts = []
            for mode in ('direct', 'loop'):
                attempted = [r for c in curves for r in c if r['mode'] == mode and r['slot'] > 0]
                counts.append(f"{sum(r['valid'] for r in attempted)}/{len(attempted)}" if attempted else 'N/A')
            valid_rows.append([label, name, *counts])
    make_table(out/'loop_budget.tex', r'Task & Proposer & $n$ & Fixed & Direct@6 & Loop@6 & Direct@24 & Loop@24', rows,
               r'Proposer and search-budget sensitivity. Budgets count proposal slots, including failed proposals. Each included run has completed all 24 slots and evaluation at fixed prefixes. Scores use the original task metric times 100; a single completed seed has no estimated SD. Missing results remain N/A. This larger design-space study is separate from the six-slot main comparison.',
               'tab:core-budget', 'Xlcrrrrr')
    make_table(out/'proposal_validity.tex', 'Task & Proposer & Direct valid/slots & Loop valid/slots', valid_rows,
               r'Valid executable proposals among attempted slots in the completed runs of Table~\ref{tab:core-budget}. Each slot allows the same two schema-validation attempts. A larger slot budget need not yield an equal number of trained candidates across proposers.',
               'tab:core-validity', 'lXrr')
    (out/'snapshot.json').write_text(json.dumps(payload, indent=2) + '\n')

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size': 9, 'pdf.fonttype': 42, 'svg.fonttype': 'none'})
    for role in ('development', 'heldout'):
        fig, axes = plt.subplots(2, 3, figsize=(8, 5.7), constrained_layout=True)
        for ax, (task, label) in zip(axes.flat, TASKS):
            for backend, color in [('qwen', '#356FA3'), ('luna', '#D97732')]:
                for mode, style in [('direct', '--'), ('loop', '-')]:
                    samples = defaultdict(list)
                    if role == 'development':
                        for p, curve in payload['curves'].items():
                            if Path(p).parts[1] == task and Path(p).parts[3] == backend:
                                for row in curve:
                                    if row['mode'] == mode: samples[row['slot']].append(100*row['primary'])
                    else:
                        for run in grouped[('model_loop', task, backend)]:
                            for key, value in run.items():
                                if key.startswith(mode+'_b'):
                                    samples[int(key.split('_b')[1])].append(100*value['primary'])
                    if samples:
                        xs = sorted(samples)
                        ax.plot(xs, [statistics.mean(samples[x]) for x in xs], style, color=color,
                                label=f'{backend} {mode}', linewidth=1.6)
            ax.set(title=label, xlim=(0, 24), xticks=[0, 6, 12, 18, 24], xlabel='Proposal slots')
            ax.set_ylabel('Dev. score (%)' if role=='development' else 'Test score (%)')
            ax.grid(alpha=.2)
            if not ax.lines:
                ax.set_yticks([])
                ax.text(.5,.5,'N/A: pending',ha='center',transform=ax.transAxes)
            else:
                ax.legend(fontsize=7)
        axes.flat[-1].axis('off')
        axes.flat[-1].text(.05,.8,'Same candidates and trainer\nShared first proposal per backend\nCompleted runs only\nCounts: Table B.3\nValidity: Table B.4',
                           va='top',linespacing=1.6,transform=axes.flat[-1].transAxes)
        fig.savefig(PAPER/f'assets/core_{role}_budget.pdf')
        fig.savefig(PAPER/f'assets/core_{role}_budget.svg')
        plt.close(fig)
    print(f'Published {len(payload["studies"])} independently verified study records.')


if __name__ == '__main__':
    main()
