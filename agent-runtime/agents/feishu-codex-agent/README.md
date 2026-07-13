# Feishu Codex Agent

一个以飞书为入口、以官方 `lark-cli` 为主要执行层的最小 AI Agent：

```text
飞书群聊 @Codex -> 本地/服务器 Agent -> Codex/OpenAI -> lark-cli -> 飞书回复
```

MVP 阶段不把 `codex mcp add lark-mcp` 作为入口；`lark-openapi-mcp` 可作为后续备用工具层。

## 当前状态

- Node Agent 与本地 `lark-cli` 位于 `{ACC_ROOT}/agent-runtime`；Codex CLI 路径由根配置解析。
- npm prefix、cache、临时目录、home/appdata 都指向 F 盘，避免下载安装到 C 盘。
- `lark-cli config init --new` 已完成飞书应用配置。
- `lark-cli auth status` 已验证 bot 可用；user token 如显示 `needs_refresh`，会在下一次 user API 调用时自动刷新。
- `lark-cli event list --json`、`event schema im.message.receive_v1 --json`、`event consume ... --as bot` 已验证。
- 当前 bot 已能看到群聊 `陈智拓的智能体团队`。
- Agent 默认 `DRY_RUN=true`；当前 `.env` 可改为 `DRY_RUN=false` 做真实回复测试。

## 目录结构

```text
{ACC_ROOT}/agent-runtime
|-- .tools/                 # portable Node.js
|-- .npm-global/            # Codex CLI and lark-cli
|-- .npm-cache/             # npm cache
|-- .home/                  # lark-cli home/config cache
|-- .runtime/               # runtime logs and pid files
`-- feishu-codex-agent/
    |-- package.json
    |-- tsconfig.json
    |-- .env.example
    |-- README.md
    |-- scripts/
    |-- src/
    |   |-- index.ts
    |   |-- env.ts
    |   |-- eventConsumer.ts
    |   |-- eventParser.ts
    |   |-- handler.ts
    |   |-- router.ts
    |   |-- larkCli.ts
    |   |-- agent.ts
    |   |-- confirmationStore.ts
    |   `-- types.ts
    `-- tests/
        `-- router.test.ts
```

## 环境加载

运行链路优先使用 Python/Node 直接调用可执行文件，不依赖 shell shim：

```bash
node --version
npm --version
codex --version
{ACC_ROOT}/agent-runtime/.npm-global/lark-cli.cmd --help
```

已验证版本：

```text
node v24.16.0
npm 11.13.0
codex-cli 0.139.0
lark-cli 1.0.53
```

## 安装与测试

```bash
cd /d {ACC_ROOT}\agent-runtime\agents\feishu-codex-agent
npm install
npm test
```

`package.json` 提供：

```json
{
  "scripts": {
    "build": "tsc -p tsconfig.json",
    "start": "node dist/src/index.js",
    "test": "npm run build && node --test dist/tests/*.test.js",
    "lark:event:list": "lark-cli event list --json",
    "lark:event:schema": "lark-cli event schema im.message.receive_v1 --json"
  }
}
```

## .env

从模板创建：

```bash
python -c "from pathlib import Path; Path('.env').write_text(Path('.env.example').read_text(encoding='utf-8'), encoding='utf-8')"
```

关键变量：

```dotenv
DRY_RUN=true
LOG_LEVEL=info
LARK_IDENTITY=bot
LARK_BOT_NAME=Codex
LARK_CLI_OUTPUT_ENCODING=utf-8
AGENT_PROVIDER=local
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
CONFIRM_TIMEOUT_MS=600000
MAX_CONTEXT_MESSAGES=30
```

生产或真实飞书回复测试时，将 `DRY_RUN=false`。

## lark-cli 配置

创建或绑定飞书应用：

```bash
lark-cli config init --new
```

如果命令输出浏览器链接，请在浏览器中完成配置。不要伪造 App ID/App Secret，也不要把密钥写入仓库。

登录并验证：

```bash
lark-cli auth login --recommend
lark-cli auth status
```

## 事件监听

验证事件能力：

```bash
lark-cli event list --json
lark-cli event schema im.message.receive_v1 --json
lark-cli event consume im.message.receive_v1 --as bot
```

Agent 启动后会执行：

```text
lark-cli event consume im.message.receive_v1 --as bot
```

实现要点：

- 读取 stdout NDJSON 事件流。
- 等待 stderr 中的 ready marker，不使用固定 sleep。
- 解析 `chat_id`、`message_id`、`sender_id`、`content`、`message_type`、`create_time`。
- 支持 `lark-cli event consume` 的扁平事件结构。
- 忽略 bot/app 自己发出的消息，避免循环回复。

## 启动

```bash
cd /d {ACC_ROOT}\agent-runtime\agents\feishu-codex-agent
npm run build
npm start
```

Agent 只响应：

- 群聊中 `@Codex` 的消息。
- 私聊机器人消息。
- 明确以 `Codex` 或 `/codex` 开头的消息。

回复使用官方快捷命令：

