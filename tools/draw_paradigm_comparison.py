"""Draw three research paradigms from one semantically colored blueprint."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

PAPER = Path(__file__).resolve().parents[1]

INK = "#172B3A"
DATA = "#238B7B"
DATA_FILL = "#E7F5F2"
MODEL = "#356FA3"
MODEL_FILL = "#E8F1F8"
HARNESS = "#76539A"
HARNESS_FILL = "#F1EAF7"
GATE = "#D97732"
GATE_FILL = "#FBEDE3"
GHOST = "#AAB4BD"
GHOST_FILL = "#F4F6F7"
DIVIDER = "#D9E0E5"


def draw() -> None:
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 12,
        "pdf.fonttype": 42,
        "svg.fonttype": "none",
    })
    fig, ax = plt.subplots(figsize=(11.5, 6.25))
    ax.set(xlim=(0, 12), ylim=(0, 6.65))
    ax.axis("off")
    text_bounds = []

    def label(x, y, value, size=12, color=INK, weight="normal", **kwargs):
        kwargs.setdefault("ha", "center")
        kwargs.setdefault("va", "center")
        return ax.text(x, y, value, fontsize=size, color=color, fontweight=weight,
                       linespacing=1.16, zorder=8, **kwargs)

    def box(x, y, w, h, value, role, active=True, size=11.5, weight="normal"):
        palette = {
            "data": (DATA, DATA_FILL),
            "model": (MODEL, MODEL_FILL),
            "harness": (HARNESS, HARNESS_FILL),
            "gate": (GATE, GATE_FILL),
        }
        edge, fill = palette[role] if active else (GHOST, GHOST_FILL)
        ax.add_patch(FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.015,rounding_size=0.07",
            linewidth=1.35, edgecolor=edge, facecolor=fill,
            linestyle="-" if active else (0, (3, 2)), zorder=5,
        ))
        artist = label(x + w / 2, y + h / 2, value, size=size,
                       color=edge, weight=weight)
        text_bounds.append((artist, (x, y, w, h)))

    def arrow(start, end, color, bidirectional=False, dashed=False, z=3):
        ax.add_patch(FancyArrowPatch(
            start, end, arrowstyle="<|-|>" if bidirectional else "-|>",
            mutation_scale=11, linewidth=1.35, color=color,
            linestyle=(0, (3, 2)) if dashed else "-",
            shrinkA=1.5, shrinkB=1.5, zorder=z,
        ))

    def route(points, color, dashed=False):
        style = (0, (3, 2)) if dashed else "-"
        for p, q in zip(points[:-2], points[1:-1]):
            ax.plot([p[0], q[0]], [p[1], q[1]], color=color,
                    linewidth=1.35, linestyle=style, zorder=2)
        arrow(points[-2], points[-1], color, dashed=dashed)

    def blueprint(x0, mode):
        """Reuse the full blueprint while showing only accessible data holders."""
        active_harness = mode in {"central", "ours"}

        box(x0 + 0.55, 5.03, 2.65, 0.67,
            "Research harness\npropose · retain · remember",
            "harness", active_harness, size=10.6, weight="bold")
        box(x0 + 0.68, 4.00, 2.39, 0.65,
            "Executable design\n+ predictive model",
            "model", True, size=10.7, weight="bold")
        box(x0 + 0.68, 2.88, 2.39, 0.65,
            "Local fitting\n+ evaluation" if mode == "central" else
            "Update + evidence\naggregation",
            "model" if mode == "central" else "gate",
            size=10.7, weight="bold")

        lab_x = (x0 + 0.14, x0 + 1.44, x0 + 2.74)
        if mode == "central":
            box(x0 + 1.12, 1.47, 1.51, 0.66, "Accessible\nlocal data",
                "data", size=9.7, weight="bold")
        else:
            for lx, name in zip(lab_x, ("Lab 1", "Lab 2", "Lab K")):
                box(lx, 1.47, 0.91, 0.66, f"{name}\nlocal data",
                    "data", size=9.7, weight="bold")
            label(x0 + 2.53, 1.80, "...", 10, DATA)

        if mode == "central":
            # One accessible dataset, with explicit fitting and metric feedback.
            arrow((x0 + 1.34, 5.02), (x0 + 1.34, 4.67), HARNESS)
            label(x0 + 0.99, 4.84, "proposal", 8.8, HARNESS)
            arrow((x0 + 1.18, 3.99), (x0 + 1.18, 3.55), MODEL)
            label(x0 + 0.88, 3.77, "model", 8.6, MODEL)
            arrow((x0 + 2.57, 3.54), (x0 + 2.57, 3.98), MODEL)
            label(x0 + 2.90, 3.77, "update", 8.6, MODEL)
            arrow((x0 + 1.875, 2.15), (x0 + 1.875, 2.86), DATA)
            route([(x0 + 3.08, 3.20), (x0 + 3.44, 3.20),
                   (x0 + 3.44, 5.36), (x0 + 3.21, 5.36)], GATE)
            label(x0 + 3.56, 4.27, "evaluation", 8.5, GATE,
                  rotation=90)
        else:
            # Model distribution and aggregated update occupy separate lanes.
            arrow((x0 + 1.18, 3.99), (x0 + 1.18, 3.55), MODEL)
            label(x0 + 0.88, 3.77, "model", 8.6, MODEL)
            arrow((x0 + 2.57, 3.54), (x0 + 2.57, 3.98), GATE)
            label(x0 + 2.90, 3.77, "update", 8.6, GATE)
            for lx, port in zip(lab_x, (x0 + 1.02, x0 + 1.88, x0 + 2.72)):
                arrow((lx + 0.455, 2.15), (port, 2.86), MODEL,
                      bidirectional=True)
            label(x0 + 1.88, 1.18, "Local fitting; updates + metrics shared",
                  8.8, MODEL)

            if mode == "ours":
                arrow((x0 + 1.34, 5.02), (x0 + 1.34, 4.67), HARNESS)
                label(x0 + 0.99, 4.84, "proposal", 8.8, HARNESS)
                route([(x0 + 3.08, 3.20), (x0 + 3.44, 3.20),
                       (x0 + 3.44, 5.36), (x0 + 3.21, 5.36)], GATE)
                label(x0 + 3.56, 4.27, "evidence card", 8.5, GATE,
                      rotation=90)

    panels = [
        (0.10, "(a) Centralized bio-agent", "one accessible dataset", "central"),
        (4.10, "(b) Collaborative training", "fixed executable design", "collab"),
        (8.10, "(c) BioCoLoop", "model + design learning", "ours"),
    ]
    for x0, title, subtitle, mode in panels:
        label(x0 + 1.875, 6.33, title, 14.2, INK, "bold")
        label(x0 + 1.875, 6.02, subtitle, 10.6, GHOST)
        blueprint(x0, mode)

    for x in (4.0, 8.0):
        ax.plot([x, x], [0.98, 6.47], color=DIVIDER, linewidth=1.0, zorder=1)

    # Semantic color legend.
    legend = [
        (DATA, DATA_FILL, "local data"),
        (MODEL, MODEL_FILL, "predictive model"),
        (HARNESS, HARNESS_FILL, "research harness"),
        (GATE, GATE_FILL, "aggregation / evidence gate"),
    ]
    x = 0.92
    for edge, fill, name in legend:
        ax.add_patch(FancyBboxPatch(
            (x, 0.42), 0.26, 0.22,
            boxstyle="round,pad=0.01,rounding_size=0.03",
            linewidth=1.1, edgecolor=edge, facecolor=fill, zorder=5,
        ))
        label(x + 0.38, 0.53, name, 9.6, INK, ha="left")
        x += {"local data": 2.25, "predictive model": 2.45,
              "research harness": 2.55}.get(name, 0)
    label(6.0, 0.10,
          "Dashed gray: inactive research harness. K denotes participating laboratories.",
          9.3, GHOST)

    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    for artist, (x, y, w, h) in text_bounds:
        bounds = artist.get_window_extent(renderer).transformed(ax.transData.inverted())
        assert bounds.x0 >= x and bounds.x1 <= x+w, f"Text overflows box: {artist.get_text()}"
        assert bounds.y0 >= y and bounds.y1 <= y+h, f"Text overflows box: {artist.get_text()}"
    for suffix in ("pdf", "svg"):
        fig.savefig(PAPER / f"assets/paradigm_comparison.{suffix}",
                    metadata={"Creator": "BioCoLoop"})
    svg = PAPER / "assets/paradigm_comparison.svg"
    svg.write_text("\n".join(line.rstrip() for line in svg.read_text().splitlines()) + "\n")
    plt.close(fig)


if __name__ == "__main__":
    draw()
