"""Independently rescore the sealed expanded recipes and report every policy."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import sys

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score

PAPER=Path(__file__).resolve().parents[1]
PROJECT=PAPER.parent
sys.path.insert(0,str(PROJECT))
from extensions.recipe_expansion_20261110_v2.common import OUT,checked,dump,read,sha
from extensions.recipe_expansion_20261110_v2.evaluate import verify_seals,check_authorization

BOOTSTRAPS=2000
BOOTSTRAP_SEED=20261110
POLICIES=("fixed_D00","direct","raw","structured","random","gp_ei")
CELL=PAPER/"provenance/fbhk_followup_20261109/policy_summary.json"


def weighted_metrics(y,probability,weights,task):
    """Vectorized weighted AP/AUROC, including exact score ties."""
    y=np.asarray(y,np.float64)
    p=np.asarray(probability,np.float64)
    w=np.asarray(weights,np.float64)
    if w.ndim==1:
        w=w[None,:]
    if w.shape[1]!=len(y) or p.shape!=y.shape or not np.isfinite(w).all() or (w<0).any():
        raise ValueError("Invalid resampling weights")
    order=np.argsort(p,kind="stable")
    if task=="protein":
        order=order[::-1]
    sorted_p=p[order]
    starts=np.r_[0,np.flatnonzero(np.diff(sorted_p))+1]
    positive=w[:,order]*y[order]
    negative=w[:,order]*(1-y[order])
    pg=np.add.reduceat(positive,starts,axis=1)
    ng=np.add.reduceat(negative,starts,axis=1)
    total_p=pg.sum(1)
    total_n=ng.sum(1)
    valid=(total_p>0)&(total_n>0)
    if task=="dti":
        preceding=np.cumsum(ng,axis=1)-ng
        numerator=(pg*(preceding+.5*ng)).sum(1)
        value=np.divide(numerator,total_p*total_n,out=np.full(len(w),np.nan),where=valid)
    else:
        tp=np.cumsum(pg,axis=1)
        rows=np.cumsum(pg+ng,axis=1)
        precision=np.divide(tp,rows,out=np.zeros_like(tp),where=rows>0)
        numerator=(pg*precision).sum(1)
        value=np.divide(numerator,total_p,out=np.full(len(w),np.nan),where=valid)
    return value


def register(out=OUT):
    checked(out)
    value=dict(schema="expanded-recipes-analysis-v1",source_sha256=sha(__file__),
        protocol_sha256=sha(out/"protocol.json"),bootstraps=BOOTSTRAPS,bootstrap_seed=BOOTSTRAP_SEED,
        primary_contrast="structured minus exact random, paired mean across all three registered seeds, per task",
        secondary_policies=list(POLICIES),
        resampling=dict(dti="original test rows, conditional on the fixed predictors; not independent protein/drug resampling",
                        protein="compound clusters shared by all methods and seeds"),
        interval="two-sided percentile 95%; fixed-model test-sample uncertainty, not new backbone/controller repetitions",
        comparison="Expected selected single-model score for random search; never an average-prediction ensemble",
        original_cell_summary_sha256=sha(CELL),
        success="positive mean structured-minus-random on both new tasks; existing cell positive point estimate reported separately, including its interval",
        test_result_used_to_choose_recipe=False)
    path=out/"analysis_registration.json"
    dump(path,value,frozen=True)
    stamp=out/"analysis_registration_timestamp.json"
    if not stamp.exists():
        dump(stamp,dict(registered_utc=datetime.now(timezone.utc).isoformat(),
                       registration_sha256=sha(path),test_evaluation_started=(out/"evaluation/authorization.json").exists()),frozen=True)
    print("ANALYSIS_REGISTERED",sha(path))


def policy_weights(selections,controls,menu):
    weights={"fixed_D00":{"D00":1.}}
    for arm in ("direct","raw","structured"):
        weights[arm]={selections[arm]["design_id"]:1.}
    weights["gp_ei"]={controls["gp_ei"]["design_id"]:1.}
    for name,value in controls.items():
        if "weights" in value:
            weights[name]=value["weights"]
    if not all(abs(sum(value.values())-1)<1e-12 and set(value)<=set(menu) for value in weights.values()):
        raise ValueError("Invalid sealed policy probability")
    return weights


def final_report(out=OUT):
    protocol=check_authorization(out)
    analysis=read(out/"analysis_registration.json")
    if analysis["source_sha256"]!=sha(__file__) or analysis["protocol_sha256"]!=sha(out/"protocol.json"):
        raise ValueError("Frozen analysis differs")
    if read(out/"analysis_registration_timestamp.json")["test_evaluation_started"]:
        raise ValueError("Analysis was not registered before held-out authorization")
    tasks={}
    sources={str(out/"protocol.json"):sha(out/"protocol.json"),str(CELL):sha(CELL)}
    for task in protocol["tasks"]:
        folder=out/"evaluation"/task
        report=read(folder/"scores.json")
        query=dict(np.load(folder/"test.npz",allow_pickle=False))
        y=query["y"]
        groups,inverse=np.unique(query["group"],return_inverse=True)
        rng=np.random.default_rng(BOOTSTRAP_SEED)
        counts=rng.multinomial(len(groups),np.ones(len(groups))/len(groups),size=BOOTSTRAPS)
        boot_weights=counts[:,inverse].astype(np.float32)
        del counts
        policy_values={}
        policy_boot={}
        policy_development={}
        selection_ids={}
        candidate_checks=[]
        costs=[]
        for seed in protocol["seeds"]:
            search=out/"search"/task/f"seed{seed}"
            selections,controls=read(search/"selections.json"),read(search/"controls.json")
            weights=policy_weights(selections,controls,protocol["candidates"])
            grid=read(out/task/f"seed{seed}/development_grid.json")
            values,replicates={},{}
            for identifier in protocol["candidates"]:
                path=folder/f"seed{seed}_{identifier}_probability.npy"
                probability=np.load(path,allow_pickle=False)
                metadata=report["scores"][str(seed)][identifier]
                if sha(path)!=metadata["prediction_sha256"]:
                    raise ValueError("Saved prediction changed")
                actual=float(roc_auc_score(y,probability) if task=="dti" else average_precision_score(y,probability))
                if abs(actual-metadata["metrics"]["primary"])>1e-12:
                    raise ValueError("Independent score differs")
                if sha(grid[identifier]["checkpoint"])!=grid[identifier]["checkpoint_sha256"]:
                    raise ValueError("Fitted checkpoint changed")
                selected=max((point for point in grid[identifier]["trajectory"] if "development" in point),
                             key=lambda point:(point["development"]["primary"],-point["development"]["loss"]))
                if selected["round"]!=grid[identifier]["best_round"] or selected["development"]!=grid[identifier]["development"]:
                    raise ValueError("Development checkpoint selection changed")
                values[identifier]=actual
                replicates[identifier]=weighted_metrics(y,probability,boot_weights,task)
                parity=weighted_metrics(y,probability,np.ones(len(y)),task)[0]
                if abs(parity-actual)>1e-12:
                    raise ValueError("Weighted bootstrap scorer does not reproduce ordinary score")
                candidate_checks.append(dict(seed=seed,design_id=identifier,primary=actual,checkpoint_round=selected["round"]))
                costs.append({key:grid[identifier][key] for key in
                              ("seconds","actual_optimizer_steps","actual_examples_seen","trainable_parameters")})
            for name,w in weights.items():
                policy_values.setdefault(name,[]).append(sum(weight*values[identifier] for identifier,weight in w.items()))
                policy_development.setdefault(name,[]).append(sum(weight*grid[identifier]["development"]["primary"] for identifier,weight in w.items()))
                policy_boot.setdefault(name,[]).append(sum(weight*replicates[identifier] for identifier,weight in w.items()))
                selection_ids.setdefault(name,[]).append(dict(seed=seed,weights=w))
            sources[str(search/"selection_seal.json")]=sha(search/"selection_seal.json")
        rows={}
        for name,values in policy_values.items():
            draws=np.mean(policy_boot[name],axis=0)
            draws=draws[np.isfinite(draws)]
            rows[name]=dict(heldout_mean=100*statistics.mean(values),heldout_seed_sd=100*statistics.stdev(values),
                per_seed_heldout=[100*value for value in values],development_mean=100*statistics.mean(policy_development[name]),
                conditional_ci95=(100*np.quantile(draws,[.025,.975])).tolist(),valid_bootstraps=len(draws),
                selections=selection_ids[name])
        contrasts={}
        for comparator in ("random","direct","raw","gp_ei"):
            delta=np.asarray(policy_values["structured"])-np.asarray(policy_values[comparator])
            draws=np.mean(np.asarray(policy_boot["structured"])-np.asarray(policy_boot[comparator]),axis=0)
            draws=draws[np.isfinite(draws)]
            contrasts["structured_minus_"+comparator]=dict(mean_pp=100*float(delta.mean()),
                conditional_ci95=(100*np.quantile(draws,[.025,.975])).tolist(),
                per_seed_pp=(100*delta).tolist(),wins=int((delta>1e-12).sum()),
                ties=int((np.abs(delta)<=1e-12).sum()),losses=int((delta < -1e-12).sum()),valid_bootstraps=len(draws))
        tasks[task]=dict(policies=rows,contrasts=contrasts,candidate_checks=candidate_checks,
            fitted_candidates=len(costs),all_candidate_training_seconds=sum(row["seconds"] for row in costs),
            optimizer_steps_per_candidate=sorted({row["actual_optimizer_steps"] for row in costs}),
            exposures_per_candidate=sorted({row["actual_examples_seen"] for row in costs}),
            trainable_parameter_range=[min(row["trainable_parameters"] for row in costs),max(row["trainable_parameters"] for row in costs)],
            bootstrap_unit=analysis["resampling"][task],test_rows=len(y),test_clusters=len(groups))
        sources[str(folder/"scores.json")]=sha(folder/"scores.json")
        print(task,"VERIFIED",contrasts["structured_minus_random"],flush=True)
    cell=read(CELL)
    result=dict(schema="expanded-recipes-complete-report-v1",status="COMPLETE",tasks=tasks,
        success_on_both_new_tasks=all(task["contrasts"]["structured_minus_random"]["mean_pp"]>0 for task in tasks.values()),
        existing_cell_reference=cell["policies"]["structured"],
        existing_cell_contrast=cell["paired_primary_differences"],
        interpretation=analysis["interval"],new_fits=216,development_pilot_fits=110,
        old_tests_previously_exposed=True,new_blind_biological_split=False,
        source_bindings=sources,analysis_sha256=sha(out/"analysis_registration.json"))
    dump(out/"final_report.json",result,frozen=True)
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("command",choices=("register","report"))
    parser.add_argument("--out",type=Path,default=OUT)
    args=parser.parse_args()
    if args.command=="register":
        register(args.out)
    else:
        report=final_report(args.out)
        print(json.dumps(dict(status=report["status"],success=report["success_on_both_new_tasks"]),indent=2))


if __name__=="__main__":
    main()
