# {{PROJECT_NAME}}

这个目录是一份可按实验追溯的研究工作区：一次尝试一份 `EXP-*.md`，参数、环境、命令、日志和判断各归其位。记录在聊天中由 AI 维护，也可以直接手改。

## 从哪读起

| 你想知道 | 看这里 |
| --- | --- |
| 现在在做什么、当前配方和授权 | `CURRENT.md` 人工区 |
| 某次实验到底怎么跑的、结果如何 | `experiments/GRP-*/EXP-*.md`（唯一事实源） |
| 某个决定何时、为什么改 | `CHANGELOG.md`（只追加） |
| 比较协议、数据与指标口径 | `SETTINGS.md` |
| 只在讨论、暂不推进的想法 | `ideas/IDEA-*.md`（暂存，不是计划或证据） |
| AI 的读写规则、证据底线 | `AGENTS.md` |

`INDEX.md`、`NEXT.md`、`registry.json` 和带 `ledger:` 标记的区块都是可重建的派生视图，别把它们当事实源。

## 一次回合长什么样

聊天里说「试试 lr 5e-4，其他不动」，AI 会先读 `CURRENT.md` 和当前组，然后建一份 EXP（附不可变预期快照）、从真实入口导出生效配置、过门禁、记录实际结果、追加 CHANGELOG、更新 CURRENT。你不用手动敲命令。

```sh
# 只建台账，不启动训练
python tools/research.py group-new --slug learning-rate --title "学习率探索"
python tools/research.py new --group GRP-001 --expected config.expected.json --title "学习率对照"
python tools/research.py list --json
python tools/research.py show EXP-0001
python tools/research.py reindex
python tools/research.py status
python tools/research.py idea-new --slug moe-fusion --title "MoE 路由替代 concat"  # 暂存想法，不进台账
```

用 `--expected` 建档时，实验名由声明里的字段和值生成（`--name-field` 选展示字段，`--label` 起短名）；编号与名称以记录为准，不从文件名猜配置。`run_dir`、`code`、`config` 可用 `set` 登记，目录存在不代表进程存活。

## 执行前门禁

真实执行入口解析完默认值、配置文件和覆盖项后，导出最终配置，再让命令走门禁：

```sh
python tools/run_with_gate.py \
  --expected <EXP 记录目录>/config.expected.json \
  --effective <尝试目录>/config.effective.json \
  --receipt <尝试目录>/config.check.json \
  -- python train.py --config configs/run.yaml
```

退出码 0 只表示声明字段匹配；1/2 时门禁不会启动命令。拿不到真实导出就记“未核验”并停下，不能手写生效文件充数。报告只证明输入文件一致，不证明进程身份或实现语义。

## 边界

- 初始化只建模板与工具，不产生实验、不训练、不联网。
- 已有文件不覆盖；旧记录不自动迁移，迁移须明确授权。
- 台账锁按平台路由：Linux/macOS 用 flock，Windows 用 SQLite 事务；需要 Python 3.10+。
