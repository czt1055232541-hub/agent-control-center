# 日志与请求关联

ACC 日志位于 `{ACC_ROOT}/runtime/logs`；飞书 Agent 日志位于 `{FEISHU_AGENT_ROOT}/runtime/logs`。两侧物理目录保持独立，由 ACC 统一展示。

HTTP 响应包含 `X-Request-ID`，错误 JSON 同时包含 `request_id`。定位故障时先复制 request ID，再在 ACC 日志中搜索同一值。

预期 4xx 只记录方法、路径、状态和错误码；未捕获 5xx 才记录异常堆栈。日志不得记录 token、真实 Bot/用户/群 ID 或完整本地配置。

现阶段保留可读文本与现有 JSONL 操作日志。只有接入日志平台后才统一转换为 JSON Lines。
