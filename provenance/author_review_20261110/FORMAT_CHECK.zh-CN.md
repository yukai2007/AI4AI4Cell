# ICLR 2027格式核对

核对日期：2026-11-10（Asia/Shanghai）。官方来源：[Author Guidelines](https://iclr.cc/Conferences/2027/AuthorGuidelines)、[2027模板](https://media.iclr.cc/Conferences/ICLR2027/iclr-2027-style-files.zip)、[AI use policy](https://iclr.cc/Conferences/2027/AIPolicyForAuthors)。

| 项目 | 本轮落实 |
| --- | --- |
| 当前官方模板 | 根目录conference `.sty`/`.bst`、natbib和fancyhdr与下载的2027官方包逐字节一致；未改模板 |
| 页数 | 按rebuttal正文最多10页核验，计入结论续页；附录在参考文献之后 |
| 页面和版芯 | 官方US Letter与5.5×9 inch版芯；PDF页面几何核验，未另改页边距或版芯 |
| 字体和字号 | 官方示例`times`包配合T1编码；PDF实测正文为Times兼容Nimbus Roman、标称10pt；排除字体回退 |
| 间距 | 删除自设全局caption/float间距及列表段间距压缩；采用官方样式默认值 |
| 匿名审稿 | 保留Anonymous authors、ICLR 2027 under-review页眉和行号；检查正文、PDF元数据及链接的匿名性 |
| 声明 | 保留独立的Reproducibility、Ethics及必需AI use声明，位于正文后；AI使用范围与研究实际一致 |
| 文献和图表 | 官方bibliography样式；核对编译引用、标签、图表位置、字形与溢出；全部PDF页面渲染检查 |

模板包SHA256：`0d940dfa9398ae99a18f24a85a8a683f367204b6af6d17d2899e60a67102529e`。实际编译页数、字体、源码绑定和检查结果由`build_receipt.json`记录。

复核命令（在`paper/`）：

```bash
python tools/build_author_review_tables.py --check
/liziqing/yukai/project_collab_auto_research_cell_federated/.tools/tectonic-0.16.0/tectonic \
  --only-cached --keep-intermediates --keep-logs --outdir build main.tex
python tools/finalize_author_review.py --pdf build/main.pdf --log build/main.log
```

首次安装编译依赖时需要联网取得Times/T1字体包，之后可用上述缓存构建。官方原始模板包随本目录保存为`iclr2027-style-files.zip`，发布检查直接读取它作逐字节比对。
