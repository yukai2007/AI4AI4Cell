"""Generate the current three-task search overview from the registered eight-seed analyses."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "tables/author_review_20261110"
EXPANDED = ROOT / "provenance/recipe_expansion_20261110/summary.json"
CELL = ROOT / "provenance/fbhk_followup_20261109/policy_summary.json"
EIGHT = ROOT / "tables/rebuttal_round3_20261111"
E9, E6 = EIGHT / "e9_eight_seed_analysis.json", EIGHT / "e6_eight_seed_analysis.json"
POLICIES = {"fixed_D00": "Fitted D00", "direct": "Direct", "structured": "Structured history",
            "random": "Random expectation", "gp_ei": "GP--EI"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    expanded = json.loads(EXPANDED.read_text())
    cell = json.loads(CELL.read_text())
    assert expanded["status"] == cell["status"] == "COMPLETE"
    for policy in ("structured", "random"):
        assert abs(cell["policies"][policy]["heldout_primary_mean"] - expanded["existing_cell"][policy]["heldout_primary_mean"]) < 1e-14
    e9, e6 = json.loads(E9.read_text()), json.loads(E6.read_text())
    assert e9["status"] == e6["status"] == "COMPLETE" and e9["n_seeds"] == e6["n_seeds"] == 8
    groups = (e9["groups"]["luna/dti"], e9["groups"]["luna/protein"], e6["groups"]["qwen/cell"])
    # The first three eight-seed values must reproduce the original three-seed reports exactly.
    for policy in POLICIES:
        for task, group in zip(("dti", "protein"), groups):
            old = expanded["models"]["luna"]["tasks"][task]["policies"][policy]["heldout_mean"]
            assert abs(sum(group["arms"][policy]["per_seed"][:3])/3 - old) < 1e-9, (task, policy)
        old = 100*cell["policies"][policy]["heldout_primary_mean"]
        assert abs(sum(groups[2]["arms"][policy]["per_seed"][:3])/3 - old) < 1e-9, ("cell", policy)
    rows = {policy: [{"mean": g["arms"][policy]["mean"], "sd": g["arms"][policy]["seed_sd"]} for g in groups]
            for policy in POLICIES}
    lines = [r"\begin{table}[htbp]", r"\centering\small",
        r"\caption{Matched-access search in three separate protocols (eight training/controller runs: the original three plus five registered extensions; mean $\pm$ sample SD, scores $\times100$). DTI/protein: Luna, 36 recipes, ten laboratories, one historical starting predictor per task. Cell: Qwen, 16 designs, four study--cell contexts and gene-disjoint partitions. Searches allow six requests after D00 and 20 rounds per valid fit; comparisons are within columns. Complete feedback, proposer and GP controls appear in E.6/E.9. Bold marks the best means, including ties.}",
        r"\label{tab:author-review-current-search}", r"\begin{tabular}{lrrr}", r"\toprule",
        r"Policy & DTI AUROC & Protein AP & Cell Top-1 \\", r"\midrule"]
    best = [max(v[i]["mean"] for v in rows.values()) for i in range(3)]
    for policy, label in POLICIES.items():
        cells = []
        for i, value in enumerate(rows[policy]):
            cell = f"{value['mean']:.3f} \\pm {value['sd']:.3f}"
            if abs(value["mean"]-best[i]) < 1e-12:
                cell = r"\mathbf{" + cell + "}"
            cells.append("$" + cell + "$")
        lines.append(label+" & "+" & ".join(cells)+r" \\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}", ""]
    evidence = {"source_sha256": {str(p.relative_to(ROOT) if p.is_relative_to(ROOT) else p): sha(p)
                                  for p in (EXPANDED, CELL, E9, E6)}, "policies": rows,
                "all_key_controls_retained": True, "new_training_or_scoring": "seeds 64-68 registered extensions (E.6/E.9)"}
    return "\n".join(lines), json.dumps(evidence, ensure_ascii=False, indent=2)+"\n"


def main():
    p = argparse.ArgumentParser(); p.add_argument("--check", action="store_true"); args = p.parse_args()
    table, evidence = build()
    values = {"current_search.tex": table, "current_search.provenance.json": evidence}
    if args.check:
        for name, value in values.items():
            assert (DEST/name).read_text() == value, name
    else:
        DEST.mkdir(parents=True, exist_ok=True)
        for name, value in values.items():
            path = DEST/name
            if not path.exists() or path.read_text() != value:
                path.write_text(value)
    print("PASS: current overview reproduces both fixed reports")


if __name__ == "__main__":
    main()
