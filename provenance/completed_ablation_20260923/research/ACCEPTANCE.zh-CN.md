# 三项要求验收与蛋白组独立来源核对

截止 2026-09-23。这里只读核对真实实验与原始来源；没有修改正文、旧协议、训练或 checkpoint。`references.bib` 增补两篇实际已运行来源文献。

## 1. 验收表：实验完成与论文纳入分开

更新：已实际阅读新增英文正文、附录和生成表；以下列出纳入位置。两处B.2文字纠正已由root落实并独立复读，内容PASS，记录见MANUSCRIPT_REVIEW.zh-CN.md；最终PDF视觉由root验收。

| 要求 | 实验验收 | 证据与范围 | 论文纳入验收 |
|---|---|---|---|
| Qwen2.5 与第二 research backend 对照 | 已完成 | Qwen / gpt-5.6-luna，各 5 端点、6 proposal slots、12 项同菜单；DTI seed42，其余 seed61 | 已纳入4.5、5.4、B.3与短loop表 |
| K=1/2/5/10 的实验室数量 | 已完成 | 五端点同时有 participation（增加可用数据）与 partition（固定总数据重新分片）两组 | 已纳入4.5、5.3、B.1；两种定义分开 |
| DTI ≥3 个独立外源数据集 | 已完成 | BioSNAP / Davis / Human，每源单独、三源合并、target-only 全部最终 heldout 完成 | 已纳入5.3、B.2；正负方向全报告 |
| 细胞 ≥3 个独立外源研究 | 已完成 | Replogle / Nadig / Jiang，既有源实验最终结果已汇总 | 已纳入4.5、5.3与B.2 |
| 蛋白组 ≥3 个独立外源研究 | **未完成：目前 2 个** | Lin 与 Ruprecht 已训练并评分；decryptE 仅完成处理矩阵可取性及单文件 schema 核验 | 已纳入4.5、5.3、B.2；正文与表注均明确两源 |
| 所有五端点短 loop budget 曲线 | 已完成 | 6 slots / 12 designs；两 backend；固定的 direct 与 loop 前缀均有 heldout | 已纳入5.4、B.3完整前缀曲线 |
| 更长 loop 及收敛分析 | 部分覆盖完成 | 4 个轻端点、24 slots / 36 designs，两 backend；长 DTI 没有完成的最终评分 | 已纳入5.4、B.4，明确仅四轻端点 |
| 6→24 次连续预算曲线 | 不成立 | 两个实验改变了候选空间，不能拼成仅改变 loop 次数的同一条曲线 | 已在4.5、B.3/B.4与图注分开菜单 |
| 蛋白组辅助 pilot 的 loop 正增益 | 未得到 | 4 source arms 的 fixed 与两提案 loop heldout AP/AUROC 全相同 | 已在B.2与独立fixed/loop表报告持平 |
| 整篇论文最终完成且“只差多 seed” | 本审计不签收 | 蛋白第三来源未实跑，长预算 DTI 未闭合；当前注册作业 COMPLETE 不等于所有原始要求完成 | 英文已纳入且保留真实未完成scope；最终PDF视觉由root验收 |

精确路径、状态和 SHA-256 在 `completion_snapshot.json`。DTI 最终记录是 `results/tonight_completion_20260923/native_final_lab_v1/summary.json` 与 `native_final_cross_v2/summary.json`；早期 `case_receipt.json` 的 `heldout_evaluated=false` 只是训练阶段记录。DTI partition K10 与 participation K10 采用同一十客户定义，合法复用同一结果；不是多一条独立运行。

## 2. 已执行的蛋白组辅助实验：应如何准确写入论文

这是**新增多任务共享表征的独立来源迁移附加实验**。原 PTPC 主表的输入、标签与旧结果保持原样；附加实验内部使用同一个新预测器比较 target-only 与增加外源。因此可以归因于该附加实验中的来源变化，但不能把它当成原主表架构不变的新一列分数。

| 数据来源 | 实跑条件 / drug split | 输入与原始目标 | 本地损失 |
|---|---|---|---|
| PTPC target | train386 / dev105；原10客户；heldout148 | 原6h+24h observed response 与原 binary efficacy | BCE with logits |
| Lin2026 | 28 条；20 train / 8 dev；5 / 2 drugs；4 cell contexts | 24h、10μM protein log2FC → 已发布 Ratio1/2/3 的连续均值 | MSE，不二值化 |
| Ruprecht2020 | 109 条；85 train /24 dev；17/5 drugs；5 contexts | 24h LFQ-derived log2FC → 72h或96h CTG EC50 的 log10(nM) | 区间距离平方损失 |

Ruprecht 的109个样本分为49 exact、18 approximate、42 right-censored。`~` 数值采用 factor-of-two 区间；≥10000nM或`>`作为右删失。这两项是已冻结 adapter 的分析约定，不冒充作者报告的置信区间。预测值 p 的损失为 `relu(lower-p)^2 + upper_valid * relu(p-upper)^2`。该研究的蛋白测量剂量根据 EC50 设定；虽然模型不输入 profiling dose，获得蛋白测量的实验过程仍有这种依赖，解释为同条件观测响应的辅助迁移更准确。

Lin 严格使用名称完全一致的条件，未将 HCT16 自动推断为 HCT116。每条件公共蛋白为4085–4156；Ruprecht为1921–2026。外源先按 canonical compound key 和去立体化学图匹配排除目标 development/heldout 化合物，再按药物分组划分 source train/dev；归一化只拟合 source train。

