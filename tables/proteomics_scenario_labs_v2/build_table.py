"""Render all four fixed source arms after independent saved-prediction verification."""
from pathlib import Path
import csv
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = ROOT / 'results/proteomics_scenario_labs_20260924'
ARMS = ('target_only', 'plus_decrypte', 'plus_existing2', 'plus_all3')
LABELS = ('Target study', '+ decryptE', '+ Lin + Ruprecht', '+ Lin + Ruprecht + decryptE')


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8 << 20), b''):
            h.update(block)
    return h.hexdigest()


def main():
    completion = read(OUT/'status.json')
    receipt = read(OUT/'independent_rescore.json')
    protocol = read(OUT/'protocol.json')
    results = read(OUT/'heldout/results.json')
    if completion['status'] != 'COMPLETE' or receipt['status'] != 'PASS':
        raise ValueError('Complete training and independent PASS required')
    if set(completion['completed_arms']) != set(ARMS) or not receipt['all_four_arms']:
        raise ValueError('All four prespecified source arms are required')
    if completion['independent_rescore_sha256'] != sha(OUT/'independent_rescore.json'):
        raise ValueError('Verification receipt changed')
    if receipt['protocol_sha256'] != sha(OUT/'protocol.json') or receipt['results_sha256'] != sha(OUT/'heldout/results.json'):
        raise ValueError('Frozen protocol or scores changed')
    rows = []
    for arm, label in zip(ARMS, LABELS):
        fitpath = OUT/f'fits/{arm}/fit.json'
        fit = read(fitpath)
        if fit['rounds'] != 100 or fit['seed'] != 61 or completion['fit_sha256'][arm] != sha(fitpath):
            raise ValueError('Fit metadata mismatch')
        scores = receipt['results'][arm]['metrics']
        official = results['scores'][arm]
        if sha(official['predictions']) != official['predictions_sha256']:
            raise ValueError('Saved predictions changed')
        if any(abs(scores[m]-official['metrics'][m]) > 1e-12 for m in ('ap', 'auroc')):
            raise ValueError('Prediction-level score mismatch')
        rows.append(dict(arm=arm,label=label,K=protocol['arms'][arm]['K'],
            N=protocol['arms'][arm]['n_train'],ap=scores['ap'],auroc=scores['auroc'],
            best_round=fit['best']['round'],training_seconds=fit['training_seconds']))
    body = []
    for row in rows:
        values = []
        for metric in ('ap', 'auroc'):
            value = f"{100*row[metric]:.2f}"
            if row[metric] == max(r[metric] for r in rows):
                value = r'\textbf{'+value+'}'
            values.append(value)
        body.append(f"{row['label']} & {row['K']} & {row['N']} & {values[0]} & {values[1]} " + r'\\')
    caption = (r'One worker per proteomic study. The target training pool is merged '
        r'into one client; Lin, Ruprecht and decryptE each form one additional client. '
        r'$K$ counts training clients and $N$ counts training conditions. All four '
        r'fixed-design arms use 100 rounds, the same initialization (seed 61), and '
        r'equal-weight evaluation over the original ten target development panels. '
        r'AP and AUROC are percentages on the common target held-out set; best values are bold.')
    tex = '\n'.join([r'\begin{table}[t]',r'\centering',r'\small',
        r'\setlength{\tabcolsep}{5pt}',r'\caption{'+caption+'}',
        r'\label{tab:proteomics-study-clients}',r'\begin{tabular}{lrrrr}',r'\toprule',
        r'Training sources & $K$ & $N$ & AP $\uparrow$ & AUROC $\uparrow$ \\',
        r'\midrule',*body,r'\bottomrule',r'\end{tabular}',r'\end{table}',''])
    (HERE/'table.tex').write_text(tex)
    with (HERE/'results.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader();writer.writerows(rows)
    deltas={r['arm']:{m+'_delta_pp':100*(r[m]-rows[0][m]) for m in ('ap','auroc')} for r in rows}
    provenance=dict(status='VERIFIED',rows=rows,target_relative_delta_pp=deltas,
        original_target_dev_panels=10,training_workers_one_per_study=True,
        target_train_conditions=386,seed=61,rounds=100,proposal_slots=0,
        campaign_wall_seconds=completion['wall_seconds'],cpu_seconds=completion['cpu_seconds'],
        gpu_hours=0,api_calls=0,input_sha256={str(OUT/f):sha(OUT/f) for f in
        ('protocol.json','binding.json','status.json','heldout/results.json','independent_rescore.json')},
        table_sha256=sha(HERE/'table.tex'),generator_sha256=sha(__file__))
    (HERE/'provenance.json').write_text(json.dumps(provenance,indent=2,allow_nan=False)+'\n')
    text=['# 蛋白组严格每研究一实验室对照','',
        '四个预先固定配置均完成100轮，seed61，0 proposal slots，全CPU、无GPU/API。',
        'Target原十个训练分片合并为一个worker；Lin、Ruprecht、decryptE各一个worker。',
        'Checkpoint选择仍为原十个target开发panel等权AP/BCE，不以外源开发分数或test选模型。',
        '','| 训练来源 | K | 训练条件N | AP (%) | AUROC (%) |','|---|---:|---:|---:|---:|']
    for r in rows:
        text.append(f"| {r['label']} | {r['K']} | {r['N']} | {100*r['ap']:.2f} | {100*r['auroc']:.2f} |")
    text.extend(['','完整保存四臂，无按test高低筛选。该实验改变外源数据可获得性，不匹配总训练条件数，也不是loop消融。',
        '与先前target十片协议不同：合并后target每local epoch共7个minibatch；不把旧协议分数混用为同一对照。',
        '共享参数按各训练client样本数加权，source-private heads只由其所有者更新；结构、初始化与损失保持冻结。',
        f"总墙钟 {completion['wall_seconds']:.2f} 秒；CPU {completion['cpu_seconds']:.2f} 秒。",'',
        '独立验证使用保存预测的NumPy AP分数阈值公式与AUROC成对次序公式，逐项与官方scorer核对，容差1e-12。',
        '正文输入：`\\input{tables/proteomics_scenario_labs_v2/table}`。',''])
    (HERE/'summary.zh-CN.md').write_text('\n'.join(text))
    print(json.dumps(dict(status='VERIFIED',table=str(HERE/'table.tex'),rows=rows,deltas=deltas)))


if __name__ == '__main__':
    main()
