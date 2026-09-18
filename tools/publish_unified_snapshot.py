"""Publish a role-separated manuscript snapshot, never substituting legacy scores.

Reads aggregate result JSON only. Final-test cells remain N/A: this publisher
does not implement a test scorer or infer test results from development fits.
"""
from pathlib import Path
import argparse
from datetime import datetime, timezone
import hashlib
import json
import statistics

PAPER = Path(__file__).resolve().parents[1]
TASKS = [('native_dti', 'DTI'), ('ptpc', 'Proteomics'), ('vcc_pilot', 'VCC'),
         ('norman_double_pilot', 'Norman'), ('tahoe_drug_pilot', 'Tahoe')]
ARMS = [('single_fixed', '1', 'Fixed model'), ('single_direct', '1', 'Direct'),
        ('single_loop', '1', 'Our loop'), ('federated_fixed', '10', 'Fixed model'),
        ('federated_direct', '10', 'Direct'), ('federated_loop', '10', 'Our loop')]


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
    return snapshot


def score_table(snapshot, out, final=False):
    lines = [r'\begin{table}[t]', r'\centering\small', r'\setlength{\tabcolsep}{4pt}',
             r'\begin{tabular}{clrrrrr}', r'\toprule',
             r'Labs & Method & DTI & Proteomics & VCC & Norman & Tahoe \\',
             r' & & AUROC & AP & Top-1 & Top-1 & Top-1 \\', r'\midrule']
    for arm, labs, name in ARMS:
        values = []
        for task, _ in TASKS:
            run = snapshot['tasks'][task]['runs']['42']
            if final or run is None:
                values.append('N/A'); continue
            score = round(100*run['scores'][arm]['primary'], 2)
            best = max(round(100*v['primary'], 2) for v in run['scores'].values())
            cell = f'{score:.2f}'
            values.append(r'\textbf{'+cell+'}' if score == best else cell)
        if arm == 'federated_fixed':
            lines.append(r'\midrule')
        lines.append(f'{labs} & {name} & '+' & '.join(values)+r' \\')
    lines.extend([r'\midrule', r'1/10 & Cosine reference & N/A & N/A & N/A & N/A & N/A \\',
                  r'\bottomrule', r'\end{tabular}'])
    if final:
        caption = ('Reserved common-test comparison for the uniform protocol (three-seed mean and sample SD). '
                   'All values are N/A because no uniform-run final-test scores are available in this snapshot. '
                   'DTI denotes the unseen-drug endpoint; random and unseen-protein results will be separate. '
                   'The cosine reference is not yet rerun under this protocol. Older test scores are not substituted.')
        label = 'tab:unified-final'
    else:
        caption = ('Completed first-seed development results (seed 42), all metrics multiplied by 100; higher is better. '
                   'AUROC/AP are equal-client means; cell scores are intervention-macro Top-1. '
                   'Bold marks every column maximum, including ties. Unfinished studies and the pending cosine row are N/A, '
                   'not zero-valued baselines. These are not final-test results or three-seed means.')
        label = 'tab:unified-development'
    lines.extend([r'\caption{'+caption+'}', r'\label{'+label+'}', r'\end{table}'])
    (out/('final.tex' if final else 'development.tex')).write_text('\n'.join(lines)+'\n')


