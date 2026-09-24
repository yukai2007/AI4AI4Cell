"""Separate post-selection evaluation of actual, sealed public-harness runs.

Never import or invoke this module from a controller. No held-out response file
is opened (even for hashing) until a durable evaluation seal exists.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time

from broker import (BASE, ROOT, HERE, UNIFIED, CLIENTS, ROUNDS, SLOTS, ROLE, Broker,
                    BrokerConfig, _trace_receipt, _verify_files, dump, read, sha, load_v3_designs)

SCHEMA = "public-harness-heldout-results-v1"
SEAL_SCHEMA = "public-harness-heldout-seal-v1"
DTI_ROWS = {"random": 5505, "unseen_drug": 3791, "unseen_protein": 2507}
CELL_ROWS = {"vcc_corrected": 360, "norman_double_corrected": 1350, "tahoe_drug_corrected": 67}


def _check_fit(record, config, definition):
    if (record.get("config") != config or record.get("clients") != CLIENTS or
            record.get("seed") != definition["config"]["seed"] or record.get("rounds") != ROUNDS or
            len(record.get("history", [])) != ROUNDS or record.get("test_read") is not False):
        raise ValueError("Selected/request fit differs from the complete ten-client V3 protocol")
    checkpoint = Path(record["checkpoint"])
    receipt = read(checkpoint.parent / "execution_receipt.json")
    if receipt.get("fresh_fit") is not True or receipt.get("cache_hit") is not False:
        raise ValueError("Cached or nonexecuted candidates cannot enter production evaluation")
    _verify_files({str(checkpoint): receipt["checkpoint_sha256"],
                   str(checkpoint.parent / "fit.json"): receipt["fit_sha256"]})
    if read(checkpoint.parent / "fit.json") != {k: v for k, v in record.items() if k != "checkpoint"}:
        raise ValueError("Immutable fit metadata differs from the recorded fit")
    # Recompute the checkpoint-selection decision from the complete dev curve.
    curve = [row for row in record["history"] if "development" in row]
    if [r["round"] for r in curve] != list(range(5, 101, 5)):
        raise ValueError("Candidate does not contain the complete fixed development cadence")
    best = max(curve, key=lambda r: (r["development"]["primary"], -r["development"]["loss"]))
    if record["best"] != best:
        raise ValueError("Candidate checkpoint was not selected by the frozen development rule")


def validate_run(run_dir):
    """Read only development/source artifacts and reject synthetic evidence first."""
    run_dir = Path(run_dir).resolve()
    definition = read(run_dir / "definition.json")
    if definition.get("execution_kind") != "fresh-canonical-v3":
        raise ValueError("Only real fresh-canonical-v3 runs may be evaluated; synthetic/replay evidence is forbidden")
    if (definition.get("schema") != "public-harness-development-v1" or definition.get("rounds") != ROUNDS
            or definition.get("slots") != SLOTS or definition.get("clients") != CLIENTS
            or definition.get("test_read") is not False or definition.get("designs") != load_v3_designs()):
        raise ValueError("Not the frozen main-table development protocol")
    config = BrokerConfig(**definition["config"])
    if Path(config.output_dir) != run_dir:
        raise ValueError("Run directory differs from its registered output location")
    Broker(config)._verify(definition, data=True)  # No fitting, worker, torch import, or test access.
    state, selection, seal = (read(run_dir / name) for name in
                              ("state.json", "selected_development.json", "selection_seal.json"))
    if state.get("status") != "DEVELOPMENT_SEALED" or state.get("used_slots") != SLOTS:
        raise ValueError("Native development selection has not been sealed after six slots")
    if (seal.get("schema") != "public-harness-development-selection-seal-v1" or seal.get("role") != ROLE or
            seal.get("execution_kind") != "fresh-canonical-v3" or seal.get("test_read") is not False or
            seal.get("feedback_to_controller") is not False or seal.get("heldout_evaluation_performed") is not False):
        raise ValueError("Invalid development-only selection seal")
    for key in ("task", "seed", "harness"):
        if selection.get(key) != getattr(config, key) or seal.get(key) != getattr(config, key):
            raise ValueError("Selection identity does not match the native run")
    _verify_files({str(run_dir / "definition.json"): seal["definition_sha256"],
                   str(run_dir / "selected_development.json"): seal["selection_sha256"],
                   seal["checkpoint"]: seal["checkpoint_sha256"]})
    if _trace_receipt(config.native_trace_path, required=True) != seal["native_trace"]:
        raise ValueError("Final native execution trace changed after selection was sealed")
    entries = seal["request_receipts"]
    if len(entries) != SLOTS or [e["slot"] for e in entries] != list(range(1, SLOTS + 1)) or entries != state["requests"]:
        raise ValueError("Exactly six immutable native submission receipts are required")
    menu = definition["designs"]
    incumbent = state["baseline"]
    if Path(incumbent["checkpoint"]).resolve() != run_dir / "fits/fixed_D00/best.pt":
        raise ValueError("Reference checkpoint is not the fresh fit in this run")
    _check_fit(incumbent, menu["D00"], definition)
    seen = {"D00"}
    metadata = {str(run_dir / name): sha(run_dir / name) for name in
                ("definition.json", "state.json", "selected_development.json", "selection_seal.json")}
    for entry in entries:
        path = Path(entry["path"]).resolve()
        if path != run_dir / "requests" / f"slot_{entry['slot']:02d}.json" or sha(path) != entry["sha256"]:
            raise ValueError("Submission receipt path or hash changed")
        metadata[str(path)] = entry["sha256"]
        request = read(path)
        if request.get("slot") != entry["slot"] or request.get("test_read") is not False or request.get("cache_hit") is not False:
            raise ValueError("Submission receipt violates the execution contract")
        reply = request["reply"]
        if reply.get("remaining_slots") != SLOTS - entry["slot"] or reply.get("test_read") is not False:
            raise ValueError("Controller received inconsistent budget/evidence metadata")
        raw = request["request"]
        design_id = raw.get("design_id") if isinstance(raw, dict) else None
        status = request["status"]
        if status != reply["status"]:
            raise ValueError("Request/result status differs")
        if status == "INVALID":
            if reply.get("accepted") or request.get("fit"):
                raise ValueError("Invalid requests cannot select or fit models")
        elif status == "DUPLICATE":
            if design_id not in seen or reply.get("accepted") or request.get("fit"):
                raise ValueError("Duplicate receipt does not describe a prior design")
        elif status in ("COMPLETE", "NUMERICAL_FAILURE"):
            fields = {"design_id", "hypothesis", "experiment", "expected_effect"}
            if not isinstance(raw, dict) or set(raw) != fields or any(not isinstance(raw[k], str) or not raw[k].strip() for k in fields):
                raise ValueError("Executed request did not satisfy the four-string native submission schema")
            if design_id not in menu or design_id in seen:
                raise ValueError("An executed request is outside the legal untried menu")
            seen.add(design_id)
            if status == "NUMERICAL_FAILURE":
                if reply.get("accepted"):
                    raise ValueError("A numerical failure cannot replace the incumbent")
            else:
                candidate = request["fit"]
                if Path(candidate["checkpoint"]).resolve() != run_dir / "fits" / f"slot_{entry['slot']:02d}_{design_id}" / "best.pt":
                    raise ValueError("Candidate checkpoint is not the fresh fit for its native submission slot")
                _check_fit(candidate, menu[design_id], definition)
                a, b = candidate["best"]["development"], incumbent["best"]["development"]
                accepted = (a["primary"], -a["loss"]) > (b["primary"], -b["loss"])
                if reply.get("accepted") != accepted or reply.get("candidate") != a:
                    raise ValueError("Candidate evidence/acceptance differs from measured development")
                if accepted:
                    incumbent = candidate
        else:
            raise ValueError("Incomplete/infrastructure-failed requests cannot enter held-out evaluation")
        if reply["incumbent"]["config"] != incumbent["config"] or reply["incumbent"]["development"] != incumbent["best"]["development"]:
            raise ValueError("Published controller development history is inconsistent")
    if selection["record"] != incumbent or state["incumbent"] != incumbent or incumbent["checkpoint"] != seal["checkpoint"]:
        raise ValueError("Final checkpoint is not the independently reconstructed development incumbent")
    if sha(Path(incumbent["checkpoint"]).parent / "fit.json") != seal["fit_sha256"]:
        raise ValueError("Selected fitting record changed after selection seal")
    if definition["created_unix"] > seal["sealed_unix"]:
        raise ValueError("Selection seal preceded run registration")
    return definition, selection, seal, metadata


def prepare_seal(run_dir, output, device):
    run_dir, output = Path(run_dir).resolve(), Path(output).resolve()
    definition, selection, development_seal, metadata = validate_run(run_dir)
    config = BrokerConfig(**definition["config"])
    trace = Path(config.native_trace_path)
    if output == trace or trace in output.parents:
        raise ValueError("Evaluation output must be outside the sealed native trace")
    reference_dir = (BASE / "heldout_ptpc_neural" / f"seed{config.seed}" if config.task == "ptpc_neural"
                     else BASE / "heldout_v3" / config.task / f"seed{config.seed}")
    reference = read(reference_dir / "seal.json")
    verification = read(reference_dir / "verification.json")
    if (reference["task"] != config.task or reference["seed"] != config.seed or reference["role"] != ROLE
            or verification["status"] != "PASS" or reference["data_manifest_sha256"] != definition["binding"]["data_manifest_sha256"]):
        raise ValueError("Original reference does not certify the same task/data/held-out role")
    _verify_files(reference["evaluation_sources_sha256"])
    evaluation_sources = dict(reference["evaluation_sources_sha256"])
    evaluation_sources.update({str(HERE / name): sha(HERE / name) for name in
                               ("heldout_public.py", "verify_public.py", "broker.py", "runtime_worker.py")})
    metadata[str(reference_dir / "seal.json")] = sha(reference_dir / "seal.json")
    metadata[str(reference_dir / "verification.json")] = sha(reference_dir / "verification.json")
    if config.task == "native_tapb":
        if set(reference["endpoints"]) != set(DTI_ROWS) or any(reference["endpoints"][k]["rows"] != n for k, n in DTI_ROWS.items()):
            raise ValueError("All three original TAPB endpoints are required")
        endpoints = {k: {"path": v["path"], "expected_sha256": v["expected_sha256"], "rows": v["rows"]}
                     for k, v in reference["endpoints"].items()}
        primary_endpoint, primary_metric = "random", "auroc"
        parity_path = BASE / config.task / "development_prediction_parity.json"
        if sha(parity_path) != reference["development_parity_sha256"] or read(parity_path)["status"] != "PASS":
            raise ValueError("Original predictor/development parity evidence changed")
        metadata[str(parity_path)] = sha(parity_path)
    else:
        count = 148 if config.task == "ptpc_neural" else CELL_ROWS[config.task]
        endpoints = {"primary": {"path": reference["heldout_path"], "expected_sha256": reference["heldout_sha256"], "rows": count}}
        primary_endpoint, primary_metric = "primary", "ap" if config.task == "ptpc_neural" else "macro_accuracy"
    record = selection["record"]
    payload = {"schema": SEAL_SCHEMA, "task": config.task, "seed": config.seed, "harness": config.harness,
               "role": ROLE, "execution_kind": "fresh-canonical-v3", "run_dir": str(run_dir),
               "development_sealed_unix": development_seal["sealed_unix"], "checkpoint": record["checkpoint"],
               "checkpoint_sha256": development_seal["checkpoint_sha256"], "config": record["config"],
               "rounds": ROUNDS, "slots": SLOTS, "clients": CLIENTS, "primary_endpoint": primary_endpoint,
               "primary_metric": primary_metric, "endpoints": endpoints, "study_metadata_sha256": metadata,
               "evaluation_sources_sha256": evaluation_sources, "reference_seal": str(reference_dir / "seal.json"),
               "feedback_to_controller": False, "test_checkpoint_selection": False,
               "reference_hashes_copied_without_response_access": True, "device": device}
    output.mkdir(parents=True, exist_ok=True)
    path = output / "seal.json"
    if path.exists():
        previous = read(path)
        if {k: v for k, v in previous.items() if k != "sealed_unix"} != payload:
            raise ValueError("Existing public-harness evaluation seal differs; never overwrite provenance")
    else:
        dump(path, dict(payload, sealed_unix=time.time()))
    return read(path), record


def _runtime(task):
    if task == "native_tapb":
        expected = Path(read(BASE / task / "data/manifest.json")["worker_python"]).resolve()
        if Path(sys.executable).resolve() != expected:
            raise ValueError("Native TAPB evaluation requires the manifest's worker_python interpreter")
    # Register adapters/native environment before any torch import.
    import runtime_worker
    import numpy as np
    import torch
    from core import restore
    torch.set_num_threads(2)
    return np, torch, restore


def evaluate(run_dir, output, device="cpu"):
    seal, record = prepare_seal(run_dir, output, device)
    output = Path(output).resolve()
    if (output / "results.json").exists():
        from verify_public import verify
        verify(output)
        return read(output / "results.json")
    np, torch, restore = _runtime(seal["task"])
    # First content access to any response file starts strictly after the seal.
    decoded = time.time()
    for endpoint in seal["endpoints"].values():
        if sha(endpoint["path"]) != endpoint["expected_sha256"]:
            raise ValueError("Original held-out response hash differs from its precommitted reference")
    started = time.monotonic()
    task, endpoints = seal["task"], {}
    if task == "native_tapb":
        import pandas as pd
        from heldout_native_tapb import input_features, predict_frame
        from tapb_native_adapter import TAPBAdapter
        from runtime.experiments.drugevolve_transfer.scoring import score_predictions
        frames = {name: pd.read_csv(meta["path"]) for name, meta in seal["endpoints"].items()}
        for name, frame in frames.items():
            if len(frame) != seal["endpoints"][name]["rows"] or list(frame.columns) != ["SMILES", "Protein", "Y"]:
                raise ValueError("Original TAPB roster/schema changed")
        features, feature_receipt = input_features(frames, device)
        dump(output / "input_features.json", feature_receipt)
        adapter = TAPBAdapter(BASE / task / "data", 0, device)
        torch.manual_seed(seal["seed"])
        model = adapter.model(record["config"]).to(device).eval()
        restore(model, torch.load(record["checkpoint"], map_location="cpu", weights_only=False))
        for name, frame in frames.items():
            probability = predict_frame(adapter, model, frame, features)
            metrics = score_predictions(frame.Y.to_numpy(), probability)
            prediction = frame.copy()
            prediction.insert(0, "original_row_index", np.arange(len(frame)))
            prediction["probability"] = probability
            path = output / f"{name}_predictions.csv"
            prediction.to_csv(path, index=False, float_format="%.17g")
            endpoints[name] = {"primary": metrics["auroc"], "metrics": metrics, "rows": len(frame),
                               "predictions": str(path), "predictions_sha256": sha(path)}
    elif task == "ptpc_neural":
        from heldout_ptpc_neural import archive, features
        from ptpc_neural_adapter import Predictor
        from extensions.proteomics.scoring import phenotype_scores
        query = archive(seal["endpoints"]["primary"]["path"])
        if len(query["y"]) != 148 or len(np.unique(query["condition_key"])) != 148:
            raise ValueError("Original PTPC 148-condition roster changed")
        manifest = read(BASE / task / "data/manifest.json")
        train = archive(manifest["source"])
        if set(train["compound_key"].tolist()) & set(query["compound_key"].tolist()):
            raise ValueError("Original train/development compounds overlap the held-out roster")
        x = torch.as_tensor(features(query), dtype=torch.float32, device=device)
        if tuple(x.shape) != (148, 2 * manifest["n_proteins"] + manifest["n_drug_features"]):
            raise ValueError("Held-out feature layout differs from the registered model")
        model = Predictor(manifest["n_proteins"], manifest["n_drug_features"], record["config"]["residual"]).to(device).eval()
        restore(model, torch.load(record["checkpoint"], map_location="cpu", weights_only=False))
        with torch.inference_mode():
            probability = torch.cat([model(chunk).sigmoid().cpu() for chunk in x.split(512)]).numpy()
        metrics = phenotype_scores(query["y"], probability)
        path = output / "primary_predictions.npz"
        np.savez_compressed(path, original_row_index=np.arange(len(probability)), probabilities=probability,
                            labels=query["y"], condition_key=query["condition_key"], compound_key=query["compound_key"])
        endpoints["primary"] = {"primary": metrics["ap"], "metrics": metrics, "rows": 148,
                                "predictions": str(path), "predictions_sha256": sha(path)}
    else:
        from engine import evaluate as cell_evaluate, summarize
        from scdebart import make_head
        source = Path(read(BASE / task / "data/manifest.json")["data_root"])
        manifest = read(source / "manifest.json")
        with np.load(seal["endpoints"]["primary"]["path"], allow_pickle=False) as archive:
            query = dict(archive)
        if len(query["ids"]) != CELL_ROWS[task] or query["choices"].shape != (CELL_ROWS[task], 5):
            raise ValueError("Original cell response count/five-choice roster changed")
        if set(query["ids"].tolist()) != set(manifest["test"]) or set(manifest["test"]) & set(manifest["train"] + manifest["dev"]):
            raise ValueError("Cell intervention split identities changed")
        for identity, choices in zip(query["ids"], query["choices"]):
            if choices.tolist() != manifest["candidate_rosters"][str(identity)]:
                raise ValueError("Original cell candidate order changed")
        hidden = np.load(source / "public_hidden.npy", mmap_mode="r")
        mask = np.load(source / "scoring_mask.npy", allow_pickle=False)
        initial = torch.load(source / "initial_head.pt", map_location="cpu", weights_only=True)
        model = make_head(initial, record["config"]).to(device).eval()
        restore(model, torch.load(record["checkpoint"], map_location="cpu", weights_only=False))
        with torch.inference_mode():
            evidence = cell_evaluate(model, hidden, query, mask, device, return_rows=True)
        metrics = summarize([evidence])
        rows = [dict(row, original_row_index=i) for i, row in enumerate(evidence["rows"])]
        path = output / "primary_predictions.json"
        dump(path, rows)
        endpoints["primary"] = {"primary": metrics["macro_accuracy"], "metrics": metrics, "rows": len(rows),
                                "predictions": str(path), "predictions_sha256": sha(path)}
    primary = endpoints[seal["primary_endpoint"]]
    result = {"schema": SCHEMA, "task": task, "seed": seal["seed"], "harness": seal["harness"],
              "role": ROLE, "execution_kind": "fresh-canonical-v3", "feedback_to_controller": False,
              "primary_endpoint": seal["primary_endpoint"], "primary_metric": seal["primary_metric"],
              "primary": primary["primary"], "metrics": primary["metrics"], "endpoints": endpoints,
              "seal_sha256": sha(output / "seal.json"), "heldout_decoded_unix": decoded,
              "completed_unix": time.time(), "evaluation_seconds": time.monotonic() - started,
              "checkpoint_sha256": seal["checkpoint_sha256"], "dictionary_updated": False,
              "environment": {"python": sys.version, "executable": sys.executable, "torch": torch.__version__,
                              "numpy": np.__version__, "device": device}}
    if task == "native_tapb":
        result["input_features_sha256"] = sha(output / "input_features.json")
    dump(output / "results.json", result)
    dump(output / "audit.json", {"status": "PASS", "task": task, "seed": seal["seed"], "harness": seal["harness"],
         "original_scorer": True, "common_original_roster": True, "sealed_before_response_access": seal["sealed_unix"] <= decoded,
         "no_test_checkpoint_selection": True, "no_controller_feedback": True, "fresh_native_controller_trace_verified": True})
    # A separate code path reopens saved predictions and recomputes every metric.
    from verify_public import verify
    verify(output)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--seal-only", action="store_true", help="Bind metadata without opening response files or loading torch")
    args = parser.parse_args()
    output = args.output or args.run_dir.with_name(args.run_dir.name + "_heldout")
    if args.seal_only:
        prepare_seal(args.run_dir, output, args.device)
        print("Evaluation seal written; no held-out response read")
    else:
        result = evaluate(args.run_dir, output, args.device)
        print({"status": "VERIFIED", "task": result["task"], "seed": result["seed"], "output": str(output)})


if __name__ == "__main__":
    main()
