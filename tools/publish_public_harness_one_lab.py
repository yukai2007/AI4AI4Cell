"""Publish the verified seed-42 public-controller comparison with lab-0 access.

The two task-adapted public controllers receive only laboratory 0.  BioCoLoop
retains the ten-laboratory setting from the prespecified core experiment.  This
script rejects an otherwise valid public-controller result if its held-out seal
or development definition names any laboratory other than 0.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

PAPER = Path(__file__).resolve().parents[1]
ROOT = PAPER.parent
ORIGINAL = ROOT / "extensions/public_harness_20260924"
ONE_LAB = ROOT / "extensions/public_harness_one_lab_20260925"
for path in (ORIGINAL,):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import publish_public_harness as old
from publish_strong_snapshot import collect as collect_reference

TASKS = old.TASKS
PUBLIC = ("ai_scientist_v2", "ai_researcher")
LABELS = {"ai_scientist_v2": "AI-Scientist-v2 (1 lab)",
          "ai_researcher": "AI-Researcher (1 lab)"}
FAILURE_TOKENS = {
    "Tool response remained invalid after": r"$F_{\mathrm{tool}}$",
    "Native required-tool stage ended": r"$F_{\mathrm{tool}}$",
    "Native stage exhausted with a failed completion/tool receipt": r"$F_{\mathrm{pipe}}$",
    "Native context exceeds declared token limit": r"$F_{\mathrm{ctx}}$",
    "too many values to unpack (expected 2)": r"$F_{\mathrm{pipe}}$",
}
REQUIRED = ("seal.json", "results.json", "audit.json", "verification.json")


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _verify_readonly(folder, task):
    python = (Path(read(ROOT / "results/unified_bio_20260918/native_tapb/data/manifest.json")
                        ["worker_python"]).resolve() if task == "native_tapb"
              else ROOT / "extensions/public_harness_20260924/.venv/bin/python")
    command = [str(python), "-B", str(ONE_LAB / "verify_readonly_one_lab.py"),
               str(Path(folder).resolve())]
    completed = subprocess.run(command, check=True, capture_output=True, text=True,
                               env={**__import__("os").environ,
                                    "PYTHONPATH": str(ONE_LAB) + ":" + str(ORIGINAL) + ":" + str(ROOT)})
    receipt = json.loads(completed.stdout)
    if receipt.get("status") != "PASS":
        raise ValueError("Independent one-lab verifier did not pass")
    return receipt


def _failure(run):
    status_path = run / "run_status.json"
    if not status_path.is_file():
        return None
    status = read(status_path)
    if status.get("status") != "FAILED":
        return None
    error = status.get("error", "").removeprefix("Error: ")
    token = next((value for prefix, value in FAILURE_TOKENS.items()
                  if error.startswith(prefix)), None)
    if token is None:
        raise ValueError(f"Unregistered public-controller failure: {error}")
    definition_path = run / "development/definition.json"
    if not definition_path.is_file() or read(definition_path).get("clients") != [0]:
        raise ValueError("Failed controller run is not bound to lab 0")
    if (run / "heldout/results.json").exists():
        raise ValueError("A failed controller run cannot also have a held-out score")
    return {"status": "failed", "display": token, "error": error,
            "run_status_sha256": sha(status_path),
            "definition_sha256": sha(definition_path)}


def _score(run, harness, task):
    folder = run / "heldout"
    missing = [name for name in REQUIRED if not (folder / name).is_file()]
    if missing:
        failure = _failure(run)
        if failure is not None:
            return failure
        raise ValueError(f"Incomplete one-lab result for {harness}/{task}: {missing}")
    result, seal = read(folder / "results.json"), read(folder / "seal.json")
    verification = _verify_readonly(folder, task)
    if (result.get("harness") != harness or result.get("task") != task
            or result.get("seed") != 42 or result.get("role") != old.ROLE
            or seal.get("harness") != harness or seal.get("task") != task
            or seal.get("seed") != 42 or seal.get("role") != old.ROLE):
        raise ValueError("One-lab result identity differs from its path")
    if (seal.get("clients") != [0]
            or seal.get("laboratory_access") != "lab 0 only"
            or seal.get("collaborative_aggregation") is not False
            or seal.get("rounds") != 100 or seal.get("slots") != 6
            or result.get("execution_kind") != "fresh-canonical-v3"
            or seal.get("execution_kind") != "fresh-canonical-v3"
            or result.get("feedback_to_controller") is not False
            or seal.get("feedback_to_controller") is not False):
        raise ValueError("Public controller used a different access or budget contract")
    if verification.get("status") != "PASS":
        raise ValueError("Independent held-out verification did not pass")
    definition_path = Path(seal["run_dir"]) / "definition.json"
    definition = read(definition_path)
    if (definition.get("clients") != [0]
            or definition.get("rounds") != 100 or definition.get("slots") != 6
            or definition["config"].get("upstream_commit") != old.HARNESSES[harness]["commit"]):
        raise ValueError("Development definition is not the registered lab-0 protocol")
    primary = result.get("primary")
    if isinstance(primary, bool) or not isinstance(primary, (int, float)) or not math.isfinite(primary):
        raise ValueError("Held-out primary metric is not finite")
    selection = read(definition_path.parent / "selected_development.json")
    record = selection["record"]
    fit_name = Path(record["checkpoint"]).parent.name
    selected_design = fit_name.rsplit("_", 1)[-1]
    if not selected_design.startswith("D"):
        raise ValueError("Selected checkpoint does not encode a registered design")
    return {"status": "scored", "primary": float(primary),
            "selected_design": selected_design,
            "selected_round": record["best"]["round"],
            "proposal_slots_used": selection.get("proposal_slots_used", 6),
            "receipts": {name: sha(folder / name) for name in REQUIRED},
            "definition_sha256": sha(definition_path),
            "checkpoint_sha256": result.get("checkpoint_sha256")}


def collect(base, reference_base):
    base, reference_base = Path(base).resolve(), Path(reference_base).resolve()
    manifest = read(base / "queue_manifest.json")
    supervisor = read(base / "supervisor_status.json")
    if (manifest.get("schema") != "public-harness-one-lab-matrix-v1"
            or manifest.get("clients") != [0]
            or manifest.get("collaborative_aggregation") is not False
            or manifest.get("research_model") != "Qwen2.5-7B-Instruct"
            or manifest.get("designs") != 12 or manifest.get("candidate_cap") != 6
            or manifest.get("candidate_rounds") != 100
            or supervisor.get("status") not in ("COMPLETE", "COMPLETE_WITH_FAILURES")):
        raise ValueError("The one-lab matrix is incomplete or uses another protocol")
    reference = collect_reference(reference_base, [42, 43, 44])
    tasks = {}
    for task in TASKS:
        reference_runs = reference["tasks"][task]["runs"]
        core = {}
        for method in ("single_fixed", "single_direct", "federated_loop"):
            values = [reference_runs[str(seed)]["scores"][method]["primary"]
                      for seed in (42, 43, 44)]
            mean = sum(values) / 3
            sd = (sum((value - mean) ** 2 for value in values) / 2) ** 0.5
            core[method] = {"mean": mean, "sd": sd,
                            "seed42": reference_runs["42"]["scores"][method]["primary"]}
        public = {harness: _score(base / harness / task / "seed42", harness, task)
                  for harness in PUBLIC}
        tasks[task] = {"core": core, "public": public}
    return {"schema": "public-harness-one-lab-publication-v1",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "base": str(base), "reference_base": str(reference_base),
            "protocol": {"public_controller_laboratories": [0],
                         "biocoloop_laboratories": list(range(10)),
                         "research_model": "Qwen2.5-7B-Instruct",
                         "designs": 12, "candidate_cap": 6, "candidate_rounds": 100},
            "manifest_sha256": sha(base / "queue_manifest.json"),
            "supervisor_sha256": sha(base / "supervisor_status.json"),
            "source_sha256": {str(Path(__file__).resolve()): sha(__file__),
                              **{str(path): sha(path) for path in sorted(ONE_LAB.glob("*.py"))}},
            "tasks": tasks}


def table_text(snapshot):
    core_methods = ("single_fixed", "single_direct", "federated_loop")
    public_methods = ("single_direct", "ai_scientist_v2", "ai_researcher", "federated_loop")

    def number(panel, method, task):
        item = snapshot["tasks"][task]
        if panel == "core":
            return 100 * item["core"][method]["mean"]
        if method in PUBLIC:
            run = item["public"][method]
            return None if run["status"] != "scored" else 100 * run["primary"]
        return 100 * item["core"][method]["seed42"]

    ranks = {}
    for panel, methods in (("core", core_methods), ("public", public_methods)):
        for task in TASKS:
            ranks[panel, task] = sorted({round(number(panel, method, task), 2)
                                        for method in methods if number(panel, method, task) is not None},
                                       reverse=True)

    def cell(panel, method, task):
        value = number(panel, method, task)
        if value is None:
            return snapshot["tasks"][task]["public"][method]["display"]
        rounded = round(value, 2)
        shown = f"{rounded:.2f}"
        ranking = ranks[panel, task]
        if rounded == ranking[0]:
            shown = r"\textbf{" + shown + "}"
        elif len(ranking) > 1 and rounded == ranking[1]:
            shown = r"\underline{" + shown + "}"
        if panel == "core":
            shown += r" $\pm$ " + f"{100 * snapshot['tasks'][task]['core'][method]['sd']:.2f}"
        return shown

    def row(panel, method, label):
        return label + " & " + " & ".join(cell(panel, method, task) for task in TASKS) + r" \\"

    lines = [r"\begin{table}[t]", r"\centering\footnotesize", r"\setlength{\tabcolsep}{2.6pt}",
             r"\renewcommand{\arraystretch}{1.00}", r"\begin{tabularx}{\linewidth}{@{}Xrrrrr@{}}", r"\toprule",
             r"\textbf{Model / method} & \multicolumn{1}{c}{DTI} & \multicolumn{1}{c}{Proteomics} & \multicolumn{3}{c}{Cell perturbation} \\",
             r"\cmidrule(lr){2-2}\cmidrule(lr){3-3}\cmidrule(l){4-6}",
             r" & \shortstack{BindingDB\\AUROC $\uparrow$} & \shortstack{PTPC\\AP $\uparrow$} & \shortstack{VCC\\Top-1 $\uparrow$} & \shortstack{Norman\\Top-1 $\uparrow$} & \shortstack{Tahoe\\Top-1 $\uparrow$} \\",
             r"\midrule", r"\multicolumn{6}{l}{\textbf{A. Core comparison, seeds 42--44 (mean $\pm$ SD)}} \\",
             row("core", "single_fixed", "Fixed model (1 lab)"),
             row("core", "single_direct", "Qwen direct (1 lab)"),
             row("core", "federated_loop", r"\textbf{BioCoLoop} (10 labs)"),
             r"\midrule", r"\multicolumn{6}{l}{\textbf{B. Research-controller comparison, seed 42}} \\",
             row("public", "single_direct", "Qwen direct (1 lab)"),
             row("public", "ai_scientist_v2", LABELS["ai_scientist_v2"]),
             row("public", "ai_researcher", LABELS["ai_researcher"]),
             row("public", "federated_loop", r"\textbf{BioCoLoop} (10 labs)"),
             r"\bottomrule", r"\end{tabularx}",
             (r"\caption{Main results. A: core mean $\pm$ SD over seeds 42--44. "
              r"B: seed-42 task-adapted public controllers use laboratory 0 and BioCoLoop uses ten laboratories. "
              r"All use Qwen2.5-7B-Instruct, 12 designs, at most six candidates and 100 rounds per candidate. "
              r"Scores are $\times100$; bold/underline mark the best/second-best in each panel. "
              r"$F_{\mathrm{pipe}}$ denotes a terminal controller-pipeline failure.}"),
             r"\label{tab:public-harness-comparison-three-seed}", r"\end{table}"]
    return "\n".join(lines) + "\n"


def write(snapshot, output_dir):
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    (output / "main_public_harness_three_seed.tex").write_text(table_text(snapshot))
    (output / "snapshot_one_lab.json").write_text(json.dumps(snapshot, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--reference-results", type=Path,
                        default=ROOT / "results/unified_bio_20260918")
    parser.add_argument("--output-dir", type=Path,
                        default=PAPER / "tables/public_harness_comparison")
    args = parser.parse_args()
    evidence = collect(args.base, args.reference_results)
    write(evidence, args.output_dir)
    print(json.dumps({"status": "PUBLISHED", "output": str(args.output_dir.resolve()),
                      "protocol": evidence["protocol"]}, indent=2))
