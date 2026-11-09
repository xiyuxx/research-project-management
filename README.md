# research-project-management

一个 Agent Skill：把聊天里冒出来的实验想法变成能回溯的记录，并在真正开跑之前拦住"名字和参数对不上"的情况。

## 为什么需要

跑实验时最难的不是写训练脚本，而是三周后回答不了"这次和上次到底差在哪"：参数散在 shell 历史、配置文件和日志里；文件名写着 `lr-1e-3`，实际跑的是 5e-4；为了记住一个决定，顺手把旧记录改得和当时不一样。

这个 Skill 用一套固定结构处理这三件事：

- **一次尝试一份 `EXP-*.md`**：计划与实际参数、完整生效配置、代码与环境、命令、评估口径、日志与证据，历史只追加不改写。
- **按研究问题分组**：组里只维护共同条件、探索变量和当前判断，单次细节留在 EXP。
- **执行前核验**：从真实执行入口导出最终配置，与声明逐字段比对，不一致就不启动命令。

## 一次回合

> 用户：「baseline 跑通了，lr 1e-3 后期 loss 抖得厉害，帮我试一下 5e-4，其他不动。」

AI 读完当前状态后建档，得到 `EXP-0002-optimizer-lr-5e-4`，附一份编号绑定的不可变预期快照；训练前导出真实生效配置并过门禁；跑完把实际结果写进 EXP、追加 CHANGELOG、更新 CURRENT。完整文本见 [examples/first-round.md](research-project-management/examples/first-round.md)。

## 安装

要求 Linux 或 macOS（台账使用 POSIX 文件锁）、Python 3.10+、无第三方依赖。`SKILL.md` 的 `name` 必须与安装目录同名。

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
    ├── scripts/init_project.py         # 初始化（仅 POSIX）
    ├── scripts/check_config.py         # 声明 vs 生效配置比对
    ├── scripts/run_with_gate.py        # 通过才启动命令
    ├── assets/project/                 # 初始化模板
    └── tests/                          # 行为测试
```

初始化后的项目里，`EXP-*.md` 是唯一事实源；`INDEX.md`、`NEXT.md`、`registry.json` 和 `ledger:` 标记区块都是可重建的派生视图。

## 已知边界

- 只支持 Linux/macOS；Windows 需要替换台账的文件锁实现。
- 不联网、不下载数据、不自动启动训练或外部提交。
- 配置门禁只比对声明字段与两个输入文件；拿不到真实导出时技能会要求记"未核验"并停下，但无法替你验证导出文件真的来自那个进程。
- 升级 Skill 不会改写已初始化的项目；迁移需要显式操作。

## 版本

当前 0.2.0，变更见 [CHANGELOG.md](CHANGELOG.md)。初始化出的项目在 `AGENTS.md` 顶部记录所用版本，便于以后判断是否需要迁移。

## 许可

MIT，见 [LICENSE](LICENSE)。
