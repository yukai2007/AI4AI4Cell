"""Publish the three-seed Qwen/Luna grouped main table from verified evidence."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import sys


PAPER = Path(__file__).resolve().parents[1]
ROOT = PAPER.parent
TOOLS = PAPER / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import publish_public_harness_one_lab as one  # noqa: E402


TASKS = one.TASKS
PUBLIC = one.PUBLIC
SEEDS = (42, 43, 44)
METHODS = ("single_fixed", "single_direct", "ai_scientist_v2",
           "ai_researcher", "federated_loop")
METHOD_LABELS = {
    "single_fixed": "Fixed model",
    "single_direct": "Direct",
    "ai_scientist_v2": "AI-Scientist-v2",
    "ai_researcher": "AI-Researcher",
    "federated_loop": r"\textbf{BioCoLoop}",
}
MODEL_LABELS = {
    "qwen": "Qwen2.5-7B-Instruct",
    "luna": "GPT-5.6 Luna (low reasoning)",
}
LUNA_FAILURE_TOKENS = {
    **one.FAILURE_TOKENS,
    "Native context uses ": r"$F_{\mathrm{ctx}}$",
    "GPT-5.6 Luna transport/tool-isolation failure": r"$F_{\mathrm{svc}}$",
}
# Native-message admission budgets accepted for the Luna public controllers.
# 28000 is the registered matched budget; 65536 is the extended admission used
# for the AI-Researcher rows whose accumulated native history exceeded it.
LUNA_ADMISSION_CAPS = (28000, 65536)
EXTENDED_NATIVE_TOKEN_CAP = 65536


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def stats(values):
    if len(values) != len(SEEDS):
        raise ValueError("Core method is missing a registered seed")
    return {"complete": True, "completed": len(values), "attempted": len(values),
            "mean": statistics.mean(values), "sd": statistics.stdev(values),
            "failure_tokens": [], "values": dict(zip(map(str, SEEDS), values))}


def luna_failure(run, harness, task, seed):
    status_path = run / "run_status.json"
    if not status_path.is_file():
        return None
    status = read(status_path)
    if status.get("status") != "FAILED":
        return None
    if (status.get("harness"), status.get("task"), status.get("seed")) != (harness, task, seed):
        raise ValueError("Failed Luna run identity differs from its matrix position")
    error = status.get("error", "").removeprefix("Error: ")
    token = next((value for prefix, value in LUNA_FAILURE_TOKENS.items()
                  if error.startswith(prefix)), None)
    if token is None:
        raise ValueError(f"Unregistered Luna controller failure: {error}")
    definition_path = run / "development/definition.json"
    definition = read(definition_path)
    if (definition.get("clients") != [0] or definition.get("config", {}).get("seed") != seed
            or (run / "heldout/results.json").exists()):
        raise ValueError("Failed Luna run violates the lab-0 failure contract")
    return {"status": "failed", "display": token, "error": error,
            "run_status_sha256": sha(status_path),
            "definition_sha256": sha(definition_path)}


def luna_public_score(run, harness, task, seed):
    run = Path(run).resolve()
    heldout = run / "heldout"
    missing = [name for name in one.REQUIRED if not (heldout / name).is_file()]
    if missing:
        failure = luna_failure(run, harness, task, seed)
        if failure is None:
            raise ValueError(f"Incomplete Luna public-controller result: {run}: {missing}")
        return failure

    result, seal = read(heldout / "results.json"), read(heldout / "seal.json")
    verification = one._verify_readonly(heldout, task)
    expected = (harness, task, seed, one.old.ROLE)
    if ((result.get("harness"), result.get("task"), result.get("seed"), result.get("role")) != expected
            or (seal.get("harness"), seal.get("task"), seal.get("seed"), seal.get("role")) != expected):
        raise ValueError("Luna public-controller identity differs from its matrix position")
    if (seal.get("clients") != [0]
            or seal.get("laboratory_access") != "lab 0 only"
            or seal.get("collaborative_aggregation") is not False
            or seal.get("rounds") != 100 or seal.get("slots") != 6
            or result.get("execution_kind") != "fresh-canonical-v3"
            or seal.get("execution_kind") != "fresh-canonical-v3"
            or result.get("feedback_to_controller") is not False
            or seal.get("feedback_to_controller") is not False
            or verification.get("status") != "PASS"):
        raise ValueError("Luna public controller violates the registered lab-0 protocol")
    definition_path = Path(seal["run_dir"]) / "definition.json"
    definition = read(definition_path)
    if (definition.get("clients") != [0] or definition.get("rounds") != 100
            or definition.get("slots") != 6 or definition.get("config", {}).get("seed") != seed
            or definition["config"].get("upstream_commit") != one.old.HARNESSES[harness]["commit"]):
        raise ValueError("Luna development definition is not the registered protocol")
    backend_path = run / "model_calls/backend.json"
    backend = read(backend_path)
    if (backend.get("model") != "gpt-5.6-luna"
            or backend.get("reasoning_effort") != "low"
            or backend.get("generation_seed_supported") is not False
            or backend.get("declared_input_cap") not in LUNA_ADMISSION_CAPS
            or backend.get("max_calls") != 160
            or backend.get("tool_events_allowed") is not False):
        raise ValueError("Unexpected Luna public-controller backend")
    primary = result.get("primary")
    if isinstance(primary, bool) or not isinstance(primary, (int, float)) or not math.isfinite(primary):
        raise ValueError("Luna held-out primary metric is not finite")
    selection = read(definition_path.parent / "selected_development.json")
    record = selection["record"]
    selected_design = Path(record["checkpoint"]).parent.name.rsplit("_", 1)[-1]
    if not selected_design.startswith("D"):
        raise ValueError("Selected Luna checkpoint lacks a registered design")
    return {
        "status": "scored", "primary": float(primary),
        "selected_design": selected_design, "selected_round": record["best"]["round"],
        "proposal_slots_used": selection.get("proposal_slots_used", 6),
        "receipts": {name: sha(heldout / name) for name in one.REQUIRED},
        "definition_sha256": sha(definition_path), "backend_sha256": sha(backend_path),
        "checkpoint_sha256": result.get("checkpoint_sha256"),
        "declared_input_cap": backend.get("declared_input_cap"),
    }


def summarize_public(runs):
    values = [run["primary"] for run in runs.values() if run["status"] == "scored"]
    failures = [run["display"] for run in runs.values() if run["status"] != "scored"]
    summary = {"runs": runs, "completed": len(values), "attempted": len(runs),
               "complete": len(values) == len(runs),
               "failure_tokens": sorted(set(failures))}
    summary["extended_context_seeds"] = sorted(
        seed for seed, run in runs.items()
        if (run.get("declared_input_cap") or 28000) > 28000)
    if values:
        summary["mean"] = statistics.mean(values)
        summary["sd"] = statistics.stdev(values) if len(values) > 1 else None
    return summary


def qwen_additional_score(run, harness, task, seed):
    run = Path(run).resolve()
    heldout = run / "heldout"
    missing = [name for name in one.REQUIRED if not (heldout / name).is_file()]
    if missing:
        failure = one._failure(run)
        if failure is None:
            raise ValueError(f"Incomplete Qwen public-controller result: {run}: {missing}")
        status = read(run / "run_status.json")
        if (status.get("harness"), status.get("task"), status.get("seed")) != (harness, task, seed):
            raise ValueError("Failed Qwen run identity differs from its matrix position")
        return failure
    result, seal = read(heldout / "results.json"), read(heldout / "seal.json")
    verification = one._verify_readonly(heldout, task)
    expected = (harness, task, seed, one.old.ROLE)
    if ((result.get("harness"), result.get("task"), result.get("seed"), result.get("role")) != expected
            or (seal.get("harness"), seal.get("task"), seal.get("seed"), seal.get("role")) != expected):
        raise ValueError("Qwen public-controller identity differs from its matrix position")
    if (seal.get("clients") != [0]
            or seal.get("laboratory_access") != "lab 0 only"
            or seal.get("collaborative_aggregation") is not False
            or seal.get("rounds") != 100 or seal.get("slots") != 6
            or result.get("execution_kind") != "fresh-canonical-v3"
            or seal.get("execution_kind") != "fresh-canonical-v3"
            or result.get("feedback_to_controller") is not False
            or seal.get("feedback_to_controller") is not False
            or verification.get("status") != "PASS"):
        raise ValueError("Qwen public controller violates the registered lab-0 protocol")
    definition_path = Path(seal["run_dir"]) / "definition.json"
    definition = read(definition_path)
    if (definition.get("clients") != [0] or definition.get("rounds") != 100
            or definition.get("slots") != 6 or definition.get("config", {}).get("seed") != seed
            or definition["config"].get("upstream_commit") != one.old.HARNESSES[harness]["commit"]):
        raise ValueError("Qwen development definition is not the registered protocol")
    primary = result.get("primary")
    if isinstance(primary, bool) or not isinstance(primary, (int, float)) or not math.isfinite(primary):
        raise ValueError("Qwen held-out primary metric is not finite")
    selection = read(definition_path.parent / "selected_development.json")
    record = selection["record"]
    selected_design = Path(record["checkpoint"]).parent.name.rsplit("_", 1)[-1]
    if not selected_design.startswith("D"):
        raise ValueError("Selected Qwen checkpoint lacks a registered design")
    return {
        "status": "scored", "primary": float(primary),
        "selected_design": selected_design, "selected_round": record["best"]["round"],
        "proposal_slots_used": selection.get("proposal_slots_used", 6),
        "receipts": {name: sha(heldout / name) for name in one.REQUIRED},
        "definition_sha256": sha(definition_path),
        "checkpoint_sha256": result.get("checkpoint_sha256"),
    }


def _retry_is_terminal(run):
    run = Path(run)
    if not run.exists():
        return False
    if (run / "heldout" / "results.json").is_file():
        return True
    status = run / "run_status.json"
    return status.is_file() and read(status).get("status") == "FAILED"


def collect_qwen(seed42_base, additional_base, reference_results, retry_base=None):
    seed42 = one.collect(seed42_base, reference_results)
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
            or len(manifest.get("jobs", [])) != len(TASKS) * len(PUBLIC) * 2
            or supervisor.get("status") not in ("COMPLETE", "COMPLETE_WITH_FAILURES")
            or supervisor.get("active") or supervisor.get("pending")):
        raise ValueError("Qwen additional-seed matrix is incomplete or uses another protocol")
    tasks = {}
    for task in TASKS:
        public = {}
        for harness in PUBLIC:
            retry = (retry_base / harness / task / "seed42"
                     if retry_base is not None else None)
            runs = {"42": (qwen_additional_score(retry, harness, task, 42)
                            if retry is not None and _retry_is_terminal(retry)
                            else seed42["tasks"][task]["public"][harness])}
            for seed in (43, 44):
                retry = (retry_base / harness / task / f"seed{seed}"
                         if retry_base is not None else None)
                path = (retry if retry is not None and _retry_is_terminal(retry)
                        else additional_base / harness / task / f"seed{seed}")
                runs[str(seed)] = qwen_additional_score(path, harness, task, seed)
            public[harness] = summarize_public(runs)
        tasks[task] = {"core": seed42["tasks"][task]["core"], "public": public}
    return {
        "schema": "qwen-public-controller-three-seed-evidence-v1",
        "seed42_evidence": seed42, "additional_base": str(additional_base),
        "retry_base": str(retry_base) if retry_base is not None else None,
        "manifest_sha256": sha(additional_base / "queue_manifest.json"),
        "supervisor_sha256": sha(additional_base / "supervisor_status.json"),
        "tasks": tasks,
    }


def collect_luna_public(base, retry_base=None):
    base = Path(base).resolve()
    manifest, supervisor = read(base / "queue_manifest.json"), read(base / "supervisor_status.json")
    if (manifest.get("schema") != "public-harness-one-lab-luna-three-seed-v1"
            or manifest.get("seeds") != list(SEEDS) or manifest.get("clients") != [0]
            or manifest.get("collaborative_aggregation") is not False
            or manifest.get("research_model") != "gpt-5.6-luna"
            or manifest.get("reasoning_effort") != "low"
            or manifest.get("generation_seed_supported") is not False
            or manifest.get("designs") != 12 or manifest.get("candidate_cap") != 6
            or manifest.get("candidate_rounds") != 100
            or len(manifest.get("jobs", [])) != len(TASKS) * len(PUBLIC) * len(SEEDS)
            or supervisor.get("status") not in ("COMPLETE", "COMPLETE_WITH_FAILURES")
            or supervisor.get("active") or supervisor.get("pending")):
        raise ValueError("Luna public-controller matrix is incomplete or uses another protocol")
    retry_base = Path(retry_base).resolve() if retry_base is not None else None
    tasks = {}
    for task in TASKS:
        tasks[task] = {}
        for harness in PUBLIC:
            runs = {}
            for seed in SEEDS:
                retry = (retry_base / harness / task / f"seed{seed}"
                         if retry_base is not None else None)
                path = (retry if retry is not None and _retry_is_terminal(retry)
                        else base / harness / task / f"seed{seed}")
                runs[str(seed)] = luna_public_score(path, harness, task, seed)
            tasks[task][harness] = summarize_public(runs)
    return {"base": str(base), "retry_base": str(retry_base) if retry_base is not None else None,
            "manifest_sha256": sha(base / "queue_manifest.json"),
            "supervisor_sha256": sha(base / "supervisor_status.json"), "tasks": tasks}


def collect_luna_core(base, verification_path):
    base, verification_path = Path(base).resolve(), Path(verification_path).resolve()
    manifest, supervisor = read(base / "queue_manifest.json"), read(base / "supervisor_status.json")
    verification = read(verification_path)
    if (manifest.get("schema") != "luna-main-core-three-seed-queue-v1"
            or manifest.get("research_model") != "gpt-5.6-luna"
            or manifest.get("reasoning_effort") != "low"
            or manifest.get("seeds") != list(SEEDS)
            or supervisor.get("status") != "COMPLETE" or supervisor.get("failed")
            or verification.get("status") != "PASS"
            or verification.get("base") != str(base)
            or verification.get("manifest_sha256") != sha(base / "queue_manifest.json")
            or verification.get("supervisor_sha256") != sha(base / "supervisor_status.json")):
        raise ValueError("Luna core matrix lacks a matching complete independent verification")
    verified = {(record["task"], record["seed"]): record
                for record in verification.get("records", []) if record.get("status") == "PASS"}
    if len(verified) != len(TASKS) * len(SEEDS):
        raise ValueError("Independent Luna core verification is incomplete")
    tasks = {}
    for task in TASKS:
        per_seed = {}
        for seed in SEEDS:
            root = base / task / f"seed{seed}"
            result_path = root / "heldout/results.json"
            result = read(result_path)
            record = verified[task, seed]
            if (record.get("root") != str(root.resolve())
                    or record.get("result_sha256") != sha(result_path)
                    or record.get("selection_sha256") != sha(root / "development/selected_development.json")
                    or set(result.get("results", {})) != {
                        f"{participation}_{mode}"
                        for participation in ("single", "federated")
                        for mode in ("fixed", "direct", "loop")
                    }):
                raise ValueError("Verified Luna core evidence changed after independent scoring")
            per_seed[str(seed)] = {
                method: result["results"][method]["primary"]
                for method in ("single_fixed", "single_direct", "federated_loop")
            }
        tasks[task] = {
            method: stats([per_seed[str(seed)][method] for seed in SEEDS])
            for method in ("single_fixed", "single_direct", "federated_loop")
        }
    return {"base": str(base), "verification": str(verification_path),
            "verification_sha256": sha(verification_path), "tasks": tasks}


def collect(qwen_seed42, qwen_additional, luna_public, luna_core, luna_verification,
            reference_results, retry_base=None, luna_retry_base=None):
    qwen = collect_qwen(qwen_seed42, qwen_additional, reference_results,
                        retry_base=retry_base)
    public_luna = collect_luna_public(luna_public, retry_base=luna_retry_base)
    core_luna = collect_luna_core(luna_core, luna_verification)
    models = {"qwen": {}, "luna": {}}
    for task in TASKS:
        qwen_core = qwen["tasks"][task]["core"]
        qwen_methods = {
            method: {"complete": True, "completed": 3, "attempted": 3,
                     "mean": qwen_core[method]["mean"], "sd": qwen_core[method]["sd"],
                     "failure_tokens": []}
            for method in ("single_fixed", "single_direct", "federated_loop")
        }
        qwen_methods.update(qwen["tasks"][task]["public"])
        luna_methods = dict(core_luna["tasks"][task])
        luna_methods.update(public_luna["tasks"][task])
        fixed_mean_delta = abs(
            qwen_methods["single_fixed"]["mean"] - luna_methods["single_fixed"]["mean"]
        )
        fixed_sd_delta = abs(
            qwen_methods["single_fixed"]["sd"] - luna_methods["single_fixed"]["sd"]
        )
        if fixed_mean_delta > 1e-3 or fixed_sd_delta > 1e-3:
            raise ValueError("LLM-independent fixed reference differs beyond reproducibility tolerance")
        # Fixed model never calls an LLM.  Use the established Qwen fixed row as
        # the canonical baseline in both blocks, while retaining the fresh Luna
        # fixed evidence (and its tiny numerical delta) in the snapshot below.
        luna_methods["single_fixed"] = dict(qwen_methods["single_fixed"])
        models["qwen"][task], models["luna"][task] = qwen_methods, luna_methods
    return {
        "schema": "qwen-luna-grouped-main-three-seed-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "protocol": {
            "seeds": list(SEEDS), "designs": 12, "candidate_cap": 6,
            "candidate_rounds": 100, "public_controller_laboratories": [0],
            "biocoloop_laboratories": list(range(10)),
            "generation_seed_note": (
                "Qwen uses registered decoding seeds; Luna service generation has no exposed seed. "
                "The 42--44 labels still control training and search repetitions."
            ),
            "fixed_reference_note": (
                "The fixed arm does not call an LLM. The canonical table row is the Qwen fixed reference; "
                "fresh Luna fixed rescoring is retained in luna_core_evidence and matched within 1e-3."
            ),
        },
        "qwen_evidence": qwen, "luna_public_evidence": public_luna,
        "luna_core_evidence": core_luna, "models": models,
    }


TASK_SHORT = {
    "native_tapb": "DTI",
    "ptpc_neural": "Proteomics",
    "vcc_corrected": "VCC",
    "norman_double_corrected": "Norman",
    "tahoe_drug_corrected": "Tahoe",
}
TASK_HEADER = {
    "native_tapb": r"\shortstack{BindingDB\\AUROC $\uparrow$}",
    "ptpc_neural": r"\shortstack{PTPC\\AP $\uparrow$}",
    "vcc_corrected": r"\shortstack{VCC\\Top-1 $\uparrow$}",
    "norman_double_corrected": r"\shortstack{Norman\\Top-1 $\uparrow$}",
    "tahoe_drug_corrected": r"\shortstack{Tahoe\\Top-1 $\uparrow$}",
}
TABLE_PREAMBLE = [
    r"\definecolor{TblInk}{gray}{0.45}",
    r"\definecolor{TblUp}{RGB}{20,84,150}",
    r"\definecolor{TblDown}{RGB}{183,58,52}",
    r"\providecommand{\TblPartial}{\textsuperscript{\textcolor{TblInk}{$\dagger$}}}",
    r"\providecommand{\TblZero}{\textcolor{TblInk}{--}}",
    r"\providecommand{\TblStar}{\textsuperscript{\textcolor{TblInk}{$\star$}}}",
    r"\providecommand{\TblUp}[1]{\textcolor{TblUp}{$\uparrow$#1}}",
    r"\providecommand{\TblDown}[1]{\textcolor{TblDown}{$\downarrow$#1}}",
    # Seven equal-width columns: the label column is ragged right, the six
    # endpoint/rank columns are centred so no single column absorbs the slack.
    r"\newcolumntype{L}{>{\raggedright\arraybackslash}X}",
    r"\newcolumntype{Q}{>{\centering\arraybackslash}X}",
]


def task_ranks(snapshot, model):
    """Average rank of every complete method on every endpoint of one block."""
    ranks = {}
    for task in TASKS:
        scored = [(method, round(100 * snapshot["models"][model][task][method]["mean"], 2))
                  for method in METHODS
                  if snapshot["models"][model][task][method]["complete"]]
        ordered = sorted({value for _, value in scored}, reverse=True)
        position = {value: [index + 1 for index, kept in enumerate(ordered) if kept == value]
                    for value in ordered}
        for method, value in scored:
            ranks.setdefault(method, []).append(statistics.mean(position[value]))
    return {method: (statistics.mean(values) if values else None)
            for method, values in ranks.items()}


def _plain_label(value):
    return re.sub(r"\\textbf\{|\}|\\", "", value)


SHORT_BLOCK = {"qwen": "Qwen2.5", "luna": "Luna"}


def incomplete_note(snapshot):
    """Name the cells that did not complete, keeping counts and typed failures."""
    parts = []
    for model in MODEL_LABELS:
        for method in METHODS:
            entries = []
            for task in TASKS:
                summary = snapshot["models"][model][task][method]
                if summary["complete"]:
                    continue
                tokens = "/".join(sorted(set(summary.get("failure_tokens", [])))) or r"$F$"
                entries.append((TASK_SHORT[task], f"{summary['completed']}/"
                                f"{summary['attempted']}", tokens))
            if not entries:
                continue
            counts = sorted({count for _, count, _ in entries})
            listed = ("all five" if len(entries) == len(TASKS) else
                      ", ".join(task for task, _, _ in entries))
            tokens = "/".join(sorted({token for _, _, token in entries}))
            label = _plain_label(METHOD_LABELS[method]).split(" (")[0]
            parts.append(f"{SHORT_BLOCK[model]} {label} {listed} "
                         f"{'/'.join(counts)} ({tokens})")
    return (r"\emph{Incomplete cells} ($\dagger$ partial, {\TblZero} unscored; typed "
            r"failures and counts: " + "; ".join(parts) + r"; details in Appendix~C).")


def table_text(snapshot):
    rankings = {}
    for model in MODEL_LABELS:
        for task in TASKS:
            rankings[model, task] = sorted({
                round(100 * snapshot["models"][model][task][method]["mean"], 2)
                for method in METHODS
                if snapshot["models"][model][task][method]["complete"]
            }, reverse=True)
    mean_rank = {model: task_ranks(snapshot, model) for model in MODEL_LABELS}

    def cell(model, method, task):
        summary = snapshot["models"][model][task][method]
        count = f"{summary['completed']}/{summary['attempted']}"
        if not summary["complete"]:
            if summary["completed"] == 0:
                return r"\TblZero"
            if summary.get("sd") is None:
                value = f"{100 * summary['mean']:.2f}\,({count})"
            else:
                value = f"{100 * summary['mean']:.2f} $\pm$ {100 * summary['sd']:.2f}"
            return value + r"\TblPartial"
        rounded = round(100 * summary["mean"], 2)
        shown = f"{rounded:.2f}"
        ranking = rankings[model, task]
        if rounded == ranking[0]:
            shown = r"\textbf{" + shown + "}"
        elif len(ranking) > 1 and rounded == ranking[1]:
            shown = r"\underline{" + shown + "}"
        star = r"\TblStar" if summary.get("extended_context_seeds") else ""
        return shown + r" $\pm$ " + f"{100 * summary['sd']:.2f}" + star

    best_rank = {model: min(value for value in mean_rank[model].values()
                            if value is not None) for model in MODEL_LABELS}

    def rank_cell(model, method):
        value = mean_rank[model].get(method)
        baseline = mean_rank[model].get("single_fixed")
        if value is None:
            return r"\textcolor{TblInk}{--}"
        shown = f"{value:.2f}"
        if value == best_rank[model]:
            shown = r"\textbf{" + shown + "}"
        if method == "single_fixed":
            return shown
        delta = baseline - value
        if delta >= 0.05:
            return shown + r"\,\TblUp{" + f"{delta:.1f}" + "}"
        if delta <= -0.05:
            return shown + r"\,\TblDown{" + f"{abs(delta):.1f}" + "}"
        return shown

    def row(model, method):
        label = METHOD_LABELS[method]
        return label + " & " + " & ".join(
            [cell(model, method, task) for task in TASKS] + [rank_cell(model, method)]
        ) + r" \\"

    body = [
        r"\centering\scriptsize",
        r"\setlength{\tabcolsep}{2.0pt}", r"\renewcommand{\arraystretch}{0.84}",
        r"\begin{tabularx}{\linewidth}{@{}LQQQQQQ@{}}", r"\toprule",
        (r"\textbf{Model / method} & \multicolumn{1}{c}{DTI} & "
         r"\multicolumn{1}{c}{Proteomics} & \multicolumn{3}{c}{Cell perturbation} & "
         r"\multicolumn{1}{c}{Average} \\"),
        r"\cmidrule(lr){2-2}\cmidrule(lr){3-3}\cmidrule(lr){4-6}\cmidrule(l){7-7}",
        (r" & \shortstack{BindingDB\\AUROC $\uparrow$} & \shortstack{PTPC\\AP $\uparrow$} & "
         r"\shortstack{VCC\\Top-1 $\uparrow$} & \shortstack{Norman\\Top-1 $\uparrow$} & "
         r"\shortstack{Tahoe\\Top-1 $\uparrow$} & \shortstack{Mean rank\\$\downarrow$} \\"),
        r"\midrule",
    ]
    for index, model in enumerate(MODEL_LABELS):
        if index:
            body.append(r"\midrule")
        body.append(r"\multicolumn{7}{@{}l}{\textbf{" + MODEL_LABELS[model] + r"}} \\")
        body.extend(row(model, method) for method in METHODS)
    star_note = ""
    if any(r"\TblStar" in line and r"\providecommand" not in line for line in body):
        star_note = (r" $\star$ marks a cell whose controller was admitted under an extended "
                     r"native-context budget")
        missing = [(_plain_label(MODEL_LABELS[model]).split(" (")[0], _plain_label(METHOD_LABELS[method]),
                    TASK_SHORT[task])
                   for model in MODEL_LABELS for method in METHODS for task in TASKS
                   if not snapshot["models"][model][task][method]["complete"]
                   and snapshot["models"][model][task][method]["completed"] == 0]
        if missing:
            listed = ", ".join(" ".join(parts) for parts in missing)
            star_note += (r"; the cell it does not score is " + listed +
                          r", whose native trajectory did not finish inside that budget")
        star_note += r" (Appendix~C)."
    lines = list(TABLE_PREAMBLE)
    lines += [
        r"\begin{table}[t]",
        (r"\caption{Main comparison by self-improving model (mean $\pm$ sample SD, seeds 42--44; scores "
         r"$\times100$). Public self-improving agents use laboratory 0 and BioCoLoop ten under a shared design "
         r"library, fits and held-out scorer. Bold marks the best complete value per endpoint and the lowest "
         r"mean rank; underline marks the runner-up; $\dagger$ partial and {\TblZero} unscored cells are not "
         r"imputed. Mean rank ranks the methods of a block from 1 (best) to 5 on every endpoint they completed "
         r"and averages those ranks, so lower is better and the $\uparrow$/$\downarrow$ offset is the gap to "
         r"that block's fixed reference. The three cell endpoints are five-option identification tasks with a "
         r"20\% chance level, so their headroom above chance is small."
         + star_note + "}"),
        r"\label{tab:public-harness-comparison-three-seed}",
    ]
    lines += body
    lines += [
        r"\bottomrule", r"\end{tabularx}",
        r"\end{table}",
    ]
    return "\n".join(lines) + "\n"


def write(snapshot, output_dir):
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    (output / "main_public_harness_three_seed.tex").write_text(table_text(snapshot))
    (output / "snapshot_llm_grouped_three_seed.json").write_text(
        json.dumps(snapshot, indent=2, allow_nan=False) + "\n"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qwen-seed42-base", type=Path, required=True)
    parser.add_argument("--qwen-additional-base", type=Path, required=True)
    parser.add_argument("--qwen-retry-base", type=Path)
    parser.add_argument("--luna-public-base", type=Path, required=True)
    parser.add_argument("--luna-retry-base", type=Path)
    parser.add_argument("--luna-core-base", type=Path, required=True)
    parser.add_argument("--luna-verification", type=Path, required=True)
    parser.add_argument("--reference-results", type=Path,
                        default=ROOT / "results/unified_bio_20260918")
    parser.add_argument("--output-dir", type=Path,
                        default=PAPER / "tables/public_harness_comparison")
    args = parser.parse_args()
    evidence = collect(
        args.qwen_seed42_base, args.qwen_additional_base, args.luna_public_base,
        args.luna_core_base, args.luna_verification, args.reference_results,
        retry_base=args.qwen_retry_base, luna_retry_base=args.luna_retry_base,
    )
    write(evidence, args.output_dir)
    print(json.dumps({"status": "PUBLISHED", "protocol": evidence["protocol"]}, indent=2))
