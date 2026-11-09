# 一个完整回合（示例，不是真实实验）

下面是一次典型对话从一句话到落盘的全过程。内容为格式示范，参数与数字均为虚构，不能当作实验结果引用。

## 1. 用户

> baseline 已经跑通了，lr 1e-3 后期 loss 抖得厉害。帮我试一下 5e-4，其他不动。

## 2. AI 先读什么

按 `AGENTS.md` 的顺序只读必要部分，不预载全部历史：

- `AGENTS.md`、`SETTINGS.md`、`CURRENT.md`：授权边界、当前全局配方、当前组
- `experiments/INDEX.md` 找到当前组 `GRP-001-learning-rate`
- `experiments/GRP-001-learning-rate/README.md`：共同条件与基线
- `experiments/GRP-001-learning-rate/EXP-0001-baseline.md`：基线的实际条件
- 最近几条 `CHANGELOG.md`：确认 lr 是否已经试过别的值

读完后只问真正影响下一步的分歧，例如“预算仍按 20k 步？还是要在 5e-4 下延长？”其余条件直接沿用基线。

## 3. 建档：声明 → 编号 → 名称

先把本轮聊天里的条件写成声明（`changes` 要包含所有关键条件，不只是改动项）：

```json
{
  "experiment_id": "auto",
  "changes": {
    "optimizer.lr": 0.0005,
    "optimizer.weight_decay": 0.01,
    "training.steps": 20000,
    "training.seed": 42
  }
}
```

```sh
python tools/research.py new --group GRP-001 --expected expected.json \
  --title "lr 5e-4 对照" --name-field optimizer.lr --label optimizer.lr=lr
```

输出：

```text
experiments/GRP-001-learning-rate/EXP-0002-optimizer-lr-5e-4.md
```

工具把完整 changes 存成 `EXP-0002-optimizer-lr-5e-4/config.expected.json`（不可变快照，编号已绑定），原 `expected.json` 不动；`--name-field` 只影响展示名，不缩小校验范围。

## 4. 落盘的实验记录长什么样

`experiments/GRP-001-learning-rate/EXP-0002-optimizer-lr-5e-4.md` 开头：

```markdown
---
id: EXP-0002
slug: optimizer-lr-5e-4
title: lr 5e-4 对照
status: planned
review_status: pending
created: 2026-11-09
updated: 2026-11-09
run_dir: runs/EXP-0002-optimizer-lr-5e-4
expected_snapshot: experiments/GRP-001-learning-rate/EXP-0002-optimizer-lr-5e-4/config.expected.json
---
```

正文（人工区示例值，实际写真实观察）：

```markdown
## 问题、假设与对照

- 问题：lr 1e-3 后期 loss 尖峰是否来自步长过大。
- 对照：EXP-0001（同数据、同 seed、同 20k 步预算，仅 lr 不同）。
- 假设：5e-4 让尖峰变少，代价是前期下降更慢。

## 计划与实际条件

- 计划：optimizer.lr=5e-4，weight_decay=0.01，steps=20000，seed=42。
- 实际：见 `config.effective.json`（`optimizer.lr=0.0005`，其余与声明一致）。
- 代码：`train@a1b2c3d`，dirty=false；环境见 `runs/EXP-0002-optimizer-lr-5e-4/env.txt`。
- 数据与初始化：与 EXP-0001 相同，未改划分。

## 运行尝试与配置核验

- 尝试 1：2026-11-09 14:02，命令见 `runs/EXP-0002-optimizer-lr-5e-4/cmd.txt`。
- 门禁：`config.check.json`，status=passed，声明字段全部 match。
- 未核验项：无（真实入口已导出最终对象）。
```

`status=planned` 表示只建档；跑完才改为 `running` / `done`，`review_status` 是人工解释是否闭环，两者独立。

## 5. 执行前门禁的实际输出

```sh
python tools/run_with_gate.py \
  --expected experiments/GRP-001-learning-rate/EXP-0002-optimizer-lr-5e-4/config.expected.json \
  --effective runs/EXP-0002-optimizer-lr-5e-4/config.effective.json \
  --receipt runs/EXP-0002-optimizer-lr-5e-4/config.check.json \
  -- python train.py --config configs/grid.yaml
```

通过时先打印检查报告，再启动命令；不通过时命令根本不会执行：

```json
{
  "status": "mismatch",
  "experiment_id": "EXP-0002",
  "checks": [
    {"field": "optimizer.lr", "expected": 0.0005, "actual": 0.001, "status": "different"}
  ],
  "scope": "仅核对声明字段与输入文件；不证明配置来自真实进程或实现语义正确"
}
```

此时记录“门禁未通过、未执行”，修正导出或重新讨论条件后另建尝试；不改旧报告，也不把 expected 改成实际值来“通过”。

## 6. 跑完之后

追加 `CHANGELOG.md`（只追加，不改旧条目）：

```markdown
## 2026-11-09 · lr 5e-4 对照

- 尝试：GRP-001 / EXP-0002，基线 EXP-0001，仅 optimizer.lr 1e-3 → 5e-4。
- 实际：20k 步，seed 42，其余条件与基线一致；门禁 passed。
- 观察：后期 loss 尖峰从 6 次降到 1 次；前期 loss 高于基线约 0.04。
- 判断：暂缓采用。单 seed、单数据集，不能说明是步长效应还是随机波动；下一步固定 seed 42 复跑基线确认尖峰可复现。
```

更新 `CURRENT.md` 的人工区：把“当前选定 lr=1e-3（稳定）”这句替换为带依据的新说法，或写明“仍在 1e-3，5e-4 待复现”，旧说法不和新说法并存。

最后向用户报告：实际做了什么、观察到什么、哪些还不能解释、一个具体的下一步。
