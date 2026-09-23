# 引文与 ICLR 投稿规则核查

核查日期：2026-09-22。范围为核查开始时正文、附录实际使用的18个引用，另核验新增外源细胞实验的3篇数据来源。没有改动共享正文或主 bibliography。规则已直接查到 ICLR 2027 官方文件，不只照搬去年。

## 需要实际落实的修改

1. **最近相关工作的定位要准确。** Chiron 已有 AI agent 调用界面，可以准备数据、部署 worker、启动与监督训练；Helmsman 已有 agent 驱动的协同学习系统设计与模拟验证。可以突出我们的生物任务共同接口、聚合测量驱动的设计修改、历史证据打包和受控比较，但不能把这些既有工作描述为完全没有 agents，也不宜把“首次把 agent 与 collaborative learning 结合”作为区别。[Chiron 固定版本 README](https://raw.githubusercontent.com/aristoteleo/chiron/3241b35c8b516c126aa68da450708de3da717ee0/README.md)；[Helmsman v2](https://arxiv.org/html/2510.14512v2)。
2. **补数据集的原始出处。** 当前 Norman 数据段没有引用，已有 `norman2019genetic` 却未使用；VCC、Tahoe 也应给出各自确切数据 release/研究来源。scDEBART 不能替代原始数据集的归属引用。新增 Replogle、Nadig、Jiang 外源实验可采用本目录的 `suggested_external_sources.bib`，三篇标题、完整作者、年份、DOI 已核验；不是按 UMM 的容器标签推断出处。
3. **已有文献尚未发现明确错指 DOI 或伪造标题；两个待核验项已在追加检查中关闭。** scDEBART 官方 ICML 2026 poster/61521 页面的 JSON-LD 明确作者为 Jieun Sung、Wankyu Kim，与主 bib 一致；OpenReview 全文仍403，但不影响作者身份核验。DrugBAN 实际 adapter 加载的本地官方仓库 HEAD 为 `9923f8c99959e00263103ff9ac61ba0eaccc8e02`，工作树干净，remote 为作者官方库，与主 bib 固定提交一致。详见 `release_trace_followup.md`。
4. `ahlmann2025linear` 可补 `volume={22}, number={8}, pages={1657--1661}`。引用结论限于其前向基因扰动预测基准：不能用来直接证明我们五选一逆向任务的排序结论。[原文全文](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC12328236/fullTextXML)。
5. **ProteinTalks 任务要写成我们构造的 observed-response 子任务。** 原文 Methods 的 PTPC 是 983 个已标注 perturbation-level 样本；我们491条件源池与148条件test是本项目按访问/预处理/划分形成的子集，应引用自己的 manifest 作证，不让读者误以为复现了原文完整 PTPC 榜单。原论文确实有观测6h/24h输入与BCE效能头，依据本地原文p14 Eq.(7–11)、p15 “Few-shot transfer on PTPC”。[原文 DOI](https://doi.org/10.1038/s41586-026-11001-9)。

## 18 个活跃引文的核查结果

| Bib key | 身份和相邻主张 | 修复或注意 |
|---|---|---|
| Jiang2025AIDE | arXiv v1 标题、7位作者、日期匹配；§3.1–3.2支持草拟/调试/改进和历史摘要 | 可保留 |
| Lu2024AIScientist | arXiv v1标题、6位作者、日期匹配；Experiment Iteration支持执行日志与结果驱动重规划 | 可保留 |
| Zhou2026DrugEvolve | Crossref和官方README的20位作者、标题、2026-08-20、DOI匹配 | 出版商正文访问失败；本文所需机制由固定版本官方代码文档支持 |
| DrugEvolveCode | 固定提交可访问；README有多角色、内外记忆、lineage与循环 | 可保留简洁 related-work 位置，不据此复活旧不对齐跑分 |
| Sheller2020 | 出版商与Crossref作者、标题、2020、article12598匹配 | 支持跨机构医疗训练动机 |
| Bai2023DrugBAN | 出版商与Crossref作者、标题、2023、5:126–136匹配 | 架构描述与官方实现一致；全文方法在线受限 |
| DrugBANCode | 出版商链接正确官方库；实际加载的本地仓库固定 HEAD 与 bib 一致且工作树干净 | 2026是快照引用年份，不是论文年份 |
| McMahan2017 | PMLR54、5位作者、2017、1273–1282匹配 | 用于聚合机制；本项目optimizer/buffer细节是自己的实现 |
| Sun2026ProteinTalks | Crossref及本地论文首页33位作者、标题、2026-09-09、DOI匹配；已读原文相关Methods | 严格区分原文全协议与本项目子任务 |
| Li2025Helmsman | arXivv2作者、标题、2025-12-19匹配；Methods/A7支持生成、修复与模拟实验 | 必须承认其已有自动设计功能 |
| Khodak2021FedEx | NeurIPS34论文7位作者、标题、2021匹配；Figure1/§2–3支持本地验证驱动的调参 | 不宜把本地验证用于设计选择写成此前从未研究 |
| ahlmann2025linear | Crossref及EuropePMC全文匹配 | 补卷期页；不要外推到所有当前大模型/逆向任务 |
| lin2025tapb | Nature官网全文与Crossref7位作者、标题、2025、16:10867匹配 | Fig5支持预提取ESM2/目标字典；client0字典属于我们的适配 |
| Wang2024scFed | 完整作者/标题/DOI匹配；EuropePMC Methods 支持本地分类和聚合 | 期刊25(1)2024正确；Crossrefprint2023与publisheronline2024存在日期冲突，不应机械改2023 |
| Bakhtiari2025FedscGen | 出版商全文作者/标题/2025/26:216匹配 | 其SMPC确有实现；不能暗示我们的当前协议已提供同级保护 |
| Ding2026Tabula | arXivv1的17位作者、标题、2026日期匹配；98页PDF已成功读取相关方法 | 物理p6明确Chiron的agent接口，p32说明聚合；2025bioRxiv是另一版本 |
| ChironCode | 固定提交README完整读取；作者/接口与出处匹配 | 有agent接口；本项目应强调设计改进的具体差异 |
| sung2026scdebart | 官方README支持模型机制；官方ICML2026 poster/61521确认标题与两位作者 | 作者身份已验证；OpenReview全文访问仍受限 |

核查开始时未使用的5项为 `norman2019genetic`、`yang2013gdsc`、`lin2023evolutionary`、`cao2025cipfn`、`qin2026cmadti`。未使用并不等于错误；Norman应补引用，其他不要为了凑参考文献强行引入。若正文使用ESM2，直接加 `lin2023evolutionary` 是合理选择，但应核验其与实际checkpoint的对应关系。

## ICLR 2027：已验证的规则与本地现状

按[2027 Author Guidelines](https://iclr.cc/Conferences/2027/AuthorGuidelines)，初稿正文上限9页，参考文献和后置附录另计；采用匿名投稿和官方模板。AI use 独立声明必需；Ethics和Reproducibility段落推荐、不计正文页数。最终还须检查编译成品的页码、匿名链接和补充材料。

[2027 AI Policy](https://iclr.cc/Conferences/2027/AIPolicyForAuthors)要求论文及提交表同步披露AI用途；假说、研究/实验设计、方法实现、数据整理、结果解释、翻译等需按实际情况说明。当前声明已有编码/分析/绘图/检索/编辑，可更具体列出方法与实验设计、假说细化、结果解释，以及中文版翻译（若确由AI辅助）。不要写未经实际完成的“全部作者逐一验证”或编造审查人数。

Reproducibility段应作为导航，指向正文方法、附录训练/划分/预算说明、匿名代码及数据元信息，而非把所有工程细节重复一遍。隐私场景可以在Ethics中简明说明模拟机构划分、公开数据来源、研究用途；无需用防御性段落打断方法主线。[2026规则作为历史对照](https://iclr.cc/Conferences/2026/AuthorGuide)也建议上述导航式表述，但2027的AI披露已明确为必需。

官方2027模板来源为 https://media.iclr.cc/Conferences/ICLR2027/iclr-2027-style-files.zip 。本轮在内存下载比对，本地4文件与官方逐字节一致：

| 文件 | SHA-256 |
|---|---|
| iclr2027_conference.sty | 797deef41724e93761426ac0cbcca46279a91cc650dd1f0ce76a4f08d2098ea6 |
| iclr2027_conference.bst | 2d67552db7ed38ccfccb5957b52f95656e25c249724761d3cf5f7922ad1844c5 |
| natbib.sty | 88bc70c0e48461934cab5b2accef06b74a8b3ac45ad03ccd3f2a6b7e0d6d530d |
| fancyhdr.sty | b56ec4434b9f4607529a4b23dc68ad8d4b94f1f631c8cddaf7da78140d53a5ea |

作者OpenReview档案、author list、reciprocal reviewer登记、投稿表AI声明、最终上传版本需作者在平台确认；本地排版审查不能代替这些检查。本审计未操作投稿平台。

## 证据文件与边界

- `source-ledger.csv`：18活跃引文、3外源研究、VCC/Tahoe及官方规则的25行证据记录。
- `claim-evidence-matrix.csv`：11项相邻主张与出处的映射。
- `suggested_external_sources.bib`：三个外源细胞研究及 VCC/Tahoe 数据来源增补，未自动并入主 bib。
- `release_trace_followup.md`：VCC/Tahoe 从实际训练 manifest 到上游 release 的链条，以及 scDEBART/DrugBAN 补核验。
- `citation_review_plan.md`：检索范围与截止日期。

本轮 literature-review skill 所指的 sibling `paper-writing` 和 `general-writing` 文件不存在；采用直接原始来源核验和人工编辑建议作为回退。未把检索摘要当作原文已读：受限全文与部分核验项目已逐项标出。
