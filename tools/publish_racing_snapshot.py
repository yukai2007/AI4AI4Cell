"""Publish the verified four-endpoint V6 racing table, never a V3 fallback."""
from pathlib import Path
import argparse
import hashlib
import json
import math
import statistics

PAPER = Path(__file__).resolve().parents[1]
ROOT = PAPER.parent
SEEDS = [53, 54, 55]
TASKS = [
    ('ptpc_neural', 'ptpc_neural', 'Proteomics: efficacy'),
    ('vcc_corrected', 'vcc_single_gene', 'Cell: VCC single-gene'),
    ('norman_double_corrected', 'norman_double_gene', 'Cell: Norman double-gene'),
    ('tahoe_drug_corrected', 'tahoe_drug', 'Cell: Tahoe drug'),
]
ROLE = 'retrospective held-out; no feedback to controller'
PROTOCOL = dict(candidate_count_per_arm=10, full_client_rounds_per_arm=800,
                development_measurements_per_arm=160, direct='10 designs x 80 rounds',
                loop='10 designs x 20-round screen + 6 promoted designs x 100-round validation',
                seeds=SEEDS)

def read(path):
    if not Path(path).is_file():
        raise ValueError(f'Missing racing publication evidence: {path}')
    return json.loads(Path(path).read_text())

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8 << 20), b''):
            h.update(block)
    return h.hexdigest()

def require(value, message):
    if not value:
        raise ValueError(message)

def close(a, b, message):
    require(math.isfinite(a) and math.isfinite(b) and abs(a-b) <= 1e-12, message)

def rescore(task, path, seal):
    """Recompute the primary metric from saved scores/probabilities, not logits inferred anew."""
    import sys
    import numpy as np
    sys.path.insert(0, str(ROOT))
    query_path = Path(seal['heldout_path'])
    require(sha(query_path) == seal['heldout_sha256'], 'Racing held-out roster changed')
    with np.load(query_path, allow_pickle=False) as archive:
        query = {k: archive[k] for k in ('y',) if k in archive} if task == 'ptpc_neural' else {
            k: archive[k] for k in ('ids', 'choices')}
    values, prediction_hashes = {}, {}
    for arm in ('direct', 'loop'):
        prediction = path / f'{arm}_predictions.{"npz" if task == "ptpc_neural" else "json"}'
        if task == 'ptpc_neural':
            from extensions.proteomics.scoring import phenotype_scores
            with np.load(prediction, allow_pickle=False) as archive:
                values[arm] = phenotype_scores(query['y'], archive['probabilities'])['ap']
        else:
            rows = read(prediction)
            ids = np.asarray([r['intervention'] for r in rows])
            choices = np.asarray([r['choices'] for r in rows])
            scores = np.asarray([r['scores'] for r in rows], dtype=np.float32)
            require(np.array_equal(ids, query['ids']) and np.array_equal(choices, query['choices']),
                    'Racing prediction/query order differs')
            require(scores.shape == choices.shape and np.isfinite(scores).all(), 'Invalid racing prediction scores')
            require(np.all((choices == ids[:, None]).sum(axis=1) == 1), 'Invalid racing choice roster')
            truth = np.argmax(choices == ids[:, None], axis=1)
            ranks = np.argmax(np.argsort(-scores, axis=1, kind='stable') == truth[:, None], axis=1) + 1
            require(np.array_equal(ranks, [r['rank'] for r in rows]), 'Racing saved rank differs from scores')
            values[arm] = float(np.mean([np.mean(ranks[ids == g] == 1) for g in np.unique(ids)]))
        prediction_hashes[arm] = sha(prediction)
    return values, prediction_hashes

