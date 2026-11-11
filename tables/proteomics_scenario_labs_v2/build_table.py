#!/usr/bin/env python3
"""Render all four fixed source arms over validated seeds 61-68."""
from pathlib import Path
import csv
import json
import statistics
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SEEDS = (61, 62, 63, 64, 65, 66, 67, 68)
OUTS = {
    61: ROOT / "results/proteomics_scenario_labs_20260924",
    **{
        seed: ROOT / f"results/rebuttal_round3_20261111/proteomics_sources_seed{seed}"
        for seed in SEEDS if seed != 61
    },
}
ARMS = ("target_only", "plus_decrypte", "plus_existing2", "plus_all3")
LABELS = (
    "Target study", "+ decryptE", "+ Lin + Ruprecht",
    "+ Lin + Ruprecht + decryptE",
)
sys.path.insert(0, str(ROOT / "extensions/rebuttal_round3_20261111"))
import aggregate_proteomics_8seed as aggregate

read = aggregate.read
sha = aggregate.sha
require = aggregate.require


def load(seed, checked=None):
    """Shared validator preserves and strengthens every original per-seed check.

    Seed61 uses its original study directory; later seeds use the rebuttal roots.
    The validator checks completion, independent PASS, all four arms, receipt and
    protocol hashes, fit identity, saved predictions, and the 1e-12 score agreement.
    """
    require(seed in SEEDS, "Seed outside the fixed table")
    record = aggregate.load(seed) if checked is None else checked
    require(record["out"] == OUTS[seed], "Table input directory differs")
    completion = record["status"]
    receipt = record["check"]
    protocol = record["protocol"]
    results = record["result"]
    rows = []
    for arm, label in zip(ARMS, LABELS):
        fit = record["fits"][arm]
        scores = receipt["results"][arm]["metrics"]
        official = results["scores"][arm]
        rows.append(dict(
            seed=seed, arm=arm, label=label,
            K=protocol["arms"][arm]["K"],
            N=protocol["arms"][arm]["n_train"],
            ap=scores["ap"], auroc=scores["auroc"],
            best_round=fit["best"]["round"],
            training_seconds=fit["training_seconds"],
            origin=official.get("origin", "ORIGINAL_SEED61"),
        ))
    return completion, rows


