"""Independent saved-prediction rescoring; no model fitting or selection."""
from __future__ import annotations

import argparse
import math
from pathlib import Path
import time

from broker import ROLE, _verify_files, dump, read, sha


def binary_metrics(labels, probabilities, *, proteomics=False):
    """Independent tied-rank AUROC/AP and binary formulas, without sklearn."""
    y, p = list(map(float, labels)), list(map(float, probabilities))
    if (not y or len(y) != len(p) or any(v not in (0., 1.) for v in y)
            or any(not math.isfinite(v) or not 0 <= v <= 1 for v in p)):
        raise ValueError("Invalid original row-aligned binary predictions")
    positives, negatives = sum(y), len(y) - sum(y)
    if not positives or not negatives:
        raise ValueError("Both classes are required on the frozen primary endpoint")
    groups = {}
    for label, value in zip(y, p):
        positive, negative = groups.get(value, (0, 0))
        groups[value] = (positive + int(label), negative + int(not label))
    wins, prior_negative = 0., 0
    for value in sorted(groups):
        positive, negative = groups[value]
        wins += positive * (prior_negative + .5 * negative)
        prior_negative += negative
    tp, fp, ap = 0, 0, 0.
    for value in sorted(groups, reverse=True):
        positive, negative = groups[value]
        tp, fp = tp + positive, fp + negative
        ap += (positive / positives) * tp / (tp + fp)
    decisions = [v >= .5 for v in p]
    tp = sum(label == 1 and decision for label, decision in zip(y, decisions))
    tn = sum(label == 0 and not decision for label, decision in zip(y, decisions))
    fp, fn = int(negatives) - tn, int(positives) - tp
    epsilon = 1e-7 if proteomics else 1e-15
    clipped = [min(1 - epsilon, max(epsilon, v)) for v in p]
    loss = -sum(label * math.log(value) + (1 - label) * math.log1p(-value) for label, value in zip(y, clipped)) / len(y)
    if proteomics:
        return dict(ap=ap, auroc=wins / (positives * negatives), accuracy_at_0_5=(tp + tn) / len(y), bce=loss)
    denominator = (tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)
    return dict(auroc=wins / (positives * negatives), average_precision=ap,
                mcc=(tp * tn - fp * fn) / math.sqrt(denominator) if denominator else 0.,
                accuracy=(tp + tn) / len(y), log_loss=loss, n_samples=len(y),
                n_positive=int(positives), n_negative=int(negatives), threshold=.5, log_loss_epsilon=epsilon)


def cell_metrics(rows, original_ids, original_choices):
    import numpy as np
    ids, choices = np.asarray(original_ids), np.asarray(original_choices)
    if len(rows) != len(ids) or choices.shape != (len(ids), 5):
        raise ValueError("Original five-option row roster changed")
    if [row["original_row_index"] for row in rows] != list(range(len(rows))):
        raise ValueError("Saved original row indices changed")
    np.testing.assert_array_equal([row["intervention"] for row in rows], ids)
    np.testing.assert_array_equal([row["choices"] for row in rows], choices)
    scores = np.asarray([row["scores"] for row in rows], dtype=np.float64)
    if scores.shape != choices.shape or not np.isfinite(scores).all() or not np.all((choices == ids[:, None]).sum(axis=1) == 1):
        raise ValueError("Cell prediction scores or truth identities are invalid")
    truth = (choices == ids[:, None]).argmax(axis=1)
    order = np.argsort(-scores, axis=1, kind="stable")
    ranks = (order == truth[:, None]).argmax(axis=1) + 1
    np.testing.assert_array_equal(ranks, [row["rank"] for row in rows])
    # Match original float32 score/temperature rounding, then independent float64 logsumexp.
    logits = (scores.astype(np.float32) / np.float32(.1)).astype(np.float64)
    shifted = logits - logits.max(axis=1, keepdims=True)
    ce = -shifted[np.arange(len(ids)), truth] + np.log(np.exp(shifted).sum(axis=1))
    return dict(accuracy=float(np.mean(ranks == 1)),
                macro_accuracy=float(np.mean([np.mean(ranks[ids == group] == 1) for group in np.unique(ids)])),
                mrr=float(np.mean(1 / ranks)), top3=float(np.mean(ranks <= 3)), cross_entropy=float(ce.mean()),
                n_queries=len(ids), n_interventions=len(np.unique(ids)))


def assert_metrics(actual, expected, tolerance=1e-12):
    if not actual or any(key not in expected or expected[key] is None for key in actual):
        raise ValueError("Missing original-scoring metrics")
    errors = [abs(float(value) - float(expected[key])) for key, value in actual.items()]
    if any(not math.isfinite(value) for value in errors) or max(errors) > tolerance:
        raise ValueError("Independent prediction rescoring differs from original scorer")
    return max(errors)


