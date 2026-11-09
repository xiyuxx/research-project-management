# research-project-management

一个 Agent Skill：给「在聊天里推进的科研项目」一套可回溯的落盘方式。决定、尝试、真正生效的配置和证据各有位置；开跑之前从真实入口导出配置核对，声明和实际不一致就不启动。

## 为什么需要

如果只是"跑实验"，你不需要这套结构。需要它的场景很具体：**研究是在对话里推进的**，而对话恰好是最不可靠的事实载体。不用它时，下面四件事是默认状态，不是偶尔失误：

1. **对话会丢，决定跟着丢。** 你在会话里说「先固定 concat 融合，add 在这次数据上没意义」，理由只存在于上下文里。换会话、上下文压缩、隔几天再开工，AI 只能从残缺材料重新推断，于是同一个问题被重提一遍，甚至得出相反结论。
2. **AI 的复述是生成的，不是读出来的。** 问「上次为什么放弃这个方向」，它会给出一个通顺的答案：可能把计划当成结果、漏掉失败或续训的尝试、把两次实验的参数拼成一次。没有固定事实源，你分不清哪句来自记录、哪句是补全。
3. **"说过的参数"不等于"生效的参数"。** 真实配置由默认值、配置文件、CLI 覆盖和代码里的自动推导共同决定。聊天里定的是 lr 5e-4，而 5e-4 只写在启动命令的覆盖项里；这次启动漏了它，默认值 1e-3 生效。日志只记录跑成了什么，不记录你原本想跑什么，事后没有环节能发现这条记录对不上。
4. **总结会覆盖历史。** 复盘时为了让文档"干净"，人会（AI 更会）把当时的判断改写成现在知道的结论。于是"当时为什么这么选"永久消失，复现与归因都失去依据。

这个 Skill 把四件事分别落到结构上：

| 没有它时 | 有它时 |
| --- | --- |
| 决定只活在对话里 | 形成的条件、实际结果和决定写进 `EXP-*.md` 与只追加的 `CHANGELOG.md`，新会话从磁盘恢复 |
| AI 凭记忆复述，真假难辨 | `EXP-*.md` 是唯一事实源，`INDEX` / `NEXT` / `registry` 只是可重建视图，汇报读原文 |
| 声明与生效配置可能不一致且无人发现 | 门禁只接受从真实入口导出的生效配置，逐字段比对，不一致就不启动 |
| 旧结论被顺手的总结改写 | 历史只追加，纠错另写新条目，旧记录不动 |

至于一次尝试具体记什么（计划与实际的差异、完整生效参数、代码版本、命令、评估口径、证据路径）、按研究问题怎么分组，都已固定在 `EXP-*.md` 模板与分组规则里，不需要每轮重新约定。

## 一次回合

> 用户：「baseline 跑通了，lr 1e-3 后期 loss 抖得厉害，帮我试一下 5e-4，其他不动。」

AI 读完当前状态后建档，得到 `EXP-0002-optimizer-lr-5e-4`，附一份编号绑定的不可变预期快照；训练前导出真实生效配置并过门禁；跑完把实际结果写进 EXP、追加 CHANGELOG、更新 CURRENT。完整文本见 [examples/first-round.md](research-project-management/examples/first-round.md)。

## 安装

要求 Python 3.10+、无第三方依赖；台账锁按平台路由（Linux/macOS 用 flock，Windows 用 SQLite 事务）。`SKILL.md` 的 `name` 必须与安装目录同名。

```sh
git clone <仓库地址> rp-skill
cd rp-skill/research-project-management

mkdir -p ~/.claude/skills
ln -sfn "$PWD" ~/.claude/skills/research-project-management
```

其他支持 Agent Skills 目录约定的宿主同理（omp 用 `~/.omp/agent/skills`）；宿主只支持复制安装时，把整个 `research-project-management/` 复制过去即可。只需要这个目录，仓库外层的 README 与 CI 配置不参与运行。

## 快速开始

```sh
# 1. 初始化一个空目录（--dry-run 只预览将写入的文件）
python scripts/init_project.py ~/research/demo --name "Demo"
cd ~/research/demo

# 2. 建组、建档；声明里的 changes 会变成不可变预期快照
python tools/research.py group-new --slug learning-rate --title "学习率探索"
cat > expected.json <<'JSON'
{"experiment_id": "auto", "changes": {"optimizer.lr": 0.0005, "training.seed": 42}}
JSON
python tools/research.py new --group GRP-001 --expected expected.json \
  --title "lr 5e-4 对照" --name-field optimizer.lr --label optimizer.lr=lr

# 3. 执行前门禁：0 才启动后面的命令，1/2 直接拒绝
python tools/run_with_gate.py \
  --expected experiments/GRP-001-learning-rate/EXP-0001-optimizer-lr-5e-4/config.expected.json \
  --effective runs/EXP-0001-optimizer-lr-5e-4/config.effective.json \
  --receipt runs/EXP-0001-optimizer-lr-5e-4/config.check.json \
  -- python train.py --config configs/run.yaml
```

`new` 只建台账，不启动训练；`run_with_gate.py` 只负责"检查后启动或不启动"，不认证进程身份，也不代表你已经授权这次执行。只想核验时改用 `tools/check_config.py`。

## 目录

```text
.
├── README.md
├── CHANGELOG.md
├── LICENSE
├── .github/workflows/test.yml
└── research-project-management/        # 分发时只需要这个目录
    ├── SKILL.md                        # 工作流与硬规则
    ├── examples/first-round.md         # 一个完整回合的成品形态
    ├── references/config-check.md      # 门禁的输入契约与操作顺序
    ├── scripts/init_project.py         # 初始化（跨平台）
    ├── scripts/check_config.py         # 声明 vs 生效配置比对
    ├── scripts/run_with_gate.py        # 通过才启动命令
    ├── assets/project/                 # 初始化模板
    └── tests/                          # 行为测试
```

初始化后的项目里，`EXP-*.md` 是唯一事实源；`INDEX.md`、`NEXT.md`、`registry.json` 和 `ledger:` 标记区块都是可重建的派生视图。

## 已知边界

- 锁按平台路由：Linux/macOS 用 `flock`，Windows 用 SQLite 写事务；同一项目不要用 `RESEARCH_LOCK` 混用两种锁。Windows 上会多一个 `experiments/.ledger.lock.db`。
- 不联网、不下载数据、不自动启动训练或外部提交。
- 配置门禁只比对声明字段与两个输入文件；拿不到真实导出时技能会要求记"未核验"并停下，但无法替你验证导出文件真的来自那个进程。
- 升级 Skill 不会改写已初始化的项目；迁移需要显式操作。

## 版本

当前 0.2.0，变更见 [CHANGELOG.md](CHANGELOG.md)。初始化出的项目在 `AGENTS.md` 顶部记录所用版本，便于以后判断是否需要迁移。

## 许可

MIT，见 [LICENSE](LICENSE)。
