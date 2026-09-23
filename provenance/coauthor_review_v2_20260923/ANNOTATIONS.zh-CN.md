# 第二轮批注原文与锚点

来源：AI4AI4Cellv2-yc.pdf

SHA-256：`345ba5c0b8a09a8a09890c8bee04bd5f964c68c2030c0217ff8ff2282a8f2d44`

共 32 页；27 个批注对象。空文字高亮也全部保留。

## V2-01 / P1 / xref 701 / Highlight

批注：（无文字，保留高亮锚点）

锚点：015
016
017
018
019
020
021
022
023
laborative learning typically optimizes fixed models, whereas automated model
design and research generally rely on centralized training and evaluation signals.
Bridging the two is nontrivial: distributed evidence must support not only opti-
mization, but also the evaluation and refinement of computational changes that
generalize beyond their local settings. To tackle this, we introduce BioCoLoop, a
collaborative research framework that couples client-local parameter fitting with an
evidence-guided proposal–evaluation loop. Local training shards update a shared
predictor, while local development shards produce aggregate evidence cards that
guide the next executable proposal. Across three biological settings spanning drug–
target interaction prediction, observed-response proteomics, and cell perturbation,
we evaluate BioCoLoop with ten simulated laboratories against single-laboratory

## V2-02 / P1 / xref 708 / Highlight

批注：fixed model， client，这类表示相同含义的用词需要统一，而且尽可能用常见的词汇

锚点：fixed models,

## V2-03 / P1 / xref 710 / Highlight

批注：这句话的引入太快了，我感觉逻辑应该是：AI 驱动的生物研究很有价值，（可以引用一下最近cell的一系列工作），说一下趋势正在从手工设计模型，向self-improve演进。现有研究范式主要专注单个场景，有一定局限，因为它忽略在Bio场景上有一个重要的挑战，就是数据共享，

我们这个文章旨在探究，在不共享数据的情况下，能否通过collabrate 假设提出、模型架构设计等经验，使得这部分自进化的经验可以彼此增益？

锚点：Privacy and data-sharing constraints often require these measurements to remain at their original institutions

## V2-04 / P1 / xref 724 / Highlight

批注：这不是互补的任务，而是setting的不同

锚点：complementary approaches.

## V2-05 / P1 / xref 722 / Highlight

批注：最好不用couple，或者combine，会让人觉得我们是A+B，直接叙述我们的框架和核心创新即可

锚点：couples these interfaces in a two-level research cycle.

## V2-06 / P2 / xref 745 / Highlight

批注：这个题目不准确，应该是AI+bio settingh或者范式的区别

锚点：Figure 1: Three ways to use biological measurements.

## V2-07 / P2 / xref 742 / Highlight

批注：建议参考其他论文，分点来写

锚点：Our contributions are threefold. First,

## V2-08 / P2 / xref 743 / Highlight

批注：这个写的是你做了哪些实验，不是贡献，贡献应该是你做了这些实验说明了什么，除了方法有效之外，最好再加上做了实验有哪些发现

锚点：Third, we evaluate BioCoLoop across the three task families above. Controlled comparisons separate the effects of laboratory participation, proposal feedback and training-budget allocation. We also examine how performance changes with the research model, the number of participating laboratories, additional independent datasets and the number of research iterations.

## V2-09 / P2 / xref 762 / Highlight

批注：贡献应该是一个框架，文章写作的时候需要适当包装和抽象

锚点：we connect laboratory-local parameter fitting to distributed evaluation of executable model designs through a common biological research interface.

## V2-10 / P3 / xref 764 / Highlight

批注：因为是一个新的设定，所以开始需要用数学公式抽象地先说明，输入输出是什么，期望得到什么样的效果，便于读者理解

锚点：FRAMEWORK OVERVIEW

## V2-11 / P3 / xref 788 / Highlight

批注：补充必要的数学公式，说明网络参数的更新，以及模型Proposal等原则的更新规则

锚点：EVIDENCE-GUIDED PROPOSAL AND REVISION

## V2-12 / P4 / xref 780 / Highlight

批注：图中补充Outer和Inner之间的关系和数据流向，另外，这个图例有点糊，你看看能不能搞高清一点，可以去https://www.flaticon.com/类似的网站看看

