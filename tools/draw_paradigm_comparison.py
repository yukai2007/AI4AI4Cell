"""Vector schematic: accessible-data agents, local-update training, and their coupling.

The first two columns are conceptual configurations, not universal statements
about prior work. No task scores or privacy guarantees are implied by this asset.
"""
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

PAPER = Path(__file__).resolve().parents[1]
INK = '#213547'
BLUE = '#38638e'
TEAL = '#167969'
ORANGE = '#ad6a2d'
GRAY = '#657586'


def draw():
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'pdf.fonttype': 42,
                         'svg.fonttype': 'none', 'font.size': 15})
    fig, ax = plt.subplots(figsize=(10.5, 4.95))
    ax.set(xlim=(0, 12), ylim=(0, 5.65))
    ax.axis('off')

    def text(x, y, label, size=15, color=INK, weight='normal', **kwargs):
        kwargs.setdefault('ha', 'center')
        kwargs.setdefault('va', 'center')
        ax.text(x, y, label, fontsize=size, color=color, fontweight=weight,
                linespacing=1.22, **kwargs)

    def box(x, y, w, h, label, color, fill, size=15, weight='normal'):
        ax.add_patch(FancyBboxPatch((x, y), w, h,
            boxstyle='round,pad=0.015,rounding_size=0.08',
            linewidth=1.4, edgecolor=color, facecolor=fill))
        text(x+w/2, y+h/2, label, size, color, weight)

    def arrow(a, b, color=GRAY, bidirectional=False, style='-'):
        ax.add_patch(FancyArrowPatch(a, b, arrowstyle='<->' if bidirectional else '-|>',
            mutation_scale=13, linewidth=1.55, linestyle=style,
            shrinkA=3, shrinkB=3, color=color))

    def route(points, color, style='-'):
        ax.plot([p[0] for p in points[:-1]], [p[1] for p in points[:-1]],
                color=color, linewidth=1.55, linestyle=style)
        arrow(points[-2], points[-1], color, style=style)

    def labs(start, y=1.62):
        for offset, label in [(0, 'Lab 1'), (1.22, 'Lab 2'), (2.44, 'Lab 10')]:
            x = start+offset
            box(x, y, .98, .57, label, TEAL, '#e8f4ef', size=14)
            # A small lock body plus shackle marks local data, not a DP claim.
            ax.add_patch(Rectangle((x+.40, y-.24), .18, .15,
                                   linewidth=.9, edgecolor=TEAL, facecolor='#e8f4ef'))
            ax.plot([x+.435, x+.435, x+.545, x+.545],
                    [y-.09, y-.045, y-.045, y-.09], color=TEAL, linewidth=.9)
        text(start+2.32, y+.29, '...', 15, TEAL)

    # Large titles remain readable at the manuscript's full text width.
    for x, title, subtitle, color in [
        (2.0, 'Bio-agent research', 'Accessible-data loop', BLUE),
        (6.0, 'Collaborative training', 'Predefined-design updates', GRAY),
        (10.0, 'AI4AI4Bio', 'Collaborative research loop', TEAL)]:
        text(x, 5.26, title, 17.5, color, 'bold')
        text(x, 4.89, subtitle, 13.5, color)
    for x in (4, 8):
        ax.plot([x, x], [.51, 5.48], color='#d8e1e8', linewidth=1.05)

    # A: the agent can revise a model using feedback from accessible measurements.
    box(.38, 3.93, 3.22, .60, 'Research agent', BLUE, '#eef3fa', weight='bold')
    box(.72, 2.90, 2.54, .62, 'Train + evaluate', BLUE, '#eef3fa')
    box(.63, 1.67, 2.72, .64, 'Accessible bio data', BLUE, '#eef3fa', size=15)
    arrow((2, 3.91), (2, 3.54), BLUE)
    text(2.73, 3.73, 'design', 13, BLUE)
    arrow((2, 2.33), (2, 2.88), BLUE)
    route([(3.29, 3.20), (3.78, 3.20), (3.78, 4.23), (3.61, 4.23)], BLUE, '--')
    text(3.65, 3.71, 'feedback', 12, BLUE, rotation=90)
    text(2, 1.20, 'Iterative model designs', 15, BLUE, 'bold')
    text(2, .72, 'Additional labs require\naccessible measurements', 14, ORANGE)

    # B: private data can train a shared model while its design remains fixed.
    box(4.36, 3.93, 3.28, .60, 'Fixed model design', GRAY, '#f1f3f6', weight='bold')
    box(4.58, 2.90, 2.84, .62, 'Aggregate model updates', TEAL, '#e8f4ef', size=13.5)
    arrow((6, 3.91), (6, 3.54), GRAY)
    labs(4.28)
    for x in (4.77, 5.99, 7.21):
        arrow((6+(x-6)*.74, 2.89), (x, 2.21), TEAL, True)
    text(6, 2.60, 'model updates', 12, TEAL,
         bbox=dict(facecolor='white', edgecolor='none', pad=1.0))
    text(6, 1.20, 'Raw data stay local', 15, TEAL, 'bold')
    text(6, .72, 'Research design is fixed\nin this configuration', 14, GRAY)

    # C: aggregate evidence closes a shared design loop above collaborative training.
    box(8.33, 3.93, 3.34, .60, 'Shared research loop', BLUE, '#eef3fa', weight='bold')
    box(8.59, 2.90, 2.82, .62, 'Collaborative training', TEAL, '#e8f4ef', weight='bold')
    arrow((9.20, 3.91), (9.20, 3.54), BLUE)
    text(9.12, 3.74, 'design', 12, BLUE, ha='right')
    arrow((10.66, 3.54), (10.66, 3.91), BLUE, style='--')
    text(10.82, 3.73, 'evidence', 12, BLUE, ha='left')
    labs(8.28)
    for x in (8.77, 9.99, 11.21):
        arrow((10+(x-10)*.74, 2.89), (x, 2.21), TEAL, True)
    text(10, 2.60, 'model updates', 12, TEAL,
         bbox=dict(facecolor='white', edgecolor='none', pad=1.0))
    text(10, 1.20, 'Model + design learning', 15, TEAL, 'bold')
    text(10, .72, 'Evidence guides both\nparameters and model designs', 14, TEAL)

    text(6, .18, 'Complementary configurations, not an exhaustive taxonomy of prior methods.',
         12, GRAY)
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    for suffix in ('pdf', 'svg'):
        fig.savefig(PAPER/f'assets/paradigm_comparison.{suffix}', metadata={'Creator': 'AI4AI4Bio'})
    svg = PAPER/'assets/paradigm_comparison.svg'
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
    plt.close(fig)


if __name__ == '__main__':
    draw()