新模型共享蛋白编码器（蛋白+观测 mask→64）和药物编码器（Morgan2048→32）；target head 接两个时间点64+64及drug32，auxiliary heads 接一个时间点64、drug32及五槽context。复用 core_v3 的 local worker/aggregation，再通过 ownership wrapper 聚合 shared 参数及对应来源的 head。这里的 source-specific head 指参数归属，不表示加密或参数从不离开本地：当前 RPC 仍传全 state。

每个 fit 100 rounds；每轮新 AdamW、一个 local epoch、batch64、clip1；每5轮由目标十客户平均 AP、再以 BCE 选择 checkpoint。auxiliary dev 是诊断，不作为目标 checkpoint 选择指标。外层复用既有 proposer/四字段提案/menu/feedback/retain；每 source arm 两个 Luna 提案。

实际 target AP（×100）是 target-only34.9786、+Lin35.0122、+Ruprecht35.4985、+both35.3147。AP 点估计提高，但 Ruprecht / both 的 AUROC 分别从74.7475降至74.2785/74.1703。已有固定模型药物簇 bootstrap 区间均包含0；这是已训练模型的条件抽样区间，不是跨seed不确定性。完整正、负、零结果应一起写。

## 3. 新增引用与原始来源

主 `paper/references.bib` 已加入两项：

- `Lin2026HDAC`：Chuwei Lin等，Communications Biology 9:176，2026-01-28。DOI虽然含2025，发表年份是2026。[原文](https://www.nature.com/articles/s42003-025-09455-0)。Source Data `sup fig 1b`提供本实验实际使用的三个 Ratio 列；原文 figure 与 methods 的 viability replicate 描述有差别，因此这里写“已发布的三个测量值”而不推断其额外重复设计。
- `Ruprecht2020Proteome`：Benjamin Ruprecht等，Nature Chemical Biology 16:1111–1119，2020。[原文](https://www.nature.com/articles/s41589-020-0572-3)。公开 Supplementary Data1 的 EC50、compound映射和各cell数据 sheet 对应实际 adapter。

作者列表、标题、DOI、年份均经 publisher metadata/full HTML 与已下载 supplement 核对；Lin 的 web extractor 失败后用 publisher requests HTML 读取，不依赖搜索摘要。详细原始下载链接见 `source-ledger.csv`。论文没有新增 decryptE 引用，因为它还不是已执行来源；内部 `evidence_sources.bib` 为后续接入保留准确出处。

## 4. decryptE：现在能快速闭合到哪一步

原文公开测量144种化合物的 Jurkat 18h、1/10/100/1000/10000nM蛋白剂量响应，并有匹配的连续表型；它是第三项独立研究，但不是原PTPC binary efficacy定义。[原文](https://www.nature.com/articles/s41587-024-02218-y)，[官方 MassIVE](https://massive.ucsd.edu/ProteoSAFe/QueryMSV?id=MSV000093659)。原文2024-05-07 online，正式卷43、406–415为2025。

本次有界检查成功取到 **main Jurkat proteome** 中 Vorinostat 的完整处理文件（不是另外的CLK子研究）：3,901,411bytes，7871行×37列，SHA-256为 `13933c5fb89bd6f78450657ad42abb9f8c119b02cc1e2253d84f6b7956c51131`。文件在 `/tmp/aicell_decrypte_check_h0s4tlt7/jurkat_vorinostat_ALL.txt`，官方完整URL构造及列选择规则在 `decryptE_readiness.json`。

与现有5171目标UniProt的直接交集4211；按每剂量正有限强度且unique peptides>0保留，五个剂量各有3980/3997/4005/3992/4010个有效公共蛋白。已有本地补表的 `Drug + Cell Type=Jurkat + Type=Metabolic activity + dose` 能精确对应连续代谢活动值；处理18h后还需3.5h resazurin读出，不把它当PTPC6h/24h双时间点。`.pred_class`、蛋白IC50与拟合参数不当输入，避免把后处理结论当测量。

官方main目录列出145个文件，共564,387,423bytes；与论文144化合物的关系仍需核对。全取超出本次200MB限制，故只下载约3.9MB用于schema验证，没有全量准备或训练。

最小后续实现：在**新版本附加实验**中加入一个连续代谢活动 head（MSE）；保持PTPC目标与shared trainer/loop，蛋白正值取log2并保留missing mask；按药物作target身份排除/source分组和train-only归一化；完整冻结source文件清单与schema；增加配对target-only、+decryptE及+三源的训练/heldout评分。原2源结果不覆盖、不追写。先对145/144文件与化学身份做闭包，再确定实际样本量，不能用144×5直接声称可训练720条。

工程上已解除“公开蛋白矩阵不知如何获取”的阻塞；该pilot原12次完整fit只记录约273.5秒训练，新增一源的GPU算力不大可能是主瓶颈。但矩阵下载/闭包/adapter/冻结协议尚未完成，因此本次**不能签署当天三源已经闭合或只剩多seed**。下一轮有明确可实现路线，无须替换PTPC主任务，也不能保证加入第三源后分数必涨。

## 5. 文件清单与核验范围

- `review-plan.md`：先建立的有界范围与停止条件。
- `source-ledger.csv`：14条原始/执行证据记录。
- `claim-evidence-matrix.csv`：逐项verified/unsupported/pending，未将候选来源写成完成结果。
- `completion_snapshot.json`：读出的真实状态、菜单大小、seed、结果SHA和蛋白源统计。
- `decryptE_readiness.json`：公开单文件完整schema与剩余接口工作。
- `evidence_artifacts.bib` / `evidence_sources.bib`：内部证据索引；主文只新增两篇实际来源。

已更新上表实际纳入位置，没有将未完成实验改成完成。本审计没有启动训练，没有因结果优劣筛选已运行source arms，也没有修改主表或旧科学输入。
