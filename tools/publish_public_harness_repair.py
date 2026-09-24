"""Publish verified final-adapter AI-Researcher seed-42 results.

The five endpoints come from three immutable queues: PTPC from transport-v2,
the remaining short endpoints from budget-cap-v4, and DTI from the dedicated
priority queue. Every number is independently reconstructed by the original
public-harness verifier before it can enter a table.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import publish_public_harness as original

TASKS = original.TASKS
NAMES = ("DTI AUROC", "Proteomics AP", "VCC Top-1", "Norman Top-1", "Tahoe Top-1")
VERSION = "airesearcher-task-transport-budget-cap-v4"
FILES = ("compact_repair_seed42.tex", "snapshot_compact_repair.json")


def _measured(snapshot, task):
    return snapshot["tasks"][task]["public_harnesses"]["ai_researcher"]["runs"]["42"]


def _validate_scored(run, measured, version, adapter_file):
    status_path = run / "run_status.json"
    status = original.read(status_path)
    if status.get("transport_revision") != version or status.get("status") != "DEVELOPMENT_COMPLETE":
        raise ValueError("Scored repair has no matching completed transport revision")
    expected_adapter = original.EXTENSION / adapter_file
    if str(expected_adapter) not in measured["adapter_paths"]:
        raise ValueError("Measured repair did not execute the registered final adapter")
    return {"status": "Scored", "primary": measured["primary"], "receipt": measured,
            "run_status_sha256": original.sha(status_path)}


def _run_item(snapshot, base, task, version, adapter_file):
    run = base / "ai_researcher" / task / "seed42"
    status_path = run / "run_status.json"
    measured = _measured(snapshot, task)
    if measured is not None:
        return _validate_scored(run, measured, version, adapter_file)
    status = original.read(status_path) if status_path.exists() else {}
    if status.get("status") == "FAILED":
        error = status.get("error") or ""
        tool_failure = error.startswith("Error: Tool response remained invalid after 3 format attempts:")
        return {"status": "Failed", "primary": None, "error": error,
                "failure_type": "tool" if tool_failure else "unclassified",
                "display": r"$F_{\mathrm{tool}}$" if tool_failure else "Failed",
                "run_status_sha256": original.sha(status_path)}
    return {"status": "Pending", "primary": None}


def verify_budget_cap_readonly(folder):
    """Run the capped-slot validator and unchanged metric rescorer without writes."""
    import verify_public as metric_verifier
    import verify_public_budget_cap_v4 as budget_verifier

    folder = Path(folder).resolve()
    path = folder / "verification.json"
    prior = path.read_bytes()
    stored = json.loads(prior)
    result = original.read(folder / "results.json")
    original.check_prediction_hashes(folder, result)
    captured = []
    old_dump = metric_verifier.dump

    def capture(target, value):
        if Path(target).resolve() != path:
            raise RuntimeError("Read-only capped verification attempted an unexpected write")
        captured.append(value)

    metric_verifier.dump = capture
    try:
        computed = budget_verifier.verify(folder)
    finally:
        metric_verifier.dump = old_dump
    if captured != [computed] or path.read_bytes() != prior:
        raise ValueError("Capped-slot rescoring did not preserve its original receipt")
    stable = lambda value: {key: item for key, item in value.items() if key != "verified_unix"}
    if stable(computed) != stable(stored):
        raise ValueError("Fresh capped-slot rescoring differs from the stored verification receipt")
    return computed


def collect_budget_cap(base):
    previous = original.verify_readonly
    original.verify_readonly = verify_budget_cap_readonly
    try:
        return original.collect(base)
    finally:
        original.verify_readonly = previous


def _validate_direct_dti_registration(dti_base):
    """Validate the pre-heldout identity of the balanced parallel DTI run.

    The direct runner writes the same immutable run configuration and broker
    definition as the supervised queue.  Accepting this layout avoids moving
    evidence into a misleading queue directory while keeping publication
    conditional on the normal heldout verifier below.
    """
    run = Path(dti_base) / "ai_researcher" / "native_tapb" / "seed42"
    config_path = run / "config.json"
    definition_path = run / "development" / "definition.json"
    if not config_path.is_file() or not definition_path.is_file():
        return None
    config = original.read(config_path)
    definition = original.read(definition_path)
    definition_config = definition.get("config", {})
    expected_adapter = original.EXTENSION / "airesearcher_budget_cap_v4.py"
    if (config.get("harness") != "ai_researcher"
            or config.get("task") != "native_tapb"
            or config.get("seed") != 42
            or config.get("upstream_commit") != original.HARNESSES["ai_researcher"]["commit"]
            or str(expected_adapter) not in config.get("adapter_paths", [])):
        raise ValueError("Direct DTI run identity differs from the registered final adapter")
    if (definition_config.get("task") != "native_tapb"
            or definition_config.get("seed") != 42
            or definition_config.get("harness") != "ai_researcher"
            or definition.get("rounds") != 100
            or definition.get("slots") != 6):
        raise ValueError("Direct DTI run changed the shared candidate-training protocol")
    return {
        "config_sha256": original.sha(config_path),
        "definition_sha256": original.sha(definition_path),
        "gpu_ids": config.get("gpu_ids"),
    }


def collect(short_base, dti_base=None):
    short_base = Path(short_base).resolve()
    dti_base = Path(dti_base).resolve() if dti_base else short_base.parent / "seed42_dti_priority_v3"
    manifest_path = short_base / "queue_manifest.json"
    if not manifest_path.exists():
        return {"registered": False, "resolved": False, "scored": 0, "tasks": {}}

    sys.path.insert(0, str(original.EXTENSION))
    manifest = original.read(manifest_path)
    if manifest.get("schema") != "public-harness-budget-cap-repair-queue-v4":
        raise ValueError("Expected the final budget-cap repair registration")
    from airesearcher_budget_cap_v4 import source_pins as short_source_pins
    expected_jobs = {("ai_researcher", task, 42) for task in
                     ("norman_double_corrected", "vcc_corrected", "tahoe_drug_corrected")}
    jobs = {(job["harness"], job["task"], job["seed"]) for job in manifest["jobs"]}
    if (jobs != expected_jobs or manifest["source_sha256"] != short_source_pins()
            or manifest["max_gpu_hours"] != 2.0 or manifest["fitting_gpus"] != [0]
            or manifest.get("proposal_budget", {}).get("maximum") != 6):
        raise ValueError("Final short-repair registration changed")

    predecessor = Path(manifest["ptpc_queue"]).resolve()
    if predecessor != short_base.parent / "compact_repair_v2":
        raise ValueError("Unexpected PTPC predecessor queue")
    predecessor_manifest = original.read(predecessor / "queue_manifest.json")
    from airesearcher_transport_v2 import source_pins as predecessor_source_pins
    if (predecessor_manifest.get("schema") != "public-harness-compact-repair-queue-v2"
            or predecessor_manifest.get("source_sha256") != predecessor_source_pins()):
        raise ValueError("PTPC predecessor registration changed")

    short_snapshot = collect_budget_cap(short_base)
    predecessor_snapshot = original.collect(predecessor)
    reference = short_snapshot["tasks"]
    result = {
        "schema": "public-harness-final-adapter-publication-v3",
        "registered": True,
        "adapter_version": VERSION,
        "seed": 42,
        "short_base": str(short_base),
        "dti_base": str(dti_base),
        "manifest_sha256": original.sha(manifest_path),
        "source_sha256": manifest["source_sha256"],
        "tasks": {},
        "scored": 0,
        "resolved": True,
        "replaces_original_failures": False,
        "scientific_verification": "unchanged full public-harness verifier",
        "proposal_budget_semantics": "at most six; native early termination retained",
    }

    item = _run_item(predecessor_snapshot, predecessor, "ptpc_neural",
                     "airesearcher-task-transport-compact-v2", "airesearcher_transport_v2.py")
    item["source_queue"] = "transport-v2"
    result["tasks"]["ptpc_neural"] = item
    for task in ("norman_double_corrected", "vcc_corrected", "tahoe_drug_corrected"):
        item = _run_item(short_snapshot, short_base, task, VERSION, "airesearcher_budget_cap_v4.py")
        item["source_queue"] = "budget-cap-v4"
        result["tasks"][task] = item

    dti_manifest_path = dti_base / "queue_manifest.json"
    if dti_manifest_path.exists():
        dti_manifest = original.read(dti_manifest_path)
        from prioritize_seed42_dti_v3 import source_pins as dti_source_pins
        if (dti_manifest.get("schema") != "public-harness-seed42-dti-priority-v3"
                or dti_manifest.get("source_sha256") != dti_source_pins()
                or dti_manifest.get("final_job") != {"harness": "ai_researcher",
                                                     "task": "native_tapb", "seed": 42}
                or dti_manifest.get("max_gpu_hours") != 48.0):
            raise ValueError("Final DTI priority registration changed")
        dti_snapshot = collect_budget_cap(dti_base)
        item = _run_item(dti_snapshot, dti_base, "native_tapb", VERSION,
                         "airesearcher_budget_cap_v4.py")
        item["source_queue"] = "seed42-dti-priority-v3"
    else:
        direct_registration = _validate_direct_dti_registration(dti_base)
        if direct_registration is None:
            item = {"status": "Pending", "primary": None, "source_queue": None}
        else:
            dti_snapshot = collect_budget_cap(dti_base)
            item = _run_item(dti_snapshot, dti_base, "native_tapb", VERSION,
                             "airesearcher_budget_cap_v4.py")
            item["source_queue"] = "balanced-direct-v5"
            item["registration"] = direct_registration
    result["tasks"]["native_tapb"] = item

    for task in TASKS:
        row = result["tasks"][task]
        row["biocoloop_seed42"] = reference[task]["original"]["federated_loop"]["runs"]["42"]["primary"]
        result["scored"] += row["status"] == "Scored"
        result["resolved"] &= row["status"] in {"Scored", "Failed"}
    return result


def table(snapshot):
    if not snapshot["registered"]:
        return "% No registered final-adapter study.\n"

    def cell(task, reference=False):
        row = snapshot["tasks"][task]
        if not reference and row["status"] != "Scored":
            return row.get("display", row["status"])
        value = 100 * row["biocoloop_seed42"] if reference else 100 * row["primary"]
        other = row["primary"] if reference else row["biocoloop_seed42"]
        text = f"{value:.2f}"
        if other is not None and round(value, 2) >= round(100 * other, 2):
            text = r"\textbf{" + text + "}"
        return text

    return "\n".join([
        r"\begin{table}[t]", r"\centering\footnotesize", r"\setlength{\tabcolsep}{3pt}",
        r"\begin{tabularx}{\linewidth}{@{}Xrrrrr@{}}", r"\toprule",
        "Method / transport & " + " & ".join(NAMES) + r" \\", r"\midrule",
        "AI-Researcher / final adapter & " + " & ".join(cell(task) for task in TASKS) + r" \\",
        "BioCoLoop & " + " & ".join(cell(task, True) for task in TASKS) + r" \\",
        r"\bottomrule", r"\end{tabularx}",
        r"\caption{Final-adapter comparison at seed 42 with ten laboratories. AI-Researcher retains its native early-stop decision under a six-candidate maximum; no candidate is imputed to spend unused budget. All candidate fits and held-out scores use the shared scientific protocol. Values are multiplied by 100; bold marks the better value or a tie among scored pairs. Original-adapter outcomes remain in Table~\ref{tab:public-harness-comparison-seed42}.}",
        r"\label{tab:public-harness-final-adapter}", r"\end{table}", ""])


def write(short_base, output, dti_base=None):
    snapshot = collect(short_base, dti_base)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    (output / FILES[0]).write_text(table(snapshot))
    (output / FILES[1]).write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n")
    return snapshot


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--dti-base", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    snapshot = write(args.base, args.output_dir, args.dti_base)
    print(json.dumps({key: snapshot[key] for key in ("registered", "resolved", "scored")}))
