# 师姐批注原文与锚点

来源：AI4AI4Cell (7)(1).pdf
SHA-256：`d398c411eaab91a1557a034d24d07d46ebe660b841ab48b96c6fb08982a74f37`

共 20 页，29 个批注标记；保留空文本高亮以便与旁边便笺配对。

## P1 / xref 428 / Highlight

批注：（无文字高亮，见相邻便笺）

锚点：(Bakhtiari et al., 2025; Sheller et al., 2020).

## P1 / xref 433 / Text

批注：最终定稿前，务必检查所有参考文献引用的正确性

锚点：sharing constraints limit centralized access. Complementary measurements of molecular interac-
tions, protein responses and cellular perturbations could improve predictive models, but cannot al-
ways be pooled across laboratories (Bakhtiari et al., 2025; Sheller et al., 2020). A key challenge for
self-improving AI in this setting is to use such distributed evidence to improve both model parameters
and the computational solutions built around them.
Collaborative learning typically optimizes parameters within a predefined model design through
client-local updates (McMahan et al., 2017; Sheller et al., 2020; Wang et al., 2024; Ding et al., 2026),

## P1 / xref 439 / Highlight

批注：这部分文字可以配合着图1去写，适当展开，目前这个以及后面介绍RSI的有点短；client-local中的client的含义也最好写清楚，因为审稿人未必懂联邦学习

锚点：Collaborative learning typically optimizes parameters within a predefined model design through client-local updates

## P1 / xref 443 / Highlight

批注：（无文字高亮，见相邻便笺）

锚点：A key challenge for self-improving AI

## P1 / xref 448 / Text

批注：这里直接写self-improve AI有点突兀。可能前面加一句为什么要用self-improving AI 更好。

锚点：sharing constraints limit centralized access. Complementary measurements of molecular interac-
tions, protein responses and cellular perturbations could improve predictive models, but cannot al-
ways be pooled across laboratories (Bakhtiari et al., 2025; Sheller et al., 2020). A key challenge for
self-improving AI in this setting is to use such distributed evidence to improve both model parameters
and the computational solutions built around them.
Collaborative learning typically optimizes parameters within a predefined model design through
client-local updates (McMahan et al., 2017; Sheller et al., 2020; Wang et al., 2024; Ding et al., 2026),

## P1 / xref 454 / Highlight

批注：computational changes在这里具体指什么需要展开，AI写作可能会写的比较模糊

锚点：computational changes

## P1 / xref 459 / Highlight

批注：这句话目前讲的是general的AI for AI 的研究现状，可以适当补充 AI for AI bio场景的引用或者适当展开

锚点：automated model design and research generally rely on centralized training and evaluation

## P1 / xref 464 / Highlight

批注：最好不好出现这种双破折号，很容易判定为AI

锚点：trial—including rejected and failed trials—adds

## P1 / xref 468 / Highlight

批注：在讲Inner 和 Outer之前，需要加1-2句话，讲清楚模型和核心思想，比如说先说明框架包含内外循环，否则这里直接讲内循环读者会困惑，不知道啥是内循环

锚点：Its inner

## P2 / xref 472 / Highlight

批注：（无文字高亮，见相邻便笺）

锚点：Lab 1 local data

## P2 / xref 476 / Text

批注：centralized是没有lab2 labNdata的，可以直接把剩下的几个灰色的删掉

锚点：Lab 1
local data
Lab 2
local data
Lab 10
local data
Lab 1
local data
Lab 2
local data
Lab 10
local data
Lab 1
local data
Lab 2
local data
Lab 10
local data
local data
predictive model
research harness
aggregation / evidence gate
Dashed gray modules show capabilities omitted from a configuration.

## P2 / xref 487 / Highlight

批注：参考之前的ICLR写法，这个部分应该单独成段

锚点：Our contributions are (i)

## P2 / xref 491 / Highlight

批注：arm evaluation很奇怪，这不是常见用词，如果AI写的句子你看不懂，就需要改写或者删掉

锚点：arm evaluation

## P2 / xref 496 / Highlight

批注：这个harness不是你的贡献，你的贡献应该具体为其中的loop机制

锚点：evidence-guided harness

## P2 / xref 500 / Highlight

批注：建议分为两个方面来写，collabrative 以及 AI4AI in bio的研究现状，

锚点：RELATED WORK AND COMPARISON SCOPE

## P3 / xref 505 / Highlight

批注：第一段一般是整体框架的overview, 输入输出是什么，大体包含哪些模块，流程是什么

