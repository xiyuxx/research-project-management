# {{PROJECT_NAME}}

这是人与 AI 通过聊天推进研究的管理框架，不包含模型、训练器或虚构实验。先读 [AGENTS.md](AGENTS.md)、[SETTINGS.md](SETTINGS.md)、[CURRENT.md](CURRENT.md) 和 [实验索引](experiments/INDEX.md)，再按需读相关组、EXP 与 [历史](CHANGELOG.md)。AI 记录必要事实、报告有依据的现状并提出一个下一步；先做最小对照，不默认大型实验矩阵或自动训练。

| 信息 | 权威位置 |
| --- | --- |
| 当前全局配方、模块选定值、方向、授权和边界 | CURRENT.md 人工区 |
| 当前研究设置和比较协议 | SETTINGS.md |
| 当前主题问题、共同条件、变量及判断 | experiments/GRP-NNN-slug/README.md 人工区 |
| 单次实验的实际条件、运行和证据 | 组内 EXP 或旧平铺 EXP |
| 重要尝试、数据、判断变更和历史更正 | CHANGELOG.md，只追加 |
| 台账索引和摘要 | INDEX、registry、NEXT、CURRENT 及组 README 生成区，均可重建 |
| 深入解释、真实运行产物 | reviews/、runs/ 或显式 run_dir |

## 实验台账

```sh
python tools/research.py group-new --slug learning-rate --title "学习率探索"
python tools/research.py new --group GRP-001 --expected config.expected.json --title "学习率对照"
python tools/research.py list --json
python tools/research.py show EXP-0001
python tools/research.py reindex
python tools/research.py status
```

命令仅示范接口，不代表实验或结论。组编号和全局唯一 EXP 编号由工具分配；组名为 `GRP-NNN-slug`。分组实验名根据预期文件的 `changes` 字段及其值生成，可用 `--label field=alias` 指定字段短名，否则使用规范化的完整字段名；数值使用统一表示。预期文件中的 experiment_id 可先写 `auto`，建档后使用 EXP 配套目录内编号化的不可变预期快照；原文件不改。名称必须与快照一致。主题尚未确定时可继续 `new --slug baseline --title "基线核对"` 建立平铺实验，旧平铺记录仍可读，不自动迁移。台账依赖 POSIX 文件锁，仅支持 Linux/macOS；需要 Python 3.10+。

`new` 只建档，不启动训练；`--command` 只记录文本。`--code PATH --config PATH` 可快照真实配置。实际 run_dir 可用 `set EXP-0001 run_dir=/actual/path` 登记；目录存在、台账 running 不代表进程存活。`set --result` 只更新 EXP 结果生成区；`reindex` 更新派生视图，保留人工区域。结果和证据以 EXP 为准，不在组汇总重复手工维护。

## 执行前配置检查

依据 AGENTS 的门禁，从真实执行入口导出最终生效配置，并保留本次预期、生效文件和新报告：

```sh
python tools/check_config.py --expected <预期快照.json> --effective <生效配置.json> --receipt <新报告.json>
```

输入契约见 `--help`。退出码 0 只表示声明字段匹配；1/2 均须阻止正式计算，通过后受检条件不可再覆盖。没有真实导出接口即未核验，不能用默认值或手写副本冒充。报告不能认证进程来源或替代用户授权，建档也不执行检查或训练。

## 既有项目

已有项目不直接覆盖初始化；先在空目录生成参考，再人工选择增量引入。保留旧编号、平铺记录及产物，不推断旧任务语义；选择唯一写入口，不能与旧工具双写。不要覆盖旧正文或移动产物来适应新结构。
