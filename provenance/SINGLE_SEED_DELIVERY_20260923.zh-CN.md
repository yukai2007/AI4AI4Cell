# 单日预算下的论文交付状态（2026-09-23）

## 当前结论

**本轮已经挂起的 diverse 数据、lab 数量、研究模型及 loop 消融全部完成。** 最终汇总于北京时间 **2026-09-23 19:35** 写出，七个实验模块均为 `COMPLETE`，队列中没有待跑或运行中的实验。新增重复 seed 未列为本轮完成条件。

完整分数、每个 loop 前缀、轨迹与来源哈希见 [实验汇总](../../results/tonight_completion_20260923/final_delivery/RESULTS.zh-CN.md) 和 [机器可读结果](../../results/tonight_completion_20260923/final_delivery/summary.json)。后者 SHA-256：`8eb30ad05acaf714dbaa8c180a0657dcd9bc6c8b9bebccba620f097159eb7541`。

**仍有两点需要在后续论文整合中明确：蛋白组只有两个独立外源；loop 的收益目前并非跨任务普遍成立。** 本轮完成的是已定义、数据可用的实验矩阵，不将缺失的第三蛋白组来源计作完成。

## 1. 不同来源的数据：真实 held-out 结果

### DTI：三个独立外源及联合来源

原生 TAPB 模型，seed61，每项完整训练 100 轮，同一目标测试集与 scorer。以下差值均为 AUROC 百分点。

| 来源设置 | AUROC（%） | 相对 target-only |
|---|---:|---:|
| Target-only | 85.4719 | — |
| + BIOSNAP | 82.4383 | −3.0336 |
| + Davis | 87.8573 | +2.3854 |
| + Human | **87.9497** | +2.4778 |
| + 全部三个外源 | 84.2952 | −1.1767 |

Davis 与 Human 在这组配对实验中提高了目标 AUROC；BIOSNAP 和全部来源联合出现负迁移。AP、MCC、accuracy、log loss 也已记录并独立复算，不仅保留 AUROC。

正式完整结果：[native_final_cross_v2/summary.json](../../results/tonight_completion_20260923/native_final_cross_v2/summary.json)。

### Cell：VCC + 三个独立 collection

Replogle、Nadig、Jiang 三个独立外源，target-only、三个单外源和联合外源，共 5 个条件 × seeds61–63 = 15 项结果均完成。Jiang 将目标 macro Top-1 从 **29.4853% 提升至 33.0680%（+3.5827 个百分点）**；其他两个单外源和联合外源的负迁移同样完整保留。

### Proteomics：两个独立外源 pilot

Lin、Ruprecht 两个外源，4 个来源设置各自 fixed/loop，共 8 项最终测试完成。12 个候选均训练 100 轮，8 次真实 Luna 调用完成。新增多任务共享编码器与来源专属 head 使用同架构 target-only 配对对照，作为补充实验，不替换原主表模型。

| 来源设置 | Fixed AP（%） | 两步 Loop AP（%） | 相对 target-only（百分点） |
|---|---:|---:|---:|
| Target-only | 34.9786 | 34.9786 | — |
| + Lin | 35.0122 | 35.0122 | +0.0336 |
| + Ruprecht | **35.4985** | **35.4985** | +0.5199 |
| + 两来源 | 35.3147 | 35.3147 | +0.3361 |

外源 AP 点估计小幅提升，配对 bootstrap 区间跨零；该 pilot 中 loop 与 fixed 的 AP 持平。第三来源 decryptE 的公开处理矩阵已核验可下载，目标蛋白交集和标签对应已确认；尚未完成全量接入及训练，未计入已完成来源。详细结果：[蛋白组 pilot 报告](../../results/proteomics_external_pilot_20260923/RESULT.zh-CN.md)。

## 2. DTI 实验室数量：两个问题分开比较

所有设置均为 seed61、完整 100 轮训练，并使用同一 held-out scorer。

| 设置 | K=1 | K=2 | K=5 | K=10 |
|---|---:|---:|---:|---:|
| Participation：增加参与实验室及可用数据，AUROC（%） | 83.6457 | 84.4298 | 89.6212 | **93.8838** |
| Partition：总数据固定，改变划分数，AUROC（%） | 85.4719 | 88.9625 | 88.0465 | **93.8838** |

