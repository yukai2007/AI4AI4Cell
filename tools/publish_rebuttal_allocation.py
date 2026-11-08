"""Publish the independently validated, fresh-runtime allocation controls."""
from pathlib import Path
import argparse
import hashlib
import json
import math
import statistics

PAPER = Path(__file__).resolve().parents[1]
SOURCE = PAPER.parent / 'results/rebuttal_20261109/allocation/v2/public'
OUT = PAPER / 'tables/rebuttal_20261109'
TASKS = ('ptpc_neural', 'vcc_corrected', 'norman_double_corrected', 'tahoe_drug_corrected')
METHODS = ('uniform_80', 'random_promotion_exact', 'score_only_global',
           'score_only_stratified', 'evidence_guided')
LABELS = ('Uniform (80 rounds)', 'Random promotion', 'Score only (global)',
          'Score only (LR groups)', 'Score + trajectory')


def validate(data, provenance):
    assert data['status'] == 'COMPLETE'
    assert provenance['validation_status'] == 'PASS'
    assert data['no_historical_fit_reuse'] and data['no_cpu_benchmark_reuse']
    assert tuple(data['methods']) == METHODS
    assert set(data['tasks']) == set(TASKS)
    assert data['training_seeds'] == [53, 54, 55]
    cost = data['cost']
    assert cost['new_fits'] == {'r20': 120, 'r80': 120, 'r100': 120}
    assert cost['actual_total_aggregation_rounds'] == 24000
    assert cost['per_policy_aggregation_rounds'] == 800
    assert cost['per_policy_development_evaluations'] == 160
    assert cost['actual_fit_training_seconds'] > 0
    assert cost['actual_training_wall_seconds'] > 0
    pooled = {m: [] for m in METHODS[:-1]}
    for task in TASKS:
        rows = data['paired'][task]
        assert set(rows) == {'53', '54', '55'}
        for method in METHODS:
            values = [rows[str(seed)]['scores'][method] for seed in (53, 54, 55)]
            assert all(math.isfinite(x) and 0 <= x <= 1 for x in values)
            expected = data['summary'][task][method]
            assert math.isclose(expected['mean'], statistics.mean(values), abs_tol=1e-12)
            assert math.isclose(expected['sample_sd'], statistics.stdev(values), abs_tol=1e-12)
        for seed, row in rows.items():
            for method in METHODS[:-1]:
                delta = row['scores']['evidence_guided'] - row['scores'][method]
                assert math.isclose(row['trajectory_minus_control'][method], delta, abs_tol=1e-12)
                pooled[method].append(delta)
            random = data['random_promotion_distribution'][task][seed]
            assert random['subsets'] == 210
            assert math.isclose(random['conditional_expectation'], row['scores']['random_promotion_exact'], abs_tol=1e-12)
            assert 0 <= random['minimum'] <= random['maximum'] <= 1
            assert random['minimum'] - 1e-12 <= random['conditional_expectation'] <= random['maximum'] + 1e-12
            assert 0 <= random['within_seed_policy_sd'] <= 1
    for method, values in pooled.items():
        wins = sum(x > 1e-12 for x in values)
        losses = sum(x < -1e-12 for x in values)
        assert data['twelve_pair_wtl'][method] == dict(wins=wins, ties=12-wins-losses, losses=losses)
    serialized = json.dumps([data, provenance])
    for marker in ('/liziqing/', '/home/', 'yukai', 'query.npz', 'prediction_sha256'):
        assert marker not in serialized, marker


def table(data):
    lines = [r'\begin{table}[htbp]',
        r'\caption{Fresh-runtime allocation controls. Scores $\times100$ are mean $\pm$ sample SD over training seeds 53--55. All policies use the same ten laboratories and ten designs, with 800 aggregation rounds and 160 aggregate development evaluations. Promotion policies screen ten designs for 20 rounds and restart six for 100; uniform allocation fits all ten for 80. Random promotion integrates all 210 six-design subsets per seed, and its displayed SD is across seed-conditional expectations. All 360 fits are newly trained; the original Table~\ref{tab:strong-effects} is retained separately. Bold marks the best unrounded mean, including ties.}',
        r'\label{tab:rebuttal-allocation}', r'\centering\small',
        r'\setlength{\tabcolsep}{4pt}', r'\begin{tabular}{lrrrr}', r'\toprule',
        r'Allocation policy & Proteomics & VCC & Norman & Tahoe \\',
        r' & AP $\uparrow$ & Top-1 $\uparrow$ & Top-1 $\uparrow$ & Top-1 $\uparrow$ \\',
        r'\midrule']
    best = {task: max(data['summary'][task][m]['mean'] for m in METHODS) for task in TASKS}
    for method, label in zip(METHODS, LABELS):
        cells = []
        for task in TASKS:
            value = data['summary'][task][method]
            mean = f'{100 * value["mean"]:.2f}'
            if abs(value['mean'] - best[task]) < 1e-12:
                mean = r'\mathbf{' + mean + '}'
            cells.append('$' + mean + r'\pm' + f'{100 * value["sample_sd"]:.2f}' + '$')
        lines.append(label + ' & ' + ' & '.join(cells) + r' \\')
    lines.extend([r'\bottomrule', r'\end{tabular}', r'\end{table}', ''])
    return '\n'.join(lines)


def export():
    raw = (SOURCE / 'allocation_public.json').read_text()
    provenance = json.loads((SOURCE / 'provenance.json').read_text())
    data = json.loads(raw)
    validate(data, provenance)
    provenance['public_snapshot_sha256'] = hashlib.sha256(raw.encode()).hexdigest()
    return {'allocation.json': raw,
            'allocation_provenance.json': json.dumps(provenance, indent=2, ensure_ascii=False) + '\n',
            'allocation.tex': table(data)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    files = export()
    for name, content in files.items():
        if args.check:
            assert (OUT / name).read_text() == content, name
        else:
            (OUT / name).write_text(content)
    print('PASS: 360 fits, 12 task-seed pairs, five allocation policies, aggregate-only export')


if __name__ == '__main__':
    main()
