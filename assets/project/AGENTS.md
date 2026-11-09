# {{PROJECT_NAME}}：协作约定

## 聊天与授权

研究由人与 AI 在聊天中推进。先读本文件、SETTINGS.md、CURRENT.md 和 experiments/INDEX.md，再按问题读取相关组 README、EXP 和 CHANGELOG；不预加载所有历史。先以最小对照验证价值，再根据证据补充归因和确认，不默认大型实验矩阵。AI 维护必要记录，报告有证据的现状并提出一个下一步；不要自动启动训练。

训练、下载数据、外部提交或移动/删除旧产物前必须获得实际用户授权。CURRENT 的人工区维护当前授权、资源与禁止事项；没有记录不能推断已授权。

## 事实与生成区

- EXP 是每次实验实际条件、运行、评估和证据的权威记录；编号全局唯一。研究主题按 experiments/GRP-NNN-slug/ 分组，主题尚未确定可使用平铺实验；旧平铺记录仍可读，不自动迁移。
- 组 README 维护当前研究问题、起点、共同条件快照、探索变量和当前判断；实验结果汇总由 EXP 派生，不另行手工维护同一事实。组判断变化的重要历史追加 CHANGELOG。
- CURRENT 是可随时修改的当前全局配方、模块选定值及证据、方向、边界和交接；CHANGELOG 只追加重要研究事件、全局/局部尝试、数据与 EXP 证据及历史更正。SETTINGS 记录当前协议；reviews 保存必要的深入解释，runs 保存实际产物。
- INDEX、registry、NEXT、CURRENT 摘要及组 README 标记内的汇总为派生视图，不保存唯一人工事实。台账操作使用 `python tools/research.py`，不要与旧工具双写；已有项目不自动迁移。
- front matter 为单行标量，重复键表示多项，不是通用 YAML。`next`、`next_done`、`constraint` 分别表示开放任务、已完成任务和边界。执行状态与人工解释状态独立；done 不自动清空 next 或完成解释。

CURRENT 的 `<!-- ledger:current:start -->` / `<!-- ledger:current:end -->` 是台账摘要，不是进程存活声明；组 README 的 `<!-- ledger:group:start -->` / `<!-- ledger:group:end -->` 是生成汇总。EXP 的 `<!-- ledger:result:start -->` / `<!-- ledger:result:end -->` 可由 `set --result` 更新；区外的实际观察、解释及证据不得覆盖。人工内容保留在生成区外，标记不完整时先人工修复。

## 执行前配置门禁

- 聊天明确本次预期，保存含 experiment_id 和非空 changes 映射的 config.expected.json；按字段和值生成名称的分组建档可先用 `auto` 占位，使用建档后写入 EXP 的编号化不可变预期快照核验。
- 必须从真实执行入口解析默认值、文件、CLI 覆盖和自动推导后的实际对象，导出 experiment_id 加 config 对象的 config.effective.json；不能手写副本或拿默认配置充数。
- AI 必须调用 `python tools/check_config.py --expected <预期快照> --effective <生效文件> --receipt <新报告路径>`；每次执行保留独立输入和报告。
- 实际执行器在正式计算前检查退出码：0 仅表示声明字段匹配，1/2 必须停止；通过后不可另行覆盖受检条件。检查不替代训练授权。
- 无真实导出接口时明确未核验，补齐接口后再执行；不能凭名字或源码声称通过。输入契约见 tools/check_config.py 的 --help 及 skill 的配置检查参考。记录命令、代码、环境及证据；报告不认证进程身份或实现语义，也不代表实验已经运行或成功。

## 证据底线

不伪造进程、指标、配置或结论。建档不代表运行，目录存在不代表进程存活，单次涨点不代表机制成立。事实、假设、解释与判断分开；不可得信息明确未记录，不能填假值。
