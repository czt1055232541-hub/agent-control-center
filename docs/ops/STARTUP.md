# 启动与停止

在 `{ACC_ROOT}` 中使用唯一 Python 入口：

```text
python scripts/stack.py status --json
python scripts/stack.py stack start-native
python scripts/stack.py stack start-deepseek
python scripts/stack.py stack stop
python scripts/stack.py serve-control-center --open
python scripts/stack.py status-control-center
python scripts/stack.py stop-control-center
python scripts/stack.py watchdog status
python scripts/stack.py watchdog start --task-id TASK-ID --assignee 代码执行官 --phase 开发实现 --task-text "任务摘要"
python scripts/stack.py watchdog stop --task-id TASK-ID --assignee 代码执行官 --phase 开发实现
python scripts/stack.py a2a sync
python scripts/stack.py a2a probe --help
```

启动前先执行 `status --json` 和 `/api/config/status?check_runtime=true`。不要根据端口号直接终止进程；先确认 PID、可执行文件和命令行属于目标组件。

`stack stop` 不停止 Codex Desktop。关闭 Codex Desktop 仍需显式安全开关和单独操作。