def effect_table(snapshot, out):
    lines = [r'\begin{table}[t]', r'\centering\small', r'\setlength{\tabcolsep}{4pt}',
             r'\begin{tabular}{lrrrrr}', r'\toprule',
             r'Development contrast & DTI & Proteomics & VCC & Norman & Tahoe \\', r'\midrule']
    comparisons = [('Loop $-$ fixed (10 labs)', 'federated_loop', 'federated_fixed'),
                   ('Loop $-$ direct (10 labs)', 'federated_loop', 'federated_direct'),
                   ('10 $-$ 1 labs (both loop)', 'federated_loop', 'single_loop')]
    for label, a, b in comparisons:
        cells = []
        for task, _ in TASKS:
            run = snapshot['tasks'][task]['runs']['42']
            cells.append('N/A' if run is None else f"{100*(run['scores'][a]['primary']-run['scores'][b]['primary']):+.2f}")
        lines.append(label+' & '+' & '.join(cells)+r' \\')
    lines.extend([r'\midrule', r'Completed development seeds & '+' & '.join(
        f"{sum(r is not None for r in snapshot['tasks'][t]['runs'].values())}/3" for t, _ in TASKS)+r' \\'])
    for label, a, b in [('3-seed loop $-$ direct', 'federated_loop', 'federated_direct'),
                         ('3-seed FL $-$ single (loop)', 'federated_loop', 'single_loop')]:
        cells = []
        for task, _ in TASKS:
            runs = list(snapshot['tasks'][task]['runs'].values())
            if any(r is None for r in runs):
                cells.append('N/A'); continue
            values = [100*(r['scores'][a]['primary']-r['scores'][b]['primary']) for r in runs]
            cells.append(f'${statistics.mean(values):+.2f}\\pm{statistics.stdev(values):.2f}$')
        lines.append(label+' & '+' & '.join(cells)+r' \\')
    lines.extend([r'\bottomrule', r'\end{tabular}',
        r'\caption{Independent attribution contrasts, percentage points on the corresponding primary metric. First-seed development only; zero means a measured tie. Three-seed effects remain N/A until all prespecified runs finish. The participation contrast changes available training data; it is not a same-data centralized comparison.}',
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
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'pdf.fonttype': 42, 'svg.fonttype': 'none'})
    fig, ax = plt.subplots(figsize=(11.4, 6.7))
    ax.set_xlim(0, 12); ax.set_ylim(0, 7); ax.axis('off')
    blue, green, ink = '#365e86', '#24796e', '#243746'
    def box(x, y, w, h, title, body, color=blue, fill='#f2f6fb'):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.06,rounding_size=0.10',
                                  linewidth=1.4, edgecolor=color, facecolor=fill))
        ax.text(x+w/2, y+h-.21, title, ha='center', va='center', fontsize=15, fontweight='bold', color=color)
        ax.text(x+w/2, y+.29, body, ha='center', va='center', fontsize=13.5, color=ink, linespacing=1.35)
    def arrow(a, b, color=blue, both=False):
        ax.add_patch(FancyArrowPatch(a, b, arrowstyle='<->' if both else '-|>', mutation_scale=14,
                                     color=color, linewidth=1.5, shrinkA=3, shrinkB=3))
    ax.text(.2, 6.83, 'OUTER RESEARCH LOOP  |  fixed local Qwen2.5-7B', fontsize=16, fontweight='bold', color=blue)
    for x, title, body in [(0.2, '1  Hypothesize', 'testable revision\nexpected effect'),
                           (3.2, '2  Instantiate', 'executable design\nsame candidate menu'),
                           (6.2, '3  Train + evaluate', '100 local epochs\ndevelopment evidence'),
                           (9.2, '4  Retain / revise', 'primary score + loss\nfailures stay in history')]:
        box(x, 5.47, 2.6, 1.08, title, body)
    for x in [2.8, 5.8, 8.8]: arrow((x, 6.02), (x+.4, 6.02))
    ax.plot([10.5, 10.5, 1.5, 1.5], [5.46, 5.14, 5.14, 5.45], color=blue, linestyle='--', linewidth=1.3)
    ax.text(6, 4.94, 'Only aggregate diagnostics return to the research model', ha='center', fontsize=13.5, color=blue)
    box(.3, 3.87, 11.35, .85, 'INNER FEDERATED TRAINING  |  one shared coordinator',
        'broadcast parameters  /  aggregate local updates  /  fixed scorer', green, '#edf7f3')
    # Route the training call outside the feedback-label band to avoid overlap.
    ax.plot([7.5, 7.5, 11.93, 11.93], [5.47, 5.34, 5.34, 4.29], color=blue, linewidth=1.4)
    arrow((11.93, 4.29), (11.65, 4.29))
    for x, title, body in [(.3, 'Laboratory 1', 'private train + dev\nlocal model update'),
                           (4.22, 'Laboratory 2', 'private train + dev\nlocal model update'),
                           (8.14, 'Laboratory 10', 'private train + dev\nlocal model update')]:
        box(x, 2.32, 3.5, 1.08, title, body, green, '#edf7f3')
        arrow((x+1.75, 3.86), (x+1.75, 3.42), green, True)
    ax.text(8.0, 2.82, '...', fontsize=18, color=green, ha='center')
    ax.text(6, 1.98, 'SAME core, controller, budget and selector; task-specific prediction adapters',
            ha='center', fontsize=13.5, color=ink)
    for x, title, body in [(.3, 'DTI', 'molecule + protein\nDrugBAN / AUROC'),
                           (4.22, 'Proteomic efficacy', 'measured 24h proteome\nlogistic head / AP'),
                           (8.14, 'Cell perturbations', 'single / double / drug\nscDEBART head / Top-1')]:
        box(x, .56, 3.5, 1.08, title, body)
    ax.text(6, .13, 'Six controls: 1 vs 10 laboratories  x  fixed / feedback-free direct / feedback-guided loop',
            ha='center', fontsize=13.5, color=ink)
    fig.subplots_adjust(left=.01, right=.99, bottom=.01, top=.99)
    for suffix in ['pdf', 'svg']:
        fig.savefig(PAPER/f'assets/unified_pipeline.{suffix}')
    svg = PAPER/'assets/unified_pipeline.svg'
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--results', type=Path, default=PAPER.parent/'results/unified_bio_20260918')
    args = parser.parse_args()
    snapshot = collect(args.results)
    out = PAPER/'tables/unified_v3'; out.mkdir(parents=True, exist_ok=True)
    (out/'snapshot.json').write_text(json.dumps(snapshot, indent=2, allow_nan=False)+'\n')
    score_table(snapshot, out); score_table(snapshot, out, final=True)
    effect_table(snapshot, out); secondary_table(snapshot, out); pipeline()
    print(json.dumps(dict(snapshot=snapshot['snapshot_utc'], completed={t: sum(x is not None for x in v['runs'].values()) for t,v in snapshot['tasks'].items()})))


if __name__ == '__main__':
    main()
