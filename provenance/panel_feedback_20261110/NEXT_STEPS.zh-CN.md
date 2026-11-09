# 本轮之后的待办

日期：2026-11-10（Asia/Shanghai）。本文件接续38页精简稿的未解决清单；新增证据见同目录 `summary.json` 和 `CHANGES.zh-CN.md`。

已完成：旧source-defined两类adapter的panel反馈链路已在新版本修复，72个checkpoint的primary/loss完全复现，720个panel分数恢复，8次配对10轮训练不改变权重或选择。论文新增附录小节E.8和表E.9，三份英文回复同步48-fit、40-lab及本轮诊断。注意旧表E.7是成本表，旧小节E.7是lab identity；不要混淆表号和小节号。

待办按优先级：

1. **独立开发选择验证**：本轮固定A/B诊断的细胞seed61/62仍反向；旧checkpoint已使用全panel选轮次，不能当独立确认。新协议需保留各评估轮checkpoint，只用proposal面板选轮次/设计，封存后评分confirmation面板。
2. **预算匹配的真实机制实验**：本轮只验证工程和开发诊断，没有执行修复后的LLM搜索。最小计划已写入protocol的 `future_mechanism_plan`，状态为未执行；需另行冻结backend/model binding、提示、调用/失败预算和输出目录。保留Direct/Raw/Structured/Random/GP-EI及Fixed。不要用已看过的测试分数选择任务、menu或提示。
3. **新的生物grouped split**：用于回答原VCC/Tahoe跨划分泛化；20-roster和本轮252个panel子集均不替代新划分。已有测试已暴露，回顾评分不能叫盲测。
4. **逐lab完整controller轮换和计算匹配**：40-fit仅是fixed单seed身份敏感性；DTI词典仍由lab0构造。单lab补足十lab优化步、全controller轮换尚未做。
5. **机制结论边界**：稳定history优势仍未建立；Structured−Direct +0.263pp的区间跨零，GP-EI仍更高。allocation收益和固定模型源迁移不能替代history效应。蛋白迁移正向、细胞迁移负向均保留。
6. **投稿动作**：没有发布OpenReview，没有更新Overleaf，没有合并main。三回复是作者审阅草稿；线上新评论、截止日期和字符限制本轮未查询，投稿前另核。

复现和完整计划见同目录 `CHANGES.zh-CN.md`。原38页/41页版本、旧结果表和既有未跟踪文件均保留；新的修订分支交付不等于论文已提交。