Participation 的 K=1→10 提升为 **10.2381 个百分点**。固定数据量的 partition 结果也随划分变化，且 K=2→5 并非单调；因此两条曲线分别呈现，不把全部变化归因于数据量。K=1、K=10 的等价训练复用已有逐项凭据，不作为额外独立重复。

正式结果：[native_final_lab_v1/summary.json](../../results/tonight_completion_20260923/native_final_lab_v1/summary.json)。

## 3. 研究模型与 loop：已完整测完，收益按场景陈述

- **四个轻任务**：ProteinTalks、VCC、Norman、Tahoe；Qwen/Luna；short6 与 long24 共 16 组均完成，并保留各自预设预算前缀及完整开发轨迹。两种协议的设计空间不同，分开分析。
- **DTI**：12 个 seed42、100-round 候选全部齐备，其中 8 个经源码、数据和配置等价核验复用，D01/D02/D03/D10 新完成。Qwen/Luna 各 direct/loop、预算 0/1/2/4/6，共 20 项前缀测试全部完成并独立复算。seed42 按缓存可用性选定。

| DTI 研究模型 | Direct AUROC（%） | Loop AUROC（%） | Loop − Direct（百分点） |
|---|---:|---:|---:|
| Qwen | 94.2679 | 94.2679 | 0.0000 |
| Luna | 94.6000 | 94.2679 | −0.3321 |

轻任务 short6 中，Norman/Luna 的 loop 提升 **0.8148 个百分点**，其余 7 组终点持平。long24 中，7 组终点持平，VCC/Luna 为 −0.2228 个百分点。Norman/Luna 的 long24 loop 在第 4 个槽达到共同开发目标，direct 为第 22 个槽，体现这组实验的搜索效率收益，而非终点精度差。

当前证据支持研究不同任务上的搜索效率、有效来源和负迁移；**loop 的跨任务稳定精度收益仍是论文需要加强的核心点，不只是补 seed 的问题。**

独立核验：[轻任务 loop 汇总](../../results/tonight_completion_20260923/audit/loop_completed_summary.zh-CN.md)、[DTI 20 项前缀复算](../../results/tonight_completion_20260923/audit/dti_loop_completed_rescore.json)。

## 4. 完成凭据、预算与恢复记录

- 训练、开发选择、封存测试和独立复算均完成；DTI 5 个二分类指标独立复算通过，cell/proteomics 共 23 项已完成结果也已复算。
- 原联合外源训练在第 50 轮中断，旧 partial 保留；`plus_all_retry1` 从原 seed61 初始化完整重训 100 轮，现已正式评分。
- 最后一次评分的 checkpoint 复制遇到磁盘配额不足；仅将本次失败评分产生的约 95 MiB 临时副本移至 `/tmp/ai4ai4cell-scoring-quota-20260923.v3kO2z`，逐文件核对移动前后哈希。原始训练模型未删除或修改。
- 正式恢复评分目录为 `native_final_cross_v2`。它使用已完成 checkpoint 的硬链接避免重复占空间；内容哈希在评分前后核对，选择逻辑、原 scorer 与独立复算不变。旧失败记录及 [存储恢复凭据](../../results/tonight_completion_20260923/native_final_cross_v1/quota_recovery.json) 保留；`finalize_cross_all_retry2` 与 `collect_ablation_delivery_retry2` 均以退出码 0 完成。
- 预算起点保持 2026-09-22 22:10:34，硬截止 2026-09-23 22:10:34。本轮于 19:35 完成，约 **171.30 GPU·小时**（八卡连续保留的保守口径；不等同于实际活跃 GPU 时长；历史缓存训练开销另计），在 192 GPU·小时上限内。

## 5. 论文文件状态

主表现有 seeds42–44 的五个endpoint数值保持不变。后续整合已将本轮完整结果写入§4.5、§5.3–5.4及Appendix B，新增生成表、完整预算曲线、配置菜单和504槽提案轨迹。图2已替换为用户提供PPT的矢量版，英文PDF与中文版均重新构建；最终校验与Git同步状态以 `completed_ablation_20260923/build_receipt.json` 和交付说明为准。

正文整合重点是：增加独立来源和 K 敏感性证据，分开讲述数据参与、来源适配与 loop 搜索效率；同时落实 loop 增益偏弱这一实际发现。第三个蛋白组独立外源仍需全量下载、适配和训练；DTI长24槽不属于本次已完成短6槽协议。
