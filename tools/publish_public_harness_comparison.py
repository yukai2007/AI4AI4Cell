"""Failure-aware comparison, separate from the frozen runtime and old publisher.

Scores always come from publish_public_harness.collect's full verification.
Only hash-bound, accounted native-controller failures recorded by the frozen
supervisor are terminal without a score. This module never evaluates a failure,
changes a runtime receipt, edits a manuscript, or publishes injected fixtures.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import time

import publish_public_harness as publisher

PAPER, ROOT, EXTENSION = publisher.PAPER, publisher.ROOT, publisher.EXTENSION
SEEDS, TASKS, HARNESSES = publisher.SEEDS, publisher.TASKS, publisher.HARNESSES
METHODS, ORIGINAL_ARMS = publisher.METHODS, publisher.ORIGINAL_ARMS
DEFAULT_OUTPUT = PAPER / "tables/public_harness_comparison"
OUTPUT_FILENAMES = ("main_public_harness_seed42.tex", "main_public_harness_three_seed.tex",
                    "completion_public_harness.tex", "results_public_harness.tex", "snapshot_comparison.json")
FAILURE_PREFIXES = {
    "Tool response remained invalid after": "Failed-tool",
    "Native required-tool stage ended": "Failed-tool",
    "Native stage exhausted with a failed completion/tool receipt": "Failed-pipeline",
    "Native context exceeds declared token limit; no silent truncation.": "Failed-context",
}
FAILURES = ("Failed-context", "Failed-tool", "Failed-pipeline")
COUNT_KEYS = {"Scored": "scored", "Failed-context": "failed_context", "Failed-tool": "failed_tool",
              "Failed-pipeline": "failed_pipeline", "Pending": "pending"}
LABELS = {"single_fixed": "Fixed task models (1 lab)", "single_direct": "Qwen direct (1 lab)",
          "federated_loop": r"\textbf{BioCoLoop} (10 labs)",
          **{key: value["label"] for key, value in HARNESSES.items()}}
TOKENS = {"Failed-context": r"$F_{\mathrm{ctx}}$", "Failed-tool": r"$F_{\mathrm{tool}}$",
          "Failed-pipeline": r"$F_{\mathrm{pipe}}$", "Pending": "Pending"}


def _number(value, description):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError("Invalid nonnegative finite " + description)
    return value


def _hashes(expected, *, exact_paths=None):
    if not isinstance(expected, dict) or not expected:
        raise ValueError("Missing nonempty evidence/source hashes")
    if exact_paths is not None and set(expected) != {str(path) for path in exact_paths}:
        raise ValueError("Evidence hash paths differ from the registered files")
    for name, digest in expected.items():
        if not isinstance(digest, str) or len(digest) != 64 or publisher.sha(name) != digest:
            raise ValueError("Evidence/source hash changed: " + str(name))


def _validate_definition(definition, job):
    """Read-only source/upstream checks; never instantiate a broker or trainer."""
    from broker import BASE, BrokerConfig, _upstream_binding, load_v3_designs
    if (definition.get("schema") != "public-harness-development-v1"
            or definition.get("execution_kind") != "fresh-canonical-v3"
            or definition.get("rounds") != 100 or definition.get("slots") != 6
            or definition.get("clients") != list(range(10))
            or definition.get("test_read") is not False
            or definition.get("heldout_role") != publisher.ROLE
            or definition.get("feedback_to_controller") != "development_only"
            or definition.get("designs") != load_v3_designs()
            or definition.get("selection") != "development_primary_then_lower_loss"):
        raise ValueError("Failed run is not the frozen production development protocol")
    config = BrokerConfig(**definition["config"])
    if any(getattr(config, key) != value for key, value in job.items()):
        raise ValueError("Production definition identity differs from registered job")
    if config.upstream_commit != HARNESSES[job["harness"]]["commit"]:
        raise ValueError("Failed run uses a different pinned upstream commit")
    expected_adapters = {str(EXTENSION / name) for name in
                         ("airesearcher_adapter.py", "qwen_backend.py", "run_baseline.py")}
    if set(config.adapter_paths) != expected_adapters:
        raise ValueError("Failed run adapter registry differs")
    binding = definition["binding"]
    sources = binding["source_sha256"]
    required_sources = expected_adapters | {str(EXTENSION / name) for name in ("broker.py", "runtime_worker.py")}
    if not required_sources.issubset(sources):
        raise ValueError("Failed run source binding omits production adapters")
    _hashes(sources)
    if (binding.get("data_manifest_sha256") != publisher.sha(BASE / job["task"] / "data/manifest.json")
            or binding.get("upstream") != _upstream_binding(config)):
        raise ValueError("Failed run registered data manifest/upstream binding changed")
    # Historical prequeue runs can have relocated output_dir/native_trace_path.
    # The immutable adopted receipt binds their current definition/status paths.


def _validate_accounting(receipt, status, manifest, supervisor):
    accounting = receipt.get("accounting")
    if not isinstance(accounting, dict):
        raise ValueError("Failed run lacks compute accounting")
    consumed = _number(supervisor.get("reserved_gpu_hours"), "supervisor GPU hours")
    initial = _number(manifest.get("initial_reserved_gpu_hours"), "initial GPU hours")
    if consumed < initial:
        raise ValueError("Supervisor accounting fell below immutable initial accounting")
    start, finish = status["started_unix"], status["completed_unix"]
    if accounting.get("kind") == "immutable_prequeue_receipt":
        adopted = [item for item in manifest.get("adopted_prequeue_runs", []) if item.get("output") == receipt["output"]]
        if len(adopted) != 1:
            raise ValueError("Failed run has no unique immutable prequeue accounting receipt")
        adopted = adopted[0]
        expected_hours = 8 * (finish - start) / 3600
        if (any(adopted.get(key) != value for key, value in receipt["job"].items())
                or adopted.get("evidence_sha256") != receipt["evidence_sha256"]
                or adopted.get("started_unix") != start or adopted.get("completed_unix") != finish
                or adopted.get("usage") != status["usage"] or adopted.get("reserved_gpus") != 8
                or not math.isclose(_number(adopted.get("reserved_gpu_hours"), "adopted GPU hours"), expected_hours, abs_tol=1e-12)
                or accounting.get("reserved_gpu_hours") != adopted["reserved_gpu_hours"]
                or initial + 1e-12 < expected_hours):
            raise ValueError("Failed-run prequeue accounting differs from immutable run evidence")
    elif accounting.get("kind") == "finished_owned_child":
        child_start = _number(accounting.get("child_started_unix"), "child start")
        child_finish = _number(accounting.get("child_finished_unix"), "child finish")
        cumulative = _number(accounting.get("cumulative_reserved_gpu_hours"), "cumulative GPU hours")
        # Frozen supervisor charges monotonic duration but persists wall-clock
        # endpoints. Permit <0.5 ms of clock/float conversion discrepancy, not
        # an unaccounted interval (1e-6 reserved GPU hours at eight GPUs).
        if (not child_start <= start <= finish <= child_finish <= time.time() + 1
                or cumulative + 1e-6 < initial + 8 * (child_finish - child_start) / 3600
                or cumulative > consumed + 1e-12):
            raise ValueError("Failed child was not fully charged through completion")
    else:
        raise ValueError("Unknown failed-run accounting kind")


def verified_failures(base):
    """Return only independently checked supervisor failures, never raw errors.

    A malformed/untrusted listed failure aborts publication, rather than being
    converted into negative evidence about a method. A raw unrecorded error is
    left Pending by collect_comparison.
    """
    import supervise
    base = Path(base).resolve()
    manifest_path, state_path = base / "queue_manifest.json", base / "supervisor_status.json"
    if not manifest_path.exists() and not state_path.exists():
        return {}, {}
    if not manifest_path.is_file() or not state_path.is_file():
        raise ValueError("Comparison needs both immutable queue manifest and supervisor ledger")
    # Capture a consistent byte-level receipt even while the queue keeps running.
    manifest_bytes, state_bytes = manifest_path.read_bytes(), state_path.read_bytes()
    manifest, state = json.loads(manifest_bytes), json.loads(state_bytes)
    if (manifest.get("schema") != "public-harness-queue-v1"
            or state.get("schema") != "public-harness-supervisor-v1"
            or manifest.get("jobs") != supervise.jobs()
            or manifest.get("source_sha256") != supervise.pinned_sources()
            or tuple(FAILURE_PREFIXES) != supervise.CONTROLLER_FAILURE_PREFIXES):
        raise ValueError("Frozen queue matrix, source binding, or supervisor protocol changed")
    failures = {}
    receipts = state.get("failed", [])
    if not isinstance(receipts, list):
        raise ValueError("Supervisor failed ledger is not a list")
    if receipts and manifest.get("continue_controller_failures") is not True:
        raise ValueError("Controller failure continuation was not immutably registered")
    for receipt in receipts:
        job = receipt.get("job")
        if job not in manifest["jobs"]:
            raise ValueError("Failed receipt is outside the fixed 30-job matrix")
        key = (job["harness"], job["task"], job["seed"])
        run = base / key[0] / key[1] / f"seed{key[2]}"
        if key in failures or receipt.get("output") != str(run):
            raise ValueError("Duplicate or redirected failed-controller receipt")
        paths = (run / "run_status.json", run / "development/definition.json")
        _hashes(receipt.get("evidence_sha256"), exact_paths=paths)
        status, definition = map(publisher.read, paths)
        # This frozen helper checks identity, exact prefix, production kind,
        # launcher exit, usage/timing, and absence of selection/held-out access.
        checked = supervise.controller_failure(run, job, status)
        if checked is None or {k: v for k, v in receipt.items() if k != "accounting"} != checked:
            raise ValueError("Untrusted/infrastructure error is not a registered controller failure")
        _validate_definition(definition, job)
        _validate_accounting(receipt, status, manifest, state)
        error = status["error"].removeprefix("Error: ")
        classification = next(value for prefix, value in FAILURE_PREFIXES.items() if error.startswith(prefix))
        failures[key] = {"status": classification, "scored": False, "terminal": True,
                         "primary": None, "receipt": receipt, "usage": status["usage"],
                         "definition_source_sha256": definition["binding"]["source_sha256"]}
    if manifest_path.read_bytes() != manifest_bytes:
        raise ValueError("Immutable queue manifest changed during comparison collection")
    return failures, {"manifest_path": str(manifest_path), "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
                      "supervisor_path": str(state_path), "supervisor_sha256": hashlib.sha256(state_bytes).hexdigest(),
                      "supervisor_status": state.get("status"), "supervisor_updated_unix": state.get("updated_unix"),
                      "failure_receipts": receipts}


def _counts(statuses):
    counts = {key: 0 for key in COUNT_KEYS.values()}
    for status in statuses:
        counts[COUNT_KEYS[status["status"]]] += 1
    counts["denominator"] = sum(counts.values())
    counts["failed"] = sum(counts[key] for key in ("failed_context", "failed_tool", "failed_pipeline"))
    counts["terminal"] = counts["scored"] + counts["failed"]
    return counts


def collect_comparison(base, reference_base=None, *, _verified_snapshot=None):
    """Collect full verified scores, then add failure-only development evidence.

    Tests may inject a score snapshot, but its output remains nonpublishable.
    There is deliberately no failure-verification bypass in this public API.
    """
    test_only = _verified_snapshot is not None
    verified = _verified_snapshot if test_only else publisher.collect(base, reference_base)
    if (verified.get("role") != publisher.ROLE or verified.get("seeds_requested") != list(SEEDS)
            or (not test_only and verified.get("artifact_role") != "verified-preview-not-integrated")):
        raise ValueError("Comparison requires the unchanged full-verification score collector")
    snapshot = copy.deepcopy(verified)
    failures, provenance = verified_failures(base)
    snapshot.update(schema="public-harness-comparison-v1",
                    artifact_role="unit-test-only" if test_only else "verified-comparison-branch-draft",
                    created_utc=datetime.now(timezone.utc).isoformat(), failure_provenance=provenance,
                    collector_edits_manuscript=False,
                    integration_scope="comparison branch draft; main branch unchanged; user approval pending",
                    comparison_scope="Task-adapted controllers under this registered local-Qwen protocol; not architecture-wide superiority")
    # The collector is read-only, but a branch manuscript may now input these
    # generated tables. Do not inherit the old preview's integration claims.
    snapshot.pop("manuscript_modified", None)
    snapshot.pop("main_table_replaced", None)
    snapshot.get("seed42_preview", {}).pop("manuscript_modified", None)
    snapshot.setdefault("source_sha256", {})[str(Path(__file__).resolve())] = publisher.sha(__file__)
    completion = {"by_method": {}}
    for method in METHODS:
        by_seed = {}
        for seed in SEEDS:
            statuses = []
            for task in TASKS:
                row = publisher._row(snapshot, task, method)
                run = row["runs"].get(str(seed))
                failure = failures.get((method, task, seed))
                if run is not None and failure is not None:
                    raise ValueError("A failed-controller job cannot also contain a scored result")
                status = ({"status": "Scored", "scored": True, "terminal": True,
                           "primary": publisher._finite_primary(run["primary"])} if run is not None else
                          failure if failure is not None else
                          {"status": "Pending", "scored": False, "terminal": False, "primary": None,
                           "reason": row.get("pending", {}).get(str(seed), "Missing independently verified score or controller-failure receipt")})
                row.setdefault("statuses", {})[str(seed)] = status
                statuses.append(status)
            by_seed[str(seed)] = _counts(statuses)
        completion["by_method"][method] = {"by_seed": by_seed, "all_seeds": _counts(
            publisher._row(snapshot, task, method)["statuses"][str(seed)] for task in TASKS for seed in SEEDS)}
        for task in TASKS:
            row = publisher._row(snapshot, task, method)
            counts = _counts(row["statuses"].values())
            row["comparison_counts"] = counts
            row["comparison_resolved"] = counts["terminal"] == 3
            if counts["scored"] != 3:
                row.update(complete=False, mean=None, sd=None)
    matrix_statuses = [publisher._row(snapshot, task, harness)["statuses"][str(seed)]
                       for harness in HARNESSES for task in TASKS for seed in SEEDS]
    completion["matrix"] = _counts(matrix_statuses)
    completion["seed42"] = _counts(publisher._row(snapshot, task, harness)["statuses"]["42"]
                                   for harness in HARNESSES for task in TASKS)
    snapshot["completion"] = completion
    snapshot["scores_complete"] = completion["matrix"]["scored"] == 30
    snapshot["comparison_resolved"] = completion["matrix"]["terminal"] == 30
    snapshot["seed42_scores_complete"] = completion["seed42"]["scored"] == 10
    snapshot["seed42_comparison_resolved"] = completion["seed42"]["terminal"] == 10
    snapshot["matrix_complete"] = snapshot["scores_complete"]
    snapshot["ready_for_explicit_manuscript_integration"] = bool(
        snapshot["comparison_resolved"] and snapshot.get("reference_complete") and not test_only)
    return snapshot


def _incomplete_cell(row, seed):
    if seed is not None:
        return TOKENS[row["statuses"][str(seed)]["status"]]
    counts = row["comparison_counts"]
    statuses = {item["status"] for item in row["statuses"].values()}
    if statuses == {"Pending"}:
        return "Pending"
    if len(statuses) == 1 and next(iter(statuses)) in FAILURES:
        return TOKENS[next(iter(statuses))] + r" $3/3$"
    label = "Mixed" if counts["failed"] else "Pending"
    summary = f"{counts['scored']}S/{counts['failed']}F/{counts['pending']}P"
    return r"\shortstack{" + label + r"\\\scriptsize " + summary + "}"


def table_text(snapshot, *, seed=None):
    if seed not in (None, 42):
        raise ValueError("Only the prespecified matched seed42 pilot is supported")
    def value(task, method):
        row = publisher._row(snapshot, task, method)
        run = row["runs"].get("42") if seed == 42 else None
        number = run["primary"] if run is not None else row["mean"] if seed is None and row["complete"] else None
        return None if number is None else round(100 * publisher._finite_primary(number), 2)
    values = {method: [value(task, method) for task in TASKS] for method in METHODS}
    rankings = [sorted({values[method][j] for method in METHODS if values[method][j] is not None}, reverse=True)
                for j in range(len(TASKS))]
    def cell(method, column):
        number = values[method][column]
        row = publisher._row(snapshot, TASKS[column], method)
        if number is None:
            return _incomplete_cell(row, seed)
        formatted = f"{number:.2f}"
        if number == rankings[column][0]:
            formatted = r"\textbf{" + formatted + "}"
        elif len(rankings[column]) > 1 and number == rankings[column][1]:
            formatted = r"\underline{" + formatted + "}"
        return formatted if seed == 42 else formatted + r" $\pm$ " + f"{100 * row['sd']:.2f}"
    lines = [r"\begin{table}[t]", r"\centering\footnotesize", r"\setlength{\tabcolsep}{3pt}",
             r"\renewcommand{\arraystretch}{1.12}", r"\begin{tabularx}{\linewidth}{@{}Xrrrrr@{}}", r"\toprule",
             r"\textbf{Model / method} & \multicolumn{1}{c}{DTI} & \multicolumn{1}{c}{Proteomics} & \multicolumn{3}{c}{Cell perturbation} \\",
             r"\cmidrule(lr){2-2}\cmidrule(lr){3-3}\cmidrule(l){4-6}",
             r" & \shortstack{BindingDB\\AUROC $\uparrow$} & \shortstack{PTPC\\AP $\uparrow$} & \shortstack{VCC\\Top-1 $\uparrow$} & \shortstack{Norman\\Top-1 $\uparrow$} & \shortstack{Tahoe\\Top-1 $\uparrow$} \\",
             r"\midrule"]
    lines.append("Fixed model (1 lab) & " + " & ".join(cell("single_fixed", j) for j in range(5)) + r" \\")
    for method in ("single_direct", "ai_scientist_v2", "ai_researcher", "federated_loop"):
        lines.append(LABELS[method] + " & " + " & ".join(cell(method, j) for j in range(5)) + r" \\")
    scope = ("Matched seed-42 comparison. " if seed == 42 else
             r"Main comparison (mean $\pm$ sample SD, seeds 42--44). Unfinished cells show scored/failed/pending counts (S/F/P). ")
    caption = (scope + "Scores are multiplied by 100; bold/underline mark best/second-best values, including ties. "
               "Public controllers use task-adapted interfaces. Only complete seed sets are averaged; "
               "execution outcomes are detailed in Appendix C.")
    if seed == 42:
        caption += (r" $F_{\mathrm{ctx}}$, $F_{\mathrm{tool}}$ and $F_{\mathrm{pipe}}$ denote context, tool and pipeline failures; Pending is unresolved.")
    suffix = "seed42" if seed == 42 else "three-seed"
    lines += [r"\bottomrule", r"\end{tabularx}", r"\caption{" + caption + "}",
              r"\label{tab:public-harness-comparison-" + suffix + "}", r"\end{table}"]
    return "\n".join(lines) + "\n"


def completion_table_text(snapshot):
    lines = [r"\begin{table}[t]", r"\centering\footnotesize", r"\setlength{\tabcolsep}{3pt}",
             r"\begin{tabularx}{\linewidth}{@{}Xrrrrrrr@{}}", r"\toprule",
             r"Method / seed & Scored & $F_{\mathrm{ctx}}$ & $F_{\mathrm{tool}}$ & $F_{\mathrm{pipe}}$ & Pending & Terminal & Total \\", r"\midrule"]
    for method in ("ai_scientist_v2", "ai_researcher"):
        for seed in SEEDS:
            count = snapshot["completion"]["by_method"][method]["by_seed"][str(seed)]
            label = LABELS[method] + f" / {seed}"
            lines.append(label + " & " + " & ".join(str(count[key]) for key in
                         ("scored", "failed_context", "failed_tool", "failed_pipeline", "pending", "terminal", "denominator")) + r" \\")
        lines.append(r"\midrule")
    count = snapshot["completion"]["matrix"]
    lines.append("Public-controller matrix" + " & " + " & ".join(str(count[key]) for key in
                 ("scored", "failed_context", "failed_tool", "failed_pipeline", "pending", "terminal", "denominator")) + r" \\")
    lines += [r"\bottomrule", r"\end{tabularx}",
              r"\caption{Public-controller execution outcomes across five endpoints and three seeds. Terminal counts include both scored runs and verified controller failures. Pending denotes unresolved work. These counts describe the public-controller adapter protocol.}",
              r"\label{tab:public-harness-completion}", r"\end{table}"]
    return "\n".join(lines) + "\n"


def results_text(snapshot):
    count = snapshot["completion"]["matrix"]
    macros = {"SnapshotDate": snapshot["created_utc"].split(".")[0].replace("T", " ").replace("+00:00", "") + " UTC",
              "Scored": count["scored"], "FailedContext": count["failed_context"], "FailedTool": count["failed_tool"],
              "FailedPipeline": count["failed_pipeline"], "Pending": count["pending"], "Terminal": count["terminal"]}
    lines = [r"\providecommand{\PublicHarness" + name + "}{}\n" + r"\renewcommand{\PublicHarness" + name + "}{" + str(value) + "}"
             for name, value in macros.items()]
    lines.append(r"\paragraph{Public-controller comparison status.} At \PublicHarnessSnapshotDate, "
                 + f"{count['scored']}/30 public-controller runs have independently verified scores, "
                 + f"{count['failed_context']} have verified context-limit failures, {count['failed_tool']} required-tool failures, "
                 + f"and {count['failed_pipeline']} native-pipeline failures; {count['pending']} remain pending. "
                 + f"Thus {count['terminal']}/30 runs are terminal, distinct from the scored fraction. "
                 + "The seed-42 pilot is matched across methods; three-seed means appear only for three verified scores. "
                 + "Execution outcomes describe the specified task adaptations and local-Qwen backend. "
                 + "Failed runs have no predictive score.")
    return "\n".join(lines) + "\n"


def write_comparison(snapshot, output_dir=DEFAULT_OUTPUT):
    if snapshot.get("artifact_role") != "verified-comparison-branch-draft":
        raise ValueError("Unit-test/injected evidence cannot be written as a publication comparison")
    output = Path(output_dir).resolve()
    protected = (PAPER, PAPER / "tables", PAPER / "tables/strong_v3", PAPER / "tables/public_harness_preview", ROOT, EXTENSION)
    if any(output == path or path in output.parents for path in (EXTENSION, PAPER / "tables/strong_v3", PAPER / "tables/public_harness_preview")) or output in protected:
        raise ValueError("Use a separate comparison directory; preserve existing/frozen artifacts")
    output.mkdir(parents=True, exist_ok=True)
    payloads = (table_text(snapshot, seed=42), table_text(snapshot), completion_table_text(snapshot), results_text(snapshot),
                json.dumps(snapshot, indent=2, allow_nan=False) + "\n")
    for name, payload in zip(OUTPUT_FILENAMES, payloads):
        (output / name).write_text(payload)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--reference-results", type=Path, default=ROOT / "results/unified_bio_20260918")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    snapshot = collect_comparison(args.base, args.reference_results)
    write_comparison(snapshot, args.output_dir)
    print(json.dumps({key: snapshot[key] for key in
                      ("comparison_resolved", "scores_complete", "seed42_comparison_resolved", "seed42_scores_complete")} |
                     {"completion": snapshot["completion"]["matrix"], "collector_edits_manuscript": False,
                      "output_dir": str(args.output_dir.resolve())}))


if __name__ == "__main__":
    main()
