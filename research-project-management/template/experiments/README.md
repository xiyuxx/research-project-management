# 实验台账

EXP 是单次实验实际事实与证据的权威记录；INDEX、registry、NEXT 及组 README 的结果汇总是派生视图。使用 `python tools/research.py` 作为本台账唯一写入口，不与旧工具双写。EXP 编号全局唯一；重建索引不改变原始事实。写入中断时保留原始记录并执行 reindex 恢复派生视图。

## 研究组与命名

`python tools/research.py group-new --slug learning-rate --title "学习率探索"` 分配 `GRP-NNN-learning-rate` 并生成组 README。人工区填写研究问题、起点、共同条件固定快照、探索变量和当前判断；标记内的实验结果汇总由 EXP 派生，不手工复制维护。重要判断变化追加 CHANGELOG。

`python tools/research.py new --group GRP-001 --expected config.expected.json --title "学习率对照"` 根据预期配置的非空 `changes` 映射中字段和值生成可读实验名。可用 `--label field=alias` 指定字段短名，未指定则规范化完整字段名；数值统一表示，例如 0.001 为 1e-3。experiment_id 可先写 `auto`，建档后 EXP 配套目录保存编号化的不可变预期快照供后续核验，原文件不变；名称须与快照一致。

主题尚未确定仍可用 `new --slug baseline --title "基线核对"` 建平铺实验。既有平铺记录继续可读，不自动迁移。组与平铺实验共用编号空间。

只是讨论过、还没决定推进的想法不进 EXP：放 `ideas/`，由用户决定推进后再建档。

## 记录与状态

front matter 是单行标量，重复键表示多项，不是完整 YAML；`next` 是开放任务，`next_done` 是人工确认的完成项，`constraint` 是边界。`--complete-next` 精确完成开放任务；`--clear-next` 只清除而不伪称完成。旧 next 的分类须人工确认。

status 为 planned/running/done/blocked/abandoned，只代表登记的执行状态，不是进程监测；review_status 为 pending/done，表示人工科研解释是否闭环。done 不自动清空 next 或完成解释，pending 不等于失败。`set --result` 只替换 result 标记区，区外详细观察与证据保留。

每个 EXP 记录预期与实际参数、环境、代码版本及 dirty 改动、对照、数据和权重、评估、每次运行尝试及失败、结果解释和消融关联。每次运行保留独立配置检查文件与报告，不能覆盖历史。真实配置可按原字节快照；没有证据不能用模板文字替代。

显式 run_dir 优先；不要移动旧产物迎合新目录。目录存在不等于运行中；真实现场须核验。有关配置门禁及授权见 AGENTS.md。
