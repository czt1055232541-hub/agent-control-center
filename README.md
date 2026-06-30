# Multiagent Configuration

## Current Bot Names

真实 Open ID 和群 chat_id 属于本地运行配置，不写入仓库。请从以下位置读取：

- `F:\1AI\Agent control center\config\stack.settings.local.json`
- `agents/feishu-codex-agent/.env`
- 环境变量 `MULTIAGENT_DEFAULT_CHAT_ID`、`MULTIAGENT_COORDINATOR_OPEN_ID`

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

日常运行、状态检查和 provider 切换优先走 Python wrapper，不直接调用 PowerShell：

```bash
python scripts/stack.py status --json
python scripts/stack.py switch-provider native
python scripts/stack.py restart codex-agent
python scripts/stack.py restart openclaw
```

OpenClaw Gateway 的底层 Windows 入口仍是 OpenClaw 自带 `gateway.cmd`，但它由 Agent Control Center 的 Python 控制层启动、记录 PID 和写日志；不要在常规流程里直接运行 PowerShell 脚本。