def main():
    require(
        SEEDS == aggregate.SEEDS and OUTS == aggregate.OUTS
        and ARMS == aggregate.ARMS,
        "Table and registered analysis identities differ",
    )
    checked, registration = aggregate.collect()
    analysis = read(aggregate.OUTPUT)
    require(
        analysis["status"] == "COMPLETE"
        and analysis["seeds"] == list(SEEDS)
        and analysis["n_seeds"] == 8
        and analysis["analysis"] == registration["analysis"]
        and analysis["preregistration_sha256"] == sha(aggregate.runner.REG)
        and analysis["aggregator_sha256"] == sha(aggregate.__file__)
        and analysis["input_sha256"] == aggregate.input_hashes(checked)
        and analysis["per_seed"] == {
            str(seed): checked[seed]["metrics"] for seed in SEEDS
        },
        "A current complete registered eight-seed analysis is required",
    )
    loaded = {seed: load(seed, checked[seed]) for seed in SEEDS}
    seed_rows = [row for seed in SEEDS for row in loaded[seed][1]]
    rows = []
    for index, (arm, label) in enumerate(zip(ARMS, LABELS)):
        per_seed = [loaded[seed][1][index] for seed in SEEDS]
        require(
            len({(row["K"], row["N"]) for row in per_seed}) == 1,
            "Arm definition differs across seeds",
        )
        row = dict(
            arm=arm, label=label, K=per_seed[0]["K"], N=per_seed[0]["N"],
        )
        for metric in ("ap", "auroc"):
            values = [100 * item[metric] for item in per_seed]
            base = [100 * loaded[seed][1][0][metric] for seed in SEEDS]
            differences = [value - target for value, target in zip(values, base)]
            counts = dict(
                wins=sum(value > 0 for value in differences),
                losses=sum(value < 0 for value in differences),
                ties=sum(value == 0 for value in differences),
            )
            mean = statistics.mean(values)
            sd = statistics.stdev(values)
            paired_mean = statistics.mean(differences)
            frozen = analysis["arms"][arm]["metrics"][metric]
            paired = frozen["paired_minus_target_only"]
            require(
                mean == frozen["mean"]
                and sd == frozen["sample_sd"]
                and paired_mean == paired["mean_pp"]
                and paired["by_seed_pp"] == {
                    str(seed): difference
                    for seed, difference in zip(SEEDS, differences)
                }
                and all(paired[key] == value for key, value in counts.items())
                and analysis["win_counts"][arm][metric] == counts,
                "Table summary differs from registered eight-seed analysis",
            )
            row.update({
                metric + "_mean": mean,
                metric + "_sd": sd,
                metric + "_paired_delta_pp": paired_mean,
                metric + "_paired_delta_by_seed_pp": differences,
                metric + "_mean_ci95": frozen["mean_ci95"],
                metric + "_paired_delta_ci95_pp": paired["mean_ci95_pp"],
                **{metric + "_" + key: value for key, value in counts.items()},
            })
            for item, difference in zip(per_seed, differences):
                item[metric + "_paired_delta_pp"] = difference
                for key, value in counts.items():
                    item[metric + "_" + key] = value
        rows.append(row)

    body = []
    for row in rows:
        values = []
        for metric in ("ap", "auroc"):
            value = f"{row[metric + '_mean']:.2f}"
            if row[metric + "_mean"] == max(item[metric + "_mean"] for item in rows):
                value = r"\textbf{" + value + "}"
            values.append(
                "$" + value + r"\,{\scriptstyle\pm"
                + f"{row[metric + '_sd']:.2f}" + "}$"
            )
            values.append(
                "--" if row["arm"] == ARMS[0]
                else f"${row[metric + '_paired_delta_pp']:+.2f}$"
            )
        body.append(
            f"{row['label']} & {row['K']} & {row['N']} & "
            + " & ".join(values) + r" \\"
        )
    caption = (
        r"One worker per proteomic study. The target training pool is merged "
        r"into one client; Lin, Ruprecht and decryptE each form one additional client. "
        r"$K$ counts training clients and $N$ counts training conditions. All four "
        r"fixed-design arms use 100 rounds, a common initialization within each seed, and "
        r"equal-weight evaluation over the original ten target development panels. "
        r"Scores are mean $\pm$ sample SD over seeds 61--68 on the common target held-out set, "
        r"in percent; $\Delta$ is the mean paired change from the target study alone. "
        r"Seeds 64--68 were added under an analysis fixed before their fits, "
        r"with fresh fits for every arm in those five seeds. Best means are bold."
    )
    tex = "\n".join([
        r"\begin{table}[t]",
        r"\centering",
        r"\small",
        r"\setlength{\tabcolsep}{5pt}",
        r"\caption{" + caption + "}",
        r"\label{tab:proteomics-study-clients}",
        r"\begin{tabular}{lrrrrrr}",
        r"\toprule",
        r"Training sources & $K$ & $N$ & AP $\uparrow$ & $\Delta$AP & AUROC $\uparrow$ & $\Delta$AUROC \\",
        r"\midrule",
        *body,
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
        "",
    ])
    # All eight seeds and the registered analysis have passed before any table write.
    (HERE / "table.tex").write_text(tex, encoding="utf-8")
    with (HERE / "results.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=list(seed_rows[0]), lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(seed_rows)
    deltas = {
        row["arm"]: {
            metric + "_paired_delta_pp": row[metric + "_paired_delta_pp"]
            for metric in ("ap", "auroc")
        }
        for row in rows
    }
    provenance = dict(
        status="VERIFIED", rows=rows, seed_rows=seed_rows,
        target_relative_delta_pp=deltas,
        win_counts=analysis["win_counts"],
        win_count_rule="Strict paired difference >0; losses <0; ties ==0, over all eight seeds",
        original_target_dev_panels=10,
        training_workers_one_per_study=True,
        target_train_conditions=386, seeds=list(SEEDS),
        new_fit_seeds=list(range(64, 69)),
        fresh_fit_arms_for_new_seeds=list(ARMS),
        rounds=100, proposal_slots=0,
        campaign_wall_seconds={
            seed: loaded[seed][0]["wall_seconds"] for seed in SEEDS
        },
        gpu_hours=0, api_calls=0,
        preregistration_sha256=sha(aggregate.runner.REG),
        eight_seed_analysis=str(aggregate.OUTPUT),
        eight_seed_analysis_sha256=sha(aggregate.OUTPUT),
        registered_analysis=registration["analysis"],
        input_sha256=aggregate.input_hashes(checked),
        table_sha256=sha(HERE / "table.tex"),
        results_csv_sha256=sha(HERE / "results.csv"),
        generator_sha256=sha(__file__),
    )
    (HERE / "provenance.json").write_text(
        json.dumps(provenance, indent=2, allow_nan=False) + "\n", encoding="utf-8",
    )
    text = [
        "# 蛋白组严格每研究一实验室对照",
        "",
        "四个固定配置均完成100轮，seeds 61-68，0 proposal slots，全CPU、无GPU/API。",
        "Seeds 64-68按拟合前固定的分析方案加入，四个arm均为全新拟合；61-63沿用既有注册结果。",
        "Target原十个训练分片合并为一个worker；Lin、Ruprecht、decryptE各一个worker。",
        "Checkpoint选择仍为原十个target开发panel等权AP/BCE，不以外源开发分数或test选模型。",
        "",
        "| 训练来源 | K | 训练条件N | AP (%) | ΔAP | AUROC (%) | ΔAUROC |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        text.append(
            f"| {row['label']} | {row['K']} | {row['N']} | "
            f"{row['ap_mean']:.2f} ± {row['ap_sd']:.2f} | "
            f"{row['ap_paired_delta_pp']:+.2f} | "
            f"{row['auroc_mean']:.2f} ± {row['auroc_sd']:.2f} | "
            f"{row['auroc_paired_delta_pp']:+.2f} |"
        )
    text.extend([
        "",
        "完整保存四臂和全部八个seed，包括负结果；无排除、无替换seed。",
        "results.csv每个seed行保留原有字段，并附对应arm在全部八个seed上的AP/AUROC胜、负、平计数。",
        "100,000次seed-block bootstrap，RNG seed 2026111201，双侧percentile 95%区间见eight_seed_analysis.json和provenance.json。",
        "该实验改变外源数据可获得性，不匹配总训练条件数，也不是loop消融。",
        "与先前target十片协议不同：合并后target每local epoch共7个minibatch；不混用旧协议分数。",
        "共享参数按各训练client样本数加权，source-private heads只由其所有者更新；结构、初始化与损失冻结。",
        "各seed墙钟（秒）：" + ", ".join(
            f"{seed}: {loaded[seed][0]['wall_seconds']:.2f}" for seed in SEEDS
        ),
        "",
        "独立验证使用保存预测的NumPy AP阈值公式与AUROC成对次序公式，逐项与官方scorer核对，容差1e-12。",
        r"正文输入：`\input{tables/proteomics_scenario_labs_v2/table}`。",
        "",
    ])
    (HERE / "summary.zh-CN.md").write_text("\n".join(text), encoding="utf-8")
    print(json.dumps(dict(
        status="VERIFIED", table=str(HERE / "table.tex"),
        rows=rows, deltas=deltas, win_counts=analysis["win_counts"],
    ), allow_nan=False))


if __name__ == "__main__":
    main()
