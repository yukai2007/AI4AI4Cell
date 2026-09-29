# 最终投稿 PDF → GitHub 源码同步

## 基准与范围

本次以作者指定的 `5046_BioCoLoop_Collaborative_A (4).pdf` 为唯一文字基准，逐段迁回可编辑 LaTeX。原件保存在 [author_submitted.pdf](author_submitted.pdf)，SHA-256 为 `3bdd4251d9b201a1e9fbf6b94ffd72fc7092b0cc33a3afdcf72b4150b4407ec8`。GitHub 基准为 `3ce4b71`；不是用早期 agent 对照分支覆盖最终稿。

同步前已有未提交稿件修改，已备份到本机 `tmp/pdfs/author_final_20260930/pre_sync_sources.tar.gz`。无关的图稿候选、构建目录和旧 PDF 没有删除或提交。

## 最终 PDF 中的主要修改及落地位置

| 部分 | 作者最终稿相对原源码的变化 | 同步文件 |
| --- | --- | --- |
| Abstract | 将核心贡献收束为：共享模型更新与 laboratory-local development evidence。明确 inner fitting/evaluation、outer proposal revision，以及单独评测的 allocation policy；定量结果留在正文。 | `biocoloop-main.tex` |
| Introduction | 简化 AI 与生物数据分散的背景，提出“本地训练与评估如何共同支持模型开发”的问题；三条贡献对应框架、证据历史机制、跨任务实证。 | `sections/01_introduction.tex` |
| Related work | 更准确地区分已有协作训练、自动设计与研究 agent；以公共执行接口和持续历史记录说明本文定位。 | `sections/02_related_work.tex` |
| Method 3.1–3.2 | 定义完整 executable configuration、可信 coordinator、本地模型状态与标量评估返回；区分按训练样本聚合参数和按开发面板等权选择模型。补充不同来源私有预测头与共享编码器的角色。 | `sections/03_method.tex` |
| Method 3.3–3.4 | 用 Norman 的 D06→D08→D07 说明保留、慢收敛与拒绝如何进入历史；解释 screening 两项晋级标准。明确主表每候选 100 rounds，allocation 是独立固定候选实验。 | 同上 |
| Experiment setting | 清晰写出三个任务的输入、输出、数据划分、基模型和主次指标；保留 observed-response proteomics 和 five-option cell identification 的任务定义。 | `sections/04_experimental_design.tex` |
| Results | 展开 Qwen/Luna 结果、训练分配置信区间、两种蛋白质组跨来源协议、匹配条件数的细胞跨来源比较、K 变化与负样本池机制；定义共同 development target 和 proposal-prefix 分析。 | `sections/05_results.tex` |
| Conclusion | 分别总结参与实验室带来的数据/评估增量、历史改变搜索轨迹，以及独立训练分配收益，不把三个证据混成同一个增益。 | `sections/07_conclusion.tex` |
| Statements / Appendix A | 更新可复现材料表述，精简实现介绍，保留完整设计映射、初始化、预算、评分、诊断与不确定性说明。 | `sections/08_reproducibility.tex`、`sections/22_appendix_unified_protocol.tex` |
| Appendix B / C | 同步跨来源、lab 数量、六轮/24 轮搜索分析；精简公开 agent 适配与失败类型说明，保留上下文预算差异和未完成标记。 | `sections/23_appendix_core_sensitivity.tex`、`sections/24_appendix_public_harness.tex` |

## 额外修正：仅三处

1. **式 (4) 新记录下标。** 已有历史为 `E_t = {e_1, …, e_t}`，下一条记录应为 `e_(t+1)`。同步修正正文和递推式，不改变算法。
2. **五选一随机 MRR。** 均匀随机排名的期望为 `(1 + 1/2 + 1/3 + 1/4 + 1/5) / 5`，乘 100 后是 **45.67**，不是原稿的 46.00；同时写清 MRR 的展示尺度。这不是修改实验得分。
3. **附录 C 的旧失败示例。** 删除“seed-42 Qwen AI-Scientist-v2 DTI 未封存、未计分”的旧案例句子，避免与当前主表该行的完整三种子汇总冲突。保留现有部分完成/未完成单元格及其类型、重跑预算和记录，不将失败记作零分。

另将 `49-50` 统一为 LaTeX 数值范围的短横线。除此之外不追加论断、不重写作者结论。

## 结果与验证

- 不启动或重跑训练；不改动 `tables/`、`assets/`、`figures/` 的任何科学产物。
- Qwen、Luna、AI-Scientist-v2、AI-Researcher 的现有结果与标准差完整保留；星号、部分完成符号和未计分标记保留。
- 训练分配的 4/8/0 与历史反馈实验的 1/8/1、0/7/1 分属不同协议，按最终 PDF 如实保留。
- `tools/verify_author_final_sync.py` 对全部 31 页提取文本逐词核对：只允许上述声明的修正及排版范围符号标准化；核对 9 页正文、匿名元数据、编译交叉引用和科学产物未变。
- [verification.json](verification.json) 记录原件、编译 PDF、源码及图表/结果产物哈希。排版检查覆盖标题摘要、两张框架图、主表、正文结束页和附录。
- 原有措辞锁定测试按作者最终语言更新，数值、预算、初始化、来源和复算记录断言未移除；另新增最终 PDF 同步回归测试。

## 后续注意

1. 原稿的 reproducibility statement 写明匿名材料随投稿提供。本轮核对的是本地及 GitHub 稿件与材料，不代表验证 OpenReview 上的附件；请作者确认投稿侧已上传。
2. GitHub 推送不等于 Overleaf 已自动拉取、编译，也不等于重新提交 OpenReview；以平台显示的实际文件为准。
3. 中文伴读版为先前版本的解释材料，本次不将其冒称最终 PDF 的逐段译本。
