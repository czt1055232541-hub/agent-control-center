# Agent Control Center — 运维手册

## 一、目录结构

```
C:\agent-control-center\
├── API.md / OPS.md / README.md
├── config/
│   ├── stack.settings.example.json  # 可提交脱敏模板
│   └── stack.settings.local.json    # 本机真实配置，已被 .gitignore 排除
├── database/                         # 未来 schema、migration、seed 预留目录
├── runtime/                         # 日志、PID、控制 token、迁移摘要等运行产物，不提交
├── scripts/                         # Python 入口，仅保留 stack.py
├── src/feishu_stack/
│   ├── api/                         # FastAPI 应用、路由、鉴权
│   ├── core/                        # settings、models、process、logs、status
│   ├── modules/                     # 与网页侧边栏一致的后端功能域
│   │   ├── agent_array/skill_tree/  # Agent 阵列、技能树、配置编辑、registry
│   │   ├── model_provider/          # OpenClaw Gateway、MoonBridge、Codex Agent、Provider 切换
│   │   ├── logs_diagnostics/        # 日志、诊断、指标
│   │   ├── backup_migration/        # 备份、线程迁移
│   │   ├── operations/              # CLI、Control Center、操作锁、stack 编排
│   │   └── */                       # dashboard、飞书连接、路由规则、任务战场、配置中心等功能域入口
│   └── *.py                         # 旧导入路径兼容 wrapper
├── tests/                           # api/core/modules 分类测试
├── agent-runtime/typing-indicator/  # 打字指示器运行面辅助服务
├── web/src/
│   ├── app/
│   ├── api/
│   ├── components/common/
│   ├── modules/
│   │   ├── agent-array/
│   │   ├── dashboard/
│   │   └── logs-diagnostics/
│   ├── hooks/
│   └── types/
└── docs/
```

目录约定：页面功能域和后端 `modules/` 保持同名语义映射；前端目录使用 kebab-case，后端目录使用 snake_case。旧顶层 Python 模块只用于兼容历史 import，新代码优先引用 `feishu_stack.modules.*`。



## 二、依赖安装

### 2.1 Python 环境

- **Python 版本：** >= 3.11（推荐 3.13）
- **Python 路径：** `python`

### 2.2 安装项目依赖

```bash
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

```bash
cd C:\agent-control-center\web
npm install
npm run build
```

---

## 三、启动与停止

### 3.1 启动全栈

```bash
# 使用 Python 入口启动 MoonBridge 模式（规范命令）
cd C:\agent-control-center
python scripts/stack.py stack start-moonbridge

# 使用 Python 入口启动 Native 模式
python scripts/stack.py stack start-native
```

启动后，Control Center API 默认监听 `http://127.0.0.1:8765`。

### 3.2 停止全栈

```bash
# 使用 Python 入口停止受管组件
cd C:\agent-control-center
python scripts/stack.py stack stop
```

### 3.3 仅启动 Control Center API

```bash
cd C:\agent-control-center
python scripts/stack.py serve-control-center --open
```

### 3.4 查看状态

```bash
# 查看全栈状态
cd C:\agent-control-center
python scripts/stack.py status --json

# 通过 API 查看
curl http://127.0.0.1:8765/api/status
```

### 3.5 启动细节说明

Control Center API 使用 `uvicorn` 运行，进程管理逻辑：

1. **启动流程：** CLI 启动 OpenClaw → MoonBridge → Codex Agent，最后启动 FastAPI 服务
2. **PID 管理：** 各组件 PID 写入 `runtime/pids/` 目录
3. **日志：** 各组件日志写入 `runtime/logs/` 目录

---

## Codex Desktop 关闭保护

`codex-desktop stop` 会关闭当前机器上的 Codex App。为避免运维或测试误杀正在工作的 Codex，控制中心默认拒绝真实关闭动作；只有显式设置 `AGENT_CONTROL_CENTER_ALLOW_CODEX_DESKTOP_STOP=1` 时才允许执行系统关闭命令。`stack stop` 不包含 Codex Desktop 关闭动作。

## 四、配置文件说明

### 4.1 配置入口

真实配置只放在 `config/stack.settings.local.json`，该文件已被 `.gitignore` 排除。仓库只提交 `config/stack.settings.example.json` 作为脱敏模板。

配置读取优先级固定为：

1. `STACK_SETTINGS_PATH` 环境变量指定的文件
2. `config/stack.settings.local.json`
3. `config/stack.settings.example.json`

本机路径、OpenID、chat ID、CLI home、token 路径、agent relay 信息等隐私内容都必须归入 local 配置，不写入模板、文档、脚本或源码。代码统一通过 `feishu_stack.core.settings.load_config()` 读取结构化配置。

**关键字段：**

| 字段 | 说明 |
|---|---|
| `stackRoot` | 项目根目录路径 |
| `pythonExe` | Python 解释器路径 |
| `codexHome` | Codex Desktop 安装目录 |
| `codexConfig` | Codex 配置路径（config.toml） |
| `codexNativeModel` | Native 模式默认模型 |
| `codexMoonBridgeModel` | MoonBridge 模式默认模型 |
| `codexMoonBridgeReasoningEffort` | MoonBridge 模式默认推理强度：`minimal` / `low` / `medium` / `high` / `xhigh` |
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
```bash
# 1. 查看 Control Center 状态
cd C:\agent-control-center
python scripts/stack.py status-control-center

# 2. 查看 API 错误日志
python -c "from pathlib import Path; p=Path('runtime/logs/control-center-api-err.log'); print('\n'.join(p.read_text(encoding='utf-8', errors='replace').splitlines()[-30:]) if p.exists() else 'missing log')"

# 3. 重启 API
python scripts/stack.py stop-control-center
python scripts/stack.py serve-control-center --open
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
```bash
# 查看日志大小
python -c "from pathlib import Path; [print(p.name, p.stat().st_size) for p in Path('runtime/logs').glob('*') if p.is_file()]"

# 清理日志（保留最近 7 天）
python -c "from pathlib import Path; import time; cutoff=time.time()-7*86400; [p.unlink() for p in Path('runtime/logs').glob('*.log') if p.stat().st_mtime < cutoff]"
```

### 5.5 Python 模块找不到

**现象：** `ModuleNotFoundError: No module named 'feishu_stack'`

**原因：** `PYTHONPATH` 环境变量未正确设置

**解决：**
```bash
# 推荐使用 scripts/stack.py，它会自动从仓库根目录加载 src
python scripts/stack.py status --json
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

```bash
# 运行全部测试
cd C:\agent-control-center
python -m pytest tests/ -v

# 运行特定测试文件
python -m pytest tests/api/test_app.py -v

# 运行单个测试
python -m pytest tests/api/test_app.py::test_status_is_read_only_without_token -v
```

