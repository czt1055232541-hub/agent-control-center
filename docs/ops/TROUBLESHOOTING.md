# 故障排查

## 页面白屏或加载失败

1. 查看全局错误兜底提示和浏览器控制台。
2. 请求 `/api/health`，记录 `X-Request-ID`。
3. 直接请求失败的 API，确认错误 JSON 的 `error_code`、`message` 和 `request_id`。
4. 确认 Web 构建产物与正在运行的服务属于同一工作区。

## 启动失败或端口冲突

1. 运行 `python scripts/stack.py status --json`。
2. 查询 `/api/config/status?check_runtime=true`。
3. 对照 ARCHITECTURE.md 确认端口所有者。
4. 只有在 PID、可执行文件和命令行都匹配目标组件后，才使用项目停止命令。

## 配置漂移

查看 `/api/config/status` 的 `drift`。修改本地配置前先备份；校验失败时不得覆盖最后有效文件。真实身份字段不应出现在响应中。
