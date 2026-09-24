# BioCoLoop 论文配图：PPT 修改入口

本文件夹集中提供当前论文 **5 张图** 的可编辑 PowerPoint 文件。每个文件只有一页，对应一张论文图。直接编辑 PPT 即可，不需要修改代码。

## 应该打开哪个文件

| 论文位置 | 图的内容 | 请编辑此 PPT |
| --- | --- | --- |
| Figure 1，Introduction；当前 PDF 第 2 页 | 三种研究范式的对比 | [Figure_1_research_paradigms.pptx](Figure_1_research_paradigms.pptx) |
| Figure 2，Method；当前 PDF 第 4 页 | BioCoLoop 内外层流程、实验室和下游任务 | [Figure_2_framework.pptx](Figure_2_framework.pptx) |
| Figure 3，Results；当前 PDF 第 8 页 | 实验室数量 K 的敏感性曲线 | [Figure_3_laboratory_count.pptx](Figure_3_laboratory_count.pptx) |
| Figure 4，Results；当前 PDF 第 9 页 | 六轮搜索：development 与 held-out 曲线 | [Figure_4_short_loop.pptx](Figure_4_short_loop.pptx) |
| Figure 5，附录；当前 PDF 第 27 页 | 扩展至 24 轮的搜索曲线 | [Figure_5_extended_loop.pptx](Figure_5_extended_loop.pptx) |

页码对应 2026-09-24 的 28 页英文稿；后续排版可能移动，**以图号和图内容为准**。

这次只新增编辑入口，没有替换论文中的正式图，没有修改结果、正文或英文/中文 PDF。

## 怎么改、怎么交回

1. 下载或直接打开上表中的 PPT。图 1–2 的文字、框和箭头都是原生对象；图 3–5 的每个子图都是原生图表，可选中后修改坐标轴、颜色和线型。
2. 使用 PowerPoint 的“选择窗格”定位被其他对象遮住的框或线。图表可以右键选择“编辑数据”；其中内嵌了 Excel 工作簿。**仅做语言和排版修改时，保持数据值不变。**
3. 请保留当前幻灯片尺寸。若要大幅改变比例，也可以，但交回时说明需要重新调整论文占位。
4. 另存为例如 `Figure_2_framework_edited.pptx`，把文件上传回来，或告诉我服务器上的完整路径。可以一次交回多张，不需要自行导出 PDF。
5. 我将直接从你修改后的 PPT 导出矢量 PDF，核对字体、裁切、文字/箭头重叠和曲线数值，再替换对应正式图；随后编译论文、检查分页并同步 GitHub。**不会重跑生成器覆盖你的手工修改。**

推荐交回信息：

> 请将 `/完整路径/Figure_2_framework_edited.pptx` 用作 Figure 2。只改了配色、文字和布局，曲线/结果数据未变。请更新论文并 push。

## “矢量图”与“可编辑 PPT”有什么区别

- 当前论文使用矢量 PDF，但 PDF 中的路径和文字不等于 PowerPoint 的框、箭头、图表对象。
- **图 2** 本来就有原生 PPT，这里是 `figures/biocoloop_framework_v2.pptx` 的逐字节副本。不要误改旧版 `figures/biocoloop_framework.pptx`。
- **图 1** 原来由 Matplotlib 生成；这里按相同内容和结构重建为原生框、文字和箭头。
- **图 3–5** 原来也是代码生成；这里按同一冻结结果快照重建为原生图表，保留全部曲线和实际横坐标。字体、刻度间距和边距可能与现有 PDF 略有差别；这是可编辑重建版，不是现有 PDF 的逐像素转换。
- 图 3 的 K=1、2、5、10 沿用原图的**等距类别轴**；图 4–5 使用数值横轴，保留非等距的 held-out 评估预算。
- **论文表格不属于这些配图**。主结果表和消融表是原生 LaTeX；可以直接在 Overleaf 改，也可以把期望的表头/排版修改发给我。

图 1 和曲线图使用 DejaVu Sans，图 2 使用 Carlito。若本机缺少字体，PowerPoint 可能替换字体；可安装对应字体，或先完成修改再由我在导出环境检查。不要以截图替代 PPT 原件。

## 正式图的替换映射（由我处理）

| 图号 | 当前论文引用 | 引用位置 |
| --- | --- | --- |
| 1 | `assets/paradigm_comparison.pdf` | `sections/01_introduction.tex` |
| 2 | `figures/biocoloop_framework_v2.pdf` | `sections/03_method.tex` |
| 3 | `assets/laboratory_sensitivity_v2.pdf` | `sections/05_results.tex` |
| 4 | `assets/completed_short6_search_v2.pdf` | `sections/05_results.tex` |
| 5 | `assets/completed_long24_search.pdf` | `sections/23_appendix_core_sensitivity.tex` |

## 源文件、检查与导出

- `source/draw_figure_1.js`：图 1 的 PptxGenJS 源码。
- `source/draw_figure_2.js`：当前图 2 原始生成器的副本；原位置为 `tools/draw_framework_v2.js`。
- `source/build_editable_result_figures.js`：图 3–5 的 PptxGenJS 源码。
- `source/result_figure_data.json`：图 3–5 的精确曲线数据，来源为 `tables/completed_ablation/snapshot.json`，不是手工抄录的舍入值。
- `validation/`：原生对象、曲线/内嵌表格一致性、渲染和溢出检查记录。
- `previews/`：各 PPT 的预览图片，可在打开 PowerPoint 前快速定位。

生成器仅用于从源码重建初始版本，不用于导入手工修改。图 1、3–5 使用 PptxGenJS 3.12.0（`jszip` 为其依赖），原图 2 的生成器使用 4.0.1。手工改图和导出 PDF 均不需要 PptxGenJS。

如需先在当前服务器预览自己的改稿，可执行：

```bash
python3 figure_editing/export_preview.py /完整路径/Figure_2_framework_edited.pptx
```

该命令将导出到独立临时目录，并显示路径、字体与溢出检查结果；**不会发布、不会覆盖 PPT、不会替换论文图**。它复用本仓库的 LibreOffice/Poppler 环境和已安装的 slides 验证工具。原有 `export_framework_v2.py` 是旧流程专用，不应直接用它的 `--publish` 选项发布任意手工修改稿。

最终手工改稿将作为新源文件保留，并重新记录其哈希和导出来源，不冒充由旧代码生成。
