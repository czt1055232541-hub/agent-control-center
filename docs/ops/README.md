# ACC 运维文档

ACC 与飞书 Agent 已合并为单仓：控制面位于 `src/web`，飞书运行面位于 `agent-runtime`，共用根配置与 runtime。原飞书仓库只作为一个发布周期内的回滚源。

- [ARCHITECTURE.md](ARCHITECTURE.md)：组件、端口和边界
- [STARTUP.md](STARTUP.md)：唯一启动、停止和状态命令
- [CONFIG.md](CONFIG.md)：共享配置契约与本机覆盖
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md)：常见故障定位
- [LOGS.md](LOGS.md)：日志、request ID 和轮转
- [RECOVERY.md](RECOVERY.md)：失败恢复和回滚
- [MIGRATION.md](MIGRATION.md)：迁移到新机器
- [COMPATIBILITY.md](COMPATIBILITY.md)：旧入口与退役条件
- [BASELINE-2026-07-13.md](BASELINE-2026-07-13.md)：本轮实施基线
- [PHYSICAL-MERGE-2026-07-13.md](PHYSICAL-MERGE-2026-07-13.md)：单仓合并、切换与回滚证据

文档变量：`{ACC_ROOT}` 为单仓根目录，`{PROJECTS_ROOT}` 为保持外置的项目工作区。
