# backup_migration

这个目录负责“留后路”和“搬上下文”。

文件说明：

- `backups.py`：处理备份清理等逻辑，避免配置和状态文件无限积累。
- `thread_migration.py`：处理线程迁移、会话继续这类操作。
- `__init__.py`：包初始化文件。

学习建议：

- 想理解“迁移会话到别的 Provider”是怎么做的，看 `thread_migration.py`。
- 想改备份保留策略，先看 `backups.py`。
