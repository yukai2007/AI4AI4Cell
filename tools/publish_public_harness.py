"""Produce a separate, verified public-harness table PREVIEW, never main.tex.

Usage:
  python -B paper/tools/publish_public_harness.py --base /path/to/matrix

Matrix layout: <base>/<harness>/<task>/seed{42,43,44}/heldout.
Writes separate complete-three-seed and strictly matched-seed42 pilot previews.
Incomplete three-seed cells and missing seed42 pilot cells are N/A.
This script never edits manuscript sources,
the original strong publisher, factorial ARMS, or existing main-table artifacts.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys

PAPER = Path(__file__).resolve().parents[1]
ROOT = PAPER.parent
EXTENSION = ROOT / "extensions/public_harness_20260924"
if str(EXTENSION) not in sys.path:
    sys.path.insert(0, str(EXTENSION))

SEEDS = (42, 43, 44)
TASKS = ("native_tapb", "ptpc_neural", "vcc_corrected", "norman_double_corrected", "tahoe_drug_corrected")
HARNESSES = {
    "ai_scientist_v2": {"label": "AI-Scientist-v2 (10 labs)",
                        "commit": "96bd51617cfdbb494a9fc283af00fe090edfae48"},
    "ai_researcher": {"label": "AI-Researcher (10 labs)",
                      "commit": "f9a6f8480860c193afff600eeffe3defcee8a978"},
}
ORIGINAL_ARMS = ("single_fixed", "single_direct", "federated_loop")
METHODS = ORIGINAL_ARMS + tuple(HARNESSES)
ROLE = "retrospective held-out; prior historical exposure; not blind confirmation"
REQUIRED = ("seal.json", "results.json", "audit.json", "verification.json")


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def check_prediction_hashes(folder, result):
    """Reject altered/redirected predictions before invoking any rescoring."""
    folder = Path(folder).resolve()
    if not result.get("endpoints"):
        raise ValueError("Missing saved prediction endpoint evidence")
    for endpoint in result["endpoints"].values():
        path = Path(endpoint["predictions"]).resolve()
        if path.parent != folder or sha(path) != endpoint["predictions_sha256"]:
            raise ValueError("Saved prediction output path or hash changed")


def verify_readonly(folder):
    """Run the full existing independent verifier without rewriting its receipt.

    The verifier's only write is its final verification.json. Intercept that
    narrow write in memory, compare the recomputation with the stored receipt,
    and restore its function even on failure. This publisher is single-threaded.
    """
    import verify_public
    folder = Path(folder).resolve()
    expected_path = folder / "verification.json"
    prior_bytes = expected_path.read_bytes()
    stored = json.loads(prior_bytes)
    result = read(folder / "results.json")
    check_prediction_hashes(folder, result)
    captured = []
    original_dump = verify_public.dump

    def capture(path, value):
        if Path(path).resolve() != expected_path:
            raise RuntimeError("Read-only verification attempted an unexpected write")
        captured.append(value)

    verify_public.dump = capture
    try:
        computed = verify_public.verify(folder)
    finally:
        verify_public.dump = original_dump
    if captured != [computed] or expected_path.read_bytes() != prior_bytes:
        raise ValueError("Read-only verification did not preserve its original receipt")
    stable = lambda value: {key: item for key, item in value.items() if key != "verified_unix"}
    if stable(computed) != stable(stored):
        raise ValueError("Fresh independent rescoring differs from the stored verification receipt")
    return computed


def _finite_primary(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("A finite primary metric is required")
    return float(value)


def aggregate_seeds(runs):
    completed = [seed for seed in SEEDS if runs.get(str(seed)) is not None]
    values = [_finite_primary(runs[str(seed)]["primary"]) for seed in completed]
    complete = completed == list(SEEDS)
    return {"complete": complete, "completed_seeds": completed, "n": len(completed),
            "mean": statistics.mean(values) if complete else None,
            "sd": statistics.stdev(values) if complete else None}


def _validate_identity(folder, harness, task, seed, result, seal, verification):
    if result.get("schema") != "public-harness-heldout-results-v1" or seal.get("schema") != "public-harness-heldout-seal-v1":
        raise ValueError("Unknown public-harness result/seal schema")
    if verification.get("schema") != "public-harness-heldout-verification-v1" or verification.get("status") != "PASS":
        raise ValueError("Independent production verification is missing")
    for record in (result, seal, verification):
        if (record.get("harness") != harness or record.get("task") != task or record.get("seed") != seed
                or record.get("role") != ROLE):
            raise ValueError("Baseline path and evidence identity/role differ")
    if result.get("execution_kind") != "fresh-canonical-v3" or seal.get("execution_kind") != "fresh-canonical-v3":
        raise ValueError("Synthetic or cache replay evidence cannot enter a public-harness preview")
    if (seal.get("rounds") != 100 or seal.get("slots") != 6 or seal.get("clients") != list(range(10))
            or result.get("feedback_to_controller") is not False or seal.get("feedback_to_controller") is not False):
        raise ValueError("Different access/budget/feedback contract cannot enter the matched main preview")
    if not seal["development_sealed_unix"] <= seal["sealed_unix"] <= result["heldout_decoded_unix"] <= result["completed_unix"]:
        raise ValueError("Selection/evaluation timing order changed")
    expected_endpoints = {"random", "unseen_drug", "unseen_protein"} if task == "native_tapb" else {"primary"}
    metric = "auroc" if task == "native_tapb" else "ap" if task == "ptpc_neural" else "macro_accuracy"
    primary_endpoint = "random" if task == "native_tapb" else "primary"
    if (set(result["endpoints"]) != expected_endpoints or result.get("primary_metric") != metric
            or result.get("primary_endpoint") != primary_endpoint):
        raise ValueError("Original main-table endpoint/metric changed")
    if result["primary"] != result["endpoints"][primary_endpoint]["primary"]:
        raise ValueError("Primary score is not the declared endpoint score")
    if (verification["result_sha256"] != sha(folder / "results.json") or verification["seal_sha256"] != sha(folder / "seal.json")
            or verification["audit_sha256"] != sha(folder / "audit.json") or result["seal_sha256"] != sha(folder / "seal.json")):
        raise ValueError("Verified artifact hashes changed")
    definition_path = Path(seal["run_dir"]) / "definition.json"
    definition = read(definition_path)
    if definition["config"]["upstream_commit"] != HARNESSES[harness]["commit"]:
        raise ValueError("Baseline native source differs from its pinned public harness")
    return definition_path, definition


def collect(base, reference_base=None, *, _reference_snapshot=None, _verification_fn=None):
    """Collect only complete verified seeds; test injection is visibly nonpublishable."""
    from publish_strong_snapshot import collect as collect_reference
    base = Path(base).resolve()
    reference_base = Path(reference_base or ROOT / "results/unified_bio_20260918").resolve()
    test_only = _reference_snapshot is not None or _verification_fn is not None
    reference = _reference_snapshot if _reference_snapshot is not None else collect_reference(reference_base, list(SEEDS))
    if reference.get("role") != ROLE or reference.get("seeds_requested") != list(SEEDS):
        raise ValueError("Original comparison uses different seeds or held-out role")
    verifier = _verification_fn or verify_readonly
    snapshot = {"schema": "public-harness-main-preview-v1", "artifact_role": "unit-test-only" if test_only else "verified-preview-not-integrated",
                "created_utc": datetime.now(timezone.utc).isoformat(), "role": ROLE, "seeds_requested": list(SEEDS),
                "base": str(base), "reference_base": str(reference_base), "manuscript_modified": False,
                "main_table_replaced": False, "harness_registry": HARNESSES, "tasks": {}, "matrix_complete": True,
                "source_sha256": {str(path): sha(path) for path in
                    (Path(__file__), PAPER / "tools/publish_strong_snapshot.py", EXTENSION / "heldout_public.py",
                     EXTENSION / "verify_public.py", EXTENSION / "broker.py")}}
    for task in TASKS:
        item = {"original": {}, "public_harnesses": {}}
        reference_runs = reference["tasks"][task]["runs"]
        for arm in ORIGINAL_ARMS:
            runs = {str(seed): None if reference_runs.get(str(seed)) is None else
                    {"primary": reference_runs[str(seed)]["scores"][arm]["primary"],
                     "reference_receipts": reference_runs[str(seed)].get("receipts", {})} for seed in SEEDS}
            item["original"][arm] = {"runs": runs, **aggregate_seeds(runs)}
        for harness in HARNESSES:
            runs, pending = {}, {}
            for seed in SEEDS:
                folder = base / harness / task / f"seed{seed}" / "heldout"
                missing = [filename for filename in REQUIRED if not (folder / filename).is_file()]
                if missing:
                    runs[str(seed)] = None
                    pending[str(seed)] = "Missing verified evidence: " + ", ".join(missing)
                    continue
                result, seal = read(folder / "results.json"), read(folder / "seal.json")
                verification = verifier(folder)
                if test_only:
                    # Test fixtures cannot produce publishable artifacts; exercise
                    # completion/ranking without forging production provenance.
                    runs[str(seed)] = {"primary": _finite_primary(result["primary"]), "test_only": True}
                    continue
                definition_path, definition = _validate_identity(folder, harness, task, seed, result, seal, verification)
                record = {"primary": _finite_primary(result["primary"]), "metrics": result["metrics"],
                          "primary_metric": result["primary_metric"], "primary_endpoint": result["primary_endpoint"],
                          "endpoints": result["endpoints"], "receipts": {str(folder / filename): sha(folder / filename) for filename in REQUIRED},
                          "definition_path": str(definition_path), "definition_sha256": sha(definition_path),
                          "checkpoint_sha256": result["checkpoint_sha256"], "reference_seal": seal["reference_seal"],
                          "upstream_commit": definition["config"]["upstream_commit"],
                          "upstream_repo": definition["config"]["upstream_repo"],
                          "adapter_paths": definition["config"]["adapter_paths"],
                          "source_sha256": definition["binding"]["source_sha256"],
                          "data_manifest_sha256": definition["binding"]["data_manifest_sha256"],
                          "runtime": definition["binding"]["runtime"]}
                runs[str(seed)] = record
            aggregate = aggregate_seeds(runs)
            item["public_harnesses"][harness] = {"runs": runs, "pending": pending, **aggregate}
            snapshot["matrix_complete"] = snapshot["matrix_complete"] and aggregate["complete"]
        snapshot["tasks"][task] = item
    snapshot["reference_complete"] = all(row["complete"] for item in snapshot["tasks"].values() for row in item["original"].values())
    snapshot["ready_for_explicit_manuscript_integration"] = bool(snapshot["matrix_complete"] and snapshot["reference_complete"] and not test_only)
    snapshot["seed42_preview"] = {
        "seed": 42, "reported_as": "matched single-seed pilot; no seed-averaging or SD",
        "same_seed_for_all_methods": True,
        "complete": all(_row(snapshot, task, method)["runs"].get("42") is not None for task in TASKS for method in METHODS),
        "public_completed_tasks": {harness: [task for task in TASKS if _row(snapshot, task, harness)["runs"].get("42") is not None]
                                   for harness in HARNESSES},
        "manuscript_modified": False,
    }
    return snapshot


def _row(snapshot, task, method):
    item = snapshot["tasks"][task]
    return item["original"][method] if method in ORIGINAL_ARMS else item["public_harnesses"][method]


def table_text(snapshot, *, seed=None):
    """Default stays the three-seed table; seed42 is a distinct pilot view."""
    if seed not in (None, 42):
        raise ValueError("Only the prespecified matched seed42 pilot is supported")

    def value_for(task, method):
        row = _row(snapshot, task, method)
        if seed == 42:
            run = row["runs"].get("42")
            return None if run is None else round(100 * _finite_primary(run["primary"]), 2)
        return None if not row["complete"] else round(100 * row["mean"], 2)

    values = {method: [value_for(task, method) for task in TASKS] for method in METHODS}
    rankings = [sorted({values[method][column] for method in METHODS if values[method][column] is not None}, reverse=True)
                for column in range(len(TASKS))]

    def cell(method, column):
        value = values[method][column]
        if value is None:
            return "N/A"
        number = f"{value:.2f}"
        if value == rankings[column][0]:
            number = r"\textbf{" + number + "}"
        elif len(rankings[column]) > 1 and value == rankings[column][1]:
            number = r"\underline{" + number + "}"
        if seed == 42:
            return number
        return number + r" $\pm$ " + f"{100 * _row(snapshot, TASKS[column], method)['sd']:.2f}"

    lines = [r"\begin{table}[t]", r"\centering\footnotesize", r"\setlength{\tabcolsep}{3pt}",
             r"\renewcommand{\arraystretch}{1.12}", r"\begin{tabularx}{\linewidth}{@{}Xrrrrr@{}}", r"\toprule",
             r"\textbf{Model / method} & \multicolumn{1}{c}{DTI} & \multicolumn{1}{c}{Proteomics} & \multicolumn{3}{c}{Cell perturbation} \\",
             r"\cmidrule(lr){2-2}\cmidrule(lr){3-3}\cmidrule(l){4-6}",
             r" & \shortstack{BindingDB\\AUROC $\uparrow$} & \shortstack{PTPC\\AP $\uparrow$} & \shortstack{VCC\\Top-1 $\uparrow$} & \shortstack{Norman\\Top-1 $\uparrow$} & \shortstack{Tahoe\\Top-1 $\uparrow$} \\",
             r"\midrule", r"\multicolumn{6}{l}{\textit{Fixed task models, one laboratory}} \\"]
    for label, columns in (("TAPB", {0}), ("ProteinTalks-derived head", {1}), ("scDEBART response head", {2, 3, 4})):
        lines.append(label + " & " + " & ".join(cell("single_fixed", j) if j in columns else "--" for j in range(5)) + r" \\")
    lines.append(r"\midrule")
    for method, label in (("single_direct", "Qwen direct (1 lab)"),
                          ("ai_scientist_v2", HARNESSES["ai_scientist_v2"]["label"]),
                          ("ai_researcher", HARNESSES["ai_researcher"]["label"]),
                          ("federated_loop", r"\textbf{BioCoLoop} (10 labs)")):
        lines.append(label + " & " + " & ".join(cell(method, j) for j in range(5)) + r" \\")
    caption = (r"\caption{Matched seed-42 pilot preview. All methods use the same training/search seed 42 and the named task models. Native AI-Scientist-v2 and AI-Researcher controllers are task-adapted with local Qwen, ten laboratories, a twelve-design menu, six proposal slots and 100-round candidates. Scores are multiplied by 100; missing seed-42 results are N/A. Bold and underline mark the best and second-best displayed scores across all five methods, including ties.}"
               if seed == 42 else
               r"\caption{Preview pending manuscript integration. All methods use the named task models. Native AI-Scientist-v2 and AI-Researcher controllers are task-adapted with local Qwen, ten laboratories, a twelve-design menu, six proposal slots and 100-round candidates. Values are mean $\pm$ sample SD over complete seeds 42--44, multiplied by 100; incomplete cells are N/A. Bold and underline mark the best and second-best displayed means across all five methods, including ties.}")
    label = r"\label{tab:public-harness-seed42-preview}" if seed == 42 else r"\label{tab:public-harness-preview}"
    lines += [r"\bottomrule", r"\end{tabularx}", caption, label, r"\end{table}"]
    return "\n".join(lines) + "\n"


def seed42_table_text(snapshot):
    return table_text(snapshot, seed=42)


def write_preview(snapshot, output_dir):
    if snapshot.get("artifact_role") != "verified-preview-not-integrated":
        raise ValueError("Unit-test/injected evidence cannot be written as a publication preview")
    output = Path(output_dir).resolve()
    if output == PAPER / "tables/strong_v3":
        raise ValueError("Use a separate preview directory; preserve all existing strong_v3 artifacts")
    output.mkdir(parents=True, exist_ok=True)
    (output / "main_public_harness.tex").write_text(table_text(snapshot))
    (output / "main_public_harness_seed42.tex").write_text(seed42_table_text(snapshot))
    (output / "snapshot_public_harness.json").write_text(json.dumps(snapshot, indent=2, allow_nan=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True, help="Matrix root containing the two harness directories")
    parser.add_argument("--reference-results", type=Path, default=ROOT / "results/unified_bio_20260918")
    parser.add_argument("--output-dir", type=Path, default=PAPER / "tables/public_harness_preview")
    args = parser.parse_args()
    snapshot = collect(args.base, args.reference_results)
    write_preview(snapshot, args.output_dir)
    print(json.dumps({"matrix_complete": snapshot["matrix_complete"],
                      "seed42_pilot_complete": snapshot["seed42_preview"]["complete"],
                      "ready_for_explicit_manuscript_integration": snapshot["ready_for_explicit_manuscript_integration"],
                      "manuscript_modified": False, "output_dir": str(args.output_dir.resolve())}))


if __name__ == "__main__":
    main()
