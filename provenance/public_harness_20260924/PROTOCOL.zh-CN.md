# 两个公开 research harness 的主表扩展

用户已选择“任务适配版，优先完成主表”。新增比较对象是 **AI-Scientist-v2** 和 **AI-Researcher** 的任务适配实验控制器，不是开放式写论文能力评测。

## 比较设计

| 项目 | 所有新增基线共同设置 |
| --- | --- |
| 任务版本 | 现有主表：BindingDB/TAPB、PTPC、VCC、Norman 双基因、Tahoe 药物扰动 |
| 数据访问 | 同 BioCoLoop，10 个实验室；训练、开发和评价划分不变 |
| 科研语言模型 | 本地 Qwen2.5-7B-Instruct；temperature 0.7，top-p 0.9，每次最多生成 512 tokens |
| 可修改范围 | 原主表 V3 的 12 个配置，不使用另一个消融研究的 36 配置空间 |
| 搜索预算 | 新训练 D00 参考模型，再给 6 个提案位置；重复、格式无效和数值失败占用位置 |
| 候选训练 | 每个有效新候选从相同任务/seed 初始化，10-lab、100 rounds；原训练器不改动 |
| 选择规则 | 同原协议：开发集主指标优先、loss 打破平局；由可信执行接口统一选择 |
| 重复 | 固定 seeds 42、43、44；两个框架 × 五个端点 × 三个 seed = 30 个研究运行 |
| 评分 | 各任务现有 scorer；DTI 同时保存 random、unseen-drug、unseen-protein 三种评价 |
| 成本 | 保存逐次语言模型调用和训练记录；相同的是提案/候选训练预算，不声称语言模型总调用数相同 |

一次研究运行最多拟合 7 个预测模型。未完成三个指定 seed 的单元格不能包装为三次运行的均值；先保留 N/A。另外提供完全匹配 seed 42 的独立预览：已有方法和新增方法都只取 seed 42，不混入其他 seed 或三次均值，以便先查看全端点比较。

## 保留了哪些原生机制

- **AI-Scientist-v2**：调用原生实验管理器、树搜索、draft/debug/improve 路径、实验评审、journal 与摘要；实验执行替换为受限任务接口，图像评审和内部额外 seed 复验关闭。
- **AI-Researcher**：执行原生 InnoFlow 的构想、选择、计划、实验实现、评审交接、提交和迭代分析流程；保留 MetaChain 的工具调用/上下文状态机制。按六次提案预算适配迭代次数。
- 两者均去掉当前固定生物任务不使用的文献/网页检索、任意 shell/生成代码执行和论文生成。原生输出经结构化解析后请求可信训练器，原始输出和失败尝试均保留。

六次提案是**全局预算**，不是要求每个原生阶段恰好执行一次。原生流程可在同一阶段提出多个请求；重复或无效请求同样收费。预算耗尽后正常结束研究，保留开发集选出的最佳有效模型；若所有提案均无效，则保留已实际训练的 D00。预算终止不意味着跑完原框架的全部研究与写作阶段。

固定候选空间意味着这里检验的是公开框架的研究控制流程在统一任务接口上的表现；表格行名和方法描述将明确标注 task-adapted。

## 版本与产物

- AI-Scientist-v2：`96bd51617cfdbb494a9fc283af00fe090edfae48`。
- AI-Researcher：`f9a6f8480860c193afff600eeffe3defcee8a978`。
- 新代码：`/liziqing/yukai/AI4AI4Cell/extensions/public_harness_20260924/`。
- 正式队列：`/liziqing/yukai/AI4AI4Cell/results/public_harness_20260924/formal_v5/`。四个已完成的 AI-Scientist-v2/seed42 运行通过符号链接引用原 `formal_v3` 中未经改写的封存结果；不重训、不移动原始证据。此前工程试运行及 v3/v4 中未完成的 AI-Researcher/PTPC 运行保留原始记录，不提供论文分数。
- 监控状态：正式队列根目录的 `supervisor_status.json`。
- 每次运行保存：`config.json`、`run_status.json`、`model_calls/`、`native_controller/`、`development/`，完成后另存 `heldout/`。
- 评价后独立重算保存预测的分数，只有验证通过的完整运行进入新增主表收集器。原有六组 factorial 对照及其发布脚本保持独立。

队列采用最多 180 个**预留 GPU·小时**、24 小时上限，为试运行预留余量。计费式记录为“为该子进程预留的 GPU 数 × 运行墙钟时间”，不是 GPU 算子实际利用率测量。失败的基础设施运行不自动当成科学负结果，也不无限重试。

队列创建时一并计入此前正式运行和 4.0 GPU·小时的工程试运行预留（覆盖原 3.0 小时预留及 v4 的额外成本）。手动启动的 AI-Scientist-v2 Tahoe/seed42 与 AI-Researcher PTPC/seed42 存在资源共享时段，仍分别按八卡记账，因此这部分是保守预算核算，不是独占硬件下的速度基准。模型调用数、token 数和实际候选拟合数另外逐项记录。

AI-Researcher 的文本工具桥接规范化含明确工具名及参数的单一调用，包括标准 function/name 形式和唯一工具名作为键的对象；参数绑定、默认值和调用错误交由真正的原生函数处理。不选择模糊或多个调用，不补造参数。v3/v4 的兼容失败均未封存开发选择或检查测试集分数。接管及成本依据保存在队列的 `ADOPTION.md`。

新队列开启 `--continue-controller-failures`：仅对明确定义的 AI-Researcher 工具格式/阶段完成失败记录 N/A 并继续独立任务，不自动重跑或评价部分选择；源码、数据完整性及训练基础设施错误仍停止。包含未完成运行时最终状态为 `FINISHED_WITH_INCOMPLETE_RUNS`，不是全部完成。

## 公开源码说明

AI-Scientist-v2 的该版本采用 The AI Scientist Source Code License 1.0；分发相关适配材料时保留完整许可，并在论文的基线方法说明中明确其使用范围。它用于新增实验基线，不用于自动生成本文。AI-Researcher 的 setup.cfg 标记 MIT，但该固定版本没有 LICENSE 正文；这里不分发其完整源码，也不补造许可文件。

本文件是执行协议，不是完成报告。实时完成数以队列状态和已通过验证的 heldout 产物为准。