```bash
lark-cli im +messages-send --chat-id <CHAT_ID> --text <TEXT> --as bot
```

## 指令路由

MVP 支持：

- 问候/能力介绍。
- 群聊总结与行动项提炼。
- 创建多维表格、写入行动项。
- 搜索/读取/生成飞书文档。
- 妙搭/Spark/Miaoda/Apps 操作规划。
- 创建任务。

工具调用策略：

1. 优先使用 `lark-cli` 快捷命令，例如 `calendar +agenda`、`im +messages-send`、`docs +create`、`base +table-create`、`apps +create`。
2. 快捷命令不足时，使用 `lark-cli` 暴露的普通 API 命令。
3. 仍不足时，使用：

```bash
lark-cli api METHOD /open-apis/xxx --params '{}'
```

当前实现对缺少完整参数的写操作采用“先规划、后执行”的安全策略，避免在 live 模式下用不完整参数创建或覆盖真实飞书资源。

## 多 Agent 协作 Skill

代码执行官的群内协作规则见 `SKILL.md`。关键点：

- native 模式使用 `model_reasoning_effort = "high"`，避免 `reasoning.effort invalid_value`。
- MoonBridge 和 native 的执行速度、参数兼容性不同，轮询 codeX agent 时按 2-5 分钟观察。
- 代码执行官只做本地开发和自测，完成后 @项目调度官 回报路径、变更、运行方式、自测结果。
- 回复正文写 `@项目调度官` 即可，发送层会转换为飞书 post 富文本 at 标签；不要输出字面 `<at user_id="...">...</at>`。

## 安全确认

以下操作必须先在飞书中请求确认：

- 批量更新多维表格记录。
- 删除记录、删除文档、覆盖文档。
- 创建或发布妙搭/Spark/Miaoda 应用。
- 发布 HTML/静态站点。
- 邀请群成员、给多人发送消息。
- 创建涉及多人参与的日历事件。
- 审批、任务转交、撤回等不可逆或高影响操作。

确认格式：

```text
我将执行以下操作，请回复 确认 继续
```

同一用户在 10 分钟内回复 `确认` 后继续执行；超时则取消。

## 飞书开放平台配置

推荐配置：

- 启用机器人能力。
- 将机器人加入目标群聊。
- 订阅事件 `im.message.receive_v1`。
- 确保事件订阅与 `lark-cli config init --new` 配置的是同一个应用。
- 根据需要开通 IM、Docs、Drive、Wiki、Base、Task、Calendar、Contact、Spark/Apps 等权限。

## 权限 Scope 清单

建议按功能逐步授权：

- IM：消息接收、发送、聊天元数据、消息历史。
- Base：app/table/field/record 读写。
- Docs/Drive/Wiki：搜索、读取、创建、导入、导出、权限。
- Task：任务、任务清单、评论、附件。
- Calendar：日程查询、日程创建、参会人。
- Contact：用户搜索、open_id 映射。
- Spark/Apps：应用读取、创建、更新、发布、访问范围。
- Approval/VC/Minutes：仅在工作流实际需要时授权。

生产前可用：

```bash
lark-cli schema <service.resource.method>
```

结合飞书开放平台控制台确认精确 scope。

## 测试用例

自动化测试覆盖以下示例：

```text
@Codex 你好，介绍一下你能做什么
@Codex 总结一下刚才的讨论
@Codex 创建一个项目任务多维表格，字段包括任务名称、负责人、截止日期、状态
@Codex 把刚才讨论中的行动项写入这个多维表格
@Codex 搜索“项目计划”相关文档并总结
@Codex 根据这段需求创建一个妙搭应用原型，但执行前先让我确认
```

运行：

```bash
npm test
```

同时覆盖：

- 群聊 @ 触发。
- 私聊触发。
- 忽略 bot 自己的消息。
- 扁平 NDJSON 事件解析。
- `im +messages-send` 参数格式。
- 高影响操作确认流。
- live 模式下不执行缺参写操作。

## 故障排查

查看状态：

```bash
lark-cli auth status
lark-cli event status
lark-cli im +chat-list --as bot --json
```

常见问题：

- `event status` 的 `RECEIVED` 不增长：确认机器人已加入群聊，事件 `im.message.receive_v1` 已订阅，发送的是 `@Codex ...` 或私聊消息。
- Agent 收到事件但不回复：查看 `.runtime\agent-live.err.log`，确认 `respond=true`，并检查 `DRY_RUN=false`。
- Shell 编码或执行策略问题：不要让运行链路经过 shell 管道；使用 Python、Node 或 `.exe` 路径直接调用。
- Agent 日志中文乱码：优先使用 `LARK_CLI_OUTPUT_ENCODING=utf-8`；只有确认当前 lark-cli 输出是系统本地编码时，才改为 `gb18030`。
- 发送消息失败：检查 bot 是否有发消息权限，群聊是否允许机器人发言，scope 是否包含 IM 发送相关权限。
- user token `needs_refresh`：通常会在下一次 user API 调用时刷新；如果失败，重新执行 `lark-cli auth login --recommend`。
