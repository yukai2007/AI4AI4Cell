# 师姐批注逐项落实记录

批注原件：`AI4AI4Cell (7)(1).pdf`，20页。共29个标记，其中24条有文字意见、5处为空文本高亮；全部原文、位置、作者与PDF哈希见 `annotations.json`，方便回到原位置核对。下表的页码指批注原稿，不是重排后的页码。

本轮原则：先讲研究问题和机制，再给实现细节；同一项结果只使用其实际验证过的解释。积极叙述不等于把固定候选的训练分配增益写成LLM提案能力的增益。

| ID / 原稿定位 | 师姐意见 | 实际修改与核验 | 状态 |
|---|---|---|---|
| C01 / P1 x433，关联x428 | 全部参考文献核验 | 独立查原论文、版本化官方仓库、DOI及会议记录；另补任务数据和外源研究出处。完整证据在 citation_audit 与 source-ledger。 | 核验与修订；访问边界逐项记录 |
| C02 / P1 x439 | 配合图1展开、解释client | Intro按单数据研究循环、跨实验室参数训练、两者结合展开；首次出现明确client是实验室的计算worker。 | 已落实 |
| C03 / P1 x448，关联x443 | self-improving动机突兀 | 先说明新增数据要求重选预测头、优化设置和训练候选，再引出自动提案—测试—修订。 | 已落实 |
| C04 / P1 x454 | computational changes模糊 | 用prediction head、learning rate、regularization、aggregation settings等具体设计对象替代泛称。 | 已落实 |
| C05 / P1 x459 | 加AI4AI生物场景 | Intro和Related Work用DrugEvolve解释药物任务中的实现、评价、记忆；不恢复旧不对齐跑分。 | 已落实 |
| C06 / P1 x464 | 去双破折号插入语 | 重写该段，不用长破折号连接旁注。保留范围与复合术语的正常连接符。 | 已落实 |
| C07 / P1 x468 | inner/outer之前先概览 | 先介绍two-level research cycle及其输入输出，再分别解释拟合和研究决策。 | 已落实 |
| C08 / P2 x476，关联x472 | centralized删其余灰色labs | 图1只保留真实单数据源，补清local fit/evaluate与反馈路径；其他场景用K。 | 已落实并渲染检查 |
| C09 / P2 x487 | 贡献独立段 | Intro结尾单独贡献段，不与实验设置拼接。 | 已落实 |
| C10 / P2 x491 | arm evaluation不自然 | 正文改为comparison/configuration；以具体实验问题解释对比。 | 已落实 |
| C11 / P2 x496 | 贡献应是loop机制而非整个harness | 贡献聚焦证据卡历史、提案修订和证据驱动训练分配；承认已有agent-enabled协作平台。 | 已落实 |
| C12 / P2 x500 | Related Work分两方面 | 改为Collaborative learning for biological data与AI for AI in biological research。 | 已落实 |
| C13 / P3 x505 | Method先overview后亮点 | §3.1首段说明任务规格、初始模型、设计空间、K实验室、输出；次段讲证据闭环。 | 已落实 |
| C14 / P3 x509 | 不用机械编号步骤 | 删除五项enumerate，改成连贯机制叙述，由图2承担流程。 | 已落实 |
| C15 / P4 x517，关联x513 | 10改K并做超参分析 | 框架/图统一K；10留在实验设置。Appendix B区分增加可用数据和固定全部数据两种K消融。四轻端点3seed已完成；DTI仍运行，不填估算。 | 写作及已完成实验已纳入；DTI待完成 |
| C16 / P4 x523 | 流程图只写任务不要指标 | 图2去AUROC/AP/Top-1；指标集中到实验契约表。 | 已落实 |
| C17 / P4 x527 | 训练实现细节移实验/附录 | 100轮、评估间隔移§4；AdamW重置、batch64、clip1、buffer聚合、动量和adapter宽度移Appendix A。 | 已落实 |
| C18 / P4 x536，关联x532 | Qwen型号是实现细节 | Method使用research controller；具体Qwen及Luna接口放实验和附录。 | 已落实 |
| C19 / P5 x542 | 区分方法抽象与细节 | Method讲证据卡和两类研究决策；JSON实形、12/36候选、解码参数、语法重试与缓存移附录。 | 已落实 |
| C20 / P7 x547 | 写明原模型名 | 主表caption及§4任务契约明确TAPB、ProteinTalks-derived efficacy head、corrected scDEBART head。 | 已落实 |
| C21 / P7 x551 | Direct用了什么harness | 行名改Qwen direct，说明同Qwen提配置、无评价历史，真正预测由任务模型完成。 | 已落实 |
| C22 / P8 x555 | 消融实验目的看不懂 | §5.2改为“反馈能否改善训练预算分配”；统一候选/数据/预算，Uniform与Evidence-guided列名；DTI开发回放移附录。 | 已落实 |
| C23 / P9 x560 | Discussion/Conclusion重复 | 结论精简为一段；后续问题在敏感性分析与伦理部分说明。移除未再引用的旧Discussion文件，Git历史可恢复。 | 已落实 |
| C24 / P10 x564 | 复现/伦理/AI声明参照会议写法 | 按2027现行规则改为导航式Reproducibility、简明Ethics和明确的AI use声明。正文页数、模板原文件、匿名正文另行检查。 | 已落实；平台表单需作者填写 |

## 新实验进入论文前的核验

`core_verification.json`于9月23日补充核验到26个完整结果文件、286个配置或预算截点、139个独立checkpoint，包含新完成的Tahoe Qwen/Luna 24槽位结果。原指标从保存预测复算，最大误差为0。它是保存预测复算，不冒充一次重新执行checkpoint推理；本轮补记的输入哈希也不冒充原始seal已有的历史绑定。模型对照还逐一验证了0–24槽位、全部提案记录和预设测试截点；DTI评分器已接入原始固定CSV的哈希检查。

主结果仍采用统一的seeds 42–44，未混入新候选空间或不同预算。Appendix B单独给新实验的完成数和N/A。更多实验室、外源数据或proposal slots不保证单调提高，论文保留全部已完成对照和反例。

## 尚需完成或由作者确认

- DTI实验室数量、跨源与长loop队列，以及其他任务剩余proposer seeds；运行状态以实验监管报告为准。
- 蛋白组外源是同一研究的不同collection/context，尚不构成三项独立研究的复现。
- 三项核心要求的逐组合验收表在研究目录 `results/core_ablation_20260922/analysis/COMPLETION.zh-CN.md`：训练、测试、独立复算、论文纳入分别计数，不能把队列已启动或单个COMPLETE标记等同于全部完成。
- 投稿平台的作者、reciprocal reviewer、AI use表单与最终上传由作者核实；本轮未操作OpenReview。
- `annotations.json`及本响应表包含合作者批注信息，供内部修改使用，不应随匿名补充材料上传。
- 文献技能引用的paper-writing/general-writing附属模板本地缺失，使用原始来源核验、直接重写、回归检查和逐页渲染作为回退。
