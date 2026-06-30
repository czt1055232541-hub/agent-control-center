# Agent Control Center — 运维手册

## 一、目录结构

```
C:\agent-control-center\
├── API.md                          # API 接口文档（本文档）
├── OPS.md                          # 运维手册（本文档）
├── README.md                       # 项目简介
├── pyproject.toml                  # Python 项目配置
├── .gitignore
├── config/
│   └── stack.settings.json         # 栈配置文件
├── runtime/
│   ├── logs/                       # 运行时日志
│   ├── pids/                       # 组件 PID 文件
│   ├── summaries/                  # 线程迁移摘要缓存
│   └── .gitkeep
├── scripts/
│   ├── start-all.ps1               # 启动全栈
│   ├── stop-all.ps1                # 停止全栈
│   ├── status-all.ps1              # 查看全栈状态
│   ├── start-control-center.ps1    # 仅启动 Control Center API
│   ├── stop-control-center.ps1     # 仅停止 Control Center API
│   ├── status-control-center.ps1   # 查看 Control Center 状态
│   └── install-control-center-shortcut.ps1  # 安装桌面快捷方式
├── src/
│   └── feishu_stack/               # Python 源码包
│       ├── __init__.py
│       ├── app.py                  # FastAPI 应用入口
│       ├── cli.py                  # 命令行入口
│       ├── config.py               # 配置加载
│       ├── control_center.py       # 入口点
│       ├── metrics.py              # Prometheus 指标定义
│       ├── status.py               # 栈状态聚合
│       ├── openclaw.py             # OpenClaw 管理
│       ├── moonbridge.py           # MoonBridge 管理
│       ├── codex_agent.py          # Codex Agent 管理
│       ├── codex_desktop.py        # Codex Desktop 检测
│       ├── codex_config.py         # Codex 配置管理
│       ├── codex_provider.py       # Provider 切换
│       ├── stack_actions.py        # 全栈编排动作
│       ├── backups.py              # 备份清理
│       ├── diagnostics.py          # 诊断模块
│       ├── logs.py / log_manager.py# 日志管理
│       ├── models.py               # 数据模型
│       ├── operations.py           # 操作锁/调度
│       ├── process.py              # 进程管理工具
│       ├── security.py             # Token 鉴权
│       ├── thread_migration.py     # 线程迁移
│       └── typing_indicator.py     # 打字指示器
├── tests/                          # 测试套件
│   ├── test_app.py
│   ├── test_cli.py
│   └── ...（每个模块对应一个测试文件）
├── typing-indicator/               # 打字指示器独立服务
│   ├── launcher.py
│   ├── typing-indicator.py
│   └── INTEGRATION.md
├── web/                            # 前端界面
│   ├── src/                        # TypeScript 源码
│   ├── dist/                       # 构建产物（静态文件）
│   └── package.json
└── docs/                           # 设计文档
```

---

## 二、依赖安装

### 2.1 Python 环境

- **Python 版本：** >= 3.11（推荐 3.13）
- **Python 路径：** `python`

### 2.2 安装项目依赖

```powershell
# 进入项目根目录
cd C:\agent-control-center

# 安装核心依赖
python -m pip install fastapi uvicorn prometheus_client httpx

# 安装开发依赖（用于运行测试）
python -m pip install pytest httpx
```

依赖清单（来自 `pyproject.toml`）：

| 包名 | 版本要求 | 用途 |
|---|---|---|
| `fastapi` | >=0.115 | Web 框架 |
| `uvicorn` | >=0.32 | ASGI 服务器 |
| `prometheus_client` | >=0.20 | Prometheus 指标暴露 |
| `httpx` | >=0.27（dev） | 测试 HTTP 客户端 |
| `pytest` | >=8（dev） | 测试框架 |

### 2.3 前端构建（可选）

```powershell
cd C:\agent-control-center\web
npm install
npm run build
```

---

## 三、启动与停止

### 3.1 启动全栈

```powershell
# 方法一：使用脚本（推荐）
C:\agent-control-center\scripts\start-all.ps1

# 方法二：使用脚本并指定模式
C:\agent-control-center\scripts\start-all.ps1 -CodexMode moonbridge  # MoonBridge 模式
C:\agent-control-center\scripts\start-all.ps1 -CodexMode native     # Native 模式

# 方法三：使用 CLI 命令
cd C:\agent-control-center
$env:PYTHONPATH="src"
python -m feishu_stack.cli stack start-moonbridge
```

启动后，Control Center API 默认监听 `http://127.0.0.1:8765`。

### 3.2 停止全栈

```powershell
# 方法一：使用脚本
C:\agent-control-center\scripts\stop-all.ps1

# 方法二：使用 CLI
cd C:\agent-control-center
$env:PYTHONPATH="src"
python -m feishu_stack.cli stack stop
```

### 3.3 仅启动 Control Center API

```powershell
C:\agent-control-center\scripts\start-control-center.ps1
```

### 3.4 查看状态

```powershell
# 查看全栈状态
C:\agent-control-center\scripts\status-all.ps1

# 通过 API 查看
curl http://127.0.0.1:8765/api/status
```

### 3.5 启动细节说明

Control Center API 使用 `uvicorn` 运行，进程管理逻辑：

1. **启动流程：** CLI 启动 OpenClaw → MoonBridge → Codex Agent，最后启动 FastAPI 服务
2. **PID 管理：** 各组件 PID 写入 `runtime/pids/` 目录
3. **日志：** 各组件日志写入 `runtime/logs/` 目录

---

## 四、配置文件说明

### 4.1 `config/stack.settings.json`

栈全局配置，JSON 格式：

