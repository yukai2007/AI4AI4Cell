"""Render the request-repair and laboratory-level selection replay table (E.9) from saved analyses."""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODES = (('direct', 'Direct'), ('raw', 'Raw history'), ('structured', 'Structured history'))
RULES = (('pooled', 'Pooled (original)'), ('median', 'Median lab gain'),
         ('lcb1', 'Mean $-$ 1 SE'), ('majority6', '$\\geq$6/10 labs'))
COLUMNS = (('qwen', 'dti', 'Qwen DTI'), ('qwen', 'protein', 'Qwen protein'),
           ('luna', 'dti', 'Luna DTI'), ('luna', 'protein', 'Luna protein'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def ms(arm):
    return f"${arm['mean']:.3f}$"


def delta(c):
    lo, hi = c['ci95_pp']
    return f"{{\\scriptsize${c['mean_pp']:+.2f}$ $[{lo:.2f}, {hi:.2f}]$}}"


def wtl(c):
    return f" ({c['wins']}/{c['ties']}/{c['losses']})"


def build():
    repair = json.loads((HERE / 'repair_analysis.json').read_text())
    replay = json.loads((HERE / 'replay_analysis.json').read_text())
    assert repair['status'] == replay['status'] == 'COMPLETE'
    assert repair['no_new_training'] is True
    groups = repair['groups']
    orig = json.loads((HERE.parent / 'rebuttal_round3_20261111/e9_eight_seed_analysis.json').read_text())
    invalid_orig = {m: sum(v[m]['invalid_slots'] for k, v in orig['all_selection_and_invalid_slot_outcomes'].items()
                           if k.startswith('qwen/') and m in v) for m, _ in MODES}
    invalid_new = {m: sum(c['invalid_slots'][m] for c in repair['costs'].values()) for m, _ in MODES}
    for task in ('dti', 'protein'):
        for m, _ in MODES:
            assert groups[task]['arms'][f'qwen_{m}']['per_seed'] == orig['groups'][f'qwen/{task}']['arms'][m]['per_seed']
    lines = [r'\begin{table}[htbp]',
             r'\caption{Retrospective sensitivity analyses on the eight-run expanded-recipe study (Table~\ref{tab:recipe-expansion-eight-seed}); '
             r'no new fits, all selections sealed before held-out scoring. Top: Qwen search rerun with registered canonicalization of redundant request metadata '
             r'(the named design is authoritative; invalid requests over 96 slots per mode, both tasks, original$\\to$repaired, in parentheses). '
             r'Bottom: three laboratory-level selection rules replayed over the sealed candidates of each structured-history search, with the paired difference '
             r'from the original pooled rule (wins/ties/losses in parentheses; second line: mean difference in percentage points and seed-block 95\% interval). Means over eight runs.}',
             r'\label{tab:round4-repair-selection}', r'\centering\footnotesize', r'\setlength{\tabcolsep}{2pt}',
             r'\begin{tabular}{lcccc}', r'\toprule',
             r' & \multicolumn{2}{c}{DTI AUROC} & \multicolumn{2}{c}{Protein AP} \\', r'Qwen mode (invalid) & original & repaired & original & repaired \\', r'\midrule']
    for m, label in MODES:
        lines.append(f"{label} ({invalid_orig[m]}$\\to${invalid_new[m]}) & {ms(groups['dti']['arms'][f'qwen_{m}'])} & {ms(groups['dti']['arms'][f'qwen_repaired_{m}'])} & "
                     f"{ms(groups['protein']['arms'][f'qwen_{m}'])} & {ms(groups['protein']['arms'][f'qwen_repaired_{m}'])} \\\\")
    lines.append(f"Random expectation & \\multicolumn{{2}}{{c}}{{{ms(groups['dti']['arms']['random'])}}} & \\multicolumn{{2}}{{c}}{{{ms(groups['protein']['arms']['random'])}}} \\\\")
    lines.append(f"GP--EI ($\\xi=.01$) & \\multicolumn{{2}}{{c}}{{{ms(groups['dti']['arms']['gp_ei'])}}} & \\multicolumn{{2}}{{c}}{{{ms(groups['protein']['arms']['gp_ei'])}}} \\\\")
    lines += [r'\midrule', r'Selection rule & ' + ' & '.join(c[2] for c in COLUMNS) + r' \\', r'\midrule']
    for rule, label in RULES:
        cells = []
        for p, t, _ in COLUMNS:
            g = replay['groups'][f'{p}/{t}/structured']
            cells.append(ms(g['arms'][rule]) + (wtl(g['contrasts'][f'{rule}_minus_pooled']) if rule != 'pooled' else ''))
        lines.append(label + ' & ' + ' & '.join(cells) + r' \\')
        if rule != 'pooled':
            lines.append(' & ' + ' & '.join(delta(replay['groups'][f'{p}/{t}/structured']['contrasts'][f'{rule}_minus_pooled'])
                                             for p, t, _ in COLUMNS) + r' \\[1pt]')
    lines += [r'\bottomrule', r'\end{tabular}', r'\end{table}', '']
    provenance = {'generator': Path(__file__).name, 'generator_sha256': sha(__file__),
                  'repair_analysis_sha256': sha(HERE / 'repair_analysis.json'),
                  'replay_analysis_sha256': sha(HERE / 'replay_analysis.json'),
                  'invalid_slots_qwen': {'original': invalid_orig, 'repaired': invalid_new},
                  'server_results': 'results/round4_20261111/{repair,replay}', 'new_training_fits': 0}
    return '\n'.join(lines), json.dumps(provenance, indent=2) + '\n'


def main():
    p = argparse.ArgumentParser(); p.add_argument('--check', action='store_true'); args = p.parse_args()
    table, provenance = build()
    outputs = {'round4.tex': table, 'provenance.json': provenance}
    for name, value in outputs.items():
        if args.check:
            assert (HERE / name).read_text() == value, name
        elif not (HERE / name).exists() or (HERE / name).read_text() != value:
            (HERE / name).write_text(value)
    print('PASS: round-4 table reproduces saved analyses')


if __name__ == '__main__':
    main()