第二段介绍其中的亮点，即你的looped机制

锚点：RESEARCH OBJECTS AND THE TWO-LEVEL CYCLE

## P3 / xref 509 / Highlight

批注：不要用这种分点的方式写，要么通过图呈现，这里只用文字叙述逻辑，要么用伪代码呈现（三线表）

锚点：one research iteration proceeds as follows:

## P4 / xref 513 / Highlight

批注：（无文字高亮，见相邻便笺）

锚点：10

## P4 / xref 517 / Text

批注：这个10只是一个超参，你在叙述的时候建议用N等代替，10作为一个超参，后续需要做相应地超参分析实验

锚点：Laboratory 1
private train + dev
local model update
Laboratory 2
private train + dev
local model update
Laboratory 10
private train + dev
local model update
...
SAME core, controller, budget and selector; task-specific prediction adapters

## P4 / xref 523 / Highlight

批注：指标需要与后文对应，建议这里只体现任务，不要写具体的指标

锚点：TAPB adapter / AUROC

## P4 / xref 527 / Highlight

批注：这里大部分是运算细节，与方法不强相关，可以放在后文实验细节那一节，或者附录

锚点：Each candidate follows a 100-round schedule. Every five rounds, local development workers re- turn scalar metrics; the coordinator retains the checkpoint with the highest equal-client mean pri- mary metric, breaking ties by lower mean development loss. Model selection is completed on de- velopment evidence, after which the selected checkpoint is frozen and evaluated with the common held-out scorer. The DTI adapter trains TAPB on frozen public protein features; proteomics trains a ProteinTalks-derived eﬀicacy head; cell tasks train the response head on frozen, mask-corrected scDEBART representations. Only these task adapters and their scorers differ across studies.

## P4 / xref 532 / Highlight

批注：（无文字高亮，见相邻便笺）

锚点：The shared research model is local Qwen2.5-7B-Instruct.

## P4 / xref 536 / Text

批注：与上文一样，属于技术细节

锚点：3.3 STRUCTURED PROPOSALS AND PERSISTENT EVIDENCE
The shared research model is local Qwen2.5-7B-Instruct. Every proposal follows the same four-field
JSON contract:
4

## P5 / xref 542 / Highlight

批注：都是细节吗？需要区分抽象的方法与细节

锚点：For example, a proposal may predict that lower learning rate with a residual response adapter im- proves development ranking without increasing loss, request the corresponding comparison with the incumbent, and select the identifier that implements that combination. The identifier, rather than free-form prose, is the executable source of truth. In the uniform study, identifiers address a common twelve-design library spanning learning rate, weight decay, server momentum and an optional zero-output-initialized width-32 residual adapter. This bounded library supplies a controlled instance of the broader harness: it preserves hypothe- sis formation, executable compilation, isolated evaluation, retention and experiment memory while making the search space identical across tasks and research modes. Appendix A lists every design. After execution, the harness appends an evidence card containing the configuration, aggregate best development metric and loss, selected round, first and last training/development diagnostics, and the accepted, rejected or failed decision. The next loop proposal receives the incumbent plus this complete sequence of evidence cards. Rejected trials remain useful because they identify exhausted directions and observed failure modes. The feedback-free direct arm uses the same Qwen checkpoint, candidate library, six proposal slots and fitting service, but receives only the identifiers it has already tried. Both modes share an identical first proposal, making subsequent divergence attributable to evaluation history rather than a different starting sample. The finalizer applies the same primary-metric/loss ordering used for checkpoint selection. Completed candidates can replace the incumbent; numerical failures are recorded and advance the proposal budget. Identical configurations within the same seed and participation setting may reuse a verified completed fit while retaining their logical position in both research traces. Proposal generation, fitting and communication costs are recorded separately.

## P7 / xref 547 / Highlight

批注：需要写明原来方法的名称

锚点：Fixed recipe (1 lab)

## P7 / xref 551 / Highlight

批注：写明用的是什么harness做的预测

锚点：Direct optimization

## P8 / xref 555 / Highlight

批注：没看懂这个实验是关于什么的

锚点：SEPARATING PARTICIPATION, SEARCH AND FEEDBACK

## P9 / xref 560 / Highlight

批注：Discussion一般就是Conclusion，只有一段，最多再加一段weakness

锚点：DISCUSSION

## P10 / xref 564 / Highlight

批注：看一下去年的论文，这个段落在写什么
以下几段也需要

锚点：REPRODUCIBILITY AND RESPONSIBLE USE
