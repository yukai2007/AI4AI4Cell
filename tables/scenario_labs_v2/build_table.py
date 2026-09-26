"""Build the fixed-design source ablation only from independently verified fits."""
from pathlib import Path
import csv
import hashlib
import json
import statistics

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = ROOT / 'results/scenario_labs_20260923'
ARMS = ('target15_k1', 'target60_k1', 'same_source60_k4', 'cross_scenario60_k4')
LABELS = ('VCC, limited data', 'VCC, all target data', 'VCC, same-source split', 'VCC + external studies')
SEEDS = (61, 62, 63)


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8 << 20), b''):
            h.update(block)
    return h.hexdigest()


def main():
    completion = read(OUT/'completion_v2.json')
    report = read(OUT/'heldout/independent_rescore_v2.json')
    protocol = read(OUT/'protocol.json')
    if completion['status'] != 'COMPLETE' or report['status'] != 'PASS' or completion['validated_fit_count'] != 12:
        raise ValueError('Twelve complete independently verified fits required')
    if completion['independent_rescore_sha256'] != sha(OUT/'heldout/independent_rescore_v2.json'):
        raise ValueError('Independent verification receipt changed')
    if report['results_sha256'] != sha(OUT/'heldout/results.json') or report['protocol_sha256'] != sha(OUT/'protocol.json'):
        raise ValueError('Protocol/results binding changed')
    rows = []
    for arm, label in zip(ARMS, LABELS):
        values = [report['scores'][f'seed{s}/{arm}'] for s in SEEDS]
        row = dict(arm=arm, label=label, K=protocol['arms'][arm]['k'], N=protocol['arms'][arm]['n'])
        for metric in ('macro_accuracy', 'mrr'):
            measurements = [v[metric] for v in values]
            row[metric+'_mean'] = statistics.mean(measurements)
            row[metric+'_sample_std'] = statistics.stdev(measurements)
        rows.append(row)
    best_top1 = max(r['macro_accuracy_mean'] for r in rows)
    best_mrr = max(r['mrr_mean'] for r in rows)
    body = []
    for row in rows:
        top1 = f"{100*row['macro_accuracy_mean']:.2f}\\pm{100*row['macro_accuracy_sample_std']:.2f}"
        mrr = f"{100*row['mrr_mean']:.2f}\\pm{100*row['mrr_sample_std']:.2f}"
        if row['macro_accuracy_mean'] == best_top1:
            top1 = r'\mathbf{' + top1 + '}'
        if row['mrr_mean'] == best_mrr:
            mrr = r'\mathbf{' + mrr + '}'
        body.append(f"{row['label']} & {row['K']} & {row['N']} & ${top1}$ & ${mrr}$ " + r'\\')
    caption = (r'Fixed-design source--scenario ablation on VCC. '
        r'$K$: training clients; $N$: training intervention conditions. '
        r'The two $K=4,N=60$ arms share a 15-condition VCC anchor and differ in the '
        r'sources of the other three clients. All arms use 100 rounds and the same '
        r'target evaluation. Mean $\pm$ sample SD over three seeds; best means are bold. '
        r'Cell counts and gene panels remain source-specific; protocol details are in Appendix B.')
    tex = '\n'.join([r'\begin{table}[t]', r'\centering', r'\small',
        r'\setlength{\tabcolsep}{5pt}', r'\caption{'+caption+'}',
        r'\label{tab:scenario-labs-matched}', r'\begin{tabular}{lrrrr}', r'\toprule',
        r'Training sources & $K$ & $N$ & Top-1 (\%) $\uparrow$ & MRR (\%) $\uparrow$ \\',
        r'\midrule', *body, r'\bottomrule', r'\end{tabular}', r'\end{table}', ''])
    (HERE/'table.tex').write_text(tex)
    with (HERE/'results.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    delta = 100*report['matched_k4_n60_delta']['mean']
    mrr_delta = rows[3]['mrr_mean']-rows[2]['mrr_mean']
    runtime = {name:dict(wall_seconds=v['wall_seconds'], training_seconds=v['training_seconds'], best_round=v['best_round'])
               for name,v in report['validated_fits'].items()}
    sources = {arm:read(protocol['arms'][arm]['manifest'])['client_specs'] for arm in ARMS}
    provenance = dict(status='VERIFIED', input_sha256={str(OUT/name):sha(OUT/name) for name in
        ('protocol.json','completion_v2.json','campaign.json','heldout/results.json','heldout/independent_rescore_v2.json')},
        rows=rows, same_k_same_n_top1_delta_pp=delta, same_k_same_n_mrr_delta=mrr_delta,
        fit_runtime=runtime, campaign_wall_seconds=completion['training_campaign_wall_seconds'],
        original_rescore_failure_preserved=True, original_models_predictions_unchanged=True,
        source_client_manifests=sources, table_sha256=sha(HERE/'table.tex'), generator_sha256=sha(__file__))
    (HERE/'provenance.json').write_text(json.dumps(provenance, indent=2, allow_nan=False)+'\n')
    summary = [
        '# 固定样本量的来源/场景实验室消融', '',
        '12/12 个 CPU fit 均完整100轮；seed61/62/63。原始scorer与独立prediction-only复算全部一致。', '',
        '| 配置 | K | 训练条件N | Top-1 (%) | MRR (%) |', '|---|---:|---:|---:|---:|']
    for r in rows:
        summary.append(f"| {r['label']} | {r['K']} | {r['N']} | {r['macro_accuracy_mean']*100:.2f} ± {r['macro_accuracy_sample_std']*100:.2f} | {r['mrr_mean']:.4f} ± {r['mrr_sample_std']:.4f} |")
    summary.extend(['',
        f'严格 K4/N60 对照：跨研究/场景相对同源分片 Top-1 为 {delta:+.4f} 个百分点，MRR 为 {mrr_delta:+.6f}。',
        '该固定设计对照没有证明跨场景条件自动提升Top-1；它说明需要区分数据可获得性、来源异质性与研究loop本身的增益。',
        '三个外源client依次为 Replogle/K562、Nadig/HepG2、Jiang/IFNB/K562；不是四种不同细胞系，也不是跨模态统一模型。',
        '全部arm用原VCC target-dev选择checkpoint，外源仅训练；属于target adaptation。两个K4的client0及其15个条件完全相同。',
        '匹配单位是干预条件。底层细胞总量：同源K4为77771，跨场景K4为33469；测量基因panel保持各源原配置。',
        f"原训练/评分campaign总墙钟 {completion['training_campaign_wall_seconds']:.2f} 秒（{completion['training_campaign_wall_seconds']/60:.2f} 分钟）；GPU=0，API=0。", '',
        '首次独立checker仅交叉熵浮点运算顺序错误：先升float64再除0.1，与原scorer先float32除0.1不同。',
        '新增rescore_v2复现原顺序，仍使用原1e-10容差；保留旧失败campaign，模型、预测、源抽样完全未改。',
        'completion_v2.json和independent_rescore_v2.json是最终完成与PASS凭据。', '',
        '正文输入：`\\input{tables/scenario_labs_v2/table}`。本目录未修改任何正文或其它表。', ''])
    (HERE/'summary.zh-CN.md').write_text('\n'.join(summary))
    print(json.dumps(dict(status='VERIFIED', table=str(HERE/'table.tex'), rows=rows,
                          top1_delta_pp=delta, mrr_delta=mrr_delta)))


if __name__ == '__main__':
    main()
