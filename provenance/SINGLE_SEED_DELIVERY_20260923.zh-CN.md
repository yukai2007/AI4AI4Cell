# 单日预算下的论文交付状态（2026-09-23）

## 结论

主论文当前可以交付：英文稿 `manuscript.pdf` 已按最新正文编译，24 页，论文工具测试 44/44 通过；中文伴读版仍保留。主表使用已完成且独立重算的 seeds 42--44 held-out 结果，不能把它们降级为伪结果或 development 分数。

“只差多 seed”只适用于已经锁定的主表、现有 cell/proteomics loop 轨迹和已完成的相同协议敏感性；它不适用于两个仍单独列出的增强实验：DTI 的新 6-slot/native 短预算研究，以及外部独立 proteomics 来源迁移。后者目前只有来源身份闭包和可行性审计，没有训练结果，正文不把它写成已完成证据。

## 已锁定，可直接放入论文

- 主表：TAPB DTI、ProteinTalks observed-response、VCC、Norman、Tahoe 五个 endpoint，task model / Qwen direct / AI4AI4Cell，seeds 42--44。
- 现有 24-slot Qwen/Luna loop 轨迹、proposal validity、negative transfer、matched-compute racing 与 held-out 重算。
- cell/VCC 三个独立外部 collection 的 cross-source 证据，以及 ProteinTalks 同一 mtPTDS 研究内三个 context 的 within-study transfer；后者不称为三个独立研究。
- lab-count 的既有 PTPC、VCC、Norman、Tahoe 多 seed 快照；新增 native DTI seed61 的 participation K10 已完成（development primary 0.9239576），并保留 checkpoint/hash。

## 已结束但不完整、且不阻塞主论文

- native DTI seed61 的 participation K10 fit 已完整（100 rounds，development primary 0.9239576），但其后续 partition K1 只写到第 10 轮，没有 `fit.json`，因此只保留为 partial，不用于论文分数。
- cross-source DTI seed61 的 target-only fit 已完整（100 rounds，development primary 0.8551163），但尚未完成全 case held-out 汇总；`plus_biosnap` 只到第 70 轮，`plus_davis`、`plus_human`、`plus_all` 没有完整 fit。当前没有相关进程运行，GPU 为空是因为队列已经退出，不代表这些 case 完成。

## 未完成、不能伪装成“只差多 seed”

- native DTI 新 12-design/6-slot cache：旧四个轻任务 seed61 的 12 个完整 fit 可复用；native DTI 的 10-client 12 个 fit 尚未产生完整 `fit.json + best.pt`，因此不发布该新短协议的 held-out loop 结论。
- 独立 proteomics 来源：Lin 与 Ruprecht 的 source-specific auxiliary-head 方案已完成身份闭包和 endpoint 风险审计；decryptE 处理矩阵尚未闭合，未启动训练。来源可行性见 `extensions/core_ablation_20260922/research/proteomics_external_20260923/ONE_DAY_FEASIBILITY.md`。

## 一日短 loop 已完成（seed61）

在四个轻任务上，Qwen2.5-7B 和 gpt-5.6-luna 均完成了统一的 12-design cache、6-slot direct/loop 选择和 held-out seal。这里的候选 fit 全部严格复用已完成的 100-round/10-client checkpoint；新增成本是 proposal、选择和 held-out 评测，而不是重复训练。结果按原 scorer 保存于 `results/budget1day_20260923/{task}/seed61/{qwen,luna}/heldout/results.json`。

- PTPC AP：Qwen/Luna direct 与 loop 的五个 prefix 均为 0.37274；说明该任务在这一短预算下保持稳定，但没有凭空制造 loop 增益。
- Norman macro Top-1：Qwen direct 的 prefix 为 15.48/14.96/35.48/22.30/22.30%，Luna loop 为 15.48/14.96/14.96/15.26/23.11%；这组结果说明 proposal 顺序会影响选择，且 held-out 必须按冻结 checkpoint 报告。
- VCC macro Top-1：Qwen 各 prefix 为 31.50%；Luna loop 在 prefix 4 出现 16.94% 的负迁移，prefix 6 回到 31.50%。负结果已保留。
- Tahoe macro Top-1：Qwen 各 prefix 为 25.37%；Luna 在 prefix 6/loop 4、6 为 26.87%，其余为 25.37%。

这组单 seed 短协议用于补充 loop 行为和模型后端审计，不替换主表的 seeds 42--44，也不把 proposal-cache replay 描述成新的训练收益。

## 算力控制

本轮从 `repetition_pause.json` 的不可变时间点起按 8 卡整机保留计费，预算 192 GPU·小时、24 小时硬截止。最新账本（2026-09-23 11:43）报告保守已用约 108.3 GPU·小时、剩余约 83.7 GPU·小时；空闲显卡不折减。重复 native、低优先级 seed 和 legacy repeatability 树已按精确 PID/start_ticks 停止，partial/checkpoint 未删除。凭据与只读核验见：

- `results/core_ablation_20260922/analysis/budget_stop_receipt_20260923.json`
- `results/core_ablation_20260922/analysis/stop_verification_20260923.json`
- `results/core_ablation_20260922/analysis/repeatability_stop_verification_20260923.json`
- `extensions/budget1day_20260923/budget_ledger.py`

任何新增训练先运行 budget ledger admission；不以瞬时显存、CPU 时间或 development 分数替代真实预算和 held-out 结果。
