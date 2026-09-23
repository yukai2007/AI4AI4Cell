# 第三独立蛋白来源：正式四臂 CPU 对照

本次扩展在保留原两源模型、数据和结果的前提下，将 Eckert 等的 decryptE 作为第三个独立辅助研究接入。四臂全部使用同一四头网络、seed 61、100 rounds 和目标 development checkpoint 选择规则；未调用研究语言模型，proposal slots = 0。

| 训练来源 | AP（%） | AUROC（%） |
| --- | ---: | ---: |
| PTPC target only | 34.978626 | 74.747475 |
| + decryptE | 35.026099 | 74.206349 |
| + Lin + Ruprecht | 35.314688 | 74.170274 |
| + Lin + Ruprecht + decryptE | 35.679742 | 74.278499 |

三源相比 target-only 的 AP 增益为 0.701115 个百分点；相比既有两源的 AP/AUROC 增益为 0.365054/0.108225 个百分点。target-only 仍取得最佳 AUROC。这是单 seed 固定设计的来源迁移对照，不是新增的 loop 或显著性证据。

四臂实际训练时间合计 101.208515 秒，watcher 全流程 131.842193 秒，GPU·小时 0、API 调用 0。独立复算对全部四组 AP/AUROC 等指标的误差均为 0，receipt 状态为 `COMPLETE_VERIFIED`。

## 原始证据与论文生成

- 运行：`results/supplemental_20260923/proteomics/seed61_slots0_cpu/`。
- 输出：上述目录的 `heldout/results.json`、`independent_rescore.json`、`definition.json`、`heldout/*_predictions.npz`。
- 数据与代码：`extensions/supplemental_20260923/proteomics/`，旧冻结两源目录未修改。
- 新表生成：在项目根运行 `python3 paper/tools/publish_supplemental_proteomics.py`。该脚本只读取 verified receipt、核对原始 results/definition 哈希后排版，不训练、不选择、不筛选来源。
- 本目录 `snapshot.json` 保留完整独立 receipt、源文件哈希、表格与生成器哈希。
- 论文位置：Appendix B.2，`tab:supplemental-source-clients` 与 `tab:supplemental-protein-three-source`。
- 旧两源加两次 proposal 的结果保留在 `tab:completed-protein-loop`，与新增 fixed-only 对照分开。

## 来源与客户端

PTPC clients 0–9 仍是同一目标语料的分片；Lin、Ruprecht、decryptE 分别占 clients 10、11、12。Lin 包含 A549/H292/PC9/PSC1；Ruprecht 包含 A549/Calu6/Calu1/2030/2122；decryptE 为 Jurkat 的五个剂量。一个研究内的 cell line 或剂量不是额外独立研究。

decryptE 最终为 124 个不同化学实体、620 条剂量条件：source train 495 条/99 实体，dev 125 条/25 实体。12 个目标 dev/test 重叠实体、6 个缺乏明确别名支持的内部名冲突和 2 个公开身份/结构注释冲突在训练前排除。每项原注释与原始矩阵保留；没有按训练或测试效果筛选。全部同化学图剂量放在同一 source split，规范化仅拟合 source train。

## 论文引用核验

- decryptE 主论文：[Nature Biotechnology DOI 页面](https://doi.org/10.1038/s41587-024-02218-y)，Methods 与公开 supplement 已核验。2024-05-07 在线发表，正式卷期为 43:406–415（2025）；BibTeX key 为 `Eckert2024DecryptE`，year 使用卷期年 2025。
- 官方数据：[MSV000093659](https://massive.ucsd.edu/ProteoSAFe/QueryMSV?id=MSV000093659)。原始 145 个主矩阵包含 Vincristine 的一个人工分类重复副本，使用统一标准目录的 144 个文件。
- Virtual Cell 背景：[作者 arXiv v2](https://arxiv.org/abs/2409.11654v2)，以及 [Cell DOI](https://doi.org/10.1016/j.cell.2024.11.015)。引用 `Bunne2024VirtualCell`，Cell 187(25):7045–7063（2024）。

两条新引用单列 `paper/references_v2.bib`，原 `references.bib` 未重写。文学综述技能要求的 paper-writing/general-writing 依赖在当前安装中缺失，采用已核验一手来源、精确协议与结果绑定的写作 fallback。
