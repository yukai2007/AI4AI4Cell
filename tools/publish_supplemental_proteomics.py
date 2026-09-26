"""Render the four fixed-source controls from the independently verified receipt.

This publisher performs no fitting, selection, rescoring, or source filtering.
"""
import hashlib
import json
from pathlib import Path

PAPER = Path(__file__).resolve().parents[1]
ROOT = PAPER.parent
STUDY = ROOT / 'results/supplemental_20260923/proteomics/seed61_slots0_cpu'
OUT = PAPER / 'tables/supplemental_20260923'
PROVENANCE = PAPER / 'provenance/supplemental_proteomics_20260923'
ARMS = [('target_only_fixed', 'Target only'),
        ('plus_decrypte_fixed', '+ decryptE'),
        ('plus_existing2_fixed', '+ Lin + Ruprecht'),
        ('plus_all3_fixed', '+ Lin + Ruprecht + decryptE')]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    receipt_path = STUDY / 'independent_rescore.json'
    receipt = json.loads(receipt_path.read_text())
    assert receipt['status'] == 'COMPLETE_VERIFIED'
    assert receipt['fixed_design_only'] and receipt['proposal_slots'] == 0
    assert receipt['seed'] == 61 and receipt['rounds'] == 100
    assert receipt['device'] == 'cpu'
    assert sha(STUDY / 'heldout/results.json') == receipt['results_sha256']
    assert sha(STUDY / 'definition.json') == receipt['definition_sha256']
    assert set(receipt['results']) == {arm for arm, _ in ARMS}
    for item in receipt['results'].values():
        assert item['max_absolute_error'] == 0.0
    OUT.mkdir(parents=True, exist_ok=True)
    PROVENANCE.mkdir(parents=True, exist_ok=True)
    lines = [r'\begin{table}[htbp]',
             r'\caption{Three-source proteomic transfer on PTPC. All four arms use the same four-head adapter, seed 61, 100-round fitting schedule and target-development checkpoint rule. AP and AUROC are multiplied by 100; bold identifies the best value in each metric. The target test set contains 148 observations from 92 compounds. These are fixed-design source comparisons; the separate two-source proposal study appears in Table~\ref{tab:completed-protein-loop}.}',
             r'\label{tab:supplemental-protein-three-source}',
             r'\centering\small',
             r'\setlength{\tabcolsep}{5pt}',
             r'\begin{tabularx}{\linewidth}{@{}Xrrr@{}}',
             r'\toprule',
             r'Additional source & AP $\uparrow$ & AUROC $\uparrow$ & $\Delta$ AP (pp) \\',
             r'\midrule']
    baseline = receipt['results']['target_only_fixed']['metrics']['ap']
    best = {metric: max(round(100 * item['metrics'][metric], 2)
                        for item in receipt['results'].values())
            for metric in ('ap', 'auroc')}
    for arm, label in ARMS:
        metric = receipt['results'][arm]['metrics']
        values = []
        for name in ('ap', 'auroc'):
            value = 100 * metric[name]
            cell = f'{value:.2f}'
            values.append(r'\textbf{' + cell + '}' if round(value, 2) == best[name] else cell)
        values.append(f"{100 * (metric['ap'] - baseline):+.2f}")
        lines.append(' & '.join([label] + values) + r' \\')
    lines += [r'\bottomrule', r'\end{tabularx}', r'\end{table}']
    target = OUT / 'proteomics_three_source.tex'
    target.write_text('\n'.join(lines) + '\n')
    snapshot = dict(schema='supplemental-proteomics-publication-v1',
        verified_receipt=receipt,
        receipt_path=str(receipt_path.relative_to(ROOT)),
        receipt_sha256=sha(receipt_path),
        table_path=str(target.relative_to(PAPER)), table_sha256=sha(target),
        publisher_sha256=sha(Path(__file__)),
        scope='Four fixed-design source arms; not agentic-loop evidence')
    (PROVENANCE / 'snapshot.json').write_text(json.dumps(snapshot, indent=2) + '\n')
    print(json.dumps({'status': 'PUBLISHED_VERIFIED', 'arms': 4, 'table': str(target)}))


if __name__ == '__main__':
    main()
