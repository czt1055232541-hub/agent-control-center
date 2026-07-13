# A2A Mention Protocol

<!-- A2A_WORKFLOW_GENERATED:BEGIN -->

## Source Of Truth

- Role names, aliases, Feishu open IDs, and the default group chat ID are read from the local Agent Control Center settings.
- Repository files must not contain real open IDs or chat IDs.
- Runtime Feishu delivery uses `OPENCLAW_FEISHU_A2A_BOTS`, generated from the same local settings at gateway startup.

## Mention Rules

- Agent replies write normalized role names such as `@项目调度官` or `@代码执行官`.
- Downstream agents must start final completion, validation, audit, or archival reports with `@项目调度官`.
- The Feishu sender converts normalized role names to `msg_type=post` rich-text `at` elements.
- Do not output literal `<at user_id="...">名称</at>` as the handoff format.
- Only 项目调度官 may mention multiple agents in a handoff reply (for parallel task dispatch); all other agents must mention at most one agent.
- Assignment or downstream reminder messages may only truly mention the current assignee; write the coordinator name without `@` when explaining where the assignee should report back.
- If a delivered Feishu message has an empty `mentions` list after a supposed handoff, the handoff failed and must be retried after fixing the mapping or sender layer.
- The coordinator must start each assignment with `python scripts/start_scheduler_watchdog.py --task-id ... --assignee ... --phase ... --task-text ...`; the script launches the watchdog only and must not send an assignment message by default.
- After the watchdog starts, the coordinator's final visible reply must contain the full assignment and a real `@assignee`; do not use user-identity dispatch unless a human explicitly requests `--dispatch-as-user` recovery.
- Watchdog prompts are also sent as Feishu `post` messages with a real `at` element for 项目调度官.
- Watchdogs run periodic coordinator checks until stopped. When a watchdog prompt fires and the downstream task is still running, 项目调度官 must confirm an active waiting watchdog exists; if none exists, start a continuation watchdog for the same TASK-ID in that same check turn.

## Team Map

| 名称 | ID 来源 | 角色 |
|---|---|---|
| 项目调度官 | 本地 A2A 配置 | 任务拆解、调度、进度管理 |
| 代码执行官 | 本地 A2A 配置 | 代码实现、修复和本地测试 |
| 运维验证官 | 本地 A2A 配置 | 运行、环境、部署和验证 |
| 质量审计官 | 本地 A2A 配置 | 质量审计、返工意见 |
| 项目档案官 | 本地 A2A 配置 | 项目记录、文档归档 |

<!-- A2A_WORKFLOW_GENERATED:END -->
