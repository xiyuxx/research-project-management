---
# front matter 由 new 命令写入（id/slug/title/status/review_status/created/updated/run_dir；用 --expected 时另有 expected_snapshot 与配置快照字段）。
---
# 实验记录

## 问题、假设与对照

<!-- 写这段要回答什么、为什么做、和谁比。格式示例：
- 问题：lr 1e-3 后期 loss 尖峰是否来自步长过大。
- 对照：EXP-0001（同数据、同 seed、同预算，仅 lr 不同）。
- 假设：5e-4 减少尖峰，代价是前期下降更慢。
计划与实际分开写；建档不代表已执行。 -->

## 计划与实际条件

<!-- 每行一个可核验事实。示例：
- 计划：optimizer.lr=5e-4，weight_decay=0.01，steps=20000，seed=42。
- 实际：见 config.effective.json；与计划的差异逐项写明。
- 代码/环境：train@a1b2c3d，dirty=false；依赖与设备见 run_dir。
- 数据：版本、划分、预处理、权重来源及可得 hash。
不可得的信息写“未记录”，不推断。 -->

## 运行尝试与配置核验

<!-- 逐次尝试一行或一节，示例：
- 尝试 1：2026-11-09 14:02，命令与日志见 run_dir；门禁 config.check.json status=passed。
- 尝试 2（失败）：OOM，未进入正式计算，保留配置与日志。
门禁用 python tools/run_with_gate.py 跑，1/2 时不启动命令；未调用、未真实导出或未通过就如实写，不能写成已通过。检查不替代授权，也不证明实现语义正确。 -->

## 评估与完整证据

<!-- 评估入口、数据划分、checkpoint 选择规则、指标口径与结果路径；示例：
- 入口：eval.py --split test；ckpt 按验证集 loss 最优选择。
- 指标：accuracy（%），单位与统计口径同上一次。
- 证据：run_dir/metrics.json、train.log（原文，不摘抄替代）。 -->

## 结果摘要（生成区）

<!-- ledger:result:start -->
尚未登记结果；不能据此推断实验已执行或失败。
<!-- ledger:result:end -->

## 人工解释与关联

<!-- 区分观察、解释、假设。示例：
- 观察：尖峰从 6 次降到 1 次；前期 loss 高约 0.04。
- 解释：可能来自步长，也可能是单 seed 波动。
- 关联：EXP-0001 为对照；复跑结果见 EXP-0003。
status=done 不等于解释完成；人工解释闭环后才设 review_status=done。判断变化追加 CHANGELOG。 -->
