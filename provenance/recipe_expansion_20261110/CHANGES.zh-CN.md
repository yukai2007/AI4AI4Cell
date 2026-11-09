# 扩展配方后的模型性能与history效果

日期：2026-11-10（Asia/Shanghai）。接续panel修复版本`b80eeea`。用户明确基线为同访问、同预算随机搜索，并允许扩大配方自由度。

## 核心结果

分数乘100；新两任务为三个head训练/controller seed的均值，条件于同一个原seed42起点。细胞沿用既有独立协议，不与新分数合并求均值。

| 类别与协议 | 变体 | 模型分数 | 对应Random | 差值/pp |
| --- | --- | ---: | ---: | ---: |
| DTI，新36配方温启动 | Luna Direct / Raw / Structured | 94.368 | 94.316 | +0.053 |
| 蛋白组，新36配方温启动 | Luna Direct | 39.017 | 38.655 | +0.361 |
| 蛋白组，同一完整新协议 | Luna Raw / Structured | 38.572 | 38.655 | −0.083 |
| 细胞，既有gene-disjoint研究 | Qwen Structured | 22.888 | 22.668 | +0.220 |

**已有三类任务的过线模型变体，但不能说history已经三类都胜出。** 新蛋白组Direct是无历史反馈的提案变体，并且与原offset GP-EI每个seed选择同一checkpoint。预先指定的主对照Luna Structured−Random只在新DTI胜出，蛋白组未胜出。不会在测试后将Direct改称history或替换主对照。

- Luna DTI Structured−Random：+0.052662 pp，三seed均正；条件95%区间[0.030981,0.077103]。
- Luna蛋白Structured−Random：−0.083061 pp，区间[−2.024697,2.233679]，两正一负。
- Qwen DTI：+0.035194 pp，区间[0.018485,0.054071]；蛋白：−0.039809 pp，区间[−1.616228,1.579192]。
- 既有细胞Structured−Random：+0.220041 pp，gene-cluster区间[−0.289605,0.738166]。不是本轮新增细胞训练。

区间均条件于已拟合/已选模型，不能解释为更多controller/backbone重复的不确定性。Direct蛋白组的+0.361是描述性点估计，不据此宣称显著优势。

## 真正增加的自由度

36配方来自3学习率×3预测头×2训练目标×2日程。学习率1e−5/1e−4/1e−3；原预测头或32/128宽零输出初始化residual；BCE或BCE+0.1本地正负排序loss；constant或cosine日程。

蛋白组使用完整12,390维实测6h/24h响应与Morgan特征，full变体可更新完整原Conv1d/MLP，residual变体从完整输入学修正，不再只在64维融合表征上改分类层。候选可训练参数为421,325–1,610,957。DTI保留原TAPB编码器，适配per-confounder分类头，可训练参数66–4,546。起点统一使用原fixed D00，没有按旧test最佳配置挑编码器。

原始端到端主表和所有旧结果保留；新温启动分数不替换它们。新协议还把开发选择改为pooled AUROC/AP并保留十panel诊断，所以不是仅改变单个因素的消融，也不是新的生物划分。

## 执行与完整性

- 正式216次全新fit：2任务×36配方×seeds71–73，各20个全客户端round，开发round2/5/10/20选checkpoint。每个Luna搜索含D00+6有效请求，共140round。
- DTI每搜索28,000优化步、7,020,860样本暴露；蛋白组1,400步、54,040暴露。不同head的FLOPs/时间不同，未声称FLOPs相等。
- 同访问Random、Direct、Raw、Structured、Fixed、两个GP-EI offset全部保留；Random精确积分C(35,6)=1,623,160子集，另有共同首槽与实际有效fit数匹配控制。它是单预测器策略期望，不是集成或独立训练重复。
- 原64维容量pilot110fit、共同历史起点拟合、共享特征提取和中断的工程调用另计。正式fit设备墙钟合计：DTI 1,714.75秒、蛋白115.60秒；不是整个研究的总成本。
- 正式模型完成：Qwen182次物理生成，Luna101次，含修复。Luna所有逻辑槽有效；Qwen有失败槽，全部占预算，完整数量和token成本见`summary.json`。
- 全部12个task/seed/proposer seal核验后由/root生成新评分授权，统一计算全部216候选测试分数。保存预测独立重算通过。
- 本次测试集早已在历史研究中暴露，故为回顾性新配方研究，不称新盲测。没有据新测试分数更换recipe、seed、prompt或停止点。

## 版本与复现

正式训练：`results/recipe_expansion_20261110/v2`；训练源码`extensions/recipe_expansion_20261110_v2`。正式搜索：`results/recipe_expansion_20261110/search_compact_v1`；源码`extensions/recipe_search_compact_20261110`。评分源码`extensions/recipe_expansion_eval_20261110/evaluate.py`；数据和预测只在本地。

源目录`v1`、`v2/search`、`luna_v1`中的容量/上下文/CLI故障轨迹完整保留为工程记录，不作为科学重复。完整版本说明在源码包内`docs/recipe_expansion_20261110/VERSIONS.zh-CN.md`。新的可逆panel编码保留四个开发评估点的所有panel数值与标签；每个请求检查解码等于原card，没有截断或指标舍入。

在`paper/`运行：

```bash
/opt/conda/envs/LDA/bin/python tools/package_recipe_compact.py --check
python tools/finalize_recipe_expansion.py --pdf build/main.pdf --log build/main.log
```

当前构建/页码/哈希见`build_receipt.json`、`TABLE_MAP.zh-CN.md`。源码和聚合证据打包为`experiment_sources.zip`，不含生物矩阵、逐样本预测、checkpoint、权重或凭据；仍需原项目和已授权数据，不是standalone包。

没有合并main、没有更新Overleaf、没有提交OpenReview。三份回复仍是作者审阅草稿。
