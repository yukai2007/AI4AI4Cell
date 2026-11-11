"""Render the pre-registered eight-seed extensions of E.6 and E.9 from their saved analyses."""
from pathlib import Path
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
SEEDS = [61, 62, 63, 64, 65, 66, 67, 68]
E6_ARMS = (('fixed_D00', 'Fully trained fixed D00'), ('direct', 'Direct (no feedback)'),
           ('raw', 'Raw history'), ('structured', 'Structured history'),
           ('random', 'Random without replacement'), ('gp_ei', 'GP--EI'))
E6_CONTRASTS = (('structured_minus_direct', 'Structured $-$ Direct'),
                ('structured_minus_raw', 'Structured $-$ Raw'),
                ('structured_minus_random', 'Structured $-$ Random'),
                ('structured_minus_gp_ei', 'Structured $-$ GP--EI'),
                ('structured_minus_fixed_D00', 'Structured $-$ Fixed D00'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(name):
    path = HERE / f'{name}_eight_seed_analysis.json'
    data = json.loads(path.read_text())
    if data['status'] != 'COMPLETE' or data['n_seeds'] != 8:
        raise ValueError(f'{name}: complete eight-seed analysis required')
    reg = data['analysis_registration']
    if reg['old_seeds'] + reg['new_seeds'] != SEEDS and name == 'e6':
        raise ValueError(f'{name}: unexpected seed set')
    return path, data


def pm(arm):
    return f"${arm['mean']:.2f} \\pm {arm['seed_sd']:.2f}$"


def contrast_row(label, c):
    lo, hi = c['seed_block_ci95']
    return (f"{label} & ${c['mean_pp']:+.3f}$ & $[{lo:.3f}, {hi:.3f}]$ & "
            f"{c['wins']}/{c['ties']}/{c['losses']} \\\\")


def invalid_slots(data, arm):
    outcomes = data['all_selection_and_invalid_slot_outcomes']
    return sum(v[arm]['invalid_slots'] for v in outcomes.values() if arm in v)


def render_e6():
    path, data = load('e6')
    group = data['groups']['qwen/cell']
    if group['seed_order'] != SEEDS:
        raise ValueError('e6: seed order changed')
    arms, contrasts = group['arms'], group['contrasts']
    best = max(arms[k]['mean'] for k, _ in E6_ARMS)
    lines = [
        r'\begin{table}[htbp]',
        r'\caption{Eight-seed extension of the gene-disjoint cell comparison (Table~\ref{tab:fresh-history-comparison}). '
        r'Seeds 61--63 are the original runs; seeds 64--68 were added under an analysis fixed before their fits, '
        r'with no replacement seeds or exclusions. Held-out Top-1 is in percent; $\pm$ is the sample SD over the eight seeds. '
        r'Intervals resample the eight training/controller seeds as paired blocks (100,000 draws), so they describe run-to-run variation, '
        r'unlike the test-gene intervals of Table~\ref{tab:fresh-history-comparison}. '
        f"Invalid slots over 48: raw {invalid_slots(data, 'raw')}, structured {invalid_slots(data, 'structured')}, direct {invalid_slots(data, 'direct')}; "
        r'invalid requests consume their slots. Bold marks the best mean.}',
        r'\label{tab:fresh-history-eight-seed}',
        r'\centering\small',
        r'\setlength{\tabcolsep}{3pt}',
        r'\begin{tabularx}{\linewidth}{@{}Xrrr@{}}',
        r'\toprule',
        r'Search method & Held-out Top-1 & & \\',
        r'\midrule',
    ]
    for key, label in E6_ARMS:
        cell = pm(arms[key])
        if arms[key]['mean'] == best:
            cell = f"$\\mathbf{{{arms[key]['mean']:.2f} \\pm {arms[key]['seed_sd']:.2f}}}$"
        lines.append(f'{label} & {cell} & & \\\\')
    lines += [r'\midrule',
              r'\multicolumn{4}{l}{\textit{Paired held-out contrasts (percentage points)}} \\',
              r'Contrast & Mean difference & 95\% CI & W/T/L \\']
    lines += [contrast_row(label, contrasts[key]) for key, label in E6_CONTRASTS]
    lines += [r'\bottomrule', r'\end{tabularx}', r'\end{table}', '']
    (HERE / 'e6_eight_seed.tex').write_text('\n'.join(lines))
    return {'analysis': path.name, 'analysis_sha256': sha(path),
            'registration': data['analysis_registration'],
            'score_sha256': data.get('score_sha256'),
            'evaluation_gate_sha256': data.get('evaluation_gate_sha256')}


if __name__ == '__main__':
    provenance = {'generator': Path(__file__).name, 'generator_sha256': sha(__file__)}
    studies = sys.argv[1:] or ['e6']
    if 'e6' in studies:
        provenance['e6'] = render_e6()
    if 'e9' in studies:
        from build_e9 import render_e9  # added once the E.9 extension completes
        provenance['e9'] = render_e9(load)
    (HERE / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
