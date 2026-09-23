# BioCoLoop 全局更名记录

日期：2026-09-23。原品牌：AI4AI4Cell。新品牌：**BioCoLoop**。

正式标题：**BioCoLoop: Collaborative Agentic Research for Biological Model Improvement**。

Bio对应生物任务，Co对应跨实验室协作，Loop对应提案、执行、评价和反馈的研究循环。名称不再将框架限定为细胞研究，也不把可审计性当作唯一主张。不是新增算法或新增结果的版本。

## 已统一的当前展示

- 英文标题、摘要、正文、图注、主表方法名。
- Figure1范式图；Figure2可编辑PPTX、矢量PDF与预览。
- 中文版封面、页眉、正文、主表、图、PDF metadata及输出名称。
- 当前README、项目入口、状态与概览，现用表格/图形/中文生成器及测试。
- 新主源文件 `biocoloop-main.tex`，`main.tex`继续作为Overleaf入口；旧 `ai4ai4cell-main.tex`成为兼容入口，不再包含一份旧论文。
- 新阅读副本 `output/pdf/BioCoLoop_manuscript.pdf` 与 `output/pdf/BioCoLoop_中文伴读版.pdf`；本地 `manuscript.pdf`同步更新。

## 刻意保留的历史标识

现有GitHub仓库地址、Overleaf连接和实际存储目录不迁移。冻结的实验schema、arm ID、源文件真实路径、数据/模型哈希、历史批注、用户原始PPT、旧版PDF及已签发收据均保留。它们是已发生实验的标识，不应通过机械替换改写。

科学快照、完整proposal trace、全部数值表的前后核验在 `migration_verification.json`。当前主表只修改方法名，评分数字、粗体/下划线、误差和原始记录不变。五张结果图仅更改Creator品牌，图形和逐页像素不变，见 `figure_metadata_rename.json`。

图二的新派生记录明确 `source_text_identical=false`；允许的文字映射为框架名称及Federated→Collaborative，原图几何、箭头、图标、字体和其余文本保持不变。原始PPT未覆盖。

PDF/幻灯片技能用于新名称的版式及可编辑图检查。已对候选BioCoLoop、CoBioLoop进行精确词及生物研究语境检索，未发现明确同名结果；这只是命名筛查，不是商标或全球唯一性认定。BioCoRE已被既有生物协作研究平台使用，因此未选用（https://www.tcbg.illinois.edu/Research/biocore/）。

最终英文PDF、测试数和源码哈希见 `build_receipt.json`。历史科学实验完成范围保持前一交付版本，不因更名改变。
