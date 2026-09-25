"""Publish a single three-seed table for core and public-controller methods."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import subprocess
import os

import publish_public_harness_one_lab as one

PAPER = Path(__file__).resolve().parents[1]
ROOT = PAPER.parent
TASKS = one.TASKS
PUBLIC = one.PUBLIC
SEEDS = (42, 43, 44)
LABELS = {
    "single_fixed": "Fixed model (1 lab)",
    "single_direct": "Qwen direct (1 lab)",
    "ai_scientist_v2": "AI-Scientist-v2 (1 lab)",
    "ai_researcher": "AI-Researcher (1 lab)",
    "federated_loop": r"\textbf{BioCoLoop} (10 labs)",
}
METHODS = tuple(LABELS)


def read(path):
    return json.loads(Path(path).read_text())


def verify_readonly(folder, task):
    """Run the independent verifier without collapsing the TAPB venv symlink."""
    if task != "native_tapb":
        return one._verify_readonly(folder, task)
    manifest = read(ROOT / "results/unified_bio_20260918/native_tapb/data/manifest.json")
    python = Path(manifest["worker_python"])
    command = [str(python), "-B",
               str(ROOT / "extensions/public_harness_one_lab_20260925/verify_readonly_one_lab.py"),
               str(Path(folder).resolve())]
    completed = subprocess.run(
        command, check=True, capture_output=True, text=True,
        env={**os.environ,
             "PYTHONPATH": ":".join((
                 str(ROOT / "extensions/public_harness_one_lab_20260925"),
                 str(ROOT / "extensions/public_harness_20260924"), str(ROOT)))})
    receipt = json.loads(completed.stdout)
    if receipt.get("status") != "PASS":
        raise ValueError("Independent one-lab verifier did not pass")
    return receipt


def _score_at(run, harness, task, seed):
    run = Path(run).resolve()
    folder = run / "heldout"
    missing = [name for name in one.REQUIRED if not (folder / name).is_file()]
    if missing:
        failed = one._failure(run)
        if failed is None:
            raise ValueError(f"Incomplete public-controller result: {run}: {missing}")
        status = read(run / "run_status.json")
        if status.get("seed") != seed or status.get("task") != task:
            raise ValueError("Failed run identity does not match its matrix position")
        return failed

    result, seal = read(folder / "results.json"), read(folder / "seal.json")
    verification = verify_readonly(folder, task)
    identity = (result.get("harness"), result.get("task"), result.get("seed"), result.get("role"))
    sealed_identity = (seal.get("harness"), seal.get("task"), seal.get("seed"), seal.get("role"))
    expected = (harness, task, seed, one.old.ROLE)
    if identity != expected or sealed_identity != expected:
        raise ValueError("Result identity differs from its matrix position")
    if (seal.get("clients") != [0]
            or seal.get("laboratory_access") != "lab 0 only"
            or seal.get("collaborative_aggregation") is not False
            or seal.get("rounds") != 100 or seal.get("slots") != 6
            or result.get("execution_kind") != "fresh-canonical-v3"
            or seal.get("execution_kind") != "fresh-canonical-v3"
            or result.get("feedback_to_controller") is not False
            or seal.get("feedback_to_controller") is not False
            or verification.get("status") != "PASS"):
        raise ValueError("Public-controller result violates the registered lab-0 protocol")
    definition_path = Path(seal["run_dir"]) / "definition.json"
    definition = read(definition_path)
    definition_seed = definition.get("seed")
    if (definition.get("clients") != [0]
            or definition.get("rounds") != 100 or definition.get("slots") != 6
            # The native public-controller definition schema predates the
            # seed-labelled queue and records the repetition in run_status,
            # while newer definitions may also copy it into this field.
            or definition_seed not in (None, seed)
            or definition["config"].get("upstream_commit") != one.old.HARNESSES[harness]["commit"]):
        raise ValueError("Development definition is not the registered protocol")
    primary = result.get("primary")
    if isinstance(primary, bool) or not isinstance(primary, (int, float)) or not math.isfinite(primary):
        raise ValueError("Held-out primary metric is not finite")
    selection = read(definition_path.parent / "selected_development.json")
    record = selection["record"]
    selected_design = Path(record["checkpoint"]).parent.name.rsplit("_", 1)[-1]
    if not selected_design.startswith("D"):
        raise ValueError("Selected checkpoint does not encode a registered design")
    return {
        "status": "scored", "primary": float(primary),
        "selected_design": selected_design, "selected_round": record["best"]["round"],
        "proposal_slots_used": selection.get("proposal_slots_used", 6),
        "receipts": {name: one.sha(folder / name) for name in one.REQUIRED},
        "definition_sha256": one.sha(definition_path),
        "checkpoint_sha256": result.get("checkpoint_sha256"),
    }


def _retry_is_terminal(run):
    """Use a retry only after it has a sealed score or terminal failure."""
    run = Path(run)
    if not run.exists():
        return False
    if (run / "heldout" / "results.json").is_file():
        return True
    status = run / "run_status.json"
    if not status.is_file():
        return False
    return read(status).get("status") == "FAILED"


def summarize(runs):
    values = [run["primary"] for run in runs.values() if run["status"] == "scored"]
    failures = [run["display"] for run in runs.values() if run["status"] != "scored"]
    result = {"runs": runs, "completed": len(values), "attempted": len(runs),
              "complete": len(values) == len(runs), "failure_tokens": sorted(set(failures))}
    if values:
        mean = sum(values) / len(values)
        sd = ((sum((value - mean) ** 2 for value in values) / (len(values) - 1)) ** 0.5
              if len(values) > 1 else None)
        result.update(mean=mean, sd=sd)
    return result


def collect(seed42_base, additional_base, reference_base, retry_base=None):
    seed42 = one.collect(seed42_base, reference_base)
    additional_base = Path(additional_base).resolve()
    retry_base = Path(retry_base).resolve() if retry_base is not None else None
    manifest = read(additional_base / "queue_manifest.json")
    supervisor = read(additional_base / "supervisor_status.json")
    if (manifest.get("schema") != "public-harness-one-lab-additional-seeds-v1"
            or manifest.get("seeds") != [43, 44] or manifest.get("clients") != [0]
            or manifest.get("collaborative_aggregation") is not False
            or manifest.get("research_model") != "Qwen2.5-7B-Instruct"
            or manifest.get("designs") != 12 or manifest.get("candidate_cap") != 6
            or manifest.get("candidate_rounds") != 100
            or len(manifest.get("jobs", [])) != 20
            or supervisor.get("status") not in ("COMPLETE", "COMPLETE_WITH_FAILURES")):
        raise ValueError("Additional-seed matrix is incomplete or uses another protocol")

    tasks = {}
    for task in TASKS:
        core = seed42["tasks"][task]["core"]
        public = {}
        for harness in PUBLIC:
            retry = (retry_base / harness / task / "seed42"
                     if retry_base is not None else None)
            runs = {"42": (_score_at(retry, harness, task, 42)
                            if retry is not None and _retry_is_terminal(retry)
                            else seed42["tasks"][task]["public"][harness])}
            for seed in (43, 44):
                retry = (retry_base / harness / task / f"seed{seed}"
                         if retry_base is not None else None)
                path = (retry if retry is not None and _retry_is_terminal(retry)
                        else additional_base / harness / task / f"seed{seed}")
                runs[str(seed)] = _score_at(path, harness, task, seed)
            public[harness] = summarize(runs)
        tasks[task] = {"core": core, "public": public}
    return {
        "schema": "public-harness-one-lab-three-seed-publication-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "seed42_base": str(Path(seed42_base).resolve()),
        "additional_base": str(additional_base),
        "retry_base": str(retry_base) if retry_base is not None else None,
        "reference_base": str(Path(reference_base).resolve()),
        "protocol": {
            "seeds": list(SEEDS), "public_controller_laboratories": [0],
            "biocoloop_laboratories": list(range(10)),
            "research_model": "Qwen2.5-7B-Instruct", "designs": 12,
            "candidate_cap": 6, "candidate_rounds": 100,
        },
        "manifest_sha256": one.sha(additional_base / "queue_manifest.json"),
        "supervisor_sha256": one.sha(additional_base / "supervisor_status.json"),
        "source_sha256": {str(Path(__file__).resolve()): one.sha(__file__)},
        "tasks": tasks,
    }


def table_text(snapshot):
    def summary(method, task):
        item = snapshot["tasks"][task]
        if method in PUBLIC:
            return item["public"][method]
        core = item["core"][method]
        return {"complete": True, "completed": 3, "attempted": 3,
                "mean": core["mean"], "sd": core["sd"], "failure_tokens": []}

    rankings = {}
    for task in TASKS:
        rankings[task] = sorted({round(100 * summary(method, task)["mean"], 2)
                                 for method in METHODS if summary(method, task)["complete"]},
                                reverse=True)

    def cell(method, task):
        item = summary(method, task)
        if not item["complete"]:
            count = f"({item['completed']}/{item['attempted']})"
            if not item.get("mean"):
                token = item["failure_tokens"][0] if len(item["failure_tokens"]) == 1 else r"$F$"
                return token + r"\," + count
            value = f"{100 * item['mean']:.2f}"
            if item.get("sd") is not None:
                value += r" $\pm$ " + f"{100 * item['sd']:.2f}"
            return value + r"\," + count
        rounded = round(100 * item["mean"], 2)
        shown = f"{rounded:.2f}"
        ranking = rankings[task]
        if rounded == ranking[0]:
            shown = r"\textbf{" + shown + "}"
        elif len(ranking) > 1 and rounded == ranking[1]:
            shown = r"\underline{" + shown + "}"
        return shown + r" $\pm$ " + f"{100 * item['sd']:.2f}"

    def row(method):
        return LABELS[method] + " & " + " & ".join(cell(method, task) for task in TASKS) + r" \\"

    lines = [
        r"\begin{table}[t]", r"\centering\scriptsize", r"\setlength{\tabcolsep}{1.65pt}",
        r"\renewcommand{\arraystretch}{0.92}",
        r"\begin{tabularx}{\linewidth}{@{}Xrrrrr@{}}", r"\toprule",
        r"\textbf{Model / method} & \multicolumn{1}{c}{DTI} & \multicolumn{1}{c}{Proteomics} & \multicolumn{3}{c}{Cell perturbation} \\",
        r"\cmidrule(lr){2-2}\cmidrule(lr){3-3}\cmidrule(l){4-6}",
        r" & \shortstack{BindingDB\\AUROC $\uparrow$} & \shortstack{PTPC\\AP $\uparrow$} & \shortstack{VCC\\Top-1 $\uparrow$} & \shortstack{Norman\\Top-1 $\uparrow$} & \shortstack{Tahoe\\Top-1 $\uparrow$} \\",
        r"\midrule",
        *[row(method) for method in METHODS],
        r"\bottomrule", r"\end{tabularx}",
        (r"\caption{Three-seed comparison (mean $\pm$ sample SD; seeds 42--44). "
         r"Public methods use laboratory 0; BioCoLoop uses ten. All rows share the "
         r"Qwen2.5-7B-Instruct backend, 12-design library, six-candidate cap, "
         r"100-round fits and held-out scorer. Scores are $\times100$; bold/underline "
         r"mark the best/second-best complete result. $(n/3)$ reports incomplete cells.}"),
        r"\label{tab:public-harness-comparison-three-seed}", r"\end{table}",
    ]
    return "\n".join(lines) + "\n"


def write(snapshot, output_dir):
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    (output / "main_public_harness_three_seed.tex").write_text(table_text(snapshot))
    (output / "snapshot_multiseed.json").write_text(json.dumps(snapshot, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed42-base", type=Path, required=True)
    parser.add_argument("--additional-base", type=Path, required=True)
    parser.add_argument("--reference-results", type=Path,
                        default=ROOT / "results/unified_bio_20260918")
    parser.add_argument("--retry-base", type=Path,
                        help="Optional fresh retry tree; existing positions override the original run")
    parser.add_argument("--output-dir", type=Path,
                        default=PAPER / "tables/public_harness_comparison")
    args = parser.parse_args()
    snapshot = collect(args.seed42_base, args.additional_base, args.reference_results,
                       retry_base=args.retry_base)
    write(snapshot, args.output_dir)
    print(json.dumps({"status": "PUBLISHED", "protocol": snapshot["protocol"]}, indent=2))
