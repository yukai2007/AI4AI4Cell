# 核验记录

日期：2026-11-10（Asia/Shanghai）。本轮执行结果，而非后续机制实验承诺。

- 新payload、已有evidence card和search v3：32项测试通过；命令为 `/opt/conda/envs/LDA/bin/python -m unittest extensions.panel_feedback_20261110.test_payload extensions.history_repair_20261109.test_evidence_cards extensions.history_repair_20261109.test_search_v3 -v`（项目根目录）。
- 既有论文结果完整性/归档：15项测试通过；命令为 `python -m unittest discover -s tools -p 'test_*fbhk_followup.py' -v`（paper目录）。合计47项。
- 两任务72个真实checkpoint、720个真实panel的primary/loss误差为0；72项Raw/Structured同事实检查通过。
- 四对、八次10轮CPU训练：训练曲线、开发分数、所选轮次和权重、最终state/velocity精确一致；发布生成器重新读取所选/最终权重核验。
- `publish_panel_feedback.py --check` 检查协议、冻结源码、完整覆盖、所有panel统计、252子集诊断、生成表及确定性源码归档；全部通过。
- 新发布检查器保留152个旧table/figure/asset文件、全部既有LaTeX输入和旧版本PDF/回执；旧结果数值改动为0。
- Tectonic 0.16.0缓存编译成功；无overfull、未定义引用、缺失字符、重复标签或LaTeX错误。字体配置提示、既有underfull提示及输入PDF版本提示不影响生成；逐页检查未见相应排版缺陷。
- 论文39页，正文结束第9页；新增附录小节E.8与表E.9位于第39页。审稿回复6页；三份完整草稿均对齐最新证据。已渲染并检查39页论文与6页回复的所有页面，新增第39页另以完整尺寸查看。
- 匿名文本/元数据/外链、页面边界及PDF注释检查通过。归档不含生物矩阵、逐样本预测、checkpoint或模型权重。

`build_receipt.json` 记录最终PDF/输入/表格/源码归档哈希和实际图表页码。投稿网站字符限制、截止日期及后续评论本轮未查询；三回复仍为作者审阅草稿。
