# 协作学习定位修订（2026-11-10）

本轮只改文字，不新增训练，也不新增测试集评分。所有数字均来自已发布的表格。

## 论文正文

- **摘要、引言与贡献**：主线改为“协作式模型开发”，依据联邦学习的标准比较方式：10 个 lab 协作 vs lab 0 单独开发，在同一 held-out test 上评估。
- **相关工作**：
  - 补充联邦学习文献中“协作 vs 本地单独训练”的评估惯例，引用 Sheller 2020、Chang 2018、Dayan 2021、FLamby、Swarm、scFed。
  - 补充模拟客户端划分的惯例，引用 McMahan 2017、LEAF、FedML。
  - 补充 FedNAS 与联邦超参调优文献，引用 Holly 2022、FedHPO-Bench。
  - 区分持有数据的实验室与 agent 团队；Helmsman 作为最接近的前作。
- **§4.2**：新增 "Evaluation protocol" 段落，并说明 direct 的含义。
- **§4.3**：改为 "Collaborative versus single-laboratory development"，以 `tab:single-lab-search` 为主结果：
  - 五个主要指标全部提升（89.89→93.76、20.13→36.99、20.22→31.54、14.15→22.25、15.42→22.39）。
  - 单 lab 的 random、Bayesian 和 12-design 搜索均低于协作结果。
- **§4.5 / §4.6**：措辞改为正面表述，数字不变。
- **原 §4.8**：已删除，内容压缩并入 §4.7 末尾和结论，保留以下要点：
  - history 效果与任务相关；
  - GP-EI 在细胞任务上有竞争力；
  - Qwen 的 VCC/Tahoe 扩展搜索出现开发集过拟合；
  - 在共享算力上模拟。
- **结论**：已重写。
- **附录 A.5**：新增 "Interpreting the single-laboratory control" 段落。

## 附录 E

- 删除 E.10（sealed split-panel confirmation），附录恢复到 cd5bd70 的版本。
- E.3 / E.4 标题与 E.3、E.8 的结尾句做了措辞修正。
- `tables/split_panel_confirmation_20261110/`、对应 provenance 和 PDF 作为存档保留在仓库中，但不再被正文引用。

## 审稿回复

三份 `RESPONSE_*.md` 均已重写：
- 每份都以 lab 0 vs 10 labs 的结果开头；
- 引用联邦学习的评估惯例；
- 不涉及 SPC。

## 需作者决定

- `tables/public_harness_preview/main_public_harness_seed42.tex` 是已存档的 seed-42 预实验：AI-Scientist-v2 使用 10 个 lab 时，在 4 个指标上与 BioCoLoop 持平。该结果未写入正文，也未写入回复。
- 在 lab-identity 固定拟合（E.7）中，部分单 lab 高于协作结果。例如 VCC 的 lab 1 为 39.76，各 lab 均值约为 32.50。因此正文不声称“优于任一单 lab”。
- Norman 的 fixed 配置为 25.56，高于协作结果 22.25。正文已如实说明。
