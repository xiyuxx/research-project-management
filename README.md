# research-project-management

通过人与 AI 的聊天，从空目录建立并推进科研项目：按研究问题分组实验，保存真实配置、环境与探索历史，维护当前快照和追加式变更日志，并在训练/评估前核验真正生效的配置。

An Agent Skill for chat-driven research project management: grouped experiments, immutable configuration evidence, an append-only history, and a pre-execution configuration gate. Linux/macOS only.

本仓库只分发一个 Skill。可安装内容全部在 [`research-project-management/`](research-project-management/) 内；外层只保留 README、LICENSE、CHANGELOG 和 GitHub 配置。安装或分发时只需要这个文件夹。

## 平台与依赖

- Linux 或 macOS（台账使用 POSIX 文件锁）；Windows 不受支持
- Python 3.10+
- 无第三方依赖
- 工具不联网、不启动训练；只读写用户指定的项目目录

## 只获取 Skill 文件夹

GitHub 网页不支持直接下载子目录。二选一：

```sh
# 稀疏检出：只取 Skill 目录
git clone --depth 1 --filter=blob:none --sparse <仓库地址> rp-skill
cd rp-skill
git sparse-checkout set research-project-management
```

或者下载整仓 zip，只复制其中的 `research-project-management/` 文件夹。

## 安装

`SKILL.md` 中的 `name` 必须与安装目录同名。

```sh
git clone <仓库地址> rp-skill
cd rp-skill/research-project-management

# Claude Code
mkdir -p ~/.claude/skills
ln -sfn "$PWD" ~/.claude/skills/research-project-management

# omp 或其他使用 Agent Skills 目录约定的宿主
mkdir -p ~/.omp/agent/skills
ln -sfn "$PWD" ~/.omp/agent/skills/research-project-management
```

若宿主只支持复制安装，将 `research-project-management/` 整个复制为 `<skills-dir>/research-project-management/`。

## 快速开始

以下命令在 `research-project-management/`（Skill 目录）内执行。

```sh
python scripts/init_project.py ~/research/demo --name "Demo" --dry-run
python scripts/init_project.py ~/research/demo --name "Demo"

cd ~/research/demo
python tools/research.py group-new --slug learning-rate --title "学习率探索"
python tools/research.py new --group GRP-001 --slug baseline --title "基线核对"
python tools/research.py reindex
```

按预期配置建档并生成实验名：

```sh
cat > expected.json <<'JSON'
{"experiment_id": "auto", "changes": {"optimizer.lr": 0.001}}
JSON
python tools/research.py new --group GRP-001 --expected expected.json \
  --title "学习率对照" --name-field optimizer.lr --label optimizer.lr=lr
```

执行前配置门禁：

```sh
python tools/check_config.py \
  --expected <预期快照> \
  --effective <真实入口导出的生效配置> \
  --receipt <新的检查报告>
```

退出码 `0` 只表示声明字段匹配；`1`/`2` 必须阻止正式计算。检查器不认证进程身份，也不能证明实现语义正确。

## 目录结构

```text
.
├── README.md
├── LICENSE
├── CHANGELOG.md
├── .gitattributes
├── .gitignore
├── .github/workflows/test.yml
└── research-project-management/   # 只需要分发这个目录
    ├── SKILL.md                   # Skill 入口与工作流
    ├── references/config-check.md # 配置门禁的输入契约与操作顺序
    ├── scripts/init_project.py    # 初始化项目（仅 POSIX）
    ├── scripts/check_config.py    # 配置比对与报告
    ├── assets/project/            # 初始化模板：AGENTS/CURRENT/CHANGELOG/experiments 等
    └── tests/                     # 行为测试
```

初始化后的项目由 `AGENTS.md`、`CURRENT.md`、`CHANGELOG.md`、`experiments/GRP-*/` 和每个 `EXP-*.md` 组成。`INDEX.md`、`NEXT.md`、`registry.json` 是可重建的派生视图；`EXP-*.md` 才是实验事实源。

## 开发与测试

```sh
python -m unittest discover -s research-project-management/tests -v
```

CI 在 `ubuntu-latest` 上覆盖 Python 3.10 与 3.12，并实际执行一次“初始化已存在空目录 → 建组 → 建档 → reindex”。

## 安全边界

- 不发起网络请求，不下载模型或数据
- 不自动启动训练、评估或外部提交；建档与检查不等于执行授权
- 不覆盖既有报告；配置检查报告只新建，不替换历史证据
- 台账与检查器不修改输入文件；写入使用临时文件与原子替换

## 许可

MIT，见 [LICENSE](LICENSE)。
