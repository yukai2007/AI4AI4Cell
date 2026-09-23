"""Render laboratory-count curves from the verified publication snapshot."""
from pathlib import Path
import hashlib
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tables/completed_ablation/snapshot.json"

def main():
    rows = json.loads(SOURCE.read_text())["laboratory"]
    tasks = ["native_tapb", "ptpc_neural", "vcc_corrected",
             "norman_double_corrected", "tahoe_drug_corrected"]
    labels = ["DTI\nAUROC", "Proteomics\nAP", "VCC\nTop-1",
              "Norman\nTop-1", "Tahoe\nTop-1"]
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9,
                         "pdf.fonttype": 42, "ps.fonttype": 42})
    fig, axes = plt.subplots(1, 5, figsize=(7.5, 2.2), constrained_layout=False)
    plotted = {}
    for ax, task, label in zip(axes, tasks, labels):
        for family, color, style, marker, legend in [
            ("participation", "#2463A5", "-", "o", "More clients + data"),
            ("partition", "#B5632E", "--", "s", "Fixed data pool")]:
            row, = [r for r in rows if r["task"] == task and r["family"] == family]
            keys = [1, 2, 5, 10]
            samples = [100 * np.asarray(row["by_k"][str(k)], dtype=float) for k in keys]
            values = [float(v.mean()) for v in samples]
            ax.plot(range(len(keys)), values, color=color, linestyle=style, marker=marker,
                    linewidth=1.5, markersize=3.5, label=legend)
            plotted[task + "/" + family] = dict(k=keys, means=values,
                samples=[v.tolist() for v in samples])
        ax.set_title(label, fontsize=10)
        ax.set_xticks([0, 1, 2, 3], ['1', '2', '5', '10'])
        ax.set_xlabel("K", fontsize=9)
        ax.tick_params(labelsize=9)
        ax.grid(axis="y", alpha=.18)
        ax.spines[["right", "top"]].set_visible(False)
    axes[0].set_ylabel("Score (%)")
    handles, names = axes[0].get_legend_handles_labels()
    fig.legend(handles, names, loc="lower center", ncol=2, frameon=False,
               bbox_to_anchor=(.5, -.025), fontsize=10)
    fig.subplots_adjust(left=.067, right=.985, bottom=.30, top=.74, wspace=.63)
    out = ROOT / "assets/laboratory_sensitivity_v2.pdf"
    fig.savefig(out)
    fig.savefig(out.with_suffix(".png"), dpi=200)
    plt.close(fig)
    receipt = dict(source=str(SOURCE.relative_to(ROOT)),
                   source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                   plotted=plotted, x_axis="Categorical tested K settings: 1, 2, 5, 10", standard_deviations="full values in Appendix B; no CI implied")
    out.with_suffix(".json").write_text(json.dumps(receipt, indent=2) + "\n")

if __name__ == "__main__":
    main()
