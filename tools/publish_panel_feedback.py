"""Verify and package the new development-only repair without changing old evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import sys
import zipfile

PAPER = Path(__file__).resolve().parents[1]
PROJECT = PAPER.parent
sys.path.insert(0, str(PROJECT))
from extensions.supplement_history_20261007.task_runner import read, sha
from extensions.panel_feedback_20261110.audit import OUT, checked_protocol, selection_diagnostic
from extensions.panel_feedback_20261110.payload import panel_payload
from package_fbhk_followup import assert_not_secret

DEST = PAPER / "provenance/panel_feedback_20261110"
TABLE = PAPER / "tables/panel_feedback_20261110/development_audit.tex"


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def build():
    protocol = checked_protocol(OUT)
    bindings = {str(OUT / name): sha(OUT / name) for name in ("protocol.json", "registration.json")}
    rows, verification = [], []
    checkpoints, gap_count, canary_fits = 0, 0, 0
    for task in protocol["tasks"]:
        audit_path, canary_path = OUT / task / "development_audit.json", OUT / task / "canary_receipt.json"
        audit, canary = read(audit_path), read(canary_path)
        for path in (audit_path, canary_path):
            bindings[str(path)] = sha(path)
        if audit["status"] != "COMPLETE" or canary["status"] != "COMPLETE" or \
                audit["cuda_initialized"] or canary["cuda_initialized"] or \
                audit["heldout_inference"] or canary["heldout_inference"]:
            raise ValueError("Incomplete or out-of-scope audit")
        checkpoints += audit["checkpoint_count"]
        gap_count += audit["nonzero_mean_worst_gaps"]
        canary_fits += canary["fresh_fits"]
        for pair in canary["pairs"]:
            if not all(pair[key] is True for key in ("exact_selected_weights", "exact_last_state_and_velocity",
                                                     "exact_training_curve", "exact_development_primary_loss")):
                raise ValueError("Canary changed training or selection")
            for arm, metadata in pair["fits"].items():
                folder = OUT / task / "canary" / pair["design_id"] / arm
                for name, key in (("fit.json", "fit_sha256"), ("best.pt", "checkpoint_sha256")):
                    if sha(folder / name) != metadata[key]:
                        raise ValueError("Canary artifact changed")
                bindings[str(folder / "fit.json")] = sha(folder / "fit.json")
                bindings[str(folder / "best.pt")] = sha(folder / "best.pt")
                bindings[str(folder / "last.pt")] = sha(folder / "last.pt")
            # Independent verification of saved state tensors, rather than
            # relying only on the canary's boolean receipt.
            import numpy as np
            import torch
            states = [torch.load(OUT / task / "canary" / pair["design_id"] / arm / "best.pt",
                                 map_location="cpu", weights_only=False) for arm in pair["fits"]]
            if set(states[0]) != set(states[1]) or any(not np.array_equal(v, states[1][k]) for k,v in states[0].items()):
                raise ValueError("Independent checkpoint comparison failed")
            lasts = [torch.load(OUT / task / "canary" / pair["design_id"] / arm / "last.pt",
                                map_location="cpu", weights_only=False) for arm in pair["fits"]]
            if lasts[0]["round"] != lasts[1]["round"]:
                raise ValueError("Independent final-round comparison failed")
            for field in ("state", "velocity"):
                if set(lasts[0][field]) != set(lasts[1][field]) or any(
                        not np.array_equal(v, lasts[1][field][k]) for k,v in lasts[0][field].items()):
                    raise ValueError("Independent final-state comparison failed")
            verification.append(dict(task=task, design_id=pair["design_id"], exact_checkpoint_equality=True))
        for seed, seed_data in audit["seeds"].items():
            gaps = []
            records = seed_data["records"]
            for identifier, record in records.items():
                measured = panel_payload(record["per_panel_development"])
                for key in ("primary", "loss", "worst_panel", "panel_primary_sd"):
                    if measured[key] != record["development"][key]:
                        raise ValueError("Exported panel summary differs from its vector")
                gaps.append(100*(measured["primary"] - measured["worst_panel"]))
            diagnostic = selection_diagnostic(records)
            if diagnostic != seed_data["selection"]:
                raise ValueError("Independent selection diagnostic differs")
            fixed = diagnostic["fixed_even_odd"]
            exhaustive = diagnostic["exhaustive"]
            rows.append(dict(task=task, seed=int(seed), checkpoints=len(records),
                mean_minus_worst_mean_pp=statistics.mean(gaps),
                mean_minus_worst_min_pp=min(gaps), mean_minus_worst_max_pp=max(gaps),
                all_panel_selected=diagnostic["all_panel_selected"],
                fixed_proposal_selected=fixed["selected"],
                proposal_delta_pp=fixed["proposal_delta_pp"], confirmation_delta_pp=fixed["confirmation_delta_pp"],
                exhaustive_partitions=exhaustive["partitions"],
                exhaustive_all_panel_winner_agreement=exhaustive["all_panel_winner_agreement"],
                exhaustive_negative_confirmation=exhaustive["negative_confirmation"],
                exhaustive_sign_reversal=exhaustive["positive_proposal_negative_confirmation"]))
    if checkpoints != 72 or canary_fits != 8 or len(rows) != 6 or len(verification) != 4:
        raise ValueError("Registered coverage incomplete")
    summary = dict(schema="panel-feedback-development-summary-v1", status="PASS", rows=rows,
        checkpoint_count=checkpoints, labelled_panel_scores=checkpoints*10,
        nonzero_mean_worst_gaps=gap_count, canary_new_fits=canary_fits,
        canary_rounds_per_fit=10, raw_structured_fact_checks=checkpoints,
        aggregate_max_abs_error=max(read(OUT / task / "development_audit.json")["aggregate_max_abs_error"] for task in protocol["tasks"]),
        paired_canary_checks=verification, source_bindings=bindings,
        original_source_bindings=protocol["source_sha256"],
        new_main_study_training_fits=0, new_llm_calls=0, new_heldout_inference=False,
        interpretation=protocol["stability"]["limit"], future_mechanism_plan=protocol["future_mechanism_plan"])
    lines = [r"\begin{table}[htbp]", r"\centering", r"\small",
        r"\caption{Development-only audit after restoring target-panel feedback. Each row reconstructs all twelve saved best checkpoints. Gap is the mean across designs of primary minus the true worst-panel score, in percentage points. A/B are fixed even/odd panel subsets. The last column counts five-panel proposal subsets selecting the same design as all ten panels, out of 252. Complement scores reuse checkpoints already selected on all ten panels; they are descriptive, not independent confirmation.}",
        r"\label{tab:panel-feedback-audit}", r"\begin{tabular}{llrrrr}", r"\toprule",
        r"Task & Seed & Mean--worst gap & A gain & B gain & Winner agreement \\", r"\midrule"]
    for row in rows:
        task = "Cell" if row["task"] == "cell" else "Protein"
        lines.append(f"{task} & {row['seed']} & {row['mean_minus_worst_mean_pp']:.2f} & "
            f"{row['proposal_delta_pp']:+.2f} & {row['confirmation_delta_pp']:+.2f} & "
            f"{row['exhaustive_all_panel_winner_agreement']}/252 " + r"\\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}", ""]
    payloads = {"summary.json": canonical(summary)}
    for path in sorted((PROJECT / "extensions/panel_feedback_20261110").glob("*.py")):
        payloads[path.relative_to(PROJECT).as_posix()] = path.read_bytes()
    payloads["paper/tools/publish_panel_feedback.py"] = Path(__file__).read_bytes()
    payloads["docs/panel_feedback_20261110/PROGRESS.zh-CN.md"] = (
        PROJECT / "docs/panel_feedback_20261110/PROGRESS.zh-CN.md").read_bytes()
    for name in ("protocol.json", "registration.json"):
        payloads["metadata/" + name] = (OUT / name).read_bytes()
    payloads["README.txt"] = (
        "Requires the original BioCoLoop research checkout, frozen source adapters, authorized prepared task data, "
        "original candidate/checkpoint caches and compatible PyTorch/NumPy environments. This is an implementation "
        "and aggregate-provenance package, not a standalone dataset. No biological response matrices, sample predictions, "
        "checkpoints, model weights or credentials are included. Absolute paths identify the evaluated local run.\n").encode()
    for name, raw in payloads.items():
        assert_not_secret(raw, name)
    return summary, "\n".join(lines).encode(), payloads


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    summary, table, payloads = build()
    if args.check:
        if (DEST / "summary.json").read_bytes() != canonical(summary) or TABLE.read_bytes() != table:
            raise ValueError("Generated table or summary changed")
        manifest = read(DEST / "experiment_sources.manifest.json")
        if manifest["generator_sha256"] != sha(__file__) or manifest["table_sha256"] != sha(TABLE) or \
                manifest["summary_sha256"] != sha(DEST / "summary.json"):
            raise ValueError("Generator/table/summary manifest differs")
        if sha(DEST / "experiment_sources.zip") != manifest["archive_sha256"]:
            raise ValueError("Source archive hash changed")
        with zipfile.ZipFile(DEST / "experiment_sources.zip") as archive:
            if set(archive.namelist()) != set(payloads):
                raise ValueError("Archive members differ")
            for name, raw in payloads.items():
                if archive.read(name) != raw:
                    raise ValueError("Archive content differs: " + name)
    else:
        DEST.mkdir(parents=True, exist_ok=True)
        TABLE.parent.mkdir(parents=True, exist_ok=True)
        (DEST / "summary.json").write_bytes(canonical(summary))
        TABLE.write_bytes(table)
        with zipfile.ZipFile(DEST / "experiment_sources.zip", "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, raw in sorted(payloads.items()):
                info = zipfile.ZipInfo(name, date_time=(2026,11,10,0,0,0))
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, raw)
        manifest = dict(status="PASS", archive_sha256=sha(DEST / "experiment_sources.zip"),
            archive_member_sha256={name: hashlib.sha256(raw).hexdigest() for name,raw in payloads.items()},
            generator_sha256=sha(__file__), table_sha256=sha(TABLE), summary_sha256=sha(DEST / "summary.json"))
        (DEST / "experiment_sources.manifest.json").write_bytes(canonical(manifest))
    print(json.dumps({k:summary[k] for k in ("status", "checkpoint_count", "aggregate_max_abs_error", "canary_new_fits", "nonzero_mean_worst_gaps")}, indent=2))


if __name__ == "__main__":
    main()
