# 配置契约

ACC 配置默认位于 `{ACC_ROOT}/config/stack.settings.local.json`，该文件包含本机路径和身份映射，不得提交。模板使用 `stack.settings.example.json`。

共享契约版本 1 包括 Codex 路径/模型、MoonBridge 端口、OpenClaw 端口、Agent 目录和 lark-cli 路径。ACC 是控制面真值来源；飞书 Agent 保留自己的运行配置，并通过 `/api/config/status` 检查漂移。

可用环境覆盖：

- `STACK_SETTINGS_PATH`：ACC 配置文件
- `FEISHU_AGENT_SETTINGS_PATH`：飞书 Agent 对比配置
- `PYTHON_EXE`、`NODE_EXE`、`NPM_EXE`：本机工具链

配置输出必须经过脱敏。键名含 token、secret、password、openId、chatId 或 appId 时不返回真实值。文件写入应使用 `atomic_write_json`：先校验、写临时文件、原子替换并只保留有限备份。
