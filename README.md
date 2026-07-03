# Multiagent Configuration

## Current Bot Names

真实 Open ID 和群 chat_id 属于本地运行配置，不写入仓库。默认唯一来源是：

- `F:\1AI\Agent control center\config\stack.settings.local.json`

`scripts/a2a_workflow_config.py` 负责读取这个配置，并派生出 Feishu 发送层、watchdog、群消息探针和各 agent prompt 需要的配置。环境变量 `MULTIAGENT_DEFAULT_CHAT_ID`、`MULTIAGENT_COORDINATOR_OPEN_ID` 只作为临时调试覆盖，不作为长期配置源。

修改角色或 open_id 后执行：

```bash
python scripts/sync_a2a_workflow_files.py
```

然后重启 OpenClaw Gateway，使 `OPENCLAW_FEISHU_A2A_BOTS` 重新生成。

| Name | Role |
|---|---|
| 项目调度官 | 任务拆解、调度、进度管理 |
| 代码执行官 | 代码实现、修复和本地测试 |
| 运维验证官 | 运行、环境、部署和验证 |
| 质量审计官 | 质量审计、返工意见 |
| 项目档案官 | 项目记录、文档归档 |

## Workflow

1. User mentions `@项目调度官` with a task.
2. `项目调度官` breaks down the work and mentions one downstream agent at a time using Feishu post rich text.
3. `@代码执行官` implements code and reports artifact path, run method, and self-test result back to `@项目调度官`.
4. `@运维验证官` validates run method, environment, availability, and operational risks, then reports back to `@项目调度官`.
5. `@质量审计官` audits requirements, defects, risks, and rework needs, then reports back to `@项目调度官`.
6. After audit passes, `@项目档案官` records the process, artifact, validation result, and audit conclusion.
7. `项目调度官` sends the final summary.

所有机器人均按本地 agent 管理；本地路径和运行检查只由具备本地访问能力的 agent 汇报。

## Python-First Operations

日常运行、状态检查和 provider 切换统一走 Python wrapper：

```bash
python scripts/stack.py status --json
python scripts/stack.py switch-provider native
python scripts/stack.py restart codex-agent
python scripts/stack.py restart openclaw
```

OpenClaw Gateway 的底层 Windows 入口仍是 OpenClaw 自带 `gateway.cmd`，但它由 Agent Control Center 的 Python 控制层启动、记录 PID 和写日志；不要在常规流程里直接运行 shell 脚本。

新增或修改运行链路时必须优先使用 Python、Node.js 直接 `spawn` 可执行文件，或稳定的 Windows 原生命令；不要把中文文本、角色名、JSON payload 或飞书 mention 流程穿过 shell 管道。

## Scheduler Watchdog

项目调度官每次向下游 agent 派发任务后，必须启动轻量倒计时提醒器。它会按任务内容自动估计等待时间，到点后以 user 身份向群内 `@项目调度官` 发送富文本 `post` 检查 prompt，防止执行 agent 失效或任务卡死。

```bash
python scripts/start_scheduler_watchdog.py --task-id TASK-YYYYMMDD-NNN --assignee 代码执行官 --phase 开发实现 --task-text "派发任务摘要"
```

`start_scheduler_watchdog.py` 会先发送富文本 @assignee 派发消息，再非阻塞启动 Python watchdog 进程，并立即返回 PID、日志路径和状态文件路径。启动同一 `task-id` 的新 watchdog 时，默认会终止并标记旧 watchdog 为 `superseded`，避免多个倒计时堆积。

当被派发 agent 已经有效回复时，项目调度官或消息处理流程必须关闭对应 watchdog：

```bash
python scripts/stop_scheduler_watchdog.py --task-id TASK-YYYYMMDD-NNN --assignee 代码执行官 --phase 开发实现
```

watchdog 的运行状态保存在 `runtime/watchdogs/`，日志保存在 `runtime/logs/`。真实 `chat_id` 和 `open_id` 仍从本地 ignored 配置或环境变量读取；dry-run 输出会脱敏。
