# 精简稿仍需解决的实验问题

本轮仅修改呈现和组织，不新增训练、不改分数，不按结果正负筛选对照。下列问题需要保留在稿件中，因为它们直接约束核心结论或回应 FBhK；优化方向均为尚未验证的下一步，不能写成已修复。精简稿页码见同目录发布回执和表格定位文件。

## P0：直接影响 history 的中心结论

### 1. 同访问、同预算下，history 的优势尚不稳定

- 位置：正文 Table 3、Appendix B.9/B.10、E.1。
- 当前事实：短搜索十个配对为1升、8平、1降；长搜索八个最终配对为7平、1降。Norman/Luna为23.11，Direct/GP为22.30、Random为22.66；DTI Direct Luna/GP为94.60而History为94.27。
- 为什么必须保留：这些是审稿人明确要求的因果隔离对照，不能用十lab对一lab的增益替代，也不能只放Norman。
- 下一步：固定任务、数据、预算和模型，比较可验证的历史表示改动（配置差异、相对参考的效果、跨panel分歧），并在预先冻结的新划分上评估；不能用同一测试集反复选择prompt或候选菜单。

### 2. 新 structured history 改变了决策，但未胜过 GP-EI

- 位置：E.6结果表、E.7成本表、Figure 6。
- 当前事实：Direct 22.625、Raw 22.625、Structured 22.888、Random 22.668、GP-EI 23.152。Structured−Direct +0.263 pp，95% CI [−1.022,1.568]；三个seed两升一平。Structured−GP为−0.264 pp。
- 为什么必须保留：Direct、Raw、Random和GP分别控制反馈有无、表示形式和常规搜索解释；全部使用同一16-design研究，不能按胜负取舍。置信区间为给定已选模型的test-gene不确定性，不是额外controller重复的区间。
- 下一步：先用开发数据检查有效历史信息是否改变排序/探索、在哪些候选产生正确预测；在预先定义的验证机制下测试更有区分度的候选空间。扩大空间本身不保证history有效，须保持随机/GP及相同预算。

### 3. 开发集改进不总能转化为测试集改进

- 位置：正文4.8、E.2/E.3、B.9、Figure 5/6。
- 当前事实：原VCC/Qwen测试31.50→19.61，Tahoe25.37→13.43。equal-lab和pooled intervention-macro一致，不能归咎于该聚合口径。20套开发roster下，原优势变成VCC/Qwen平均−1.34 pp、Tahoe−1.33 pp，仅6/20和7/20为正；VCC/Luna Direct与History仍为+2.24/+2.89 pp，各12/20为正，不能将Qwen结果泛化到全部VCC设置。
- 新研究：所有18个非固定policy/seed终点超过各自D00，但seed62的D05仍出现dev+0.057/test−0.257 pp，K562也有场景级反向；没有证明分歧已消失。
- 下一步：在训练/开发侧预注册候选提案面板与独立确认面板，比较更广干预覆盖、多个开发roster及稳健选择规则；在原VCC/Tahoe的新grouped split复验。测试集仅用于最终评估。

### 4. 异质来源下，历史反馈更弱；跨panel信息有明确实现缺口

- 位置：E.4。
- 当前事实：蛋白Qwen Direct 37.83、History 34.31；细胞22.36、19.41。Luna蛋白Direct35.35、History34.94、enriched35.39；细胞三者22.88持平。
- 实现诊断：source-defined adapter先把十个target panels汇总到一个worker，外层`worst_client`因此等于primary mean，不表示最差panel。主要选择分数未变，但提案看不到应有的panel分歧。
- 下一步：保留既有primary selection score，额外正确传递panel数量、最差值、离散度及不确定性；用同数据、同预算的表示消融测试。这是优先级较高的实现修复，但不能预先保证测试增益。

## P1：影响贡献归因与场景适用范围

### 5. allocation相对uniform的收益，并非trajectory规则独有

- 位置：正文Table 2与E.5。
- 当前事实：Norman Uniform11.48、trajectory22.32（+10.84 pp），但Random promotion22.63、score-only21.70。Tahoe trajectory22.89优于Random21.95/score-only20.90；VCC Random22.49高于trajectory20.01。
- 为什么必须保留：删掉Random会把“较少候选充分训练”的效果误归因给特定trajectory门控。
- 下一步：检查不同早期学习速度下的预算分配，预先固定rung、候选总训练量与评价次数；比较random、score-only和trajectory，记录真实GPU时间。不通过削弱random预算制造优势。

