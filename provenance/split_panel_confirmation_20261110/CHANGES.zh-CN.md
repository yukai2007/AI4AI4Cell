# 密封分半panel确认（SPC，2026-11-11）

## 新增内容
- 附录E.10与表`tab:split-panel-confirmation`（由`tools/publish_split_panel_confirmation.py`生成，`--check`可复核）。
- 正文Selection stability一句与结论一句改为引用E.10；E.3/E.8末句指向E.10。
- 三份回复：FBhK §5、cR5g §1/§3、AfJB §2加入SPC结果。
- 新版本化发布器`tools/finalize_split_panel_confirmation.py`（基于cd5bd70，367个旧资产不变，旧标签全部保留，只新增一张表）。

## 实验
- 12设计×seed61–63×cell/protein，72次新拟合，每个评估轮（20轮）保存checkpoint；与旧缓存逐位一致（训练曲线、best/last状态、720个审计panel分数）。
- A=偶数panel，B=奇数panel；A→B与B→A两个方向。轮次与设计只在选择半区上决定；两方向均密封（最后18:52:42 UTC）后，门控日志才首次读取确认半区（18:53:57 UTC）。432次选择读、144次确认读，均对应正确半区。
- 臂：fixed D00、精确random期望（C(11,6)）、GP-EI、Qwen/Luna的direct/raw/structured；每臂D00+6槽，无效槽计费。
- 143个不同checkpoint在两方向密封后各打一次测试分，保存预测独立重算一致；确认半区由保存checkpoint重新评估，0不一致。
- 独立只读代码审查（gpt-6.1-sol）：无阻断问题。次要：direct以D00为参照、history以当前incumbent为参照，二者不只差在history；panel门控单方向密封即可开确认半区（实际打分路径要求两方向密封，时间戳已核验）。

## 结论（全部臂/seed/方向保留）
- 选择乐观偏差大：选择半区减确认半区（搜索臂平均）cell 20.78/9.81，protein 4.61/53.39分（A→B/B→A）。protein两半区偏好不同训练轮次。
- cell A→B所有搜索臂测试分低于fixed D00（最高22.60 vs 30.82）；B→A GP-EI与Luna全部选D05，确认12.93→21.45，测试28.36→28.67。
- history vs direct：24次中17次选同一预测器；其余符号混合。Qwen history无效槽26/16（raw/structured，共72），direct为0；Luna各1。
- 不支持history相对direct/random/GP-EI的一致优势；GP-EI在4个设置中3个为最佳或并列最佳。
- 半区划分与测试集此前已被描述性查看：这是独立开发确认，不是新的生物学划分。

## 未完成
- 新grouped生物学划分（P0b）、实验室轮换（P1）。
- 未合并论文main，未提交OpenReview，未更新Overleaf。
