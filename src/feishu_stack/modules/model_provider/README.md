# model_provider

这个目录对应“模型与 Provider”，是当前最重要的运维模块之一。

文件说明：

- `openclaw_gateway.py`：管理 OpenClaw Gateway 的状态、启动、停止、打开界面等。
- `deepseek.py`：管理 DeepSeek 的状态、模型列表、模型切换等。
- `codex_agent.py`：管理 codex-agent 进程相关行为。
- `codex_desktop.py`：处理 Codex Desktop 应用的检测和启动控制。
- `codex_config.py`：处理 Codex 配置文件读写与 provider 切换底层逻辑。
- `provider_switch.py`：更接近“业务入口”的 provider 切换逻辑，通常由 API 和操作编排直接调用。
- `__init__.py`：包初始化文件。

学习建议：

- 想改 DeepSeek 模型切换，优先看 `deepseek.py` 和 `provider_switch.py`。
- 想改 Codex 配置写法或 provider 写入格式，看 `codex_config.py`。
- 想改 OpenClaw 启停行为，看 `openclaw_gateway.py`。
