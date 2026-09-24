"""Draw a readable, vector three-paradigm figure at its final 5.5-inch width."""
from pathlib import Path
import hashlib
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

PAPER = Path(__file__).resolve().parents[1]
INK = "#172B3A"
SECONDARY = "#536475"
DATA, DATA_FILL = "#238B7B", "#E7F5F2"
MODEL, MODEL_FILL = "#356FA3", "#E8F1F8"
HARNESS, HARNESS_FILL = "#76539A", "#F1EAF7"
GATE, GATE_FILL = "#C76A28", "#FBEDE3"
GHOST, GHOST_FILL = "#8B98A3", "#F4F6F7"
DIVIDER = "#D9E0E5"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def draw() -> None:
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7,
                         "pdf.fonttype": 42, "svg.fonttype": "none"})
    # Draw at the manuscript's actual width: fonts are not halved at inclusion.
    # Height grows only 2.0% relative to the previous figure at this width.
    fig, ax = plt.subplots(figsize=(5.5, 3.05))
    ax.set(xlim=(0, 12), ylim=(0, 6.65))
    ax.axis("off")
    text_bounds, all_labels, active_fonts = [], [], []

    def label(x, y, value, size=7, color=INK, weight="normal", **kwargs):
        kwargs.setdefault("ha", "center")
        kwargs.setdefault("va", "center")
        artist = ax.text(x, y, value, fontsize=size, color=color,
                         fontweight=weight, linespacing=1.10, zorder=8, **kwargs)
        all_labels.append(artist)
        return artist

    def box(x, y, w, h, value, role, active=True, size=7.2, weight="bold"):
        palette = {"data": (DATA, DATA_FILL), "model": (MODEL, MODEL_FILL),
                   "harness": (HARNESS, HARNESS_FILL), "gate": (GATE, GATE_FILL)}
        edge, fill = palette[role] if active else (GHOST, GHOST_FILL)
        ax.add_patch(FancyBboxPatch((x, y), w, h,
            boxstyle="round,pad=0.015,rounding_size=0.07", linewidth=.65,
            edgecolor=edge, facecolor=fill,
            linestyle="-" if active else (0, (3, 2)), zorder=5))
        artist = label(x+w/2, y+h/2, value, size, edge, weight)
        text_bounds.append((artist, (x, y, w, h)))
        if active:
            active_fonts.append(size)

    def arrow(start, end, color, bidirectional=False):
        ax.add_patch(FancyArrowPatch(start, end,
            arrowstyle="<|-|>" if bidirectional else "-|>",
            mutation_scale=6, linewidth=.65, color=color,
            shrinkA=.65, shrinkB=.65, zorder=3))

    def route(points, color):
        for p, q in zip(points[:-2], points[1:-1]):
            ax.plot([p[0], q[0]], [p[1], q[1]], color=color, linewidth=.65, zorder=2)
        arrow(points[-2], points[-1], color)

    def blueprint(x0, mode):
        box(x0+.55, 5.03, 2.65, .67, "Research harness\nPropose · remember",
            "harness", mode in {"central", "ours"})
        box(x0+.68, 4.00, 2.39, .65, "Model design\n+ predictor", "model")
        box(x0+.68, 2.88, 2.39, .65,
            "Local fitting\n+ evaluation" if mode=="central" else "Aggregate updates\n+ scores",
            "model" if mode=="central" else "gate", size=7.0)
        lab_x = (x0+.14, x0+1.44, x0+2.74)
        if mode=="central":
            box(x0+1.12, 1.47, 1.51, .66, "Accessible\nlocal data", "data", size=7.0)
        else:
            for lx, name in zip(lab_x, ("Lab 1", "Lab 2", "Lab K")):
                box(lx, 1.47, .91, .66, name+"\nData", "data", size=7.0)
            label(x0+2.53, 1.80, "...", 7, DATA)

        # The two directions occupy separate lanes, with no redundant tiny labels.
        arrow((x0+1.18, 3.99), (x0+1.18, 3.55), MODEL)
        arrow((x0+2.57, 3.54), (x0+2.57, 3.98), MODEL if mode=="central" else GATE)
        if mode=="central":
            arrow((x0+1.875, 2.15), (x0+1.875, 2.86), DATA)
        else:
            for lx, port in zip(lab_x, (x0+1.02, x0+1.88, x0+2.72)):
                arrow((lx+.455, 2.15), (port, 2.86), MODEL, bidirectional=True)
            label(x0+1.88, 1.18, "Train locally; share updates", 6.7, SECONDARY)

        if mode in {"central", "ours"}:
            arrow((x0+1.34, 5.02), (x0+1.34, 4.67), HARNESS)
            route([(x0+3.08,3.20), (x0+3.44,3.20),
                   (x0+3.44,5.36), (x0+3.21,5.36)], GATE)
            label(x0+3.66, 4.27, "Results" if mode=="central" else "Evidence",
                  6.7, GATE, rotation=90)

    panels = [(0.10,"(a) Centralized bio-agent","Centralized access","central"),
              (4.10,"(b) Collaborative training","Fixed design","collab"),
              (8.10,"(c) BioCoLoop","Model + design learning","ours")]
    for x0, title, subtitle, mode in panels:
        label(x0+1.875, 6.33, title, 7.8, INK, "bold")
        label(x0+1.875, 6.02, subtitle, 6.8, SECONDARY)
        blueprint(x0, mode)
    for x in (4.,8.):
        ax.plot([x,x],[.98,6.47],color=DIVIDER,linewidth=.5,zorder=1)

    legend = [(1.05,DATA,DATA_FILL,"Data"),
              (3.1,MODEL,MODEL_FILL,"Predictor"),
              (5.8,HARNESS,HARNESS_FILL,"Research loop"),
              (9.1,GATE,GATE_FILL,"Aggregation")]
    for x,edge,fill,name in legend:
        ax.add_patch(FancyBboxPatch((x,.43),.26,.22,
            boxstyle="round,pad=0.01,rounding_size=0.03", linewidth=.6,
            edgecolor=edge,facecolor=fill,zorder=5))
        label(x+.38,.54,name,6.7,INK,ha="left")
    label(6.,.16,"Dashed gray: inactive harness. K denotes laboratories.",6.5,SECONDARY)

    fig.subplots_adjust(left=0,right=1,bottom=0,top=1)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    for artist,(x,y,w,h) in text_bounds:
        bounds = artist.get_window_extent(renderer).transformed(ax.transData.inverted())
        assert bounds.x0>=x and bounds.x1<=x+w, f"Text overflows box: {artist.get_text()}"
        assert bounds.y0>=y and bounds.y1<=y+h, f"Text overflows box: {artist.get_text()}"
    for artist in all_labels:
        bounds = artist.get_window_extent(renderer).transformed(ax.transData.inverted())
        assert bounds.x0>=0 and bounds.x1<=12 and bounds.y0>=0 and bounds.y1<=6.65, \
            f"Text outside canvas: {artist.get_text()}"
    paths = []
    for suffix in ("pdf","svg","png"):
        path = PAPER/f"assets/paradigm_comparison.{suffix}"
        fig.savefig(path,dpi=200,metadata={"Creator":"BioCoLoop vector paradigm revision v2"})
        paths.append(path)
    svg = PAPER/"assets/paradigm_comparison.svg"
    svg.write_text("\n".join(line.rstrip() for line in svg.read_text().splitlines())+"\n")
    plt.close(fig)
    receipt = dict(schema="paradigm-readability-v2", authoring="Matplotlib native vector paths and text",
        figure_width_inches=5.5,figure_height_inches=3.05,
        previous_height_at_5_5_inches=6.25*5.5/11.5,
        minimum_active_box_font_pt=min(active_fonts),minimum_annotation_font_pt=6.5,
        text_within_boxes=True,text_within_canvas=True,
        semantic_colors={"data":DATA,"predictor":MODEL,"research":HARNESS,"aggregation":GATE},
        inactive_module="collaborative-training research harness",
        generator_sha256=sha(__file__),artifacts_sha256={p.name:sha(p) for p in paths},
        visual_review_status="PENDING")
    receipt_path = PAPER/"assets/paradigm_comparison_v2.provenance.json"
    receipt_path.write_text(json.dumps(receipt,indent=2)+"\n")
    print(json.dumps(receipt))


if __name__=="__main__":
    draw()
