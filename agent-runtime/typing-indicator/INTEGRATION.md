# Typing Indicator 集成说明

`typing-indicator` 用于监听飞书消息事件，并短暂发送 typing reaction。它是可选辅助组件，由 Agent Control Center 统一启动和停止。

## 文件

- 主脚本：`agent-runtime/typing-indicator/typing-indicator.py`
- 启动器：`agent-runtime/typing-indicator/launcher.py`
- 控制层：`src/feishu_stack/typing_indicator.py`

## 配置

运行时通过环境变量注入本机路径，不在源码里写死：

- `PYTHON_EXE`：Python 解释器路径，未设置时 launcher 使用当前解释器
- `LARK_CLI_BIN`：lark-cli 可执行文件路径，未设置时尝试 `lark-cli`
- `LARK_CLI_PROFILE`：可选 lark-cli profile；未设置时使用默认配置

Control Center 从 `config/stack.settings.local.json` 读取 `pythonExe` 和 `agent.larkCliBin` 后传入子进程。若你的 lark-cli 需要固定 profile，可在 local 配置的 `agent` 节点中增加：

```json
{
  "agent": {
    "larkCliProfile": "your-profile-name"
  }
}
```

## 启动

```powershell
python -m feishu_stack.cli start typing-indicator
```

或随 stack 启动：

```powershell
python -m feishu_stack.cli stack start-native
```

## 运行边界

typing indicator 只继承 Control Center 为它构造的子进程环境。控制层会移除 `OPENCLAW_*`、`CLAW_HOME`、`CODEX_HOME` 等容易触发错误上下文检测的变量；这不会修改系统环境，也不会改变 OpenClaw 或飞书 multi-agent 的配置。

## 行为

收到目标 bot 的消息后：

1. POST typing reaction
2. 保持短暂“正在输入”状态
3. 到期后 DELETE reaction

如果 lark-cli bus 退出，launcher 会停止 typing indicator；如果 typing indicator 自身退出，launcher 最多重启 5 次。
