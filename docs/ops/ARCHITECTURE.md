# 架构与端口

ACC 只作为观察和控制入口，不接管飞书 Agent 的 Git 历史或物理 runtime。

| 端口 | 组件 | 所有者 | 依赖 |
|---|---|---|---|
| 8765 | ACC FastAPI 与构建后的 Web | ACC | 本地配置、受管组件状态 |
| 5173 | Vite 开发服务器 | ACC Web 开发 | 8765 API |
| 18789 | OpenClaw Gateway 默认端口 | OpenClaw | OpenClaw 本机配置 |
| 38440 | MoonBridge | MoonBridge | Provider 配置 |

`stack.settings` 中的端口必须与组件自己的运行配置一致。`GET /api/config/status?check_runtime=true` 返回脱敏的配置校验、端口占用和跨仓库漂移信息。

写操作由本地控制 token 保护并使用进程内互斥锁；状态展示同时检查 PID 与真实进程/端口，不能仅凭 PID 文件判断。
