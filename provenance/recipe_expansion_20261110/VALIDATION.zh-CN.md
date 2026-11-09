# 扩展配方版本核验

日期：2026-11-10。前版基点为`b80eeea553a5610a5819e4cc790a71287c04fb9e`。

## 实验与评分

- 正式训练216/216完成：DTI与蛋白组各36配方×3个新head训练seed。110次开发容量pilot单独计费；中断控制器不作为科学重复。
- 两个提案模型×两任务×三seed的12个selection seal全部核验；之后统一授权测试评分。216份保存预测的主指标、开发选点及绑定哈希独立重算通过。
- 最终分析入口为`tools/report_recipe_compact.py`，注册哈希`b32846ab0fa3245519787cc0150cec9378d6ee574b2cb9d640fe4d424893efc4`。主对照Luna Structured−Random保持不变，蛋白组负差值完整保留。
- Random精确子集积分、共同首槽、按实际有效fit数匹配的敏感性控制和两个GP offset均保留。新研究的budget是请求/训练轮数/优化步/样本暴露；未宣称不同head具有相同FLOPs。
- 测试集曾在旧研究中暴露。本轮是回顾性温启动研究，不是新盲测或三个独立backbone训练；Direct蛋白组的过线不能解释为history优势。

## 测试

在项目根目录运行，22项通过：

```bash
/opt/conda/envs/LDA/bin/python -m unittest \
  extensions.recipe_expansion_20261110.test_recipe \
  extensions.recipe_expansion_20261110_v2.test_recipe \
  extensions.recipe_search_compact_20261110.test_packet -v
```

涵盖随机搜索精确积分及tie/shared-first情形、同起点架构、单类面板、排名目标、冻结梯度、Direct无结果泄漏、Raw/Structured事实一致、可逆panel编码、GP预算以及CLI已完成事件的读取。

在论文根目录运行，15项发布/归档测试通过：

```bash
PYTHONPATH=tools python -m unittest \
  test_finalize_fbhk_followup test_package_fbhk_followup -v
```

另运行了旧`test_appendix_compaction.py`：1项通过，4项失败。其固定措辞和旧表格包含位置断言在前版提交也同样失败；已用临时目录中的前版原文件复核，记录见`legacy_test_baseline.json`。没有修改旧测试来消除失败。首次发布测试命令缺少`PYTHONPATH=tools`产生的两个导入错误，在上述正确入口重跑后消除。

## 发布检查与版面

```bash
python tools/package_recipe_compact.py --check
python tools/finalize_recipe_expansion.py --pdf build/main.pdf --log build/main.log
git diff --check
```

生成表、源码包及manifest精确再现；发布检查确认153个旧图表资产逐字节不变，旧输入图完整保留，仅增加两张新表。旧38/41/39页版本与回执受保护。除四份更新的回复草稿外，所有已跟踪旧provenance文件逐字节不变，包含72-checkpoint/720-panel修复证据；360-fit等既有研究继续通过原校验。

论文41页，正文结束于第9页；三位审稿人回复合计7页。已渲染并逐页检查论文和回复，新增两页与表格另作全尺寸检查；无溢出、缺字、未定义引用或重复label。PDF匿名性、页面几何和注释检查通过。输出哈希、表号/页码、回复长度见构建回执；未核实线上回复字符上限。

发布仅更新独立版本PDF和日常PDF，并推送现有rebuttal分支。main、Overleaf与OpenReview不在本次发布范围。
