"""Publish aggregate-only review evidence; never train or select a checkpoint."""
from pathlib import Path
import argparse
import hashlib
import json
import math

PAPER = Path(__file__).resolve().parents[1]
PROJECT = PAPER.parent
RESULTS = PROJECT / 'results/rebuttal_20261109'
OUT = PAPER / 'tables/rebuttal_20261109'
TASKS = ['native_tapb', 'ptpc_neural', 'vcc_corrected',
         'norman_double_corrected', 'tahoe_drug_corrected']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def export():
    search_dir = RESULTS / 'search_controls/v2'
    validation_dir = RESULTS / 'validation'
    roster_dir = validation_dir / 'roster_sensitivity'
    search = read(search_dir / 'summary.json')
    validation = read(validation_dir / 'summary.json')
    roster = read(roster_dir / 'summary.json')
    for record in [search, validation, roster]:
        assert record['status'] == 'COMPLETE'
        assert record['new_training_fits'] == record['new_llm_calls'] == 0
    assert set(search['tasks']) == set(TASKS)
    assert validation['development_checkpoint_evaluations'] == 14
    assert roster['seeds'] == list(range(2026110900, 2026110920))
    assert validation['new_heldout_inference'] is False
    assert roster['new_test_inference'] is False
    assert set(validation['tasks']) == set(roster['tasks']) == {'vcc_corrected', 'tahoe_drug_corrected'}
    for task, expected in [('vcc_corrected', 2), ('tahoe_drug_corrected', 6)]:
        panels = validation['tasks'][task]['panel_sizes']
        assert validation['tasks'][task]['seed'] == 61 and len(panels) == 10
        assert all(p['n_interventions'] == expected for p in panels)
    seal_sha = sha(search_dir / 'selection_seal.json')
    for task, task_record in search['tasks'].items():
        scores = read(search_dir / task / 'scores.json')
        assert scores['verification']['status'] == 'PASS'
        assert scores['selection_seal_sha256'] == seal_sha
        assert task_record['scores_sha256'] == sha(search_dir / task / 'scores.json')
        assert task_record['seed'] == (42 if task == 'native_tapb' else 61)
        for policy, value in task_record['policies'].items():
            primary = value.get('primary', value.get('mean'))
            assert math.isfinite(primary) and 0 <= primary <= 1
            assert value['logical_rounds'] <= 700
        assert task_record['policies']['random_6']['subsets'] == 462
    compact_validation = {k: v for k, v in validation.items() if k != 'source_sha256'}
    compact_roster = {k: v for k, v in roster.items() if k != 'source_sha256'}
    source_files = [search_dir / n for n in ['summary.json', 'protocol.json',
        'selection_seal.json', 'development_prefix_analysis.json']]
    source_files += [validation_dir / 'summary.json', roster_dir / 'summary.json',
                     roster_dir / 'protocol.json']
    snapshot = dict(schema='biocoloop-review-evidence-v1', status='COMPLETE',
        matched_search=search, validation=compact_validation, roster=compact_roster,
        development_prefix=read(search_dir / 'development_prefix_analysis.json'),
        source_sha256={str(p.relative_to(PROJECT)): sha(p) for p in source_files})
    heterogeneous_path = PROJECT / 'results/supplement_history_20261007/analysis/analysis.json'
    luna_path = PROJECT / 'results/heterolab_feedback_20261019/luna/evaluation_summary.json'
    heterogeneous, luna = read(heterogeneous_path), read(luna_path)
    assert heterogeneous['status'] == luna['status'] == 'COMPLETE'
    hetero_rows = {}
    for task in ('protein', 'cell'):
        original = heterogeneous['tasks'][task]
        metric = original['primary_metric']
        hetero_rows[task] = {}
        for method in ('fixed', 'random', 'direct', 'loop'):
            cell = original['methods'][method][metric]
            assert cell['n_seeds'] == 3
            hetero_rows[task][method] = dict(mean=cell['mean'],
                sd=cell['sample_sd_across_training_seeds'])
        for method in ('direct', 'legacy_history', 'repaired_history'):
            cell = luna['tasks'][task]['methods'][method]['heldout_primary']
            assert cell['n'] == 3
            hetero_rows[task]['luna_' + method] = dict(mean=cell['mean'], sd=cell['sample_sd'])
    snapshot['source_defined_search'] = dict(training_seeds=[61, 62, 63],
        training_labs=4, metrics_times_100=False, rows=hetero_rows)
    for path in (heterogeneous_path, luna_path):
        snapshot['source_sha256'][str(path.relative_to(PROJECT))] = sha(path)
    for methods in hetero_rows.values():
        for cell in methods.values():
            assert math.isfinite(cell['mean']) and 0 <= cell['mean'] <= 1
            assert math.isfinite(cell['sd']) and cell['sd'] >= 0
    def no_private_rows(value):
        if isinstance(value, dict):
            forbidden = {'choices', 'query_ids', 'intervention', 'rank', 'raw_response', 'response', 'query_scores'}
            assert not forbidden.intersection(value)
            for item in value.values():
                no_private_rows(item)
        elif isinstance(value, list):
            for item in value:
                no_private_rows(item)
    no_private_rows(snapshot)
    encoded = json.dumps(snapshot, ensure_ascii=False, indent=2) + '\n'
    assert '/liziqing/' not in encoded, 'Host path in public aggregate'
    files = {'snapshot.json': encoded,
        'matched_search_full.tex': (search_dir / 'matched_search_table.tex').read_text(),
        'validation.tex': (validation_dir / 'validation_table.tex').read_text(),
        'roster.tex': (roster_dir / 'roster_table.tex').read_text()}
    # Compact main-text rendering; full conditional policy SD remains in E.
    rows = [('fixed', 'Fixed model'), ('random_6', 'Random, exact expectation'),
            ('gp_ei_6', 'GP--EI'), ('qwen_direct', 'Qwen direct'),
            ('qwen_loop', 'Qwen history'), ('luna_direct', 'Luna direct'),
            ('luna_loop', 'Luna history')]
    lines = [r'\begin{table}[t]',
        r'\caption{Same-access search: all methods use ten laboratories and the same development panels. Searches use twelve designs, six proposal slots and at most 700 aggregation rounds, including initialization; the fixed reference uses 100 rounds. Scores $\times100$ are conditional on one training seed per task (DTI 42; others 61), not the three-seed access comparison. Random is its exact policy expectation; variability and actual-fit sensitivities are in Appendix E. Bold marks the best unrounded score, including ties.}',
        r'\label{tab:rebuttal-matched-search-main}', r'\centering\small',
        r'\setlength{\tabcolsep}{4pt}', r'\begin{tabular}{@{}lrrrrr@{}}', r'\toprule',
        r'Method & DTI & Proteomics & VCC & Norman & Tahoe \\',
        r' & AUROC $\uparrow$ & AP $\uparrow$ & Top-1 $\uparrow$ & Top-1 $\uparrow$ & Top-1 $\uparrow$ \\',
        r'\midrule']
    get = lambda task, policy: search['tasks'][task]['policies'][policy].get(
        'primary', search['tasks'][task]['policies'][policy].get('mean'))
    for policy, label in rows:
        cells = []
        for task in TASKS:
            value = get(task, policy)
            rendered = f'{100 * value:.2f}'
            if abs(value - max(get(task, p) for p, _ in rows)) < 1e-12:
                rendered = r'\textbf{' + rendered + '}'
            cells.append(rendered)
        lines.append(' & '.join([label] + cells) + r' \\')
    lines.extend([r'\bottomrule', r'\end{tabular}', r'\end{table}', ''])
    files['matched_search_main.tex'] = '\n'.join(lines)
    hlines = [r'\begin{table}[t]',
        r'\caption{Search with source-defined laboratories. Protein: PTPC, Lin, Ruprecht and decryptE; cell: VCC, Replogle, Nadig and Jiang. All methods share four training sources and the target development panels. Searches use twelve designs, six proposal slots and at most 700 rounds; the fixed reference uses 100 rounds. Mean $\pm$ sample SD over training/search seeds 61--63; scores $\times100$. Random reports the exact policy expectation per seed, then its between-seed SD. Luna uses the same checkpoint cache but new proposal calls.}',
        r'\label{tab:rebuttal-source-history}', r'\centering\small',
        r'\begin{tabular}{lrr}', r'\toprule',
        r'Method & Proteomic AP $\uparrow$ & Cell macro Top-1 $\uparrow$ \\', r'\midrule']
    for method, label in [('fixed', 'Fixed design'), ('random', 'Random, exact expectation'),
                         ('direct', 'Qwen direct'), ('loop', 'Qwen history'),
                         ('luna_direct', 'Luna direct'), ('luna_legacy_history', 'Luna history'),
                         ('luna_repaired_history', 'Luna enriched history')]:
        cells = []
        for task in ('protein', 'cell'):
            v = hetero_rows[task][method]
            cells.append(f'${100*v["mean"]:.2f}\\pm{100*v["sd"]:.2f}$')
        hlines.append(' & '.join([label] + cells) + r' \\')
    hlines.extend([r'\bottomrule', r'\end{tabular}', r'\end{table}', ''])
    files['source_history.tex'] = '\n'.join(hlines)
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    outputs = export()
    for name, contents in outputs.items():
        if args.check:
            assert (OUT / name).read_text() == contents, name
        else:
            OUT.mkdir(parents=True, exist_ok=True)
            (OUT / name).write_text(contents)
    print(json.dumps(dict(status='PASS', files=list(outputs), new_training=False)))


if __name__ == '__main__':
    main()
