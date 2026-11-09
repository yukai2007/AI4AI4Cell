# 2026-11-10 聚焦精简稿

基于 `b9f1713`，继续使用 `rebuttal/20261109-review-revision`。本轮是写作和组织修订，没有新增实验，没有根据正负结果筛选比较，也没有覆盖原投稿主线或提交OpenReview。

## 已执行的删减与重组

1. 正文先给出整体协作、跨来源迁移和选择性充分训练的主要结果；将反复出现的逐项胜负总结改为一次完整对照和明确解释。
2. Appendix A合并重复的算法导航、角色别名、缓存与训练步骤描述，保留公式、配置表、scorer、失败槽和预算规则。
3. Appendix B压缩来源清洗、私有head、旧两来源pilot和提案轨迹的重复叙述；旧pilot的完整数值与loop持平结论仍在。
4. Appendix D删除与表格重复的五任务逐项增益罗列；所有搜索策略、预算、方差和跨零区间保留。
5. Appendix E合并重复的访问公平性、cache成本解释、来源迁移背景和promotion结果复述。完整Random/GP/Direct/History、失败槽敏感性与开发—测试诊断未移走。
6. Introduction贡献点与Conclusion改为直接陈述框架能力和受实验支持的结果；仍区分整体协作、训练分配与history特有贡献。
7. 修正旧口径：B.1固定池K=1确实使用全部target training data；缺少的是主表完整workflow的额外同计算量centralized对照，而不是完全没有全数据池单节点参照。

压缩同时覆盖阳性、中性和阴性结果的重复介绍，不以结果方向作为去留标准。

## 量化变化与检查

- 总页数：41 → 38；正文实际结束页：10 → 9。
- 改动章节按空白分词统计：10,674 → 8,591，减少2,083（约19.5%）；包括LaTeX词元，不当作语言学精确词数。
- 其中Appendix A：2821 → 2171；B：2553 → 1791；D：665 → 588；E：3024 → 2572。
- 43个被包含的LaTeX文件集合相同，29个被包含的table资产和6个figure资产逐字节不变。
- 原主表50个score cells、原四表合并的18+18行，以及全部新history/random/GP和40个lab结果验证通过。
- 15项已有发布/打包回归测试通过；完整实验包及其哈希验证通过。
- 编译无未定义引用或overfull box；38页渲染均已人工检查，没有内容越界或遮挡。
- 没有启动训练任务，也没有删除原始结果、预测、实验源码或前版PDF。

## 使用入口

- 精简稿：`output/pdf/BioCoLoop_focused_revision_20261110.pdf`。
- 日常阅读：`output/pdf/BioCoLoop_manuscript.pdf`，与精简稿一致。
- 必须保留但仍需优化的证据清单：本目录 `REMAINING_ISSUES.zh-CN.md`。
- 新页码：本目录 `TABLE_MAP.zh-CN.md`；表号本身未变。
- 发布核验：本目录 `build_receipt.json`。
- 前版41页PDF仍为 `output/pdf/BioCoLoop_FBhK_revision_20261109.pdf`，原SHA保持不变。

已有FBhK英文回复仍适用相同实验与表号；旧交付记录的页码指向旧41页稿，不应当作新稿页码。本次更改并没有建立新的统计优势，也不替代后续机制修复。
