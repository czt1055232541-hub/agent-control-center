# logs_diagnostics

这个目录对应“日志与诊断”。

文件说明：

- `diagnostics.py`：诊断逻辑总入口，比如检查 Codex、MoonBridge、飞书认证等状态。
- `metrics.py`：Prometheus 指标相关逻辑。
- `__init__.py`：包初始化文件。

学习建议：

- 想知道诊断页的数据从哪来，看 `diagnostics.py`。
- 想接监控系统或改指标输出，看 `metrics.py`。
