"""One independent score/paired-bootstrap pass for both sealed proposer models."""
import argparse
from datetime import datetime,timezone
from pathlib import Path
import statistics
import sys

import numpy as np
from sklearn.metrics import roc_auc_score,average_precision_score

PAPER=Path(__file__).resolve().parents[1]
PROJECT=PAPER.parent
sys.path.insert(0,str(PROJECT))
from extensions.recipe_expansion_20261110_v2.common import OUT as CACHE,checked,read,dump,sha
from extensions.recipe_search_compact_20261110.runner import SEARCH,verify,verify_seals
from extensions.recipe_expansion_eval_20261110.evaluate import check_authorization
from report_recipe_expansion import weighted_metrics

CELL=PAPER/"provenance/fbhk_followup_20261109/policy_summary.json"
EVALUATOR=PROJECT/"extensions/recipe_expansion_eval_20261110/evaluate.py"
HELPER=Path(__file__).with_name("report_recipe_expansion.py")
B=2000
BOOT_SEED=20261110
POLICIES=("fixed_D00","direct","raw","structured","random","gp_ei","gp_ei_zero")


def register():
    verify()
    value=dict(schema="expanded-complete-panel-analysis-v1",source_sha256=sha(__file__),
        helper_sha256=sha(HELPER),evaluator_sha256=sha(EVALUATOR),
        training_protocol_sha256=sha(CACHE/"protocol.json"),search_protocol_sha256=sha(SEARCH/"protocol.json"),
        models=["qwen","luna"],primary="Luna structured minus exact random, all three seeds, per task",
        secondary="Complete Qwen comparison and every policy, including both GP-EI offsets; no test-based arm/model selection",
        bootstraps=B,bootstrap_seed=BOOT_SEED,
        units=dict(dti="original test rows; not independent drug/protein identity resampling",protein="compound clusters"),
        interval="two-sided percentile 95%, conditional on fixed selected predictors; not further backbone/controller runs",
        all_fits_retained=216,pilot_fits_reported_separately=110,
        original_cell_source_sha256=sha(CELL),
        success="Positive Luna structured-minus-random point estimates in both new tasks; prior cell result remains a separate protocol with its full interval")
    dump(SEARCH/"analysis_registration.json",value,frozen=True)
    if not (SEARCH/"analysis_registration_timestamp.json").exists():
        dump(SEARCH/"analysis_registration_timestamp.json",dict(registered_utc=datetime.now(timezone.utc).isoformat(),
            sha256=sha(SEARCH/"analysis_registration.json"),test_authorized=(CACHE/"evaluation_compact/authorization.json").exists()),frozen=True)
    print("COMBINED_ANALYSIS_REGISTERED",sha(SEARCH/"analysis_registration.json"))


def weights_for(selections,controls):
    result={"fixed_D00":{"D00":1.}}
    for arm in ("direct","raw","structured"):
        result[arm]={selections[arm]["design_id"]:1.}
    for name in ("gp_ei","gp_ei_zero"):
        result[name]={controls[name]["design_id"]:1.}
    for name,row in controls.items():
        if "weights" in row:
            result[name]=row["weights"]
    if any(abs(sum(w.values())-1)>1e-12 for w in result.values()):
        raise ValueError("Policy probability mass differs from one")
    return result


