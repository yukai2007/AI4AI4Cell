"""Expose laboratory access without changing any frozen scored result.

The historical table stays byte-identical. This rendering removes the average
rank over unevenly completed endpoints and adds the actual lab count instead.
"""
from pathlib import Path
import argparse
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'tables/public_harness_comparison/main_public_harness_three_seed.tex'
OUTPUT = ROOT / 'tables/rebuttal_20261109/access_scenario.tex'


def render(source):
    lines = [r'\providecommand{\TblPartial}{\textsuperscript{$\dagger$}}',
             r'\providecommand{\TblZero}{--}',
             r'\providecommand{\TblStar}{\textsuperscript{$\star$}}',
             r'\begin{table}[t]',
             r'\caption{Collaboration-versus-local reference: BioCoLoop with ten participating laboratories beside workflows run by one laboratory, the usual federated comparison of collaborative and local-only development. Scores $\times100$ are mean $\pm$ sample SD over seeds 42--44. Data and local computation differ with access, so rows across the two access levels compare complete scenarios rather than search methods; Appendix Table~\ref{tab:single-lab-search} adds a ten-laboratory fixed model. Cell Top-1 chooses among five candidates (chance: 20\%). Bold and underline indicate the best and second-best complete scores within each block. $\dagger$: two scored seeds; --: no sealed score; $\star$: extended-context adaptation. Execution outcomes are in Appendix C; same-access search is in Section~4.7.}',
             r'\label{tab:public-harness-comparison-three-seed}',
             r'\centering\footnotesize', r'\setlength{\tabcolsep}{3pt}',
             r'\renewcommand{\arraystretch}{1.02}',
             r'\begin{tabular}{@{}lrccccc@{}}', r'\toprule',
             r'Method & Labs & DTI & Proteomics & \multicolumn{3}{c}{Cell perturbation (Top-1)} \\',
             r'\cmidrule(lr){3-3}\cmidrule(lr){4-4}\cmidrule(l){5-7}',
             r' & & AUROC $\uparrow$ & AP $\uparrow$ & VCC $\uparrow$ & Norman $\uparrow$ & Tahoe $\uparrow$ \\',
             r'\midrule']
    count = 0
    for line in source.splitlines():
        if line.startswith(r'\multicolumn{7}'):
            if count:
                lines.append(r'\midrule')
            lines.append(line)
        elif line.startswith(('Fixed model &', 'Direct &', 'AI-Scientist-v2 &',
                              'AI-Researcher &', r'\textbf{BioCoLoop} &')):
            fields = line.split(' & ')
            if len(fields) != 7:
                raise ValueError('Unexpected historical result row')
            labs = '10' if 'BioCoLoop' in fields[0] else '1'
            lines.append(' & '.join([fields[0], labs] + fields[1:6]) + r' \\')
            count += 1
    if count != 10:
        raise ValueError('Expected ten historical result rows')
    lines.extend([r'\bottomrule', r'\end{tabular}', r'\end{table}', ''])
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    text = render(SOURCE.read_text())
    if args.check:
        assert OUTPUT.read_text() == text, 'Access rendering differs'
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(text)
        OUTPUT.with_suffix('.provenance.json').write_text(json.dumps({
            'source': str(SOURCE.relative_to(ROOT)),
            'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
            'numeric_score_cells_changed': 0,
            'change': 'Explicit labs column; remove incomplete-endpoint mean ranks; clarify estimand',
        }, indent=2) + '\n')


if __name__ == '__main__':
    main()
