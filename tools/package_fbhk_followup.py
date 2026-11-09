"""Archive follow-up implementation and aggregate evidence, without raw data.

This is a source/provenance supplement, not a standalone executable package.
Only explicitly selected protocol metadata and aggregate results are included.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

PAPER = Path(__file__).resolve().parents[1]
PROJECT = PAPER.parent
OUT = PAPER / "provenance/fbhk_followup_20261109"
SOURCE_ROOTS = [PROJECT / "extensions/history_repair_20261109",
                PROJECT / "extensions/fbhk_followup_20261109"]
PROTOCOL_PATHS = [
    "results/history_repair_20261109/training_genetic_v1/training_registration.json",
    "results/history_repair_20261109/training_heldout_genetic_v1/protocol.json",
    "results/history_repair_20261109/training_heldout_genetic_v1/authorization.json",
    *[f"results/history_repair_20261109/search_genetic_v{version}/{name}.json"
      for version in [1, 2, 3] for name in ["protocol", "registration"]],
    "results/fbhk_followup_20261109/lab_identity/protocol.json",
]
POLICY = PROJECT / "results/history_repair_20261109/training_heldout_genetic_v1/policy_report.json"
SEARCH = PROJECT / "results/history_repair_20261109/search_genetic_v3/search_analysis.json"
RAW_FIELD_NAMES = {"excluded_condition_ids", "gene_ids", "per_gene", "per_gene_scores",
                   "memberships", "predictions", "responses", "rosters", "expression"}
REQUIREMENTS = (
    "Requires the existing BioCoLoop research checkout, its task adapters and scoring code, "
    "the authorized CellUMM/Replogle/Nadig and original task datasets, frozen scDEBART weights "
    "and compatible model dependencies, locally deployed Qwen2.5-7B-Instruct for controller "
    "rollouts, and registered feature/candidate caches. Python dependencies include PyTorch, "
    "NumPy, pandas, SciPy, scikit-learn, h5py and the original model libraries. Absolute local "
    "paths identify the evaluated run and must be configured in another environment. Source "
    "hashes identify dependencies; no raw biological data, predictions, memberships, "
    "checkpoints, model weights or credentials are distributed in this supplement. "
    "The lab-identity analysis additionally requires the earlier "
    "provenance/rebuttal_20261109/experiment_sources.zip (including "
    "extensions/rebuttal_20261109/allocation/cpu_runtime.py, allocation_shared.py and run.py) "
    "and the full research checkout's extensions/core_ablation_20260922/common.py, "
    "extensions/unified_bio_20260918/core_v3.py and task "
    "adapters. The earlier source archive alone does not include all these dependencies."
)


def digest(raw: bytes):
    return hashlib.sha256(raw).hexdigest()


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()


def relative(path):
    return path.relative_to(PROJECT).as_posix()


def assert_not_secret(raw, name):
    """Reject common literal credential formats without printing their content."""
    patterns = [rb"sk-[A-Za-z0-9_-]{24,}", rb"gh[pousr]_[A-Za-z0-9]{30,}",
                rb"github_pat_[A-Za-z0-9_]{30,}", rb"-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----"]
    if any(re.search(pattern, raw) for pattern in patterns):
        raise ValueError(f"Credential-like content in {name}; not packaged")


def sanitize_protocol(value, prefix=""):
    """Omit individual-level arrays while retaining declared aggregate metadata."""
    omitted = []
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            pointer = f"{prefix}/{key}"
            if key in RAW_FIELD_NAMES and isinstance(item, (list, dict)):
                omitted.append(pointer)
                continue
            result[key], extra = sanitize_protocol(item, pointer)
            omitted.extend(extra)
        return result, omitted
    if isinstance(value, list):
        result = []
        for index, item in enumerate(value):
            cleaned, extra = sanitize_protocol(item, f"{prefix}/{index}")
            result.append(cleaned)
            omitted.extend(extra)
        return result, omitted
    return value, []


def policy_summary():
    policy, search = json.loads(POLICY.read_text()), json.loads(SEARCH.read_text())
    if policy["status"] != "COMPLETE":
        raise ValueError("Held-out policy report is not complete")
    policies = {}
    for key, row in policy["policies"].items():
        policies[key] = {
            "heldout_primary_mean": row["primary"],
            "heldout_primary_seed_sd": row["across_training_controller_seed_sd"],
            "heldout_primary_gene_cluster_ci95": row["gene_cluster_ci95"],
            "heldout_mrr_mean": row["mrr"],
            "per_seed": [{"seed": v["seed"], "heldout_primary": v["primary"]}
                         for v in row["per_seed"]],
        }
    budget = {}
    for key, row in search["aggregate"].items():
        budget[key] = {"development": row["development"],
                       "fitting_cost": row["fitting_cost"],
                       "invalid_slots": row["invalid_slots"],
                       "llm_logical_usage_total": row["llm_logical_usage_total"]}
    return {
        "schema": "fbhk-public-aggregate-policy-summary-v1", "status": "COMPLETE",
        "source_reports": {relative(p): digest(p.read_bytes()) for p in [POLICY, SEARCH]},
        "source_protocol_sha256": policy["protocol_sha256"],
        "source_authorization_sha256": policy["authorization_sha256"],
        "training_controller_seeds": search["training_seeds"],
        "candidate_proposal_budget": search["budget"],
        "policies": policies, "paired_primary_differences": policy["paired_differences"],
        "bootstrap": policy["bootstrap"], "budget_by_policy": budget,
        "physical_llm_usage_total": search["physical_llm_usage_total"],
        "physical_training_cache_cost_total": search["physical_training_cache_cost_total"],
        "interpretation": policy["explanation"],
        "omitted": ["individual genes/conditions", "per-gene scores", "predictions",
                    "raw responses", "split memberships", "raw prompts and responses"],
    }


def lab_identity_summary():
    root = PROJECT / "results/fbhk_followup_20261109/lab_identity"
    report_path, verification_path = root / "report.json", root / "verification.json"
    if not report_path.is_file() or not verification_path.is_file():
        return None
    report = json.loads(report_path.read_text())
    verification = json.loads(verification_path.read_text())
    if verification["status"] != "PASS" or verification["report_sha256"] != digest(report_path.read_bytes()):
        raise ValueError("Lab-identity report is not independently verified")
    return {
        "schema": "fbhk-public-lab-identity-summary-v1",
        "source_reports": {relative(p): digest(p.read_bytes()) for p in [report_path, verification_path]},
        "report": {k: report[k] for k in ["schema", "rows", "n_labs", "seed", "new_fits",
                    "all_outcomes_included", "variation", "scope", "fit_elapsed_seconds",
                    "protocol_sha256", "selection_seal_sha256"]},
        "verification": {k: verification[k] for k in ["status", "new_fits_verified",
                         "prediction_scores_verified", "protocol_sha256", "report_sha256",
                         "all_fits_sealed_before_heldout", "no_gpu_models_mixed", "rendering_note",
                         "renderer_sha256", "table_sha256"]},
        "omitted": ["individual predictions", "prediction_bindings", "per-sample scores", "labels"],
    }


def build():
    payloads = {}
    source_hashes = {}
    metadata = {}
    for root in SOURCE_ROOTS:
        for path in sorted(root.rglob("*.py")):
            if not path.is_file() or path.is_symlink():
                raise ValueError(f"Not a regular source file: {path}")
            name, raw = relative(path), path.read_bytes()
            assert_not_secret(raw, name)
            payloads[name] = raw
            source_hashes[name] = digest(raw)
    self_name = relative(Path(__file__).resolve())
    payloads[self_name] = Path(__file__).read_bytes()
    source_hashes[self_name] = digest(payloads[self_name])
    test_path = Path(__file__).with_name("test_package_fbhk_followup.py")
    if test_path.is_file():
        test_name = relative(test_path)
        payloads[test_name] = test_path.read_bytes()
        source_hashes[test_name] = digest(payloads[test_name])
    for name in sorted(PROTOCOL_PATHS):
        path = PROJECT / name
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"Metadata must be a regular file: {path}")
        original = path.read_bytes()
        cleaned, omitted = sanitize_protocol(json.loads(original))
        raw = original if not omitted else json_bytes(cleaned)
        assert_not_secret(raw, name)
        payloads[name] = raw
        metadata[name] = {"source_sha256": digest(original), "archive_sha256": digest(raw),
                          "omitted_fields": omitted, "byte_identical_to_source": not omitted}
    public_summary = json_bytes(policy_summary())
    payloads["aggregate_evidence/policy_summary.json"] = public_summary
    lab_summary = lab_identity_summary()
    if lab_summary is not None:
        payloads["aggregate_evidence/lab_identity_summary.json"] = json_bytes(lab_summary)
    payloads["README.txt"] = (
        "BioCoLoop FBhK follow-up implementation and aggregate evidence\n\n"
        "Scope: new history-repair experiments, follow-up analyses and tests.\n"
        "This archive is NOT a standalone reproducibility package.\n\n" + REQUIREMENTS + "\n\n"
        "Version lineage: search_genetic_v1 was frozen before rollouts; v2 is retained as "
        "an engineering diagnostic; v3 is the final uniformly parsed controller study. "
        "Do not pool v2 and v3 as independent scientific replications. Protocol metadata "
        "retain their original hashes in the external manifest; individual-level fields "
        "are omitted and listed there when present. The aggregate policy summary is a "
        "derived public view, not a byte-identical copy of the source policy_report.json.\n"
    ).encode()
    blob = io.BytesIO()
    with zipfile.ZipFile(blob, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, raw in sorted(payloads.items()):
            entry = zipfile.ZipInfo(name, date_time=(2026, 11, 9, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o644 << 16
            archive.writestr(entry, raw)
    archive_bytes = blob.getvalue()
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as check:
        if sorted(check.namelist()) != sorted(payloads):
            raise AssertionError("Archive member mismatch")
        for name, raw in payloads.items():
            if check.read(name) != raw:
                raise AssertionError(f"Archive content mismatch: {name}")
    manifest = {
        "schema": "fbhk-followup-source-package-v1", "status": "PASS",
        "archive_sha256": digest(archive_bytes), "archive_file_count": len(payloads),
        "source_file_count": len(source_hashes), "source_sha256": source_hashes,
        "protocol_metadata": metadata,
        "archive_member_sha256": {name: digest(raw) for name, raw in sorted(payloads.items())},
        "policy_summary_sha256": digest(public_summary),
        "original_policy_report_sha256": digest(POLICY.read_bytes()),
        "includes_biological_measurements": False, "includes_individual_gene_records": False,
        "includes_checkpoints": False, "includes_credentials": False,
        "standalone": False, "requirements": REQUIREMENTS,
        "reproduce_command": "python tools/package_fbhk_followup.py --check",
        "selection": "All Python sources from both extension directories; the ten explicitly allowlisted protocol/registration/authorization JSON files, with individual-level arrays omitted; complete aggregate policy summaries.",
    }
    artifacts = {"experiment_sources.zip": archive_bytes,
                 "experiment_sources.manifest.json": json_bytes(manifest),
                 "policy_summary.json": public_summary}
    if lab_summary is not None:
        artifacts["lab_identity_summary.json"] = json_bytes(lab_summary)
    return artifacts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    artifacts = build()
    if args.check:
        failures = [name for name, raw in artifacts.items()
                    if not (OUT / name).is_file() or (OUT / name).read_bytes() != raw]
        if failures:
            raise SystemExit("Stale package artifacts: " + ", ".join(failures))
        print("PASS: source archive, aggregate summary and manifest reproduce exactly")
    else:
        OUT.mkdir(parents=True, exist_ok=True)
        for name, raw in artifacts.items():
            (OUT / name).write_bytes(raw)
        m = json.loads(artifacts["experiment_sources.manifest.json"])
        print(f"PASS: {m['source_file_count']} Python files, {len(m['protocol_metadata'])} protocol metadata files; no measurements or checkpoints")


if __name__ == "__main__":
    main()