锚点：BioCoLoop couples

## V2-13 / P4 / xref 790 / Highlight

批注：不建议用缩写，审稿人上来可能就直接先看图

锚点：DTI,

## V2-14 / P4 / xref 792 / Highlight

批注：这个位置需要改成K

锚点：10

## V2-15 / P5 / xref 793 / Highlight

批注：实验部分，一般需要介绍数据集，对比的方法，和评价指标（评价指标如果是常见指标可以不展开介绍）

锚点：DRUG–TARGET INTERACTION PREDICTION

## V2-16 / P5 / xref 795 / Highlight

批注：需要简单介绍任务设定，任务的目标是什么，输入和输出是什么，因为涉及多个子任务，读者可能并不熟悉

锚点：Benchmark contracts.

## V2-17 / P6 / xref 827 / Highlight

批注：AI感比较重，很多细节可以放在附录

锚点：The task reference is a ProteinTalks-derived observed-response eﬀicacy head: protein and drug con- volutional branches followed by a 64–32–1 classifier, trained from random initialization on observed 6h/24h responses and Morgan features. A 24h linear/Morgan model provides a complementary non- neural reference. Average precision (AP) is primary; AUROC, binary cross-entropy and accuracy at 0.5 are secondary. The 148-condition test role is evaluated after the development-selected checkpoint is frozen.

## V2-18 / P7 / xref 844 / Highlight

批注：（无文字，保留高亮锚点）

锚点：324
325
326
327
328
329
330
331
332
333
334
335
336
337
338
339
340
341
342
343
344
345
346
347
348
349
350
351
352
353
354
355
356
357
358
359
360
361
362
363
364
365
366
367
368
369
370
371
372
373
374
375
376
377
Under review as a conference paper at ICLR 2027
target-only control uses the same architecture. A separate analysis retains three within-study mtPTDS
contexts. Appendix B specifies source filtering, losses and all source combinations.
The proposer comparison uses Qwen2.5-7B-Instruct and gpt-5.6-luna across all five endpoints.
Both explore the same twelve designs in six proposal slots, with test prefixes at 0, 1, 2, 4 and 6.
A second, longer study explores 36 designs in 24 slots on proteomics and the three cell endpoints.
Within each protocol, candidates receive 100 rounds from a common initialization, the first proposal
is shared, and direct/loop differ in access to evaluation history. Failed slots consume the budget.
DTI short-search results use seed 42; the remaining proposer studies use seed 61. The complete
trajectories and fixed-prefix scores allow task-specific analysis of search progress and saturation.
5. RESULTS
5.1 MAIN HELD-OUT PERFORMANCE
Table 1 places the three task families in one comparison: DTI and proteomics each contribute one
endpoint, and cell perturbation contributes three. Each cell reports mean ± sample SD over seeds 42–
44. This SD measures training/search variability on fixed partitions. The overall column averages
the five displayed endpoints within each seed before summarizing across seeds; it is a descriptive
summary, not a common biological metric.
Method
DTI
Proteomics
Cell perturbation
Overall
TAPB
AUROC ↑
PTPC
AP ↑
VCC
Top-1 ↑
Norman
Top-1 ↑
Tahoe
Top-1 ↑
Mean
5 endpoints
Task model (1 lab)
82.83 ± 1.22 25.05 ± 4.56 29.94 ± 0.00 25.56 ± 0.00 19.40 ± 0.00 36.55 ± 0.82
Qwen direct (1 lab)
89.89 ± 1.02 20.13 ± 0.07 21.09 ± 4.38 14.15 ± 0.00 15.42 ± 6.21 32.14 ± 2.02
BioCoLoop (10 labs)
93.76 ± 1.11 36.99 ± 0.22 31.54 ± 0.08 22.25 ± 0.45 22.39 ± 2.59 41.39 ± 0.60
Table 1: Main held-out comparison. Task models are TAPB (DTI), a ProteinTalks-derived efficacy
head (PTPC) and corrected scDEBART response heads (cells). Qwen direct proposes configurations
without evaluation history; BioCoLoop adds collaborative access and evidence feedback. Values are
mean ± sample SD, multiplied by 100; SD is not a confidence interval. Overall summarizes the five
endpoints within each seed. Bold and underline mark the best and second-best displayed means. The
shared training protocol is in Section 4; all six configurations, seed counts and secondary metrics are
in Appendix A.
BioCoLoop leads four of five displayed endpoints. TAPB reaches 93.76% random-test AUROC ver-
sus 89.89% for one-laboratory direct optimization, and proteomic AP reaches 36.99% versus 20.13%.
Relative to direct optimization, VCC, Norman and Tahoe macro Top-1 increase by +10.45, +8.10 and
+6.97 points. Norman’s best displayed result remains the one-laboratory fixed recipe at 25.56%, com-
pared with 22.25% for BioCoLoop. The complete system’s five-endpoint mean is 41.39, versus 36.55
for the fixed recipe and 32.14 for direct optimization. The main comparison measures collaborative
access and research jointly; the following controls separate them.
5.2 DOES FEEDBACK IMPROVE THE ALLOCATION OF TRAINING COMPUTE?
This experiment asks whether early development measurements help allocate a fixed training bud-
get. The candidate designs and laboratory data are identical. Uniform allocation trains every design
equally; the evidence-guided loop screens all designs and promotes a subset using current perfor-
mance and learning progress. Table 2 therefore measures training allocation with proposal generation
held fixed.
Across 12 newly executed proteomics/cell task–seed comparisons, the loop wins four and ties eight.
Norman improves from 11.48% to 22.32% macro Top-1, a +10.84-point mean effect with hierarchi-
cal paired-bootstrap 95% CI [4.54, 17.73]. Tahoe improves by +1.99 points, with one win and two
ties; VCC and proteomics tie. On Norman, a promoted low-learning-rate residual design continues
improving beyond the uniform method’s stopping point. Concentrating validation on promising can-
didates improves the final predictor at the same total training budget. The DTI development replay
7

