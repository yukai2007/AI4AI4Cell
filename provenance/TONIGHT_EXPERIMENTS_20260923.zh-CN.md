# 今晚单 seed 实验最终状态

**已完成：2026-09-23T19:35:18+08:00（北京时间）。**

[查看最终实验结果与分析](/liziqing/yukai/AI4AI4Cell/results/tonight_completion_20260923/final_delivery/RESULTS.zh-CN.md) · [机器可读完成凭据](/liziqing/yukai/AI4AI4Cell/results/tonight_completion_20260923/final_delivery/summary.json)

本次可执行的 diverse 数据、实验室数量、Qwen/Luna 与 loop 预算消融矩阵已完成训练、最终测试及复算；`pending_groups=[]`。

蛋白组包含两个独立外源；第三来源 decryptE 缺少处理后数据，不计入本次完成矩阵。额外 seed 按要求暂缓。

快照更新时间：2026-09-23T19:42:43+08:00。状态来自运行凭据，不以开发分数替代最终结果。

主表现有 seeds 42–44 的封存测试结果保持不变。

本队列已无运行中或待执行实验。下列 PID 是历史运行记录，不表示任务仍在运行。

## 队列完成与恢复记录

| 队列任务 | 状态 | GPU | 记录 PID |
|---|---|---|---|
| collect_ablation_delivery | 历史 BLOCKED_DEPENDENCY；已由 `collect_ablation_delivery_retry2` 完成恢复 | 3 | — |
| collect_ablation_delivery_retry2 | COMPLETE | 3 | 55845 |
| cross_plus_biosnap | COMPLETE | 0,1 | 20726 |
| cross_plus_davis | COMPLETE | 2,3 | 20746 |
| cross_plus_human | COMPLETE | 4,5 | 20729 |
| dti_development_luna | COMPLETE | 0 | 78614 |
| dti_development_qwen | COMPLETE | 0 | 86594 |
| dti_fit_d01 | COMPLETE | 0,2 | — |
| dti_fit_d01_early | COMPLETE | 2,5 | 39263 |
| dti_fit_d02 | COMPLETE | 0,2 | — |
| dti_fit_d02_early | COMPLETE | 0,3 | 43650 |
| dti_fit_d03 | COMPLETE | 4,6 | 57344 |
| dti_fit_d10 | COMPLETE | 4,6 | 127521 |
| dti_heldout_luna | COMPLETE | 0 | 88243 |
| dti_heldout_qwen | COMPLETE | 0 | 92928 |
| finalize_cross_all | 历史 FAILED；已由 `finalize_cross_all_retry2` 完成恢复 | 5 | 49892 |
| finalize_cross_all_retry2 | COMPLETE | 5 | 53934 |
| finalize_cross_individual | COMPLETE | 3 | — |
| finalize_cross_individual_early | COMPLETE | 3 | 94043 |
| finalize_cross_individual_shared | COMPLETE | 3 | — |
| finalize_lab | COMPLETE | 3 | 21328 |
| lab_k2 | COMPLETE | 1,3 | 42465 |
| lab_k5 | COMPLETE | 1,3 | — |
| lab_k5_early | COMPLETE | 1,3 | 76176 |
| plus_all_retry1 | COMPLETE | 7,5 | 76003 |
| proteomics_external | COMPLETE | 3 | 42466 |

## 真实训练进度

| 实验 | 已写出轮次 | 完整训练凭据 |
|---|---:|---|
| plus_all | 50 / 100 | 历史中断，partial 保留；已由 plus_all_retry1 完整替代，非待运行实验 |
| plus_biosnap | 100 / 100 | 已写出 |
| plus_davis | 100 / 100 | 已写出 |
| plus_human | 100 / 100 | 已写出 |
| partition_k2 | 100 / 100 | 已写出 |
| partition_k5 | 100 / 100 | 已写出 |
| plus_all_retry1 | 100 / 100 | 已写出 |

## 最终测试结果位置

- [results/proteomics_external_pilot_20260923/seed61/heldout/results.json](/liziqing/yukai/AI4AI4Cell/results/proteomics_external_pilot_20260923/seed61/heldout/results.json)：已生成；以对应 COMPLETE 凭据及评分校验为准。
- [results/tonight_completion_20260923/native_final_lab_v1/summary.json](/liziqing/yukai/AI4AI4Cell/results/tonight_completion_20260923/native_final_lab_v1/summary.json)：已生成；以对应 COMPLETE 凭据及评分校验为准。
- [results/tonight_completion_20260923/native_final_cross_single_v1/summary.json](/liziqing/yukai/AI4AI4Cell/results/tonight_completion_20260923/native_final_cross_single_v1/summary.json)：已生成；以对应 COMPLETE 凭据及评分校验为准。
- [DTI 全跨源正式结果（v2）](/liziqing/yukai/AI4AI4Cell/results/tonight_completion_20260923/native_final_cross_v2/summary.json)：已生成；以对应 COMPLETE 凭据及评分校验为准。
- [results/budget1day_20260923/native_tapb/seed42/qwen/heldout/results.json](/liziqing/yukai/AI4AI4Cell/results/budget1day_20260923/native_tapb/seed42/qwen/heldout/results.json)：已生成；以对应 COMPLETE 凭据及评分校验为准。
- [results/budget1day_20260923/native_tapb/seed42/luna/heldout/results.json](/liziqing/yukai/AI4AI4Cell/results/budget1day_20260923/native_tapb/seed42/luna/heldout/results.json)：已生成；以对应 COMPLETE 凭据及评分校验为准。

旧 `native_final_cross_v1` 是保留的失败评分现场，不是缺失实验；正式全跨源结果为 `native_final_cross_v2`。 `finalize_cross_all_retry2` 与 `collect_ablation_delivery_retry2` 均为 COMPLETE，分别恢复了旧评分失败和下游汇总阻塞。

## 口径与预算

- DTI 模型后端对照：复用严格核对源码、数据与配置的 seed42 完整缓存，补齐 D01/D02/D03/D10 后执行 Qwen/Luna、direct/loop 及预算前缀对照。候选仍训练 100 轮。
- DTI lab-count 与跨源：seed61；participation 和固定总数据量的 partition 分开报告。
- 蛋白组：目标、+Lin、+Ruprecht、+两来源四组，各有 fixed 和 loop，共八项最终测试；这是统一接口下的辅助多任务迁移 pilot，不替换原主表模型。第三来源 decryptE 尚缺处理后蛋白矩阵，不计作完成。
- 原 plus_all 的第 50 轮中断结果仅作历史记录；替代运行 plus_all_retry1 已完成 100 轮，正式分数来自 v2 最终评分及独立复算。
- 完成时刻的预算核算：八卡连续保留 171.30 GPU·小时，距 192 GPU·小时上限尚余 20.70 GPU·小时；未重置起点。硬截止为 2026-09-23T22:10:34.937665+08:00。
- 训练→开发集选择→最终测试→复算均有各自凭据。未修改原始分数或停止其它项目任务。
