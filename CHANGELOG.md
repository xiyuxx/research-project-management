# Changelog

## 0.1.1 — 2026-11-09

- 仓库布局：Skill 内容集中到 `research-project-management/`，外层仅保留 README、LICENSE、CHANGELOG 与 GitHub 配置
- 安装、测试与 CI 路径同步调整

## 0.1.0 — 2026-11-09

- 首次发布：聊天驱动的科研项目管理 Skill
- 按研究问题分组的实验台账，全局唯一 `EXP` 编号，派生索引可重建
- 可修改的 `CURRENT.md`、只追加的 `CHANGELOG.md`、每次实验独立证据目录
- 启动前配置门禁：预期声明与真实生效配置比对，退出码 `1`/`2` 阻断执行
- 初始化器仅支持 Linux/macOS；Windows 平台显式拒绝
- JSON 与 front matter 读取接受 UTF-8 BOM
