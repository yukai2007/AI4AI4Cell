# 作者审阅版核验记录

日期：2026-11-10（Asia/Shanghai）。前版基点`7323c9f61745a3bd47057f27eb11c7758686b30a`。

- 最终论文38页，正文及结论完整结束于第9页，复现/伦理/AI声明从第10页开始，附录位于参考文献之后。三位审稿人回复合计7页。
- 正文与附录约删去两千个以空白分隔的源码词元；主要压缩重复解读和工程过程，重新组织原表格/图的阅读顺序。没有新训练、测试评分或根据测试更换配方。
- 新Table 3完全由仓库中两个已发布的聚合报告生成。DTI/蛋白组使用Luna三seed温启动研究，细胞使用Qwen三seed独立gene-disjoint研究；caption明确各列协议不同。随机搜索期望、Fixed、Direct、Structured和GP均呈现，Raw及额外GP offset仍在完整附录表。
- 357份历史实验资产、provenance和旧版PDF逐字节不变。原正文窄菜单摘要表由最新概览替代，旧五端点的完整表仍编译于E.2；其他原结果表及全部图继续包含。实验数字没有修改。
- 2027官方模板四个文件逐字节一致。移除全局图表间距压缩，使用Times/T1；最终PDF正文实测为Times兼容Nimbus Roman，未发生字体回退。匿名性、页形、注释、页数及输入时效检查通过。
- 最终编译没有Overfull box、缺字、未定义引用、重复label或未定义字体形状。已渲染并检查全部38页论文及7页回复；正文Table 3、第9页限制/结论、放大的六槽轨迹图及最新完整配方表另作全尺寸检查。
- 本轮为呈现与排版修订，使用实际报告再生成和发布检查核验，不新增与文句实现绑定的单元测试。之前训练/搜索/独立评分的完整证据及测试结果保留在原provenance。

在`paper/`完成：

```bash
python tools/build_author_review_tables.py --check
python tools/finalize_author_review.py --pdf build/main.pdf --log build/main.log
git diff --check
```

版本PDF、源文件、官方包、回复、图表编号与页码的哈希绑定由`build_receipt.json`和`TABLE_MAP.zh-CN.md`给出。主分支、Overleaf和OpenReview未更新；回复仍为作者审阅稿。
