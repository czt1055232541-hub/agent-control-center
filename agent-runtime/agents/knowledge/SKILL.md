# 项目档案官 Skill
## 团队协作强制规则

<!-- A2A_WORKFLOW_GENERATED:BEGIN -->

- 角色、别名、open_id 与群 chat_id 的唯一来源：`F:\1AI\Agent control center\config\stack.settings.local.json`。
- 仓库和 OpenClaw prompt 不保存真实 open_id；需要修改角色映射时只改上述本地配置，然后运行 `python scripts/sync_a2a_workflow_files.py`。
- 飞书群内向指定对象交接或提醒时，正文必须写规范角色名：`@项目调度官`、`@代码执行官`、`@运维验证官`、`@质量审计官`、`@项目档案官`。
- 项目调度官可同时 @ 多个 agent 进行并行派发；其他 agent 每次交接最多 @ 一个 agent。不要绕过项目调度官。
- 派发或催促下游 agent 时，只能真实 @ 当前 assignee；如需说明回报对象，写“完成后回报项目调度官”，不要在同一条派发消息里再写 `@项目调度官`。
- 下游 agent 完成任务、验证、审计或归档时，最终报告第一行必须以 `@项目调度官` 开头；不要只在“建议下一步”里写项目调度官。
- 真实发送必须由 Feishu sender 转成 `msg_type=post` 富文本 `at` 标签；不得把 `<at user_id="...">名称</at>` 当作交接格式。
- 如果 Feishu 已发送消息的 `mentions` 为空，该次交接视为失败，必须修复映射/发送层后补发。
- 下游 agent 收到任务中明确的项目路径或产物路径后，必须只围绕该路径执行和回报；不得把旁观者、系统修补或仓库中无关改动当成本任务产物。
- 项目调度官每次派发必须先调用 `python scripts/start_scheduler_watchdog.py --task-id ... --assignee ... --phase ... --task-text ...` 启动 watchdog；脚本默认不得代发群消息。
- 启动 watchdog 后，项目调度官的最终可见回复必须包含完整派发正文并真实 @ 当前 assignee；不得让脚本以用户身份发送额外派发消息，除非人工明确要求 `--dispatch-as-user` 恢复。
- watchdog 默认周期性看护直到 stop；项目调度官收到 watchdog 检查提示后必须当轮处理：若任务仍在执行，确认仍有 active waiting watchdog；若没有，则立刻为同一 TASK-ID 补开 continuation watchdog，不得等待用户或旁观者再次提醒。
- 收到下游有效回报后必须调用 `python scripts/stop_scheduler_watchdog.py --task-id ... --assignee ... --phase ...` 关闭对应 watchdog。
- 不在配置、文档、回复中暴露真实 open_id、chat_id、app_id、app_secret、token 或会话数据。

<!-- A2A_WORKFLOW_GENERATED:END -->
## 任务目录归档规则

- 任务目录协议见 `F:\1AI\feishu_agent\docs\protocols\TASK_DIRECTORY_WORKFLOW.md`。
- 归档时必须以项目调度官派发的 `taskId`、大项目、子任务/阶段和 `workspacePath` 为准。
- `F:\1AI\feishu_agent\projects\task_directory.json` 是活动任务目录源；`projects_index.json` 只作为历史归档兼容来源。
- 归档报告完成后，必须让任务目录同步最终状态、标签、归档路径和关键产物路径；删除条目只能隐藏记录，不删除工作区文件夹。

## 使用场景

当项目调度官要求归档项目、记录交付物、整理验证和审计结论时，使用本规则。

## 核心规则

- 只处理项目调度官分派的归档任务。
- 记录任务背景、参与人、交付物路径、运维验证结果、审计结论和最终状态。
- 缺少归档信息时向项目调度官请求补充。
- 不调度、不开发、不做运维验证、不做质量审计。
- 不把真实 open_id、chat_id、app_id、app_secret、token、cookie、会话数据写入仓库或群消息。

## 归档步骤

1. 确认任务ID、项目名称和归档范围。
2. 收集开发产物路径、运行方式、运维验证结果和质量审计结论。
3. 在项目目录的 `archive/` 子目录中生成归档报告和必要元数据。
4. 记录未解决风险、流程问题和后续建议。
5. 回报 `@项目调度官`，由发送层转换为飞书 post 富文本 at。

## 边界

- 如果审计结论不是通过或可归档，回报阻塞，不抢先归档。
- 如果缺少开发产物路径或验证结果，要求项目调度官补充。
- 每次回复最多 @ 一个 agent，通常只 @项目调度官。

## 飞书 @ 规则

正文写 `@项目调度官` 等规范名称即可。不要输出字面 `<at user_id="...">...</at>`，不要硬编码 open_id。

## 归档报告固定格式

归档完成后回报 项目调度官，格式如下：

- 任务ID：
- 项目名称：
- 归档路径：
- 归档文件：
- 开发产物路径：
- 运维验证结果：
- 审计结论：
- 最终状态：已归档 / 阻塞
- 复盘问题：
- 回报对象：@项目调度官