```json
{
  "stackRoot": "F:\\1AI\\Agent control center",
  "pythonExe": "E:\\Python\\python.exe",
  "codexHome": "E:\\codeX",
  "codexBin": "E:\\codeX\\bin\\codex.exe",
  "codexConfig": "E:\\codeX\\config.toml",
  "codexNativeModel": "gpt-5.5",
  "codexNativeReasoningEffort": "high",
  "codexMoonBridgeModel": "deepseek-v4-flash",
  "moonBridgeBaseUrl": "http://127.0.0.1:38440/v1",
  "moonbridge": {
    "dir": "E:\\codeX\\moon-bridge",
    "exe": "E:\\codeX\\moon-bridge\\.cache\\moonbridge.exe",
    "port": 38440
  },
  "openclaw": {
    "home": "E:\\openclaw\\clawclaw",
    "port": 18789
  },
  "agent": {
    "dir": "F:\\1AI\\feishu_agent\\agents\\feishu-codex-agent"
  },
  "runtime": {
    "dir": "runtime",
    "logs": "runtime/logs",
    "pids": "runtime/pids"
  }
}
```

**关键字段：**

| 字段 | 说明 |
|---|---|
| `stackRoot` | 项目根目录路径 |
| `pythonExe` | Python 解释器路径 |
| `codexHome` | Codex Desktop 安装目录 |
| `codexConfig` | Codex 配置路径（config.toml） |
| `codexNativeModel` | Native 模式默认模型 |
| `codexMoonBridgeModel` | MoonBridge 模式默认模型 |
| `moonbridge.port` | MoonBridge 代理端口（38440） |
| `openclaw.port` | OpenClaw 网关端口（18789） |

### 4.2 `pyproject.toml`

Python 项目元数据和打包配置。定义依赖、构建系统和 pytest 配置。

### 4.3 `runtime/` 目录

运行时数据目录，非版本控制，程序自动创建：

| 子目录 | 内容 |
|---|---|
| `runtime/logs/` | 各组件运行日志 |
| `runtime/pids/` | 各组件进程 PID 文件 |
| `runtime/summaries/` | 线程迁移摘要缓存 |

---

## 五、常见故障排查

### 5.1 API 无法访问

**现象：** `curl http://127.0.0.1:8765/api/health` 无响应或拒绝连接

**排查步骤：**
```powershell
# 1. 检查端口是否被占用
netstat -ano | findstr :8765

# 2. 检查进程是否在运行
Get-Process -Name python -ErrorAction SilentlyContinue

# 3. 查看 API 错误日志
Get-Content "C:\agent-control-center\runtime\logs\control-center-api-err.log" -Tail 30

# 4. 重启 API
C:\agent-control-center\scripts\stop-control-center.ps1
C:\agent-control-center\scripts\start-control-center.ps1
```

### 5.2 Token 校验失败

**现象：** 返回 `401` 或 `403`

**排查：**
1. 通过 `GET /api/session` 获取当前有效 Token
2. 确保请求头格式正确：`X-Control-Token: <完整的 token 字符串>`
3. Token 存储在 `runtime/control-token.txt`，重新启动服务会自动生成新 Token

### 5.3 操作返回 409 Conflict

**现象：** 执行操作时返回 HTTP 409

**原因：** 有另一个操作正在执行。Control Center 使用操作锁确保同一时间只有一个操作在运行。

**解决：** 等待当前操作完成（最长几秒），然后重试。如果锁一直未释放，重启 Control Center API。

### 5.4 日志文件过大

**现象：** `runtime/logs/` 下日志文件占用大量磁盘空间

**解决：**
```powershell
# 查看日志大小
Get-ChildItem "C:\agent-control-center\runtime\logs" | Select-Object Name, Length

# 清理日志（保留最近 7 天）
Get-ChildItem "C:\agent-control-center\runtime\logs" -Filter *.log |
  Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-7) } |
  Remove-Item
```

### 5.5 Python 模块找不到

**现象：** `ModuleNotFoundError: No module named 'feishu_stack'`

**原因：** `PYTHONPATH` 环境变量未正确设置

**解决：**
```powershell
# 运行前设置 PYTHONPATH
$env:PYTHONPATH="C:\agent-control-center\src"
```

### 5.6 Metrics 指标异常

**现象：** `GET /metrics` 返回空或指标缺失

**排查：**
1. 确认服务正常运行：`curl http://127.0.0.1:8765/api/health`
2. 直接访问：`curl http://127.0.0.1:8765/metrics`
3. 检查 `prometheus_client` 包是否正确安装

### 5.7 Codex Desktop 未检测到

**现象：** `api/status` 中 `codex_desktop_running` 为 `false`

**原因：** Codex Desktop 应用未启动，或 Get-Process 未找到 Codex 进程

**解决：** 手动启动 Codex Desktop 应用，或通过系统的"Codex"快捷方式启动。

### 5.8 Agent 之间协作异常

**现象：** 某个飞书 Agent 无响应

**排查：**
1. 检查飞书认证状态：`curl http://127.0.0.1:8765/api/lark/auth-status`
2. 查看 Agent 日志：`curl http://127.0.0.1:8765/api/logs/codex-agent`
3. 运行全量诊断：`curl http://127.0.0.1:8765/api/diagnostics`

---

## 六、测试

```powershell
# 运行全部测试
cd C:\agent-control-center
$env:PYTHONPATH="src"
python -m pytest tests/ -v

# 运行特定测试文件
python -m pytest tests/test_app.py -v

# 运行单个测试
python -m pytest tests/test_app.py::test_status_is_read_only_without_token -v
```