def verify(output):
    from heldout_public import SCHEMA, SEAL_SCHEMA, validate_run
    import numpy as np
    output = Path(output).resolve()
    result, seal, audit = (read(output / name) for name in ("results.json", "seal.json", "audit.json"))
    if (result.get("schema") != SCHEMA or seal.get("schema") != SEAL_SCHEMA or
            result.get("execution_kind") != "fresh-canonical-v3" or seal.get("execution_kind") != "fresh-canonical-v3" or
            result.get("role") != ROLE or seal.get("role") != ROLE or result.get("feedback_to_controller") is not False
            or seal.get("feedback_to_controller") is not False or seal.get("test_checkpoint_selection") is not False):
        raise ValueError("Not a production post-selection public-harness evaluation")
    for key in ("task", "seed", "harness", "primary_endpoint", "primary_metric", "checkpoint_sha256"):
        if result.get(key) != seal.get(key):
            raise ValueError("Evaluation identities differ")
    if audit.get("status") != "PASS" or any(audit.get(k) is not True for k in
            ("original_scorer", "common_original_roster", "sealed_before_response_access", "no_test_checkpoint_selection", "no_controller_feedback")):
        raise ValueError("Evaluation lacks mandatory audit invariants")
    if sha(output / "seal.json") != result["seal_sha256"]:
        raise ValueError("Evaluation seal changed")
    if not seal["development_sealed_unix"] <= seal["sealed_unix"] <= result["heldout_decoded_unix"] <= result["completed_unix"]:
        raise ValueError("Held-out response access preceded selection/evaluation sealing")
    _verify_files(seal["study_metadata_sha256"])
    _verify_files(seal["evaluation_sources_sha256"])
    _verify_files({seal["checkpoint"]: seal["checkpoint_sha256"]})
    validate_run(seal["run_dir"])
    if set(result["endpoints"]) != set(seal["endpoints"]):
        raise ValueError("Missing original held-out endpoint")
    checked = {}
    for name, endpoint in seal["endpoints"].items():
        evidence = result["endpoints"][name]
        path = Path(evidence["predictions"]).resolve()
        if path.parent != output or sha(path) != evidence["predictions_sha256"]:
            raise ValueError("Prediction output path/hash changed")
        if sha(endpoint["path"]) != endpoint["expected_sha256"]:
            raise ValueError("Original response content differs from its precommitment")
        if seal["task"] == "native_tapb":
            import pandas as pd
            query = pd.read_csv(endpoint["path"])
            prediction = pd.read_csv(path, float_precision="round_trip")
            np.testing.assert_array_equal(prediction.original_row_index.to_numpy(), np.arange(len(query)))
            for column in ("SMILES", "Protein", "Y"):
                np.testing.assert_array_equal(prediction[column].to_numpy(), query[column].to_numpy())
            actual = binary_metrics(query.Y.to_numpy(), prediction.probability.to_numpy())
            if sha(output / "input_features.json") != result["input_features_sha256"]:
                raise ValueError("Native input feature receipt changed")
            count = len(query)
        elif seal["task"] == "ptpc_neural":
            with np.load(endpoint["path"], allow_pickle=False) as archive:
                query = dict(archive)
            with np.load(path, allow_pickle=False) as archive:
                prediction = dict(archive)
            np.testing.assert_array_equal(prediction["original_row_index"], np.arange(len(query["y"])))
            for column in ("condition_key", "compound_key"):
                np.testing.assert_array_equal(prediction[column], query[column])
            np.testing.assert_array_equal(prediction["labels"], query["y"])
            actual = binary_metrics(query["y"], prediction["probabilities"], proteomics=True)
            count = len(query["y"])
        else:
            with np.load(endpoint["path"], allow_pickle=False) as archive:
                query = dict(archive)
            actual = cell_metrics(read(path), query["ids"], query["choices"])
            count = len(query["ids"])
        if count != endpoint["rows"] or evidence["rows"] != count:
            raise ValueError("Original held-out row count changed")
        maximum_error = assert_metrics(actual, evidence["metrics"])
        if abs(actual[seal["primary_metric"]] - evidence["primary"]) > 1e-12:
            raise ValueError("Primary metric does not match saved prediction rescoring")
        checked[name] = {"metrics": actual, "max_absolute_error": maximum_error, "rows": count}
    primary = result["endpoints"][seal["primary_endpoint"]]
    if result["primary"] != primary["primary"] or result["metrics"] != primary["metrics"]:
        raise ValueError("Top-level primary result differs from the declared endpoint")
    receipt = {"schema": "public-harness-heldout-verification-v1", "status": "PASS", "task": result["task"],
               "seed": result["seed"], "harness": result["harness"], "role": ROLE,
               "seal_before_response_access": True, "all_checkpoint_hashes_match": True,
               "common_original_roster": True, "no_controller_feedback": True,
               "independent_formula_rescoring": True, "max_tolerance": 1e-12, "rescored": checked,
               "result_sha256": sha(output / "results.json"), "audit_sha256": sha(output / "audit.json"),
               "seal_sha256": sha(output / "seal.json"), "verified_unix": time.time()}
    dump(output / "verification.json", receipt)
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args()
    receipt = verify(arguments.output)
    print({"status": receipt["status"], "task": receipt["task"], "seed": receipt["seed"]})