def collect_racing(base, public_path=PAPER/'provenance/v6_loop_summary.json'):
    base, public_path = Path(base).resolve(), Path(public_path)
    public = read(public_path)
    full_path = base/'v6_loop_summary/summary.json'
    full = read(full_path)
    require(public['schema'] == 'ai4ai4cell-v6-loop-public-summary' and public['protocol'] == PROTOCOL,
            'Wrong racing public protocol')
    require(sha(full_path) == public['local_full_summary_sha256'], 'Stale racing public summary binding')
    require(full['schema'] == 'ai4ai4cell-v6-loop-summary' and full['seeds'] == SEEDS and
            full['equal_compute'] is True and full['feedback_to_controller'] is False,
            'Wrong racing full-summary protocol')
    require(full['independent_rescore'] == public['independent_rescore'] == 'PASS',
            'Racing summary lacks independent verification')
    snapshot = dict(schema='verified-v6-racing-publication-v1', seeds=SEEDS, tasks={},
                    public_summary_sha256=sha(public_path), full_summary_sha256=sha(full_path),
                    protocol=PROTOCOL, result_bindings={}, independent_rescore='PASS',
                    ci_source='hash-bound independently rescored V6 full summary; not recomputed by publisher')
    totals = [0, 0, 0]
    for task, public_key, label in TASKS:
        paired, arm_values = {}, {'direct': [], 'loop': []}
        summary = full['tasks'][task]['heldout']
        public_row = public['heldout_loop_minus_direct'][public_key]
        for seed in SEEDS:
            path = base/'heldout_v6'/task/f'seed{seed}'
            result, seal = read(path/'results.json'), read(path/'seal.json')
            study = base/task/f'study_v6_seed{seed}'
            definition, selected, status = [read(study/name) for name in
                ('definition.json', 'selected_development.json', 'status.json')]
            require(result['schema'] == 'ai4ai4cell-v6-heldout-results' and
                    seal['schema'] == 'ai4ai4cell-v6-heldout-seal', 'Wrong racing result schema')
            require(result['task'] == seal['task'] == definition['task'] == task and
                    result['seed'] == seal['seed'] == definition['seed'] == seed, 'Racing task/seed mismatch')
            require(result['role'] == seal['role'] == ROLE and result['feedback_to_controller'] is False and
                    seal['feedback_to_controller'] is False, 'Racing held-out evidence boundary changed')
            require(result['seal_sha256'] == sha(path/'seal.json') and
                    seal['definition_sha256'] == sha(study/'definition.json') and
                    seal['selection_sha256'] == sha(study/'selected_development.json'), 'Stale racing seal/selection binding')
            require(status['status'] == 'DEVELOPMENT_COMPLETE' and
                    seal['development_completed_unix'] <= seal['sealed_unix'] <=
                    result['heldout_decoded_unix'] <= result['completed_unix'], 'Incomplete or unsealed racing selection')
            expected = dict(schema='ai4ai4cell-racing-v6', clients=list(range(10)),
                direct_rounds_per_candidate=80, loop_screen_rounds_per_candidate=20,
                loop_promoted_candidates=6, loop_validation_rounds_per_promoted_candidate=100,
                total_client_epochs_per_arm=8000, development_evaluations_per_arm=160,
                candidate_count_per_arm=10, restart_promoted_candidates_from_common_initialization=True,
                test_read=False)
            require(all(definition.get(k) == v for k, v in expected.items()) and
                    len(definition['slate']) == len(set(definition['slate'])) == 10, 'Wrong racing run protocol')
            rescored, predictions = rescore(task, path, seal)
            primary = 'ap' if task == 'ptpc_neural' else 'macro_accuracy'
            require(result['primary_metric'] == primary and set(result['results']) == {'direct', 'loop'},
                    'Wrong racing metrics/arms')
            for arm in ('direct', 'loop'):
                value, binding, chosen = result['results'][arm], seal['arms'][arm], selected[arm]
                require(value['checkpoint'] == binding['checkpoint'] == chosen['checkpoint'],
                        'Racing checkpoint selection mismatch')
                require(sha(binding['checkpoint']) == binding['checkpoint_sha256'], 'Racing checkpoint changed')
                require(chosen['config'] == binding['config'] and chosen['best']['round'] == binding['best_round'] and
                        chosen['seed'] == seed and chosen['clients'] == list(range(10)), 'Racing fit binding differs')
                close(value['primary'], value['metrics'][primary], 'Racing primary/metrics mismatch')
                close(value['primary'], rescored[arm], 'Racing independent re-score mismatch')
                arm_values[arm].append(value['primary'])
            effect = rescored['loop'] - rescored['direct']
            for expected_effect in (result['loop_minus_direct'], summary['per_seed'][str(seed)], public_row['per_seed'][str(seed)]):
                close(effect, expected_effect, 'Racing paired difference differs from summary')
            paired[str(seed)] = effect
            snapshot['result_bindings'][str(path.relative_to(base))] = dict(
                results_sha256=sha(path/'results.json'), seal_sha256=sha(path/'seal.json'), predictions_sha256=predictions)
        mean = statistics.mean(paired.values())
        close(mean, summary['mean'], 'Racing full-summary mean changed')
        close(mean, public_row['mean'], 'Racing public mean changed')
        interval = summary['hierarchical_paired_bootstrap_ci95']
        require(interval == public_row['hierarchical_paired_bootstrap_ci95'] and len(interval) == 2 and
                all(math.isfinite(x) for x in interval) and interval[0] <= interval[1] and
                summary['bootstrap_replicates'] == 5000, 'Invalid/stale racing confidence interval')
        wins = sum(v > 1e-12 for v in paired.values())
        losses = sum(v < -1e-12 for v in paired.values())
        wtl = [wins, len(SEEDS)-wins-losses, losses]
        totals = [a+b for a,b in zip(totals, wtl)]
        snapshot['tasks'][task] = dict(label=label, direct=statistics.mean(arm_values['direct']),
            loop=statistics.mean(arm_values['loop']), difference=mean, ci95=interval, wins_ties_losses=wtl)
    require(totals == public['heldout_wins_ties_losses'] ==
            [full['heldout_wins'], full['heldout_ties'], full['heldout_losses']], 'Racing W/T/L summary differs')
    snapshot['wins_ties_losses'] = totals
    return snapshot

