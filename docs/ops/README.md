# ACC 运维文档

ACC 是控制面，`{FEISHU_AGENT_ROOT}` 是独立运行面；两者保持独立 Git 历史和 runtime 目录。

- [ARCHITECTURE.md](ARCHITECTURE.md)：组件、端口和边界
- [STARTUP.md](STARTUP.md)：唯一启动、停止和状态命令
- [CONFIG.md](CONFIG.md)：共享配置契约与本机覆盖
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md)：常见故障定位
- [LOGS.md](LOGS.md)：日志、request ID 和轮转
- [RECOVERY.md](RECOVERY.md)：失败恢复和回滚
- [MIGRATION.md](MIGRATION.md)：迁移到新机器
- [COMPATIBILITY.md](COMPATIBILITY.md)：旧入口与退役条件
- [BASELINE-2026-07-13.md](BASELINE-2026-07-13.md)：本轮实施基线

文档变量：`{ACC_ROOT}` 为控制中心仓库，`{FEISHU_AGENT_ROOT}` 为飞书 Agent 仓库。
