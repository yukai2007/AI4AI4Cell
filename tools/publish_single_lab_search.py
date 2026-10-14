"""Publish additive search controls from a portable, aggregate-only snapshot.

Regenerate committed tables: python tools/publish_single_lab_search.py --check
Import verified local results: python tools/publish_single_lab_search.py --refresh-from PROJECT
No fitting, checkpoint selection, or individual biological records are performed/published here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics

PAPER = Path(__file__).resolve().parents[1]
OUT = PAPER / "tables/single_lab_search"
SEEDS = [42, 43, 44]
TASKS = ("native_tapb", "ptpc_neural", "vcc_corrected",
         "norman_double_corrected", "tahoe_drug_corrected")
METHODS = ("fixed", "random_6", "bayes_6", "exhaustive_12", "single_loop", "federated_loop")
ALL_METHODS = METHODS + ("exact_random_6",)
LABELS = {"fixed": "Fixed model", "random_6": "Random@6", "bayes_6": "Bayesian@6",
          "exhaustive_12": "12-design menu", "single_loop": "BioCoLoop", "federated_loop": "BioCoLoop"}
ENDPOINTS = ("random", "unseen_drug", "unseen_protein")
METRICS = ("auroc", "average_precision")
CHECKS = ("all180_full100_fits", "all15_studies", "dti_primary_three_endpoints_all_seeds",
          "gpu_statistics_complete", "metadata_overlap_audit")


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def aggregate(record):
    """Recompute three-seed sample statistics, rejecting stale or incomplete aggregates."""
    values = record["values"]
    if isinstance(values, dict):
        require(set(values) == set(map(str, SEEDS)), "Missing or unexpected seed")
        values = [values[str(seed)] for seed in SEEDS]
    else:
        require(record.get("seeds") == SEEDS, "Endpoint seed order differs")
    require(len(values) == 3, "Exactly three trained seeds required")
    require(all(isinstance(v, (int, float)) and math.isfinite(v) and 0 <= v <= 1
                for v in values), "Non-finite or out-of-range metric")
    result = dict(n=3, values=dict(zip(map(str, SEEDS), values)),
                  mean=statistics.mean(values), sd=statistics.stdev(values))
    for field in ("mean", "sd"):
        require(math.isclose(result[field], record[field], abs_tol=1e-12, rel_tol=0),
                f"Stored {field} differs from per-seed scores")
    if "n" in record:
        require(record["n"] == 3, "Stored seed count differs")
    return result


def validate(snapshot):
    require(snapshot.get("schema") == "single-lab-search-publication-v1", "Wrong publication schema")
    require(snapshot.get("status") == "COMPLETE" and snapshot.get("seeds") == SEEDS,
            "Incomplete publication")
    require(snapshot["completion_checks"] == dict.fromkeys(CHECKS, True), "Incomplete evidence gate")
    require(set(snapshot["rows"]) == set(TASKS), "Task coverage differs")
    cost = snapshot["training_cost"]
    for key, expected in (("verified_complete_studies", 15), ("verified_full100_candidates", 180),
                          ("verified_candidate_attempts", 180), ("numerical_failures", 0),
                          ("completed_candidate_rounds", 18000)):
        require(cost[key] == expected, f"Training count differs: {key}")
    require(len(snapshot["training_audits"]) == 15, "Study audit coverage differs")
    for task in TASKS:
        require(set(snapshot["rows"][task]) == set(ALL_METHODS), "Method coverage differs")
        for method in ALL_METHODS:
            aggregate(snapshot["rows"][task][method])
        for seed in SEEDS:
            audit = snapshot["training_audits"][f"{task}/seed{seed}"]
            require((audit["task"], audit["seed"], audit["candidate_attempts"],
                     audit["full100_candidates"], audit["completed_rounds"], audit["numerical_failures"])
                    == (task, seed, 12, 12, 1200, 0), "Invalid full-training study audit")
            require(set(audit["receipt_sha256"]) == {f"D{i:02d}" for i in range(12)},
                    "Candidate receipt coverage differs")
    require(snapshot["protocol"]["search_clients"] == [0], "Search accesses additional laboratories")
    require(set(snapshot["protocol"]["candidate_designs_by_id"]) == {f"D{i:02d}" for i in range(12)},
            "Portable candidate menu incomplete")
    require(set(snapshot["search_runs"]) == set(snapshot["training_audits"]), "Search trace coverage differs")
    for run in snapshot["search_runs"].values():
        ids = run["random_6_ids"]
        bayes = run["bayes_6"]
        require(len(ids) == len(set(ids)) == 7 and ids[0] == "D00", "Random search budget differs")
        require(len(bayes["candidate_ids"]) == len(set(bayes["candidate_ids"])) == 7
                and bayes["candidate_ids"][0] == "D00", "Bayesian search budget differs")
        require(len(bayes["trace"]) == 6 and [entry["design_id"] for entry in bayes["trace"]]
                == bayes["candidate_ids"][1:], "Bayesian trace differs")
        require(bayes["test_used_for_selection"] is False, "Bayesian selection uses test")
        require(run["exact_random_6"]["subset_count"] == 462
                and run["exact_random_6"]["test_used_to_choose_weights"] is False, "Exact random-search protocol differs")
    require(snapshot["protocol"]["nominal_candidate_rounds"] ==
            {"fixed": 100, "random_6": 700, "bayes_6": 700, "exhaustive_12": 1200},
            "Nominal budgets differ")
    require(set(snapshot["dti_endpoints"]) == set(METHODS), "DTI method coverage differs")
    for method in METHODS:
        require(set(snapshot["dti_endpoints"][method]) == set(ENDPOINTS), "DTI endpoint coverage differs")
        for endpoint in ENDPOINTS:
            require(set(snapshot["dti_endpoints"][method][endpoint]) == set(METRICS), "DTI metrics differ")
            for metric in METRICS:
                aggregate(snapshot["dti_endpoints"][method][endpoint][metric])
        require(snapshot["dti_endpoints"][method]["random"]["auroc"] == snapshot["rows"]["native_tapb"][method],
                "Primary and endpoint DTI values differ")
    require(set(snapshot["cluster_statistics"]) == set(TASKS[1:]), "Cluster statistic coverage differs")
    for task, data in snapshot["cluster_statistics"].items():
        require(data["bootstrap_replicates_requested"] == 10000 and data["seeds"] == SEEDS,
                "Bootstrap protocol differs")
        require(data["training_seed_resampled"] is False and data["descriptive_only"] is True,
                "Bootstrap uncertainty definition differs")
        for contrast in data["effects"].values():
            expected = snapshot["rows"][task][contrast["left"]]["mean"] - snapshot["rows"][task][contrast["right"]]["mean"]
            require(abs(contrast["estimates"]["seed_macro_mean"]["difference"] - expected) < 1e-12,
                    "Bootstrap contrast differs from table")
    encoded = json.dumps(snapshot)
    require("/liziqing/" not in encoded and "compound_key" not in encoded and "cluster_sizes" not in encoded,
            "Host-specific or individual biological metadata leaked into publication")
    def reject_absolute(value):
        if isinstance(value, dict):
            for key, item in value.items():
                require(not key.startswith("/"), "Absolute path key in snapshot")
                reject_absolute(item)
        elif isinstance(value, list):
            for item in value:
                reject_absolute(item)
        elif isinstance(value, str):
            require(not value.startswith("/"), "Absolute path value in snapshot")
    reject_absolute(snapshot)
    return snapshot


def import_results(root):
    root = Path(root).resolve()
    summary_path = root / "results/single_lab_search_20261014/final_delivery/summary.json"
    endpoints_path = summary_path.with_name("dti_endpoints.json")
    statistics_path = root / "results/single_lab_search_20261014_gpu/statistics/paired_statistics.json"
    summary, endpoints, stats = (read(p) for p in (summary_path, endpoints_path, statistics_path))
    require(summary["status"] == endpoints["status"] == stats["status"] == "COMPLETE", "Source delivery incomplete")
    require(endpoints["independent_rescoring"] is True, "DTI independent rescoring missing")
    require(stats["cpu_preview_read"] is False and stats["model_selection_using_test"] is False,
            "Wrong runtime or selection inputs")
    require(summary["statistics_sha256"] == sha(statistics_path), "Statistics digest differs")
    for task in TASKS:
        require(summary["training_status"][task] == dict.fromkeys(map(str, SEEDS), "COMPLETE"),
                "Source study unfinished")
    require(all(summary["dti_primary_endpoints"][str(seed)]["status"] == "PASS" for seed in SEEDS),
            "DTI endpoint verification missing")
    audits = {}
    search_runs = {}
    extra_sources = {}
    design_library = None
    for key, audit in summary["training_audits"].items():
        require(audit["independent_primary_verification"]["status"] == "COMPLETE_VERIFIED",
                "Primary independent verification missing")
        audits[key] = {field: audit[field] for field in ("task", "seed", "candidate_attempts",
            "full100_candidates", "completed_rounds", "numerical_failures", "protocol_sha256", "receipt_sha256")}
        study = root / "results/single_lab_search_20261014_gpu" / key
        protocol_path = study / "protocol.json"
        metadata_path = study / "search_addons/selection_metadata.json"
        protocol, metadata = read(protocol_path), read(metadata_path)
        require(sha(protocol_path) == audit["protocol_sha256"], "Training protocol changed")
        require(protocol["clients"] == metadata["clients"] == [0], "Replay data access differs")
        require(protocol["seed"] == metadata["seed"] == audit["seed"], "Replay seed differs")
        if design_library is None:
            design_library = protocol["designs"]
        require(protocol["designs"] == design_library, "Task design libraries differ")
        bayes = dict(metadata["bayes_6"])
        exact = dict(metadata["exact_random_6"])
        # DTI records these flags inside each method; lightweight metadata
        # records the same assertion at the shared replay level.
        bayes["test_used_for_selection"] = bayes.get("test_used_for_selection", metadata.get("test_used_for_selection"))
        exact["test_used_to_choose_weights"] = exact.get("test_used_to_choose_weights", metadata.get("test_used_for_selection"))
        search_runs[key] = dict(random_6_ids=protocol["methods"]["random_6"]["design_ids"],
            bayes_6=bayes, exact_random_6=exact)
        for path in (protocol_path, metadata_path):
            extra_sources[str(path)] = sha(path)
    clusters = {}
    for task in TASKS[1:]:
        item = stats["tasks"][task]
        require(item["status"] == "COMPLETE", "Task statistics incomplete")
        clusters[task] = dict(item["statistics"])
        clusters[task]["n_test_clusters"] = item["alignment"]["n_clusters"]
        clusters[task]["n_test_queries"] = item["alignment"]["n_queries"]
    snapshot = dict(schema="single-lab-search-publication-v1", status="COMPLETE", seeds=SEEDS,
        score_units="unit interval; tables multiply scores and SD by 100",
        protocol=dict(search_clients=[0], candidate_designs=12, rounds_per_candidate=100,
            nominal_candidate_rounds=summary["nominal_rounds"],
            search_execution="Development-only deterministic-candidate-cache replay; no extra adaptive training.",
            candidate_designs_by_id=design_library,
            selection="Maximize lab-0 development primary, minimize development loss on ties, retain earlier candidate on exact ties",
            checkpoint_selection="Development evaluation every five rounds within the 100-round training schedule",
            random_6="D00 plus six distinct draws from D01--D11",
            bayes_6="D00, two seeded random warm starts, then four Gaussian-process expected-improvement proposals",
            bayes_kernel=search_runs["native_tapb/seed42"]["bayes_6"]["kernel"],
            bayes_acquisition=search_runs["native_tapb/seed42"]["bayes_6"]["acquisition"],
            exhaustive_12="All twelve registered designs, not a Cartesian hyperparameter grid",
            exact_random_6="Average selected-model metrics over all 462 six-of-eleven subsets, integrating proposal-order ties; not prediction ensembling",
            reference_researcher="Qwen2.5-7B-Instruct",
            reference_rows="Historical history-enabled BioCoLoop at one and ten laboratories; not the Direct condition",
            comparison_scope="One-versus-ten laboratories includes data, evaluation-evidence and computation access differences."),
        completion_checks=summary["completion_checks"], training_cost=summary["training_cost"],
        training_audits=audits, search_runs=search_runs, rows={task: {method: aggregate(summary["rows"][task][method])
                                          for method in ALL_METHODS} for task in TASKS},
        dti_endpoints={method: {endpoint: {metric: aggregate(endpoints["results"][method][endpoint][metric])
                                          for metric in METRICS} for endpoint in ENDPOINTS} for method in METHODS},
        cluster_statistics=clusters, origins=summary["provenance"])
    validate(snapshot)
    sources = {}
    for mapping in (summary["input_artifacts_sha256"], endpoints["input_sha256"], stats["input_artifacts_sha256"], extra_sources):
        for path, digest in mapping.items():
            resolved = Path(path).resolve()
            relative = str(resolved.relative_to(root))
            require(relative not in sources or sources[relative] == digest, "Conflicting source digest")
            require(sha(resolved) == digest, f"Changed source: {relative}")
            sources[relative] = digest
    for path in (summary_path, endpoints_path, statistics_path):
        sources[str(path.relative_to(root))] = sha(path)
    provenance = dict(schema="single-lab-search-publication-provenance-v1",
        source_report_generated_utc=summary["generated_utc"],
        source_artifacts_sha256=dict(sorted(sources.items())),
        source_code_sha256={"final_report.py": summary["report_source_sha256"],
                            "endpoint_report.py": endpoints["source_sha256"]},
        privacy="Only aggregate metrics, training counts and integrity digests are published; no individual biological records.")
    return snapshot, provenance


def cell(record, best=None):
    number = f"{100 * record['mean']:.2f}"
    if best is not None and number == best:
        number = r"\mathbf{" + number + "}"
    return "$" + number + r"\,{\scriptstyle\pm" + f"{100 * record['sd']:.2f}" + "}$"


def table_start(caption, label, columns):
    return ["% Generated by tools/publish_single_lab_search.py; edit the generator, not this file.",
            r"\begin{table}[!ht]", r"\centering", r"\caption{" + caption + "}",
            r"\label{" + label + "}", r"\small", r"\setlength{\tabcolsep}{3pt}",
            r"\renewcommand{\arraystretch}{1.13}",
            r"\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}" + columns + "@{}}", r"\toprule"]


def table_end(lines):
    return "\n".join(lines + [r"\bottomrule", r"\end{tabular*}", r"\end{table}", ""])


def render(snapshot):
    validate(snapshot)
    caption = (r"\textbf{Single-laboratory search controls.} Mean $\pm$ sample SD over three training seeds, "
               r"in percentage units. Search controls use only lab~0; the history-enabled BioCoLoop references "
               r"use Qwen2.5-7B-Instruct with one or ten laboratories. The ten-laboratory setting adds training "
               r"and evaluation evidence. Bold marks the highest displayed mean per column.")
    lines = table_start(caption, "tab:single-lab-search", "lcrrrrr")
    lines += [r"Method & Labs & DTI & Proteomics & \multicolumn{3}{c}{Cell perturbation} \\",
              r"\cmidrule(lr){5-7}",
              r" & & AUROC$\uparrow$ & AP$\uparrow$ & VCC & Norman & Tahoe \\",
              r" & & & & Top-1$\uparrow$ & Top-1$\uparrow$ & Top-1$\uparrow$ \\", r"\midrule",
              r"\multicolumn{7}{l}{\emph{LLM-free controls}} \\"]
    best = {task: f"{max(snapshot['rows'][task][m]['mean'] for m in METHODS) * 100:.2f}" for task in TASKS}
    for method in METHODS:
        if method == "single_loop":
            lines += [r"\midrule", r"\multicolumn{7}{l}{\emph{History-enabled BioCoLoop references}} \\"]
        lines.append(" & ".join([LABELS[method], "10" if method == "federated_loop" else "1"] +
                     [cell(snapshot["rows"][task][method], best[task]) for task in TASKS]) + r" \\")
    comparison = table_end(lines)
    caption = (r"\textbf{Single-laboratory search across three drug--target test splits.} "
               r"AUROC and average precision (AP), mean $\pm$ sample SD over the same three seeds, expressed as percentages. "
               r"Each method's development-selected predictor is reused across all three test splits. "
               r"Lab access, candidate budgets and the historical Qwen BioCoLoop references are as in Table~\ref{tab:single-lab-search}. "
               r"Bold marks the highest displayed mean per column.")
    lines = table_start(caption, "tab:single-lab-dti-endpoints", "lcrrrrrr")
    lines += [r"Method & Labs & \multicolumn{2}{c}{Random split} & \multicolumn{2}{c}{Unseen drug} & \multicolumn{2}{c}{Unseen protein} \\",
              r"\cmidrule(lr){3-4}\cmidrule(lr){5-6}\cmidrule(lr){7-8}",
              r" & & AUROC$\uparrow$ & AP$\uparrow$ & AUROC$\uparrow$ & AP$\uparrow$ & AUROC$\uparrow$ & AP$\uparrow$ \\", r"\midrule"]
    for method in METHODS:
        if method == "single_loop":
            lines.append(r"\midrule")
        cells = []
        for endpoint in ENDPOINTS:
            for metric in METRICS:
                best_value = f"{max(snapshot['dti_endpoints'][m][endpoint][metric]['mean'] for m in METHODS) * 100:.2f}"
                cells.append(cell(snapshot["dti_endpoints"][method][endpoint][metric], best_value))
        lines.append(" & ".join([LABELS[method], "10" if method == "federated_loop" else "1"] + cells) + r" \\")
    dti = table_end(lines)
    caption = (r"\textbf{Integrating random-search variability.} Expected Random@6 score over all "
               r"$\binom{11}{6}=462$ proposal subsets, integrating proposal-order ties. This averages selected-model "
               r"metrics, not their predictions. Scores are percentages; the final row is the mean $\pm$ sample SD "
               r"across three trained seeds after search randomness is integrated out.")
    lines = table_start(caption, "tab:single-lab-search-expectation", "lrrrrr")
    lines += [r"Training seed & DTI & Proteomics & VCC & Norman & Tahoe \\",
              r" & AUROC$\uparrow$ & AP$\uparrow$ & Top-1$\uparrow$ & Top-1$\uparrow$ & Top-1$\uparrow$ \\", r"\midrule"]
    for seed in SEEDS:
        lines.append(" & ".join([str(seed)] + [f"{snapshot['rows'][task]['exact_random_6']['values'][str(seed)] * 100:.2f}"
                                              for task in TASKS]) + r" \\")
    lines += [r"\midrule", " & ".join([r"Mean $\pm$ SD"] + [cell(snapshot["rows"][task]["exact_random_6"])
                                                              for task in TASKS]) + r" \\"]
    return {"comparison.tex": comparison, "dti_endpoints.tex": dti,
            "search_expectation.tex": table_end(lines)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh-from", type=Path, help="Project containing verified local experimental result files")
    parser.add_argument("--output", type=Path, default=OUT)
    parser.add_argument("--check", action="store_true", help="Validate committed snapshot and require generated files to match")
    args = parser.parse_args()
    require(not (args.refresh_from and args.check), "Choose import or check, not both")
    args.output.mkdir(parents=True, exist_ok=True)
    if args.refresh_from:
        snapshot, provenance = import_results(args.refresh_from)
        payload = json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n"
        (args.output / "snapshot.json").write_text(payload, encoding="utf-8")
        provenance["snapshot_sha256"] = sha(args.output / "snapshot.json")
        provenance["publisher_sha256"] = sha(__file__)
        (args.output / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    else:
        snapshot = read(args.output / "snapshot.json")
        provenance = read(args.output / "provenance.json")
        require(provenance["snapshot_sha256"] == sha(args.output / "snapshot.json"), "Snapshot digest differs")
    for name, content in render(snapshot).items():
        destination = args.output / name
        if args.check:
            require(destination.read_text(encoding="utf-8") == content, f"Stale generated table: {name}")
        else:
            destination.write_text(content, encoding="utf-8")
    print(json.dumps(dict(status="PASS", complete_studies=15, full_candidate_fits=180, seeds=SEEDS,
                          tables=list(render(snapshot)))))


if __name__ == "__main__":
    main()