## V2-19 / P7 / xref 843 / Highlight

批注：强烈建议看一下之前ICLR的写法，results不会单独成一大章，在写experiments的时候就会顺便写了

另外，这个表可以展开一下，把task model展开，写出来具体的名字，这样还可以把他们论文里面引用的其他方法的性能写进来，因为一个模型只能做一个场景，其他场景就写小横线

其实我现在有一个新的想法，就是这几个任务其实就是不同形式的数据集，他们之间能否互相增益呢，这样我们就变成一个模型了，而不是一些子模型，优势更突出

锚点：RESULTS 5.1 MAIN HELD-OUT PERFORMANCE Table 1

## V2-20 / P7 / xref 845 / Highlight

批注：可以适当用柱状图等展示，突出明显的增益

锚点：DOES FEEDBACK IMPROVE THE ALLOCATION OF TRAINING COMPUTE?

## V2-21 / P8 / xref 856 / Highlight

批注：超参分析，需要做图

锚点：HOW DO LABORATORY COUNT AND INDEPENDENT SOURCES

## V2-22 / P9 / xref 864 / Highlight

批注：看起来很多数值完全一样，这个是什么问题，还没做完吗？ 在试验分析部分，除了简要说明实验的结论，还需要用文字写一些分析，即你认为为什么会是这样

锚点：Completed research-model and feedback ablation in the original 12-design,

## V2-23 / P9 / xref 862 / Highlight

批注：可以准备匿名链接，然后开源/直接承诺开源，前者更好

锚点：Section 3 specifies

## V2-24 / P9 / xref 861 / Highlight

批注：这个要比较谨慎，需要看一下其他AI4AI的论文这部分是怎么写的

锚点：AI USE STATEMENT

## V2-25 / P13 / xref 866 / Highlight

批注：如果写这些，你的论文必须要提供代码

锚点：The reported study uses core_v3.py, run_v3.py and research_v2.py.

## V2-26 / P13 / xref 867 / Highlight

批注：D是什么含义，需要说明

锚点：D01–D11

## V2-27 / P25 / xref 901 / Highlight

批注：考虑放在正文中

锚点：Figure 3: Development selection (upper panels) and held-out performance (lower panels)
