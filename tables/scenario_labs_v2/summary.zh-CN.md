# 固定样本量的来源/场景实验室消融

12/12 个 CPU fit 均完整100轮；seed61/62/63。原始scorer与独立prediction-only复算全部一致。

| 配置 | K | 训练条件N | Top-1 (%) | MRR |
|---|---:|---:|---:|---:|
| VCC, limited data | 1 | 15 | 29.36 ± 0.26 | 0.5697 ± 0.0019 |
| VCC, all target data | 1 | 60 | 29.43 ± 0.09 | 0.5600 ± 0.0009 |
| VCC, same-source split | 4 | 60 | 30.70 ± 0.42 | 0.5624 ± 0.0004 |
| VCC + external studies | 4 | 60 | 28.82 ± 0.00 | 0.5630 ± 0.0000 |

严格 K4/N60 对照：跨研究/场景相对同源分片 Top-1 为 -1.8796 个百分点，MRR 为 +0.000602。
该固定设计对照没有证明跨场景条件自动提升Top-1；它说明需要区分数据可获得性、来源异质性与研究loop本身的增益。
三个外源client依次为 Replogle/K562、Nadig/HepG2、Jiang/IFNB/K562；不是四种不同细胞系，也不是跨模态统一模型。
全部arm用原VCC target-dev选择checkpoint，外源仅训练；属于target adaptation。两个K4的client0及其15个条件完全相同。
匹配单位是干预条件。底层细胞总量：同源K4为77771，跨场景K4为33469；测量基因panel保持各源原配置。
原训练/评分campaign总墙钟 2169.07 秒（36.15 分钟）；GPU=0，API=0。

首次独立checker仅交叉熵浮点运算顺序错误：先升float64再除0.1，与原scorer先float32除0.1不同。
新增rescore_v2复现原顺序，仍使用原1e-10容差；保留旧失败campaign，模型、预测、源抽样完全未改。
completion_v2.json和independent_rescore_v2.json是最终完成与PASS凭据。

正文输入：`\input{tables/scenario_labs_v2/table}`。本目录未修改任何正文或其它表。
