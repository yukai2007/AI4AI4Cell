#!/usr/bin/env python3
"""Audit anytime loop behavior from the frozen V3 development histories.

This is a development-only prefix analysis. It never reads held-out predictions
or changes selected models. Every proposal budget from one through six is
reported, so the two-slot result cannot silently replace the final-budget tie.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from pathlib import Path


TASKS = (
    ("native_tapb", "TAPB"),
    ("ptpc_neural", "PTPC"),
    ("vcc_corrected", "VCC"),
    ("norman_double_corrected", "Norman"),
    ("tahoe_drug_corrected", "Tahoe"),
)
SEEDS = (42, 43, 44)
MODES = ("direct", "loop")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def incumbent_primary(history: list[dict]) -> list[float]:
    """Return the retained primary score after baseline and each proposal."""
    incumbent = None
    curve = []
    for row in history:
        if row.get("accepted") and "development" in row:
            incumbent = float(row["development"]["primary"])
        if incumbent is None:
            raise ValueError("History does not begin with a valid retained baseline")
        curve.append(incumbent)
    return curve


def analyze(results: Path) -> dict:
    trajectories = []
    source_sha256 = {}
    for task, label in TASKS:
        for seed in SEEDS:
            study = results / task / f"study_v3_seed{seed}"
            definition_path = study / "definition.json"
            definition = json.loads(definition_path.read_text())
            if definition.get("slots") != 6 or definition.get("test_read") is not False:
                raise ValueError(f"Unexpected V3 protocol in {definition_path}")
            source_sha256[str(definition_path.relative_to(results))] = sha256(definition_path)
            curves = {}
            for mode in MODES:
                path = study / f"federated_{mode}_history.json"
                history = json.loads(path.read_text())
                if len(history) != 7:
                    raise ValueError(f"Expected baseline plus six proposals in {path}")
                curves[mode] = incumbent_primary(history)
                source_sha256[str(path.relative_to(results))] = sha256(path)
            trajectories.append(dict(task=task, label=label, seed=seed, curves=curves))

    budgets = []
    for budget in range(1, 7):
        differences = [
            row["curves"]["loop"][budget] - row["curves"]["direct"][budget]
            for row in trajectories
        ]
        budgets.append(dict(
            proposals=budget,
            loop_better=sum(delta > 1e-12 for delta in differences),
            tied=sum(abs(delta) <= 1e-12 for delta in differences),
            direct_better=sum(delta < -1e-12 for delta in differences),
            mean_primary_difference_points=100 * statistics.mean(differences),
        ))

    budget_two_cases = []
    for row in trajectories:
        delta = row["curves"]["loop"][2] - row["curves"]["direct"][2]
        if delta > 1e-12:
            budget_two_cases.append(dict(
                task=row["label"], seed=row["seed"], difference_points=100 * delta,
            ))

    return dict(
        schema="ai4ai4cell-loop-prefix-v1",
        role="development-only executed-prefix diagnostic; no held-out feedback",
        task_seed_trajectories=len(trajectories),
        proposal_budgets=budgets,
        budget_two_positive_cases=budget_two_cases,
        source_sha256=source_sha256,
    )


def write_latex(result: dict, path: Path) -> None:
    rows = []
    for row in result["proposal_budgets"]:
        rows.append(
            f'{row["proposals"]} & {row["loop_better"]} & {row["tied"]} & '
            f'{row["direct_better"]} & {row["mean_primary_difference_points"]:+.2f} \\\\'
        )
    cases = " and ".join(
        f'{row["task"]} seed {row["seed"]} ({row["difference_points"]:+.2f})'
        for row in result["budget_two_positive_cases"]
    )
    text = "\n".join([
        r"\begin{table}[t]",
        (r"\caption{Executed-prefix analysis of all 15 ten-laboratory development trajectories "
         r"at common proposal budgets. At two proposals, the positive cases are " + cases +
         r" percentage points, with thirteen ties and no regressions.}"),
        r"\label{tab:loop-prefix}",
        r"\centering\small",
        r"\setlength{\tabcolsep}{6pt}",
        r"\begin{tabular}{rrrrr}",
        r"\toprule",
        r"Proposal budget & Loop better & Tie & Direct better & Mean $\Delta$ primary \\",
        r" & \multicolumn{3}{c}{task--seed trajectories} & points \\",
        r"\midrule",
        *rows,
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
        "",
    ])
    path.write_text(text)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    result = analyze(args.results)
    (args.output / "loop_prefix.json").write_text(json.dumps(result, indent=2) + "\n")
    write_latex(result, args.output / "loop_prefix.tex")
    print(json.dumps({key: result[key] for key in ("task_seed_trajectories", "proposal_budgets")}, indent=2))


if __name__ == "__main__":
    main()