def report():
    protocol=check_authorization(CACHE)
    analysis=read(SEARCH/"analysis_registration.json")
    if analysis["source_sha256"]!=sha(__file__) or analysis["helper_sha256"]!=sha(HELPER) or \
            analysis["evaluator_sha256"]!=sha(EVALUATOR):
        raise ValueError("Registered analysis implementation changed")
    if read(SEARCH/"analysis_registration_timestamp.json")["test_authorized"]:
        raise ValueError("Analysis was not registered before test authorization")
    seals=verify_seals()
    models={model:dict(tasks={}) for model in ("qwen","luna")}
    verification={}
    bindings={str(CACHE/"protocol.json"):sha(CACHE/"protocol.json"),str(SEARCH/"protocol.json"):sha(SEARCH/"protocol.json"),
              str(CELL):sha(CELL),str(SEARCH/"analysis_registration.json"):sha(SEARCH/"analysis_registration.json")}
    for task in protocol["tasks"]:
        folder=CACHE/"evaluation_compact"/task
        query=dict(np.load(folder/"test.npz",allow_pickle=False))
        y=query["y"]
        groups,inverse=np.unique(query["group"],return_inverse=True)
        rng=np.random.default_rng(BOOT_SEED)
        counts=rng.multinomial(len(groups),np.ones(len(groups))/len(groups),size=B)
        boot_weights=counts[:,inverse].astype(np.float32)
        del counts
        saved=read(folder/"scores.json")
        predictions,bootstraps,grids={},{},{}
        checks,costs=[],[]
        for seed in protocol["seeds"]:
            grids[seed]=read(CACHE/task/f"seed{seed}/development_grid.json")
            predictions[seed],bootstraps[seed]={},{}
            for identifier,row in grids[seed].items():
                path=folder/f"seed{seed}_{identifier}_probability.npy"
                probability=np.load(path,allow_pickle=False)
                if sha(path)!=saved["scores"][str(seed)][identifier]["prediction_sha256"] or sha(row["checkpoint"])!=row["checkpoint_sha256"]:
                    raise ValueError("Prediction/checkpoint hash differs")
                actual=float(roc_auc_score(y,probability) if task=="dti" else average_precision_score(y,probability))
                if abs(actual-saved["scores"][str(seed)][identifier]["metrics"]["primary"])>1e-12:
                    raise ValueError("Independent primary score differs")
                selected=max((point for point in row["trajectory"] if "development" in point),
                    key=lambda point:(point["development"]["primary"],-point["development"]["loss"]))
                if selected["round"]!=row["best_round"] or selected["development"]!=row["development"]:
                    raise ValueError("Checkpoint did not follow development selection")
                if abs(weighted_metrics(y,probability,np.ones(len(y)),task)[0]-actual)>1e-12:
                    raise ValueError("Bootstrap scorer ordinary-score parity failed")
                predictions[seed][identifier]=actual
                bootstraps[seed][identifier]=weighted_metrics(y,probability,boot_weights,task)
                checks.append(dict(seed=seed,design_id=identifier,primary=actual,best_round=row["best_round"]))
                costs.append({k:row[k] for k in ("seconds","actual_optimizer_steps","actual_examples_seen","trainable_parameters")})
            print(task,seed,"36 scores/bootstraps independently verified",flush=True)
        verification[task]=dict(candidate_checks=checks,fits=len(checks),test_rows=len(y),test_groups=len(groups),
            training_seconds=sum(row["seconds"] for row in costs),
            optimizer_steps=sorted({row["actual_optimizer_steps"] for row in costs}),
            examples=sorted({row["actual_examples_seen"] for row in costs}),
            parameter_range=[min(row["trainable_parameters"] for row in costs),max(row["trainable_parameters"] for row in costs)])
        for model in ("qwen","luna"):
            values,developments,draws,identifiers={},{},{},{}
            for seed in protocol["seeds"]:
                base=SEARCH/model/task/f"seed{seed}"
                selections,controls=read(base/"selections.json"),read(base/"controls.json")
                for policy,w in weights_for(selections,controls).items():
                    values.setdefault(policy,[]).append(sum(weight*predictions[seed][identifier] for identifier,weight in w.items()))
                    developments.setdefault(policy,[]).append(sum(weight*grids[seed][identifier]["development"]["primary"] for identifier,weight in w.items()))
                    draws.setdefault(policy,[]).append(sum(weight*bootstraps[seed][identifier] for identifier,weight in w.items()))
                    identifiers.setdefault(policy,[]).append(dict(seed=seed,weights=w))
                bindings[str(base/"selection_seal.json")]=sha(base/"selection_seal.json")
            policies={}
            for policy,v in values.items():
                sample=np.mean(draws[policy],axis=0)
                sample=sample[np.isfinite(sample)]
                policies[policy]=dict(heldout_mean=100*statistics.mean(v),heldout_seed_sd=100*statistics.stdev(v),
                    per_seed_heldout=[100*x for x in v],development_mean=100*statistics.mean(developments[policy]),
                    conditional_ci95=(100*np.quantile(sample,[.025,.975])).tolist(),valid_bootstraps=len(sample),selections=identifiers[policy])
            contrasts={}
            for comparator in ("random","direct","raw","gp_ei","gp_ei_zero"):
                delta=np.asarray(values["structured"])-np.asarray(values[comparator])
                sample=np.mean(np.asarray(draws["structured"])-np.asarray(draws[comparator]),axis=0)
                sample=sample[np.isfinite(sample)]
                contrasts["structured_minus_"+comparator]=dict(mean_pp=100*float(delta.mean()),
                    per_seed_pp=(100*delta).tolist(),conditional_ci95=(100*np.quantile(sample,[.025,.975])).tolist(),
                    wins=int((delta>1e-12).sum()),ties=int((np.abs(delta)<=1e-12).sum()),losses=int((delta < -1e-12).sum()))
            models[model]["tasks"][task]=dict(policies=policies,contrasts=contrasts)
            print(model,task,contrasts["structured_minus_random"],flush=True)
        bindings[str(folder/"scores.json")]=sha(folder/"scores.json")
    cell=read(CELL)
    cell_delta=cell["paired_primary_differences"]["structured_minus_random"]
    result=dict(schema="expanded-recipes-complete-paired-model-report-v1",status="COMPLETE",models=models,
        primary_model="luna",success_on_both_new_tasks=all(models["luna"]["tasks"][task]["contrasts"]["structured_minus_random"]["mean_pp"]>0 for task in protocol["tasks"]),
        model_point_estimate_success={model:all(models[model]["tasks"][task]["contrasts"]["structured_minus_random"]["mean_pp"]>0 for task in protocol["tasks"]) for model in models},
        verification=verification,new_fits=216,development_pilot_fits=110,
        existing_cell=dict(structured=cell["policies"]["structured"],random=cell["policies"]["random"],contrast=cell_delta,
                           protocol="Separate original gene-disjoint mechanism study, not a new endpoint or fit here"),
        source_bindings=bindings,selection_seal_hashes=seals,
        old_tests_previously_exposed=True,new_blind_split=False,interval_interpretation=analysis["interval"])
    dump(SEARCH/"final_report.json",result,frozen=True)
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("command",choices=("register","report"))
    args=parser.parse_args()
    if args.command=="register":
        register()
    else:
        result=report()
        print("PRIMARY_LUNA_SUCCESS",result["success_on_both_new_tasks"])


if __name__=="__main__":
    main()
