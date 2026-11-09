# 变更记录

## 未发布

- README 动机段重写：改为「没有 skill 时的四个默认失效点 → 对应的结构约束」，去掉不贴切的命名错配例子。
- 快速开始简化为「初始化 → 交给 agent」，手写命令移交给 `examples/first-round.md`。

## 0.2.2 — 2026-11-09

- 脚本输出统一为 UTF-8：在 Windows 的 cp1252 管道理下，检查报告与台账命令不再因中文抛出 `UnicodeEncodeError`（`configure_output()`，不可用时可回退）。
- 测试以 UTF-8 解码子进程输出，CI 的失败用例改为以注解形式暴露具体断言与 stderr。

## 0.2.1 — 2026-11-09

- 台账锁按平台路由：Linux/macOS 用 `fcntl.flock`，Windows 用 SQLite 写事务（`BEGIN IMMEDIATE`）；不再在 import 阶段拒绝 Windows。
- `init_project.py` 去掉 POSIX 拦截，并修掉"目标已存在空目录"在 Windows 上 rename 失败的问题（先删空目录再原子改名）。
- 测试去掉 POSIX 跳过，新增锁路由、显式后端覆盖、两种后端下的并发取号用例；CI 增加 `windows-latest` job。
- `RESEARCH_LOCK=flock|sqlite` 可显式覆盖路由（仅测试或特殊环境）；同一项目不要混用两种锁。

## 0.2.0 — 2026-11-09

- 新增 `scripts/run_with_gate.py`：先核验配置再启动命令，检查未通过时不运行任何命令；初始化时安装到项目 `tools/`。
- 新增 `examples/first-round.md`：从一句聊天到 EXP、门禁输出、CHANGELOG 追加和 CURRENT 更新的完整回合。
- 实验与分组模板改为示例注释，替换原先"记录……，不得……"的祈使说明，输出格式有可模仿的样子。
- 生成项目的 `README.md` 改为面向人的导航，事实位置只保留 `AGENTS.md` 一份，去掉重复表格。
- `SKILL.md` 的 description 补充触发与不触发场景；新增优先级：项目自身规则可以加严，不能放宽写入范围、证据底线与执行授权。
- 初始化时把 skill 版本写入生成项目的 `AGENTS.md`，便于判断升级后是否需要迁移。
- 测试与 CI 覆盖门禁包装：匹配则启动、不匹配拒绝、无效输入返回 2、被包命令的退出码原样透传。
