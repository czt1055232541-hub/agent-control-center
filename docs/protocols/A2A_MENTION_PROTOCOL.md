# A2A Mention Protocol

<!-- A2A_WORKFLOW_GENERATED:BEGIN -->

## Source Of Truth

- Role names, aliases, Feishu open IDs, and the default group chat ID are read from the local Agent Control Center settings.
- Repository files must not contain real open IDs or chat IDs.
- Runtime Feishu delivery uses `OPENCLAW_FEISHU_A2A_BOTS`, generated from the same local settings at gateway startup.

## Mention Rules

- Agent replies write normalized role names such as `@项目调度官` or `@代码执行官`.
- The Feishu sender converts normalized role names to `msg_type=post` rich-text `at` elements.
- Do not output literal `<at user_id="...">名称</at>` as the handoff format.
- Mention at most one agent in a handoff reply.
- If a delivered Feishu message has an empty `mentions` list after a supposed handoff, the handoff failed and must be retried after fixing the mapping or sender layer.
- Watchdog prompts are also sent as Feishu `post` messages with a real `at` element for 项目调度官.

## Team Map

| 名称 | ID 来源 | 角色 |
|---|---|---|
| 项目调度官 | 本地 A2A 配置 | 任务拆解、调度、进度管理 |
| 代码执行官 | 本地 A2A 配置 | 代码实现、修复和本地测试 |
| 运维验证官 | 本地 A2A 配置 | 运行、环境、部署和验证 |
| 质量审计官 | 本地 A2A 配置 | 质量审计、返工意见 |
| 项目档案官 | 本地 A2A 配置 | 项目记录、文档归档 |

<!-- A2A_WORKFLOW_GENERATED:END -->
