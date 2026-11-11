"""Render the eight-seed extension of the expanded-recipe study (E.9) from its saved analysis."""
from build_eight_seed import HERE, sha

GROUPS = (('qwen/dti', 'Qwen DTI'), ('qwen/protein', 'Qwen protein'),
          ('luna/dti', 'Luna DTI'), ('luna/protein', 'Luna protein'))
ARMS = (('fixed_D00', 'Fully fitted D00'), ('direct', 'Direct'), ('raw', 'Raw history'),
        ('structured', 'Structured history'), ('random', 'Random expectation'),
        ('gp_ei', 'GP--EI ($\\xi=.01$)'), ('gp_ei_zero', 'GP--EI ($\\xi=0$)'))
CONTRASTS = (('structured_minus_direct', 'Structured $-$ Direct'),
             ('structured_minus_raw', 'Structured $-$ Raw'),
             ('structured_minus_random', 'Structured $-$ Random'),
             ('structured_minus_gp_ei', 'Structured $-$ GP--EI ($\\xi=.01$)'),
             ('structured_minus_gp_ei_zero', 'Structured $-$ GP--EI ($\\xi=0$)'))


def cell(arm, best):
    text = f"{arm['mean']:.3f} \\pm {arm['seed_sd']:.3f}"
    return f"$\\mathbf{{{text}}}$" if abs(arm['mean'] - best) < 1e-10 else f"${text}$"


def contrast_cells(c):
    lo, hi = c['seed_block_ci95']
    return f"${c['mean_pp']:+.3f}$ ({c['wins']}/{c['ties']}/{c['losses']})", f"{{\\scriptsize$[{lo:.2f}, {hi:.2f}]$}}"


def render_e9(load):
    path, data = load('e9')
    groups = data['groups']
    missing = [g for g, _ in GROUPS if g not in groups]
    if missing:
        raise ValueError(f'e9: missing groups {missing}')
    seeds = groups[GROUPS[0][0]]['seed_order']
    if len(seeds) != 8 or any(groups[g]['seed_order'] != seeds for g, _ in GROUPS):
        raise ValueError('e9: seed order differs across groups')
    for g, _ in GROUPS:
        for key, _ in ARMS:
            if key not in groups[g]['arms']:
                raise ValueError(f'e9: {g} lacks arm {key}')
        for key, _ in CONTRASTS:
            if key not in groups[g]['contrasts']:
                raise ValueError(f'e9: {g} lacks contrast {key}')
    invalid = {p: {a: sum(v[a]['invalid_slots'] for k, v in data['all_selection_and_invalid_slot_outcomes'].items()
                          if k.startswith(p + '/') and a in v) for a in ('direct', 'raw', 'structured')}
               for p in ('qwen', 'luna')}
    slots = 6 * 8 * 2
    note = '; '.join(f"{p.capitalize()} direct/raw/structured {invalid[p]['direct']}/{invalid[p]['raw']}/{invalid[p]['structured']}"
                     for p in ('qwen', 'luna'))
    lines = [
        r'\begin{table}[htbp]',
        r'\caption{Eight-seed extension of the expanded-recipe comparison (Table~\ref{tab:expanded-recipe-results}). '
        r'The original three head-training/controller runs are retained; five runs were added under an analysis fixed before their fits, '
        r'with no replacement seeds or exclusions. Each run keeps the same 36 designs, ten training laboratories, six requests, '
        r'20-round fits and the shared seed-42 starting predictor per task. Scores are percentages; $\pm$ is the sample SD over the eight runs. '
        r'Contrasts give the mean paired difference in percentage points, a seed-block bootstrap 95\% interval (100,000 draws) and wins/ties/losses over the eight runs. '
        f'Invalid requests over {slots} per proposer and arm: {note}; they consume their slots. Bold marks the best mean per column, including ties.}}',
        r'\label{tab:recipe-expansion-eight-seed}',
        r'\centering\footnotesize',
        r'\setlength{\tabcolsep}{2pt}',
        r'\begin{tabular*}{\linewidth}{@{\extracolsep{\fill}}lrrrr@{}}',
        r'\toprule',
        'Policy & ' + ' & '.join(label for _, label in GROUPS) + r' \\',
        r'\midrule',
    ]
    best = {g: max(groups[g]['arms'][k]['mean'] for k, _ in ARMS) for g, _ in GROUPS}
    for key, label in ARMS:
        lines.append(label + ' & ' + ' & '.join(cell(groups[g]['arms'][key], best[g]) for g, _ in GROUPS) + r' \\')
    lines += [r'\midrule', r'\multicolumn{5}{@{}l}{\textit{Paired contrasts (percentage points), 95\% interval, W/T/L}} \\']
    for key, label in CONTRASTS:
        pairs = [contrast_cells(groups[g]['contrasts'][key]) for g, _ in GROUPS]
        lines.append(label + ' & ' + ' & '.join(a for a, _ in pairs) + r' \\')
        lines.append(' & ' + ' & '.join(b for _, b in pairs) + r' \\[1pt]')
    lines += [r'\bottomrule', r'\end{tabular*}', r'\end{table}', '']
    (HERE / 'e9_eight_seed.tex').write_text('\n'.join(lines))
    return {'analysis': path.name, 'analysis_sha256': sha(path), 'registration': data['analysis_registration'],
            'score_sha256': data.get('score_sha256'), 'evaluation_gate_sha256': data.get('evaluation_gate_sha256'),
            'invalid_slots': invalid}
