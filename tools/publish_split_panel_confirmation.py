"""Verify and package the split-panel confirmation study without changing old evidence."""
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
from extensions.split_panel_confirmation_20261110.common import DIRECTIONS, LLM_ARMS, OUT, PROPOSERS, SEEDS, TASKS
from extensions.split_panel_confirmation_20261110 import protocol as spc_protocol
from package_fbhk_followup import assert_not_secret

DEST = PAPER / "provenance/split_panel_confirmation_20261110"
TABLE = PAPER / "tables/split_panel_confirmation_20261110/results.tex"
ARMS = ("fixed", "random", "gp_ei") + tuple(f"{p}/{a}" for p in PROPOSERS for a in LLM_ARMS)
LABELS = {"fixed": "Fixed D00", "random": "Random (exact)", "gp_ei": "GP--EI",
          "qwen/direct": "Qwen direct", "qwen/raw": "Qwen raw", "qwen/structured": "Qwen structured",
          "luna/direct": "Luna direct", "luna/raw": "Luna raw", "luna/structured": "Luna structured"}
METRICS = ("selection", "confirmation", "heldout")


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def mean(values):
    return statistics.mean(values)


def build():
    for stage in (1, 2):
        spc_protocol.checked(stage, OUT)
    equivalence = read(OUT / "train_equivalence.json")
    if not equivalence["all_pass"] or equivalence["fits"] != 72 or len(equivalence["reports"]) != 72 or \
            any(v is False for r in equivalence["reports"] for v in r.values()):
        raise ValueError("Fresh fits do not reproduce the original cache")
    bindings = {str(OUT / name): sha(OUT / name) for name in (
        "protocol_stage1.json", "registration_stage1.json", "protocol_stage2.json",
        "train_equivalence.json", "report.json")}
    seals = {}
    for direction in DIRECTIONS:
        path = OUT / "directions" / direction / "seal.json"
        seals[direction] = read(path)
        bindings[str(path)] = sha(path)
    # The first confirmation read must follow the later seal.
    last_seal = max(seal["sealed_utc"] for seal in seals.values())
    access = {}
    for direction, (select_half, confirm_half) in DIRECTIONS.items():
        path = OUT / "directions" / direction / "access_log.jsonl"
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        for row in rows:
            if row["half"] != (select_half if row["purpose"] == "selection" else confirm_half):
                raise ValueError("Panel half read for the wrong purpose")
        confirmation = [r["utc"] for r in rows if r["purpose"] == "confirmation"]
        selection = [r["utc"] for r in rows if r["purpose"] == "selection"]
        if min(confirmation) <= last_seal:
            raise ValueError("Confirmation half opened before both seals")
        if max(selection) >= min(confirmation):
            raise ValueError("Selection read after confirmation opened")
        access[direction] = dict(selection_reads=len(selection), confirmation_reads=len(confirmation),
                                 last_selection_utc=max(selection), first_confirmation_utc=min(confirmation))
        bindings[str(path)] = sha(path)
    values, invalid, calls, unique_heldout = {}, {}, {}, 0
    for task in TASKS:
        scores = read(OUT / "scores" / f"{task}.json")
        bindings[str(OUT / "scores" / f"{task}.json")] = sha(OUT / "scores" / f"{task}.json")
        if scores["status"] != "COMPLETE" or scores["panel_recheck_failures"] or scores["feedback_to_controller"]:
            raise ValueError("Scoring incomplete or panel re-evaluation failed")
        unique_heldout += scores["unique_heldout_checkpoints"]
        for direction in DIRECTIONS:
            for seed in SEEDS:
                rows = scores["rows"][f"{direction}/seed{seed}"]
                base = OUT / "directions" / direction / task / f"seed{seed}"
                controls = read(base / "controls" / "controls.json")
                bindings[str(base / "controls" / "controls.json")] = sha(base / "controls" / "controls.json")
                def point(design):
                    row = rows[design]
                    return dict(selection=row["selection"]["primary"], confirmation=row["confirmation"]["primary"],
                                heldout=row["heldout_primary"])
                cell = {"fixed": point("D00"), "gp_ei": point(controls["gp_ei"]["design_id"])}
                weights = controls["random"]["weights"]
                if abs(sum(weights.values()) - 1) > 1e-12:
                    raise ValueError("Random weights must sum to one")
                cell["random"] = {m: sum(w * point(d)[m] for d, w in weights.items()) for m in METRICS}
                for proposer in PROPOSERS:
                    path = base / proposer / "selections.json"
                    bindings[str(path)] = sha(path)
                    selected = read(path)
                    if sha(path) != seals[direction]["selections_sha256"][path.relative_to(PROJECT).as_posix()]:
                        raise ValueError("Sealed selection changed: " + str(path))
                    calls[proposer] = calls.get(proposer, 0) + selected["llm_calls"]
                    for arm in LLM_ARMS:
                        item = selected["selections"][arm]
                        cell[f"{proposer}/{arm}"] = point(item["design_id"])
                        invalid[f"{proposer}/{arm}"] = invalid.get(f"{proposer}/{arm}", 0) + item["invalid_slots"]
                values[(task, direction, seed)] = cell
    report = read(OUT / "report.json")
    table = {}
    for task in TASKS:
        for direction in DIRECTIONS:
            for arm in ARMS:
                entry = {m: 100 * mean([values[(task, direction, s)][arm][m] for s in SEEDS]) for m in METRICS}
                for m in METRICS:
                    if abs(entry[m] - report["table"][f"{task}/{direction}/{arm}"][m]["mean_pp"]) > 1e-9:
                        raise ValueError("Independent aggregate differs from report.json")
                table[f"{task}/{direction}/{arm}"] = entry | dict(
                    per_seed_heldout_pp=[100 * values[(task, direction, s)][arm]["heldout"] for s in SEEDS],
                    per_seed_confirmation_pp=[100 * values[(task, direction, s)][arm]["confirmation"] for s in SEEDS])
    def contrast(left, right, metric):
        return [100 * (values[k][left][metric] - values[k][right][metric]) for k in sorted(values)]
    history = {}
    for proposer in PROPOSERS:
        for arm in ("raw", "structured"):
            for metric in ("confirmation", "heldout"):
                diffs = contrast(f"{proposer}/{arm}", f"{proposer}/direct", metric)
                history[f"{proposer}/{arm}-direct/{metric}"] = dict(
                    mean_pp=mean(diffs), positive=sum(d > 0 for d in diffs), zero=sum(d == 0 for d in diffs),
                    negative=sum(d < 0 for d in diffs), runs=len(diffs))
    optimism = {f"{t}/{d}": mean([table[f"{t}/{d}/{a}"]["selection"] - table[f"{t}/{d}/{a}"]["confirmation"]
                                  for a in ARMS if a != "fixed"]) for t in TASKS for d in DIRECTIONS}
    summary = dict(schema="split-panel-confirmation-summary-v1", status="PASS", table=table,
                   history_minus_direct=history, mean_search_optimism_pp=optimism,
                   invalid_slots_of_72=invalid, logical_llm_calls=calls, last_seal_utc=last_seal,
                   access=access, fresh_fits=72, saved_round_checkpoints=72 * 20,
                   unique_heldout_checkpoints=unique_heldout, train_equivalence_all_pass=True,
                   source_bindings=bindings, historically_exposed_heldout=True,
                   interpretation="Selection and confirmation use disjoint halves of the same historical target panels; "
                                  "the partition and test set were previously exposed descriptively. This is not a new biological split.")
    lines = [r"\begin{table}[htbp]", r"\centering", r"\scriptsize", r"\setlength{\tabcolsep}{3.2pt}",
        r"\caption{Split-panel confirmation. Each direction selects checkpoint rounds and designs on five development panels "
        r"(A$\to$B: even panels; B$\to$A: odd panels), seals both directions, and only then scores the other five panels "
        r"(Conf.) and the original held-out test (Test). Cell reports macro accuracy and protein AP, in points; means over "
        r"seeds 61--63 with every arm, seed and direction retained. Random is the exact expectation over all "
        r"$\binom{11}{6}$ six-design searches. Bold marks the best Test value in each column.}",
        r"\label{tab:split-panel-confirmation}", r"\begin{tabular}{lrrrrrrrr}", r"\toprule",
        r" & \multicolumn{4}{c}{Cell} & \multicolumn{4}{c}{Protein} \\",
        r"\cmidrule(lr){2-5}\cmidrule(lr){6-9}",
        r" & \multicolumn{2}{c}{A$\to$B} & \multicolumn{2}{c}{B$\to$A} & \multicolumn{2}{c}{A$\to$B} & \multicolumn{2}{c}{B$\to$A} \\",
        r"Arm & Conf. & Test & Conf. & Test & Conf. & Test & Conf. & Test \\", r"\midrule"]
    columns = [(t, d) for t in TASKS for d in DIRECTIONS]
    best = {c: max(round(table[f"{c[0]}/{c[1]}/{a}"]["heldout"], 2) for a in ARMS) for c in columns}
    for i, arm in enumerate(ARMS):
        if i in (3, 6):
            lines.append(r"\addlinespace")
        cells = []
        for t, d in columns:
            entry = table[f"{t}/{d}/{arm}"]
            test = f"{entry['heldout']:.2f}"
            cells += [f"{entry['confirmation']:.2f}", rf"\textbf{{{test}}}" if round(entry["heldout"], 2) == best[(t, d)] else test]
        lines.append(LABELS[arm] + " & " + " & ".join(cells) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}", ""]
    payloads = {"summary.json": canonical(summary)}
    for path in sorted((PROJECT / "extensions/split_panel_confirmation_20261110").glob("*")):
        if path.is_file() and path.suffix in (".py", ".sh"):
            payloads[path.relative_to(PROJECT).as_posix()] = path.read_bytes()
    payloads["paper/tools/publish_split_panel_confirmation.py"] = Path(__file__).read_bytes()
    for name in ("protocol_stage1.json", "registration_stage1.json", "protocol_stage2.json", "report.json"):
        payloads["metadata/" + name] = (OUT / name).read_bytes()
    payloads["README.txt"] = (
        "Requires the original BioCoLoop research checkout, frozen source adapters, authorized prepared task data "
        "and compatible PyTorch/NumPy environments. This is an implementation and aggregate-provenance package, not a "
        "standalone dataset. No biological response matrices, sample predictions, checkpoints, model weights, LLM "
        "transcripts or credentials are included. Absolute paths identify the evaluated local run.\n").encode()
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
                info = zipfile.ZipInfo(name, date_time=(2026, 11, 11, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, raw)
        manifest = dict(status="PASS", archive_sha256=sha(DEST / "experiment_sources.zip"),
            archive_member_sha256={name: hashlib.sha256(raw).hexdigest() for name, raw in payloads.items()},
            generator_sha256=sha(__file__), table_sha256=sha(TABLE), summary_sha256=sha(DEST / "summary.json"))
        (DEST / "experiment_sources.manifest.json").write_bytes(canonical(manifest))
    print(json.dumps(dict(status=summary["status"], history_minus_direct=summary["history_minus_direct"],
                          invalid_slots_of_72=summary["invalid_slots_of_72"],
                          mean_search_optimism_pp=summary["mean_search_optimism_pp"]), indent=1))


if __name__ == "__main__":
    main()
