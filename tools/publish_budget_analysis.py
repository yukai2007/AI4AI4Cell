"""Publish trajectory diagnostics bound to the verified Appendix B snapshot."""
from pathlib import Path
import hashlib
import json

from publish_core_review import make_table

PAPER = Path(__file__).resolve().parents[1]
RESULTS = PAPER.parent / 'results/core_ablation_20260922'
ANALYSIS = RESULTS / 'analysis/loop_budget_audit_20260923'

def read(path):
    return json.loads(path.read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    snapshot_path = PAPER / 'tables/core_review/snapshot.json'
    snapshot = read(snapshot_path)
    analysis = read(ANALYSIS / 'summary.json')
    if analysis['publication_snapshot']['sha256'] != sha(snapshot_path):
        raise ValueError('Repeat trajectory analysis after updating the paper snapshot')
    jobs = analysis['jobs']
    if {j['relative_path'] + '/heldout/results.json' for j in jobs} != set(snapshot['curves']):
        raise ValueError('The analysis must cover every completed published loop job')
    receipts = read(ANALYSIS / 'input_receipts.json')
    for relative, expected in receipts.items():
        if sha(RESULTS / relative) != expected:
            raise ValueError('Trajectory input changed after analysis: ' + relative)
    names = {'native_tapb': 'DTI', 'ptpc_neural': 'PTPC', 'vcc_corrected': 'VCC',
             'norman_double_corrected': 'Norman', 'tahoe_drug_corrected': 'Tahoe'}
    rows = []
    for task in names:
        subset = sorted([j for j in jobs if j['task'] == task], key=lambda j: (j['seed'], j['backend']))
        for job in subset:
            d, l = job['modes']['direct'], job['modes']['loop']
            comparison = job['comparisons']
            arrival = comparison['first_slot_at_common_target']
            first = '/'.join(str(arrival[m]) if arrival[m] is not None else '--' for m in ('direct', 'loop'))
            rows.append([names[task], 'Qwen' if job['backend'] == 'qwen' else 'Luna', job['seed'],
                         f"{100*comparison['common_development_primary_target']:.2f}", first,
                         f"{d['valid']}/{l['valid']}", f"{d['unvisited_menu_designs']}/{l['unvisited_menu_designs']}"])
    make_table(PAPER / 'tables/core_review/search_dynamics.tex',
        r'Task & Proposer & Seed & Dev. target & First slot D/L & Valid D/L & Unvisited D/L', rows,
        r'Search dynamics at 24 proposal slots. D/L denotes direct/loop. The development target is the higher terminal primary score in each paired comparison; first slot records its earliest attainment, and -- means not attained. This target is a retrospective diagnostic, not a stopping rule. Slot 0 is the initial design; valid counts exclude it. Unvisited counts are relative to all 36 configurations, including the initial design. The table covers every completed trajectory in the published snapshot.',
        'tab:core-search-dynamics', 'Xlcrrrr')
    payload = dict(schema='published-budget-analysis-v1', snapshot_sha256=sha(snapshot_path),
                   analysis_sha256=sha(ANALYSIS / 'summary.json'), source_sha256=receipts,
                   jobs=jobs, methodology=analysis['methodology'])
    (PAPER / 'tables/core_review/budget_analysis.json').write_text(json.dumps(payload, indent=2) + '\n')
    print(f'Published search diagnostics for {len(jobs)} complete paired jobs.')

if __name__ == '__main__':
    main()
