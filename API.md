# Agent Control Center — API 接口文档

## 概述

Control Center 基于 **FastAPI** 构建，提供 RESTful API 管理 Feishu Codex Agent 栈。
所有可写操作（启动/停止/重启/迁移等）需携带 `X-Control-Token` 请求头进行鉴权。

---

## 基本信息

| 项目 | 值 |
|---|---|
| 基础 URL | `http://127.0.0.1:8765`（默认端口） |
| API 前缀 | `/api` |
| 鉴权方式 | 请求头 `X-Control-Token: <token>` |
| 文档地址 | `http://127.0.0.1:8765/docs`（Swagger UI） |
| 数据格式 | JSON |

---

## 1. Metrics 端点

> `GET /metrics`

返回 Prometheus 格式的监控指标文本，可被 Prometheus Server 或 `curl` 直接采集。

### 1.1 `http_requests_total`

**类型：** Counter（计数器）

**标签：**
| 标签 | 说明 |
|---|---|
| `method` | HTTP 方法（GET、POST 等） |
| `status` | HTTP 状态码字符串（如 `"200"`、`"500"`） |

**含义：** 自服务启动以来处理的 HTTP 请求总数，按请求方法和状态码划分。

---

### 1.2 `http_request_duration_seconds`

**类型：** Histogram（直方图）

**标签：**
| 标签 | 说明 |
|---|---|
| `method` | HTTP 方法 |
| `endpoint` | 请求路径（如 `/api/status`、`/metrics`） |

**分桶（buckets）：**
`0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0`（单位：秒）

**含义：** 请求延迟分布。可计算 P50/P95/P99 延迟：

```
# 计算 P99 延迟（PromQL）
histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, method, endpoint))
```

---

### 1.3 `agent_status`

**类型：** Gauge（仪表盘）

**标签：**
| 标签 | 说明 |
|---|---|
| `agent` | 智能体名称（如 `项目调度官`、`代码执行官`） |

**含义：** 智能体在线状态。`1` 表示在线，`0` 表示离线。

```promql
# 查看所有智能体在线情况
agent_status

# 检查某个智能体是否在线
agent_status{agent="项目调度官"}

# 统计在线智能体数量
count(agent_status == 1)
```

### 1.4 向后兼容指标（`acc_*` 前缀）

| 指标名 | 类型 | 说明 |
|---|---|---|
| `acc_api_requests_total` | Counter | 按 endpoint / method / status_code 统计的 API 请求总数 |
| `acc_api_request_duration_seconds` | Histogram | API 请求延迟分布 |
| `acc_component_status` | Gauge | 组件运行状态（1=运行中，0=已停止），标签 `component` |
| `acc_operations_total` | Counter | 控制操作执行总数，标签 `component` / `action` / `outcome` |
| `acc_websocket_connections` | Gauge | 当前 WebSocket 连接数 |

---

## 2. 使用示例

### 2.1 直接获取监控指标

```bash
# 查看所有 Prometheus 指标
curl http://127.0.0.1:8765/metrics
```

### 2.2 查询服务健康状态

```bash
curl http://127.0.0.1:8765/api/health
```

返回：
```json
{
  "status": "ok",
  "timestamp": "2026-06-26T10:00:00+08:00",
  "version": "0.1.0"
}
```

### 2.3 获取栈状态

```bash
curl http://127.0.0.1:8765/api/status
```

### 2.4 执行控制操作（需 Token）

```bash
# 1. 获取 Token
TOKEN=$(curl -s http://127.0.0.1:8765/api/session | python -c "import sys,json;print(json.load(sys.stdin)['token'])")

# 2. 启动 OpenClaw
curl -X POST http://127.0.0.1:8765/api/openclaw/start \
  -H "X-Control-Token: $TOKEN"

# 3. 启动全栈（Native 模式）
curl -X POST http://127.0.0.1:8765/api/stack/start-native \
  -H "X-Control-Token: $TOKEN"

# 4. 启动全栈（MoonBridge 模式）
curl -X POST http://127.0.0.1:8765/api/stack/start-moonbridge \
  -H "X-Control-Token: $TOKEN"

# 5. 停止全栈
curl -X POST http://127.0.0.1:8765/api/stack/stop \
  -H "X-Control-Token: $TOKEN"
```

### 2.5 查看日志

```bash
# 查看 OpenClaw 日志（最近 120 行）
curl http://127.0.0.1:8765/api/logs/openclaw?lines=120

# 支持的组件：openclaw、moonbridge、codex-agent、codex-desktop、control-center-api、operations
```

### 2.6 线程迁移

```bash
# 列出最近会话
curl http://127.0.0.1:8765/api/thread-migration/threads?limit=10

# 迁移会话到 MoonBridge（需 Token）
curl -X POST http://127.0.0.1:8765/api/thread-migration/migrate \
  -H "X-Control-Token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "<SESSION_ID>", "target_provider": "moonbridge", "prompt": "请继续"}'
```

### 2.7 诊断

```bash
# 运行全部诊断
curl http://127.0.0.1:8765/api/diagnostics

# Codex 诊断
curl http://127.0.0.1:8765/api/doctor/codex

# 查看 MoonBridge 可用模型
curl http://127.0.0.1:8765/api/moonbridge/models

# 查看飞书认证状态
curl http://127.0.0.1:8765/api/lark/auth-status
```

---

## 3. 常见调用方式

### 3.1 Prometheus 集成

将 `/metrics` 端点配置为 Prometheus 的 `scrape_config` 目标：

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'agent-control-center'
    static_configs:
      - targets: ['127.0.0.1:8765']
    metrics_path: '/metrics'
```

### 3.2 用 Python 调用

```python
import requests

BASE = "http://127.0.0.1:8765"

# 获取指标
resp = requests.get(f"{BASE}/metrics")
print(resp.text)

# 获取 Token 并执行操作
session = requests.get(f"{BASE}/api/session").json()
token = session["token"]

headers = {"X-Control-Token": token}
resp = requests.post(f"{BASE}/api/stack/start-native", headers=headers)
print(resp.json())
```

### 3.3 用 WebSocket 订阅实时状态

```javascript
const ws = new WebSocket("ws://127.0.0.1:8765/ws/status");
ws.onmessage = (event) => {
  const status = JSON.parse(event.data);
  console.log("Stack status:", status);
};
```

### 3.4 浏览器访问

直接打开以下地址即可浏览 Swagger UI 交互式文档：

- **Swagger UI:** `http://127.0.0.1:8765/docs`
- **ReDoc 替代文档:** `http://127.0.0.1:8765/redoc`

---

## 4. 错误码

| HTTP 状态码 | 说明 |
|---|---|
| 200 | 成功 |
| 401 | 缺少 `X-Control-Token` 请求头 |
| 403 | Token 无效（禁止访问） |
| 409 | 操作冲突（有其他操作正在进行中） |
| 422 | 请求参数校验失败 |
| 500 | 服务内部错误 |
