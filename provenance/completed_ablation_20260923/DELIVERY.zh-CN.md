# 已完成实验并入论文：交付说明

## 实际更新

- §4.5：补齐K、独立来源、双research backend、两种loop协议的实验定义。
- §5.3：新增全部DTI K与独立源结果、VCC外源结果、两项独立蛋白研究的配对pilot。
- §5.4与正文新表：五端点Qwen/Luna、direct/loop短6槽对照，另分析长24槽的任务差异。
- Appendix B：全部K表、14个独立来源条件、蛋白fixed/loop、同研究contexts、短/长预算完整曲线、配置菜单、504槽提案轨迹和Norman具体修改实例。
- Figure 2：使用用户指定PPT的矢量派生，字体与文字框做排版修复；原PPT内容和文件均未改动。图注说明10-lab是一般K的主实验实例。
- 中文伴读版：15页，更新全部消融、完成状态、机制解释和阅读导航，嵌入中文字体。

原三种子主表和计算量匹配的分配实验没有混入不同seed、候选空间或新蛋白adapter分数。新的蛋白pilot单独使用同架构target-only对照。

## 三项要求的真实验收

| 要求 | 完成范围 | 尚未覆盖 |
|---|---|---|
| 研究模型剥离 | Qwen2.5-7B与gpt-5.6-luna；五端点短6槽 | 新增重复seed后置 |
| lab数量与不同来源 | 五端点K=1/2/5/10，两种定义；DTI与细胞各3外源，蛋白2外源 | 第3项独立蛋白来源尚未训练 |
| loop数目与修改分析 | 五端点0/1/2/4/6前缀；四轻端点延长至24槽；全部504槽记录 | DTI长24槽未执行 |

短协议的12种配置和长协议的36种配置是不同搜索空间，分开画曲线。“共同开发目标”统一采用双方终点中较小值，即双方均能达到的目标；较大值的诊断仍保留在机器快照中。

目前的实证结论是：训练预算分配有正收益；proposal-history在Norman的部分设置提高分数或搜索效率，但不具备跨所有任务的一致终点增益。长loop不是总能提高测试分数，所有零收益与负迁移均已保留。

## 验证

英文PDF使用原ICLR模板，正文结束于第9页。出版与稿件一致性测试59项通过；最终构建页数、PDF与源文件哈希、版式检查记录见 `build_receipt.json`。中文PDF及其164个来源绑定见 `../../output/pdf/AI4AI4Cell_中文伴读版.provenance.json`。独立内容复查见 `research/MANUSCRIPT_REVIEW.zh-CN.md`。

图表排版依照PDF/幻灯片技能做了实际渲染检查；文献核验流程用于区分独立研究与同研究contexts，并核对新增两篇蛋白来源的标签和适配细节。原始训练结果、checkpoint及冻结协议均未改写。

## 存储与同步

配额不足时，仅对本项目生成的重复checkpoint快照作哈希等价硬链接去重，原始训练模型不动；备份在 `/tmp/ai4ai4cell-owned-snapshot-backups-20260923-8dnqt377`，凭据在父研究目录的 `results/tonight_completion_20260923/audit/snapshot_deduplication_20260923.json`。

四个未追踪的历史排版预览目录从 `paper/build/` 移到 `/tmp/ai4ai4cell-build-<原目录名>-20260923` 保存：`performance_complete_20260913`、`pipeline_final_20260916`、`coauthor_integration_final_20260914`、`visual_clarity_20260915`。可恢复，未删除实验数据。出版器已改为原子写入，避免配额错误损坏原有快照。

GitHub同步使用正常fast-forward；远端同步状态以本轮最终回复中的commit为准。没有执行OpenReview投稿，也不将GitHub推送视作已验证Overleaf远端编译。
