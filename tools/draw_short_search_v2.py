"""Layout-only 5-column/2-row rendering of the frozen six-slot search study."""
from pathlib import Path
import hashlib
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator, ScalarFormatter

PAPER = Path(__file__).resolve().parents[1]
SOURCE = PAPER / 'tables/completed_ablation/snapshot.json'
OLD_RECEIPT = PAPER / 'tables/completed_ablation/provenance.json'
STEM = 'completed_short6_search_v2'
TASKS = [('native_tapb', 'DTI', 'AUROC'),
         ('ptpc_neural', 'Proteomics', 'AP'),
         ('vcc_corrected', 'VCC', 'Top-1'),
         ('norman_double_corrected', 'Norman', 'Top-1'),
         ('tahoe_drug_corrected', 'Tahoe', 'Top-1')]
COLORS = {'qwen': '#2166AC', 'luna': '#B35806'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def draw():
    source_hash = sha(SOURCE)
    old_receipt = json.loads(OLD_RECEIPT.read_text())
    assert old_receipt['outputs_sha256']['paper/tables/completed_ablation/snapshot.json'] == source_hash
    snapshot = json.loads(SOURCE.read_text())
    runs = {(r['task'], r['backend']): r for r in snapshot['loops'] if r['protocol'] == 'short6'}
    assert len(runs) == 10
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 7,
                         'axes.titlesize': 7.2, 'axes.labelsize': 7,
                         'xtick.labelsize': 6.5, 'ytick.labelsize': 6.5,
                         'pdf.fonttype': 42, 'svg.fonttype': 'none'})
    fig, axes = plt.subplots(2, 5, figsize=(5.5, 3.0), sharex='col')
    plotted = []
    for col, (task, title, metric) in enumerate(TASKS):
        for row, role in enumerate(('development', 'heldout')):
            ax = axes[row, col]
            for backend in ('qwen', 'luna'):
                run = runs[(task, backend)]
                assert run['slots'] == 6
                for mode in ('loop', 'direct'):
                    if role == 'development':
                        data = run['modes'][mode]['trajectory']
                        xs = [r['slot'] for r in data]
                        ys = [100 * r['primary'] for r in data]
                        assert xs == list(range(7))
                    else:
                        xs = [r['budget'] for r in run['prefixes']]
                        ys = [100 * r[mode + '_heldout_primary'] for r in run['prefixes']]
                        assert xs == [0, 1, 2, 4, 6]
                    assert np.isfinite(ys).all()
                    line, = ax.plot(xs, ys,
                        linestyle='--' if mode == 'direct' else '-', color=COLORS[backend],
                        linewidth=1.0 if mode == 'direct' else 1.5,
                        marker='x' if mode == 'direct' else 'o', markersize=2.7,
                        markerfacecolor='none', alpha=.95,
                        zorder=4 if mode == 'direct' else 3)
                    assert np.array_equal(line.get_xdata(), xs)
                    assert np.array_equal(line.get_ydata(), ys)
                    plotted.append(dict(task=task, backend=backend, mode=mode, role=role,
                                        seed=run['seed'], x=xs, y_times100=ys))
            if row == 0:
                ax.set_title(title + '\n' + metric + ' ×100', pad=5, linespacing=1.18)
            ax.set_xticks([0, 2, 4, 6])
            ax.set_xlim(-.25, 6.25)
            ax.tick_params(axis='both', labelsize=6.5, pad=1, length=2.3, width=.5)
            ax.yaxis.set_major_locator(MaxNLocator(3))
            ax.yaxis.set_major_formatter(ScalarFormatter(useOffset=False))
            ax.ticklabel_format(axis='y', style='plain', useOffset=False)
            ax.grid(color='#D9DEE5', linewidth=.45)
            ax.spines[['top', 'right']].set_visible(False)
            ax.spines[['left', 'bottom']].set_linewidth(.55)
            ax.margins(y=.12)
    handles = [Line2D([0], [0], color=COLORS[b],
        linestyle='--' if m == 'direct' else '-', marker='x' if m == 'direct' else 'o',
        markersize=3, markerfacecolor='none', linewidth=1.2,
        label=('Qwen' if b == 'qwen' else 'Luna') + ' ' + m)
        for b in ('qwen', 'luna') for m in ('direct', 'loop')]
    fig.legend(handles=handles, loc='upper center', bbox_to_anchor=(.54,.997),
               ncol=4, frameon=False, fontsize=6.7, columnspacing=1.0, handlelength=1.8,
               handletextpad=.45)
    fig.text(.014,.665,'Development', rotation=90, ha='center', va='center', fontsize=7.2)
    fig.text(.014,.294,'Held-out', rotation=90, ha='center', va='center', fontsize=7.2)
    fig.text(.54,.065,'Proposal slots (0 = initial design)', ha='center', va='center', fontsize=7.0)
    fig.subplots_adjust(left=.095, right=.988, bottom=.17, top=.80, wspace=.58, hspace=.43)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    canvas = fig.bbox
    labels = list(fig.texts) + [t for ax in axes.flat for t in
                              [ax.title, *ax.get_xticklabels(), *ax.get_yticklabels()]
                              if t.get_visible() and t.get_text()]
    for text in labels:
        b = text.get_window_extent(renderer)
        assert b.x0 >= canvas.x0 and b.x1 <= canvas.x1, 'Horizontal text overflow: ' + text.get_text()
        assert b.y0 >= canvas.y0 and b.y1 <= canvas.y1, 'Vertical text overflow: ' + text.get_text()
    paths = []
    for suffix in ('pdf','png'):
        path = PAPER / 'assets' / (STEM + '.' + suffix)
        fig.savefig(path, dpi=220, metadata={'Creator':'BioCoLoop frozen-snapshot short-search layout v2'})
        paths.append(path)
    plt.close(fig)
    assert sha(SOURCE) == source_hash
    receipt = dict(schema='short-search-layout-v2', source='tables/completed_ablation/snapshot.json',
        source_sha256=source_hash, source_unchanged=True,
        input_receipt_sha256=sha(OLD_RECEIPT), generator_sha256=sha(__file__),
        protocol='short6', dimensions_inches=[5.5,3.0], layout='5 columns x 2 rows; development above heldout',
        minimum_font_pt=6.5, panels=10, plotted_series=len(plotted),
        all_source_points_preserved=True, exact_line_array_validation=True,
        plot_data=plotted, text_within_canvas=True,
        artifacts_sha256={p.name:sha(p) for p in paths}, visual_review_status='PENDING')
    (PAPER/'assets'/(STEM+'.provenance.json')).write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k != 'plot_data'}))


if __name__ == '__main__':
    draw()