### 6. 主表Norman不占优，且lab 0不代表所有实验室

- 位置：主表、A.1、E.8。
- 当前事实：主表Norman fixed25.56，高于十lab Qwen22.25、Luna22.69。新40-fit独立lab试验中，Norman lab0为十lab最高；十个独立lab均值17.67±5.84。
- 固定全量数据池时，Norman K=1/2/5/10分别为49.63±4.20、19.56±0.20、26.12±0.11、15.48±0.00（B.2）。K=1确实有全量target data，但优化步数与对比负样本池改变，不是主表全workflow的同计算量centralized对照。稿件已纠正“完全没有全数据池单节点参照”的旧表述。
- 未完成：各controller在lab0–9的全套轮换、DTI轮换、单lab补足十lab等量optimizer steps的控制。
- DTI同为100 rounds时，1lab/10labs分别为7,900/79,000 optimizer steps、501,000/5,014,900次样本暴露。因此相同rounds并不等计算量；尚未做1lab重复数据补足这些训练量的控制。
- 下一步：以预先规定的实验室集合报告完整分布；DTI先解决lab0-derived dictionary和初始化协议，再作严格私有lab轮换。实验室SD与训练seed SD分开报告。

### 7. 异源数据并非总有益

- 位置：Appendix B来源研究、E.4。
- 当前事实：同四lab、60训练干预时，VCC同源30.70、异源28.82。蛋白一study一lab的all-source AP从34.41到37.53；这是固定设计源迁移，不是history效果。旧两来源pilot所有Fixed/Loop持平。
- 下一步：检查源兼容性、测量面板、细胞数量和损失尺度；若设计源权重或源筛选，须在训练/开发侧选择并保留未筛选基线，避免测试后挑来源。

### 8. 分区与实验重复的证据范围有限

- 位置：B.1、E.1、E.6–E.8。
- 当前事实：十lab cache-search每endpoint只有一个训练seed；462个随机子集不是462次独立训练。新history研究为三seed固定gene-disjoint划分；40个lab试验为单seed固定模型。固定总数据的K变化还会改变本地步数和contrastive-negative池。
- 下一步：先解决机制与选择稳定性，再追加冻结协议的独立划分和重复。把访问量、分区数、训练步数与负样本池分别控制，不以“再加seed”代替机制修复。

## 不能用于替换当前证据的历史结果

旧线性蛋白Direct43.73±0.79、Loop44.48±1.90（平均+0.75 pp）保留于`tables/unified_v3/`；其模型与当前神经蛋白头不同，一个seed提高2.26、另外两个持平，不能贴回当前主表或B.9当作该模型的阳性重跑。旧表和原始预测未删除。

## 其他保留但不应作为强阳性宣传的内容

- A.2的PTPC例子仅由loss tie-break换配置，VCC保留D00；单个提案案例只解释执行流程，不证明history整体优势。
- A.3的DTI allocation结果仅为开发集replay，预算525 vs 520 rounds，不作为同预算held-out证据。
- A.4中未经任务训练的scDEBART head在Norman为7.5%，低于20%机会水平；这说明直接迁移的适配难度，不等于训练后的模型表现。
- B.2中部分源迁移CI跨零，三来源旧adapter的AP提升但AUROC下降；必须区分指标与adapter。
- Appendix D的单lab搜索相对协作模型在细胞上有正均值，但若干配对区间跨零，不能统一称为显著。
- Appendix C和主表保留公共框架未完成seed、context重试和service/tool失败；这些不能当作其原生框架能力不行的证明。

## 建议落实顺序

1. 修复异源adapter的跨panel反馈缺口，同时预先冻结同预算对照协议。
2. 在开发侧验证独立确认面板/roster平均的选择规则，优先解决大幅dev–test分歧。
3. 完成少量预注册的真实历史表示消融；完整保留Direct/Random/GP。
4. 机制明确后，再扩展逐lab轮换、独立划分与seed数量。

本清单不是新增实验的执行记录；本轮没有启动这些训练。