def render(snapshot):
    lines = [r'\begin{table}[t]', r'\centering\small', r'\setlength{\tabcolsep}{4.5pt}',
             r'\renewcommand{\arraystretch}{1.08}', r'\begin{tabularx}{\linewidth}{@{}Xrrrr@{}}',
             r'\toprule', r'\textbf{Benchmark} & \textbf{Uniform} & \textbf{Evidence-guided} & \textbf{Gain} & \textbf{W/T/L} \\', r'\midrule']
    for task, _, _ in TASKS:
        row = snapshot['tasks'][task]
        displayed = [round(row[a]*100, 2) for a in ('direct', 'loop')]
        cells = [r'\textbf{'+f'{v:.2f}'+'}' if v == max(displayed) else f'{v:.2f}' for v in displayed]
        gain = f'{row["difference"]*100:+.2f}'
        if row['difference'] > 1e-12:
            gain = r'\textbf{'+gain+'}'
        lines.append(row['label']+' & '+' & '.join(cells)+' & '+gain+' & '+
                     '/'.join(map(str,row['wins_ties_losses']))+r' \\')
    def ci(task):
        return '['+', '.join(f'{100*v:.2f}'.replace('-',r'$-$') for v in snapshot['tasks'][task]['ci95'])+']'
    lines += [r'\bottomrule', r'\end{tabularx}',
        r'\caption{Does early evidence improve training allocation? Held-out scores use the same ten designs, ten laboratories, 800 full-client rounds and 160 development measurements per method. Uniform allocation gives every design 80 rounds; the evidence-guided loop screens all designs and fully validates six promoted candidates. Gain is evidence-guided minus uniform, in percentage points; W/T/L counts seed-level wins, ties and losses (total '+
        '/'.join(map(str,snapshot['wins_ties_losses']))+r'). Norman 95\% CI: '+ci('norman_double_corrected')+
        '; Tahoe: '+ci('tahoe_drug_corrected')+'. The separate DTI development replay is in Appendix A.}',
        r'\label{tab:strong-effects}', r'\end{table}']
    return '\n'.join(lines)+'\n'

def publish_racing(base, out, public_path=PAPER/'provenance/v6_loop_summary.json'):
    snapshot = collect_racing(base, public_path)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out/'effects.tex').write_text(render(snapshot))
    (out/'racing_snapshot.json').write_text(json.dumps(snapshot, indent=2, allow_nan=False)+'\n')
    return snapshot

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--results', type=Path, default=ROOT/'results/unified_bio_20260918')
    parser.add_argument('--out', type=Path, default=PAPER/'tables/strong_v3')
    args = parser.parse_args()
    publish_racing(args.results, args.out)
