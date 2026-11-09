# BioCoLoop rebuttal 推进记录：panel 反馈修复

日期：2026-11-10（Asia/Shanghai）。接续 `paper/REBUTTAL_HANDOFF_20261110.zh-CN.md`；旧源码、旧结果和测试分数保持原样。

本轮完成交接中的第一个 P0：在新目录 `extensions/panel_feedback_20261110/` 联动修复 source-defined 细胞/蛋白 adapter、单 target worker 外层 reducer 和历史卡投影。保留真实 panel ID、primary/loss、最差 panel、描述性 SD/range，明确 4 training labs / 10 development panels / 1 evaluation worker；不再把 worker 均值写成最差实验室。

## 已执行证据

- 协议在新开发推理前冻结：`results/panel_feedback_20261110/dev_audit_v1/protocol.json` 和 `registration.json`。协议 SHA256 为 `734ce81efea4c3b2335012603a10306d192d82358e1e7106693ab216c8dcc601`。
- 两任务 × 12设计 × seeds61–63：72个既有最佳 checkpoint 全量重算，恢复720个带标签的开发 panel 分数。primary/loss 最大绝对误差均为0；72/72真实 worst-panel 均低于均值。没有重训这72个模型，没有新测试推理。
- 两任务 × D00/D07 × 旧/新版：8次全新CPU短训练，seed61、每次10轮。四个配对的训练损失、每次开发primary/loss、所选轮次、所选权重、最终state/velocity均精确一致；真实panel轨迹完整保留。
- 72项真实记录的Raw/Structured观测事实一致性检查通过；Direct不接收分数。旧genetic v3实现未修改。
- 9项新单测以及既有evidence/search v3测试，共32项通过。AST比对确认训练循环仅替换开发汇总函数及CPU worker来源路径，没有更改优化、聚合或选择逻辑。

## 开发选择诊断：仍不稳定

在读取新panel分数前固定偶数panel为A、奇数panel为B；按A的primary/loss在原12个已存checkpoint中选择：

| 任务 | Seed | A相对D00变化/pp | B变化/pp | 252种5-panel子集与全panel选择同一设计 |
| --- | --- | ---: | ---: | ---: |
| Cell | 61 | +17.13 | −2.68 | 102/252 |
| Cell | 62 | +13.58 | −8.54 | 77/252 |
| Cell | 63 | +13.18 | +13.19 | 166/252 |
| Protein | 61 | 0.00 | 0.00 | 43/252 |
| Protein | 62 | 0.00 | 0.00 | 16/252 |
| Protein | 63 | +1.67 | 0.00 | 72/252 |

252个子集互相重叠，不能当独立重复；primary持平时loss可改变设计排名，不能把设计不一致全解释成大幅primary差异。更关键的是，旧checkpoint的训练轮次本来就按全部十panel选过，故B只是描述性补集诊断，不是独立确认集。这不是新的生物划分，也没有得到history效应估计。

## 下一步的最小实验

1. **反馈表示对照**：先用当前两个source-defined任务、12设计、seeds61–63、D00+6槽、100轮/fit，对比Fixed/Direct/Raw/Structured/Random/GP-EI；所有搜索上限700轮、最多2次生成/槽，失败占槽，Raw/Structured事实匹配。保持原全panel checkpoint/selection rule，隔离信息修复；缓存重放必须标注回顾性，不能算新训练或新盲测。正式执行前另建搜索注册、backend/model binding及结果目录。
2. **独立开发确认**：另设选择协议，保存每个开发评估轮的checkpoint；只用A选择轮次/候选，封存后才读B。不能从本轮已用全panel选出的best.pt冒充A-only选择。确认策略、预算与失败处理需在新推理前冻结。
3. **生物泛化**：VCC/Tahoe新的grouped split才回答原审稿的跨划分问题。既有测试已暴露，不能重新称为盲测；新的划分和数据访问规则应单独注册。

本轮没有执行第1–3项正式机制/泛化实验，注册中的 `future_mechanism_plan.status` 明确为 `DESIGN_ONLY_NOT_EXECUTED`。没有调用LLM、没有占用GPU，也没有提交OpenReview或更改Overleaf。

## 复现

```bash
cd /liziqing/yukai/AI4AI4Cell
/opt/conda/envs/LDA/bin/python -m unittest extensions.panel_feedback_20261110.test_payload -v

# 已存在的协议和输出不会被覆盖；重跑canary需新的版本目录。
# prepare/audit/canary入口用于复现时先阅读protocol，不能修改已绑定源码绕过检查。
/opt/conda/envs/LDA/bin/python -m extensions.panel_feedback_20261110.audit --help

cd paper
/opt/conda/envs/LDA/bin/python tools/publish_panel_feedback.py --check
```

论文仓库中 `provenance/panel_feedback_20261110/experiment_sources.zip` 保存本轮实现；仍需原项目adapter、已授权数据和旧缓存，不是standalone发布包，不包含生物矩阵、逐样本预测或权重。
