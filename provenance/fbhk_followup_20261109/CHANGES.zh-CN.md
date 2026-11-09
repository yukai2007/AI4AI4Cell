# FBhK 定向修订：作者交付说明

本版延续 `rebuttal/20261109-review-revision`，基于 `48c6438`；不覆盖原投稿 `main`，不自动提交 OpenReview。

## 本次完成

1. **同访问、同预算搜索。** 保留正文十实验室 Random without replacement、GP-EI、Direct/History 的完整比较，明确随机搜索使用 loop 的候选训练预算，不能只给 fixed model 的单次训练预算。原五 endpoint 共60个配置缓存的控制已完成；这是每 endpoint 一个训练 seed 的缓存分析，不冒充新的独立重复。
2. **历史反馈新研究完整入文。** E.6 收入新四场景/两个来源研究、三 seed、48次候选训练及真实 Qwen 提案的结果、协议、成本。Direct 22.625、Structured 22.888、Random 22.668、GP-EI 23.152；配对差和跨零CI全部保留。新实验与原 VCC/Norman/Tahoe 明确分开，不覆盖原分数。
3. **原表精简但不删不利证据。** 原 B.10/B.12 合并为两个协议 panel 的同一表；原 B.11/B.13 合并为完整轨迹统计表。18+18行逐值核验。六步/24步分别来自12/36设计，未拼成同一个预算消融。目标是事后定义、全部槽均执行，不再把target crossing写成真实省预算。
4. **开发—测试诊断。** 原14 checkpoint、140开发panel、80测试前缀重算和20roster敏感性已经完成。新增加全7政策×3seed×7prefix=147记录及矢量图。新研究18个非固定policy/seed终点均优于各自D00，但保留D05的局部反向和K562场景反向，不声称彻底修复。
5. **额外40个新实验。** 蛋白、VCC、Norman、Tahoe各lab0–9独立训练D00，单seed42、100轮，各自本地开发集选模型。全部新CPU运行和独立评分完成，没有占用或终止其他人的GPU。E.7给完整均值SD/范围；lab0并非统一乐观或悲观。SD是lab身份差异，不是seed波动。
6. **弱pilot压缩。** 两来源蛋白的8行fixed/loop重复表改为文字，保留四个来源结果和全部loop持平事实；不把它作为history有效证据。原文件保留，便于版本追溯。
7. **回复与复现。** 正式英文回复沿用 `../rebuttal_20261109/RESPONSE_FBhK.md`；本目录另有精简粘贴稿。源码包、公开聚合结果、原结果SHA、全前缀CSV及发布检查脚本随论文分支保存。

## 关键解释

- 主表回答“参与协作研究比只用自身数据得到什么整体收益”，同时改变数据和本地计算。相同100轮不代表1 lab与10 labs计算量相同。
- 同十lab的搜索表回答history是否优于更简单的搜索。固定模型是一次fit参考，不可冒充同预算搜索基线。
- 新实验匹配Direct/Structured/Random/GP的16,940个optimizer steps与532,840次样本暴露，但head参数量、LLM token和重试成本不同，不称FLOP-identical。
- 训练分配的Norman +10.84pp是相对uniform；Random promotion 22.63高于trajectory22.32，不能挪作history独有增益。
- 旧线性蛋白pilot与当前ProteinTalks-derived head不同，未为了获得阳性而塞进新主表；原完整结果仍在 `tables/unified_v3/`。
- 不是“训练同一模型越久必然掉分”：原B.12是在固定每candidate训练长度下增加候选搜索，再按开发分数换模型。把搜索轮数与训练epoch分开解释。

## 明确尚未完成／尚不能声称

- **所有controller在每个独立lab上各跑一次**尚未完成。E.7只覆盖四任务固定D00，不包含DTI，不替代完整轮换搜索。
- DTI目前依赖lab0训练目标构建的dictionary；严格轮换需逐lab重建或预先定义公共dictionary，不能直接改client ID。补lab1–9全菜单单seed成本粗估39.07 GPU小时、三seed117.21小时，还未计LLM/数据准备；不把估计当已完成实验。
- 尚无原VCC/Tahoe多套独立grouped split的重训。20roster研究仍使用原开发干预；新gene-disjoint研究是另一benchmark。
- 尚未证明history稳定优于Direct/Random/GP，也不能保证新表不会出现任何dev/test分歧。当前修订补强控制完整性和诊断，不虚构中心机制的显著性。

## 作者使用入口

- 论文：`output/pdf/BioCoLoop_FBhK_revision_20261109.pdf`。
- 英文完整回复：`provenance/rebuttal_20261109/RESPONSE_FBhK.md`。
- 精简粘贴稿：`provenance/fbhk_followup_20261109/RESPONSE_FBhK_SHORT.md`。
- 新表和原数值映射：`tables/fbhk_followup_20261109/`。
- 新曲线：`figures/fbhk_followup_20261109/history_prefix_dev_test.pdf`，另有SVG。
- 全前缀与每场景诊断：本目录 `prefix_audit.json` 和三个CSV。
- 新旧表号和最终PDF页码：本目录 `TABLE_MAP.zh-CN.md`。
- PDF哈希、实际正文页数和验证状态：本目录 `build_receipt.json`（以最终构建为准）。

源码包不是独立运行的完整项目；需要原任务adapter、前次实验扩展、获批数据及模型。包不含原始生物测量、逐样本预测或模型权重。当前分支推送不代表Overleaf/main已切换，也不代表OpenReview已更新。

## 文献与排版核验

本轮针对性核验2篇原始方法论文：Bergstra and Bengio (2012) 的随机搜索；Cawley and Talbot (2010) 的模型选择过拟合。只用于解释对照设计与可能机制，不替代本实验因果证据。来源及逐条论据见 `research/`。文献skill引用的两个附带写作模块本机不存在，使用现有论文结构、人工措辞复核及PDF逐页检查。

ICLR 2027官方指南允许讨论期正文10页，参考文献与附录另计；同时要求匿名与AI使用声明。本版继续保留这些声明。完整编译和可视检查的最终结果记录在build receipt，不以无报错编译替代内容复核。
