"""Independently re-score the saved GPT-5.6 Luna main-core predictions.

This verifier is read-only with respect to experiment outputs.  It checks the
registered three-seed protocol, selection/checkpoint bindings, saved prediction
rosters and every reported metric before emitting a publication receipt.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np


PAPER = Path(__file__).resolve().parents[1]
ROOT = PAPER.parent
CORE = ROOT / "extensions/core_ablation_20260922"
if str(CORE) not in sys.path:
    sys.path.insert(0, str(CORE))

import verify_completed_publication as verify  # noqa: E402


TASKS = (
    "native_tapb", "ptpc_neural", "vcc_corrected",
    "norman_double_corrected", "tahoe_drug_corrected",
)
SEEDS = (42, 43, 44)
ARMS = {
    f"{participation}_{mode}"
    for participation in ("single", "federated")
    for mode in ("fixed", "direct", "loop")
}
TOLERANCE = 1e-10


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def check(condition, message):
    if not condition:
        raise ValueError(message)


def verify_run(base, task, seed, query_cache, checkpoint_cache):
    root = base / task / f"seed{seed}"
    development, heldout = root / "development", root / "heldout"
    definition = read(development / "definition.json")
    status = read(development / "status.json")
    selection = read(development / "selected_development.json")
    result, seal = read(heldout / "results.json"), read(heldout / "seal.json")

    check(status.get("status") == "COMPLETE", "Development/evaluation is not complete")
    check(definition.get("schema") == "luna-main-core-three-seed-v1",
          "Unknown Luna main-core definition")
    check(definition.get("task") == task and definition.get("seed") == seed,
          "Definition identity differs from its matrix position")
    check(definition.get("rounds") == 100 and definition.get("slots") == 6,
          "Unexpected training or proposal budget")
    check(definition.get("single_client") == 0 and definition.get("test_read") is False,
          "Unexpected laboratory or held-out access contract")
    check(definition.get("research_model") == "gpt-5.6-luna"
          and definition.get("reasoning_effort") == "low"
          and definition.get("generation_seed_supported") is False,
          "Unexpected Luna backend contract")
    check(set(definition.get("arms", [])) == ARMS, "Definition does not contain six arms")
    for filename, digest in definition.get("source_sha256", {}).items():
        check(sha(filename) == digest, f"Experiment source changed: {filename}")
    manifest = ROOT / "results/unified_bio_20260918" / task / "data/manifest.json"
    check(sha(manifest) == definition.get("data_manifest_sha256"), "Data manifest changed")

    check(result.get("task") == task and seal.get("task") == task, "Held-out task mismatch")
    check(result.get("feedback_to_controller") is False
          and seal.get("feedback_to_controller") is False,
          "Held-out feedback entered controller selection")
    check(result.get("seal_sha256") == sha(heldout / "seal.json"), "Seal digest mismatch")
    check(seal.get("sealed_unix", math.inf) <= result.get("completed_unix", -math.inf),
          "Held-out chronology is invalid")
    check(set(selection) == set(result.get("results", {})) == set(seal.get("checkpoints", {})) == ARMS,
          "Selection, seal and result arms differ")

    manifest_data = read(manifest)
    if task not in query_cache:
        if task == "ptpc_neural":
            query_path = ROOT / "data/proteomics/ptpc_release_20260911/final/final.npz"
            with np.load(query_path, allow_pickle=False) as archive:
                query = {"y": archive["y"].copy()}
        elif task == "native_tapb":
            query, query_path = verify.native_query()
        else:
            query_path = Path(manifest_data["data_root"]) / "test/query.npz"
            with np.load(query_path, allow_pickle=False) as archive:
                query = {key: archive[key].copy() for key in ("ids", "choices")}
        query_cache[task] = query, query_path, sha(query_path)
    query, query_path, query_digest = query_cache[task]

    predictions = []
    max_error = 0.0
    for arm in sorted(ARMS):
        recorded = result["results"][arm]
        binding, selected = seal["checkpoints"][arm], selection[arm]
        checkpoint = Path(binding["path"])
        check(str(checkpoint) == selected["checkpoint"], "Selected checkpoint path differs from seal")
        check(binding["config"] == selected["config"] and binding["seed"] == selected["seed"] == seed,
              "Selected config/seed differs from seal")
        checkpoint_cache.setdefault(str(checkpoint), sha(checkpoint))
        check(binding["sha256"] == checkpoint_cache[str(checkpoint)], "Checkpoint digest differs")
        fit_path = checkpoint.parent / "fit.json"
        fit = read(fit_path)
        check(fit.get("config") == selected["config"] and fit.get("seed") == seed,
              "Fit identity differs from selection")
        check(fit.get("best") == selected["best"] and fit.get("rounds") == 100,
              "Selected development record differs from completed fit")

        if task == "ptpc_neural":
            prediction_path = heldout / f"{arm}_predictions.npz"
            with np.load(prediction_path, allow_pickle=False) as archive:
                metrics = verify.phenotype_scores(query["y"], archive["probability"])
            primary = metrics["ap"]
        elif task == "native_tapb":
            prediction_path = heldout / f"{arm}_predictions.npz"
            with np.load(prediction_path, allow_pickle=False) as archive:
                metrics = verify.score_predictions(query["y"], archive["probability"])
            primary = metrics["auroc"]
        else:
            prediction_path = heldout / f"{arm}_predictions.json"
            metrics = verify.cell_rescore(read(prediction_path), query)
            primary = metrics["macro_accuracy"]
        error = verify.metric_error({"primary": primary, "metrics": metrics}, recorded)
        check(error <= TOLERANCE, f"Saved prediction scorer mismatch: {error}")
        max_error = max(max_error, error)
        predictions.append({
            "arm": arm,
            "primary": primary,
            "prediction_sha256": sha(prediction_path),
            "checkpoint_sha256": binding["sha256"],
            "fit_sha256": sha(fit_path),
            "max_abs_error": error,
        })

    return {
        "status": "PASS", "task": task, "seed": seed,
        "root": str(root.resolve()),
        "definition_sha256": sha(development / "definition.json"),
        "selection_sha256": sha(development / "selected_development.json"),
        "result_sha256": sha(heldout / "results.json"),
        "seal_sha256": sha(heldout / "seal.json"),
        "query_path": str(query_path), "query_sha256": query_digest,
        "max_abs_error": max_error, "predictions": predictions,
    }


def run(base, output):
    base, output = Path(base).resolve(), Path(output).resolve()
    manifest = read(base / "queue_manifest.json")
    supervisor = read(base / "supervisor_status.json")
    check(manifest.get("schema") == "luna-main-core-three-seed-queue-v1",
          "Unknown Luna main-core queue")
    check(manifest.get("tasks") == list(TASKS)
          and manifest.get("seeds") == list(SEEDS), "Queue matrix differs")
    check(manifest.get("research_model") == "gpt-5.6-luna"
          and manifest.get("reasoning_effort") == "low",
          "Queue used another research model")
    check(supervisor.get("status") == "COMPLETE"
          and not supervisor.get("failed")
          and len(supervisor.get("completed", [])) == len(TASKS) * len(SEEDS),
          "Luna main-core queue is incomplete or contains failures")

    query_cache, checkpoint_cache, records = {}, {}, []
    report = {
        "schema": "luna-main-core-independent-verification-v1",
        "status": "PASS", "created_utc": datetime.now(timezone.utc).isoformat(),
        "base": str(base), "manifest_sha256": sha(base / "queue_manifest.json"),
        "supervisor_sha256": sha(base / "supervisor_status.json"),
        "verifier_sha256": sha(__file__), "tolerance": TOLERANCE,
        "original_results_modified": False,
        "training_or_proposal_generation": False,
        "records": records,
    }
    for task in TASKS:
        for seed in SEEDS:
            try:
                record = verify_run(base, task, seed, query_cache, checkpoint_cache)
            except Exception as error:
                report["status"] = "FAIL"
                record = {"status": "FAIL", "task": task, "seed": seed,
                          "error": f"{type(error).__name__}: {error}"}
            records.append(record)
            print(record["status"], task, seed, record.get("max_abs_error", ""),
                  record.get("error", ""), flush=True)
    report["verified_runs"] = sum(record["status"] == "PASS" for record in records)
    report["verified_predictions"] = sum(len(record.get("predictions", [])) for record in records)
    report["unique_checkpoints"] = len(checkpoint_cache)
    report["max_abs_error"] = max(
        (record.get("max_abs_error", 0.0) for record in records), default=0.0
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    receipt = run(args.base, args.output)
    print(json.dumps({key: receipt[key] for key in (
        "status", "verified_runs", "verified_predictions", "max_abs_error"
    )}, indent=2))
    raise SystemExit(0 if receipt["status"] == "PASS" else 1)
