# 蛋白组严格每研究一实验室对照

四个固定配置均完成100轮，seeds 61-68，0 proposal slots，全CPU、无GPU/API。
Seeds 64-68按拟合前固定的分析方案加入，四个arm均为全新拟合；61-63沿用既有注册结果。
Target原十个训练分片合并为一个worker；Lin、Ruprecht、decryptE各一个worker。
Checkpoint选择仍为原十个target开发panel等权AP/BCE，不以外源开发分数或test选模型。

| 训练来源 | K | 训练条件N | AP (%) | ΔAP | AUROC (%) | ΔAUROC |
|---|---:|---:|---:|---:|---:|---:|
| Target study | 1 | 386 | 34.60 ± 3.73 | +0.00 | 72.06 ± 1.93 | +0.00 |
| + decryptE | 2 | 881 | 37.39 ± 2.64 | +2.79 | 74.14 ± 1.48 | +2.09 |
| + Lin + Ruprecht | 3 | 491 | 34.30 ± 4.88 | -0.30 | 72.24 ± 2.03 | +0.18 |
| + Lin + Ruprecht + decryptE | 4 | 986 | 36.82 ± 2.90 | +2.22 | 74.13 ± 1.74 | +2.07 |

完整保存四臂和全部八个seed，包括负结果；无排除、无替换seed。
results.csv每个seed行保留原有字段，并附对应arm在全部八个seed上的AP/AUROC胜、负、平计数。
100,000次seed-block bootstrap，RNG seed 2026111201，双侧percentile 95%区间见eight_seed_analysis.json和provenance.json。
该实验改变外源数据可获得性，不匹配总训练条件数，也不是loop消融。
与先前target十片协议不同：合并后target每local epoch共7个minibatch；不混用旧协议分数。
共享参数按各训练client样本数加权，source-private heads只由其所有者更新；结构、初始化与损失冻结。
各seed墙钟（秒）：61: 76.18, 62: 92.05, 63: 95.54, 64: 156.93, 65: 156.76, 66: 156.79, 67: 156.82, 68: 156.79

独立验证使用保存预测的NumPy AP阈值公式与AUROC成对次序公式，逐项与官方scorer核对，容差1e-12。
正文输入：`\input{tables/proteomics_scenario_labs_v2/table}`。
