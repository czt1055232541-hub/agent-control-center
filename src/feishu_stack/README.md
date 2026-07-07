# feishu_stack

这是后端主代码包。你可以把它理解成“控制中心的大脑”。

这里的内容分两类：

1. 真正实现功能的目录

- `api/`：网页接口入口，前端点按钮时通常会走这里。
- `core/`：基础设施，比如配置、状态、日志、进程工具。
- `modules/`：按页面功能域分类的业务代码，是现在最推荐你阅读和修改的地方。

2. 兼容旧导入路径的薄包装文件

- `app.py`：兼容旧的 `feishu_stack.app` 导入，实际转发到 `api/app.py`。
- `cli.py`：兼容旧的命令行入口，实际转发到 `modules/operations/cli.py`。
- `config.py`：兼容旧的配置导入，实际转发到 `core/settings.py`。
- `agent_config_editor.py`、`agent_dashboard.py`、`agent_registry.py`：兼容旧的 Agent 阵列相关导入。
- `backups.py`、`thread_migration.py`：兼容旧的备份和迁移导入。
- `codex_agent.py`、`codex_config.py`、`codex_desktop.py`、`codex_provider.py`、`moonbridge.py`、`openclaw.py`、`typing_indicator.py`：兼容旧的模型与 Provider / 运行组件导入。
- `control_center.py`、`operations.py`、`stack_actions.py`：兼容旧的操作编排导入。
- `diagnostics.py`、`metrics.py`：兼容旧的诊断与指标导入。
- `log_manager.py`、`logs.py`、`models.py`、`process.py`、`security.py`、`status.py`：兼容旧的基础能力导入。
- `__init__.py`：这个包的初始化文件，也定义版本号。

学习建议：

- 新逻辑优先看 `modules/`、`api/`、`core/`。
- 顶层这些同名 `.py` 文件多数只是“转发器”，一般不需要在这里写新业务。
