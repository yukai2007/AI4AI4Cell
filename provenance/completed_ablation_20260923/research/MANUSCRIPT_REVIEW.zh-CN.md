# 新增正文与附录独立内容复核

范围：只读sections04/05/07/23及completed_ablation表，对照冻结JSON和已核验adapter。已实际纳入，不再标记publication pending；最终PDF视觉由root验收。

## 判定

**最终内容判定：PASS。** 数值、实验覆盖与独立来源范围一致。以下两处发现的问题已由root修正，并于此轮重新读取源文件确认：

1. B.2首段“For transfer, the entire target training pool is one study-level client”现已限定DTI/cell。蛋白pilot保留target0..9十客户；Lin10、Ruprecht11各为来源客户。蛋白段现已明确ten target clients。
2. B.2“reported response interval”现已改为encoded potency interval，并写清>=10000nM作为右删失是adapter约定，与~值factor2约定一致，不误称原文直接给完整区间。

无需重训；英文修改均由root完成，本审查未改英文。

## 独立通过的核对

- 10个短loop backend/endpoint对：6slots/12designs；DTIseed42、其余seed61。终点direct-loop重算1胜/8平/1负；NormanLuna+0.81pp、DTILuna-0.33pp。正文5.4和主文表一致。
- 8个长loop对：24slots/36designs，四轻端点；重算0胜/7平/1负。VCCLuna-0.22pp；VCCQwen31.50@6→19.61@24；NormanLuna终点双方23.11。正文和long24表一致。
- 短、长的菜单/seed/scope在4.5与B.3/B.4、图注均明确，无混合曲线，也未虚称长DTI完成。
- 原seed61--63结果重新算四轻端点fixed-pool均值与sampleSD，全部与表一致。PTPC34.59/37.36/39.19/37.54；Norman49.63/19.56/26.12/15.48。
- DTI K与三源分数取最终heldout而非早期training receipt；个别源提升、负迁移和all-source结果均保留。
- Lin28=20/8、Ruprecht109=85/24及药物5/2、17/5，49/18/42端点类别匹配。新encoder/来源heads与独立配对target-only明确；原主表不替换。
- 两独立蛋白研究与三个within-study contexts分开；decryptE不计入已完成实验。蛋白AP/AUROC、bootstrap区间、全部fixed-loop ties均准确。
- Conclusion区分parameter learning、compute allocation和proposal-history效果，未泛称proposal feedback普遍提分。

## 纳入与完成性

ACCEPTANCE和claim-evidence-matrix已更新实际章节。实验仍为DTI3/Cell3/Protein2外源；长loop仍仅四轻端点。两处文字问题已闭合，当前无must-fix内容项；内容PASS不等同于最终PDF视觉验收。

最后同步复读：Lin现明确为three released ratio measurements；Ruprecht明确explicit lower bounds与>=10000nM删失。长loop共同目标现统一为双方terminal development score的min，正文B.4与生成表caption一致；Norman22/4、Tahoe5/13方向未变。未把该回顾性共同目标当成预设停止规则。内容验收仍为PASS，publication incorporation已记录，不留待纳入项。
