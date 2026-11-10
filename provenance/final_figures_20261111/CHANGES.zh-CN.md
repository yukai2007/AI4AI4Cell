# 最终稿：主图替换（2026-11-11）

- 图1（§1）换为 `assets/paradigm_comparison_v4.pdf`；图2（§3）换为 `figures/biocoloop_framework_v4.pdf`，宽度改为整栏 `\linewidth`。两图的源文件均为作者提供的 SVG（与 PDF 同名并排存放）。
- 转换方式：`python3 tools/svg_to_pdf.py in.svg out.pdf`，用 librsvg/cairo 输出矢量 PDF，所有字体嵌入并子集化，无 Type 3 字体。
- 图2图注按新图内容改写，依次为 Propose / Compile / Fit + evaluate / Select、evidence $\mathcal E_t$、raw data stays local、held-out test。
- 正文的其余文字、表格和数字与 `dde879c` 相同，没有新增训练或评分。
