"""Render both proposer comparisons and archive code/aggregate provenance only."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

PAPER=Path(__file__).resolve().parents[1]
PROJECT=PAPER.parent
sys.path.insert(0,str(PROJECT))
from extensions.recipe_expansion_20261110_v2.common import OUT as CACHE,checked,read,sha
from extensions.recipe_search_compact_20261110.runner import SEARCH,verify_seals
from package_fbhk_followup import assert_not_secret

DEST=PAPER/"provenance/recipe_expansion_20261110"
TABLES=PAPER/"tables/recipe_expansion_20261110"
NAMES={"fixed_D00":"Fully fitted D00","direct":"Direct","raw":"Raw history","structured":"Structured history",
       "random":"Random expectation","gp_ei":r"GP--EI ($\xi=.01$)","gp_ei_zero":r"GP--EI ($\xi=0$)"}


def raw_json(value):
    return (json.dumps(value,ensure_ascii=False,indent=2,sort_keys=True)+"\n").encode()


def build():
    protocol=checked(CACHE)
    report=read(SEARCH/"final_report.json")
    if report["status"]!="COMPLETE" or report["new_fits"]!=216 or set(report["models"])!={"qwen","luna"}:
        raise ValueError("Incomplete repaired study")
    verify_seals()
    for filename,digest in report["source_bindings"].items():
        if sha(filename)!=digest:
            raise ValueError("Report input changed")
    for task,data in report["verification"].items():
        if data["fits"]!=108 or {(r["seed"],r["design_id"]) for r in data["candidate_checks"]}!={
                (seed,identifier) for seed in protocol["seeds"] for identifier in protocol["candidates"]}:
            raise ValueError("Candidate coverage incomplete")
        for model in report["models"].values():
            if not set(NAMES)<=set(model["tasks"][task]["policies"]):
                raise ValueError("Policy omitted")
    lines=[r"\begin{table}[htbp]",r"\centering\footnotesize",r"\setlength{\tabcolsep}{3pt}",
        r"\caption{Expanded-recipe comparison on DTI and proteomics. Each model uses the same 36 designs, ten training laboratories, six requests and 20 rounds per valid fit. Scores are means $\pm$ sample SD over three new head-training/controller runs, conditional on one shared seed42 starting predictor per task. DTI freezes the prior TAPB encoder; protein refits the complete observed-response head or a residual from all original inputs. Both proposer models and both GP offsets are retained. Bold marks the best means, including ties, not significance. These retrospective warm-start studies are separate from the original end-to-end scores.}",
        r"\label{tab:expanded-recipe-results}",r"\begin{tabular}{lrrrr}",r"\toprule",
        r" & \multicolumn{2}{c}{Qwen2.5-7B} & \multicolumn{2}{c}{Luna service} \\",
        r"Policy & DTI AUROC & Protein AP & DTI AUROC & Protein AP \\",r"\midrule"]
    for policy,name in NAMES.items():
        cells=[]
        for model in ("qwen","luna"):
            for task in ("dti","protein"):
                row=report["models"][model]["tasks"][task]["policies"][policy]
                value=f"{row['heldout_mean']:.3f} \\pm {row['heldout_seed_sd']:.3f}"
                top=max(report["models"][model]["tasks"][task]["policies"][name]["heldout_mean"] for name in NAMES)
                if abs(row["heldout_mean"]-top)<1e-12:
                    value=r"\mathbf{"+value+"}"
                cells.append("$"+value+"$")
        lines.append(name+" & "+" & ".join(cells)+r" \\")
    lines += [r"\midrule",r"\multicolumn{5}{l}{\textit{Structured minus random; percentage points and conditional 95\% intervals}} \\",
              r"Proposer & DTI $\Delta$ & DTI interval & Protein $\Delta$ & Protein interval \\"]
    for model in ("qwen","luna"):
        values=[]
        for task in ("dti","protein"):
            row=report["models"][model]["tasks"][task]["contrasts"]["structured_minus_random"]
            lower,upper=row["conditional_ci95"]
            values += [f"${row['mean_pp']:+.3f}$",f"$[{lower:.3f}, {upper:.3f}]$"]
        lines.append(("Qwen" if model=="qwen" else "Luna")+" & "+" & ".join(values)+r" \\")
    lines += [r"\bottomrule",r"\end{tabular}",r"\end{table}",""]
    cost=[r"\begin{table}[htbp]",r"\centering\small",
        r"\caption{Actual candidate-cache construction and logical search budgets. Each task has 108 new fits. A fully valid six-request search uses seven fits. Different heads have different parameter counts and FLOPs; optimizer steps and example exposures are matched. Historical initial-predictor fitting, feature extraction, the 110-fit development pilot and interrupted engineering controller runs are reported separately in the provenance.}",
        r"\label{tab:expanded-recipe-cost}",r"\begin{tabular}{lrrrr}",r"\toprule",
        r"Task & Fits & Fit seconds & Steps/search & Exposures/search \\",r"\midrule"]
    for task,name in (("dti","DTI"),("protein","Protein")):
        row=report["verification"][task]
        if len(row["optimizer_steps"])!=1 or len(row["examples"])!=1:
            raise ValueError("Training budgets differ between candidates")
        cost.append(f"{name} & 108 & {row['training_seconds']:.1f} & {7*row['optimizer_steps'][0]:,} & {7*row['examples'][0]:,} "+r"\\")
    cost += [r"\bottomrule",r"\end{tabular}",r"\end{table}",""]
    usage={}
    for model in ("qwen","luna"):
        paths=sorted((SEARCH/model/"backend").rglob("call_*.json"))
        calls=[read(path) for path in paths]
        usage[model]=dict(physical_calls=len(calls),input_tokens=sum(row.get("input_tokens") or 0 for row in calls),
            output_tokens=sum(row.get("output_tokens") or 0 for row in calls),
            generation_seconds=sum(row.get("generation_seconds") or 0 for row in calls),
            token_scope="includes CLI context overhead" if model=="luna" else "local supplied chat-template input",
            invalid_slots={task:{arm:sum(read(SEARCH/model/task/f"seed{seed}/selections.json")[arm]["invalid_slots"]
                for seed in protocol["seeds"]) for arm in ("direct","raw","structured")} for task in protocol["tasks"]},
            call_receipt_hashes={str(path):sha(path) for path in paths})
    pilot=[]
    parent=PROJECT/"results/recipe_expansion_20261110/v1"
    for path in sorted(parent.glob("*/fits/seed*/*/summary.json")):
        row=read(path)
        pilot.append({k:row[k] for k in ("task","seed","design_id","device","seconds")})
    if len(pilot)!=110:
        raise ValueError("Pilot cost omitted")
    engineering={}
    for name,path in (("qwen_uncompressed",CACHE/"search/backend"),
                      ("luna_original_transport",PROJECT/"results/recipe_expansion_20261110/luna_v1/backend")):
        old_calls=list(path.rglob("call_*.json"))
        rows=[read(p) for p in old_calls]
        engineering[name]=dict(charged_attempt_receipts=len(old_calls),
            measured_output_tokens=sum(row.get("output_tokens") or 0 for row in rows),
            input_token_preflight_failures=sum((row.get("input_tokens") or 0)>28000 for row in rows),
            raw_transport_directories=len(list(path.rglob("transport_*"))) if "luna" in name else 0,
            complete_scientific_replications=0,
            receipt_hashes={str(p):sha(p) for p in old_calls})
    evaluation_features={}
    for task in protocol["tasks"]:
        folder=CACHE/"evaluation_compact"/task
        receipt=read(folder/"features_receipt.json")
        if sha(folder/"test.npz")!=receipt["feature_sha256"] or sha(receipt["source_path"])!=receipt["source_sha256"]:
            raise ValueError("Final scoring cohort/features changed")
        if receipt["authorized_sha256"]!=sha(CACHE/"evaluation_compact/authorization.json"):
            raise ValueError("Feature extraction did not bind final authorization")
        evaluation_features[task]=receipt
    summary=dict(report,physical_llm_usage=usage,development_pilot=pilot,engineering_controller_attempts=engineering,
        common_start_costs=protocol["base_bindings"],
        feature_receipts={task:read(CACHE/task/"features/receipt.json") for task in protocol["tasks"]},
        evaluation_feature_receipts=evaluation_features,
        physical_llm_calls=sum(row["physical_calls"] for row in usage.values()))
    payloads={"aggregate_summary.json":raw_json(summary)}
    for folder in ("recipe_expansion_20261110","recipe_expansion_20261110_v2","recipe_expansion_luna_20261110",
                   "recipe_search_compact_20261110","recipe_expansion_eval_20261110"):
        for path in sorted((PROJECT/"extensions"/folder).glob("*.py")):
            payloads[path.relative_to(PROJECT).as_posix()]=path.read_bytes()
    paths=[parent/"protocol.json",CACHE/"protocol.json",SEARCH/"protocol.json",SEARCH/"analysis_registration.json",
           SEARCH/"analysis_registration_timestamp.json",CACHE/"evaluation_compact/authorization.json",
           CACHE/"search/model_binding.json"]
    paths += [CACHE/"evaluation_compact"/task/"features_receipt.json" for task in protocol["tasks"]]
    for model in ("qwen","luna"):
        for task in protocol["tasks"]:
            for seed in protocol["seeds"]:
                paths += [SEARCH/model/task/f"seed{seed}"/name for name in ("selection_seal.json","selections.json","controls.json")]
    for path in paths:
        payloads["metadata/"+path.relative_to(PROJECT/"results/recipe_expansion_20261110").as_posix()]=path.read_bytes()
    for name in ("PLAN.zh-CN.md","VERSIONS.zh-CN.md","run_search_v2.py"):
        path=PROJECT/"docs/recipe_expansion_20261110"/name
        payloads[path.relative_to(PROJECT).as_posix()]=path.read_bytes()
    for name in ("report_recipe_expansion.py","report_recipe_expansion_luna.py","report_recipe_compact.py","package_recipe_compact.py"):
        path=Path(__file__).with_name(name)
        payloads[path.relative_to(PROJECT).as_posix()]=path.read_bytes()
    payloads["README.txt"]=(
        "This is an implementation/aggregate-provenance supplement. Requires the full original BioCoLoop checkout, "
        "authorized prepared datasets, task adapters, pinned original starting models and feature caches, "
        "local Qwen2.5-7B-Instruct and compatible native/LDA Python environments; Luna runs also require access to the "
        "recorded text service. Absolute paths identify the evaluated machine. No response matrices, individual "
        "predictions, model checkpoints, weights or credentials are distributed. Engineering versions are preserved "
        "as engineering records, not independent scientific repetitions.\n").encode()
    for name,raw in payloads.items():
        assert_not_secret(raw,name)
    return summary,"\n".join(lines).encode(),"\n".join(cost).encode(),payloads


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--check",action="store_true");args=parser.parse_args()
    summary,table,cost,payloads=build()
    if args.check:
        if (DEST/"summary.json").read_bytes()!=raw_json(summary) or (TABLES/"results.tex").read_bytes()!=table or (TABLES/"resources.tex").read_bytes()!=cost:
            raise ValueError("Generated artifacts differ")
        manifest=read(DEST/"experiment_sources.manifest.json")
        if manifest["generator_sha256"]!=sha(__file__) or manifest["archive_sha256"]!=sha(DEST/"experiment_sources.zip"):
            raise ValueError("Source archive manifest differs")
        with zipfile.ZipFile(DEST/"experiment_sources.zip") as archive:
            if set(archive.namelist())!=set(payloads) or any(archive.read(name)!=raw for name,raw in payloads.items()):
                raise ValueError("Archived source content differs")
    else:
        DEST.mkdir(parents=True,exist_ok=True);TABLES.mkdir(parents=True,exist_ok=True)
        (DEST/"summary.json").write_bytes(raw_json(summary));(TABLES/"results.tex").write_bytes(table);(TABLES/"resources.tex").write_bytes(cost)
        with zipfile.ZipFile(DEST/"experiment_sources.zip","w",compression=zipfile.ZIP_DEFLATED) as archive:
            for name,raw in sorted(payloads.items()):
                info=zipfile.ZipInfo(name,date_time=(2026,11,10,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
                archive.writestr(info,raw)
        manifest=dict(status="PASS",generator_sha256=sha(__file__),archive_sha256=sha(DEST/"experiment_sources.zip"),
            archive_member_sha256={name:hashlib.sha256(raw).hexdigest() for name,raw in payloads.items()},
            summary_sha256=sha(DEST/"summary.json"),table_sha256={name:sha(TABLES/name) for name in ("results.tex","resources.tex")})
        (DEST/"experiment_sources.manifest.json").write_bytes(raw_json(manifest))
    print("COMPLETE_PAIRED_RECIPE_PACKAGE",summary["success_on_both_new_tasks"],summary["physical_llm_calls"])


if __name__=="__main__":
    main()
