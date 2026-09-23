# 蛋白组严格每研究一实验室对照

四个预先固定配置均完成100轮，seed61，0 proposal slots，全CPU、无GPU/API。
Target原十个训练分片合并为一个worker；Lin、Ruprecht、decryptE各一个worker。
Checkpoint选择仍为原十个target开发panel等权AP/BCE，不以外源开发分数或test选模型。

| 训练来源 | K | 训练条件N | AP (%) | AUROC (%) |
|---|---:|---:|---:|---:|
| Target study | 1 | 386 | 34.41 | 72.33 |
| + decryptE | 2 | 881 | 36.58 | 73.81 |
| + Lin + Ruprecht | 3 | 491 | 36.09 | 72.69 |
| + Lin + Ruprecht + decryptE | 4 | 986 | 37.53 | 74.39 |

完整保存四臂，无按test高低筛选。该实验改变外源数据可获得性，不匹配总训练条件数，也不是loop消融。
与先前target十片协议不同：合并后target每local epoch共7个minibatch；不把旧协议分数混用为同一对照。
共享参数按各训练client样本数加权，source-private heads只由其所有者更新；结构、初始化与损失保持冻结。
总墙钟 76.18 秒；CPU 110.11 秒。

独立验证使用保存预测的NumPy AP分数阈值公式与AUROC成对次序公式，逐项与官方scorer核对，容差1e-12。
正文输入：`\input{tables/proteomics_scenario_labs_v2/table}`。
