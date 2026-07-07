# modules

这个目录是现在最推荐你学习和修改的地方。它按网页功能域来分类后端业务代码。

子目录说明：

- `agent_array/`：Agent 阵列相关后端逻辑。
- `model_provider/`：模型与 Provider 相关后端逻辑。
- `logs_diagnostics/`：日志与诊断。
- `backup_migration/`：备份与迁移。
- `operations/`：操作编排、命令行、控制中心启动。
- `dashboard/`、`config_center/`、`feishu_connection/`、`routing_rules/`、`task_battlefield/`：为未来页面功能预留的模块入口。
- `__init__.py`：包初始化文件。

学习建议：

- 想改哪个页面的功能，就先找同名功能域目录。
- 如果一时不知道该去哪，看页面左侧导航栏，再对照这里的目录名。
