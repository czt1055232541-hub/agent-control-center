# Agent Control Center

本项目是一个本机桌面控制中心，用来统一管理这台机器上的 Agent 运行栈：Control Center API、React GUI、OpenClaw Gateway、MoonBridge、Feishu Codex Agent、Codex provider 切换、Codex Desktop 状态检测、日志、PID 和诊断。

它的定位是“控制面板”，不是 OpenClaw、飞书应用或 Codex 本体。真实的飞书认证、OpenClaw 凭据、Codex 登录态、MoonBridge 上游密钥都应留在各自组件的本机目录中，不应提交到本仓库。

## 快速开始

克隆后先安装 Python 依赖：

```bash
cd "C:\agent-control-center"
python -m pip install -e .[dev]
```

准备本机配置：

```bash
python -c "import shutil; shutil.copyfile('config/stack.settings.example.json', 'config/stack.settings.local.json')"
python -c "import os; os.startfile('config/stack.settings.local.json')"
```

把 `stack.settings.local.json` 里的路径、端口、模型名、Python、Node/NPM、OpenClaw、MoonBridge、Feishu Agent、lark-cli 位置改成本机实际值。程序读取配置的优先级是：

1. `STACK_SETTINGS_PATH` 环境变量指定的文件
2. `config/stack.settings.local.json`
3. 仓库自带的脱敏模板 `config/stack.settings.example.json`

`stack.settings.local.json` 已在 `.gitignore` 中，不要提交。

## 常用命令

统一使用 Python 入口管理 Codex Agent、OpenClaw、MoonBridge、Control Center 和 provider 切换；仓库不再提供 shell 启动脚本。

查看状态：

```bash
python scripts/stack.py status --json
```

启动 MoonBridge 模式：

```bash
python scripts/stack.py start moonbridge
python scripts/stack.py switch-provider moonbridge
python scripts/stack.py start codex-agent
```

切回 native 模式：

```bash
python scripts/stack.py switch-provider native
python scripts/stack.py restart codex-agent
```

启动或重启 OpenClaw Gateway：

```bash
python scripts/stack.py start openclaw
python scripts/stack.py restart openclaw
```

检查 MoonBridge 活体：

```bash
curl http://127.0.0.1:38440/v1/models
```

启动控制中心 API 和 GUI：

```bash
python scripts/stack.py serve-control-center --open
```

默认访问地址：

```text
http://127.0.0.1:8765
```

安装或刷新桌面 Python 启动器：

```bash
python scripts/stack.py install-shortcut
```

## Codex App 与 MoonBridge 模式

Codex provider 切换写入用户级 Codex 配置文件，通常是本机 Codex home 下的 `config.toml`。新版官方 Codex App 会把当前可用的 CLI 路径写入 `CODEX_CLI_PATH`；控制中心会优先使用这个 app 管理的 CLI 路径启动 Feishu Codex Agent，只有当该路径不存在时才回退到配置中的 `codexBin`。

这样做的目的是适配官方 App 更新后 CLI 目录随版本或哈希变化的情况，避免把旧的 `codex.exe` 路径写死。

MoonBridge 模式由 Control Center 统一切换：网页中的模型下拉会更新 MoonBridge YAML、当前 stack settings，以及 Codex `config.toml` 中的 `model` / `model_provider` / `model_reasoning_effort`。推理强度使用 Codex 配置值 `minimal`、`low`、`medium`、`high`、`xhigh`，界面显示为最低、低、中、高、超高。Feishu Codex Agent 默认跟随全局 Codex 配置，因此会同步使用同一组模型与推理强度。

`codex-agent` 启动时只会清理它自己的子进程环境副本中的 Agent source 自动检测变量，例如：

- `OPENCLAW_HOME`
- `CLAW_HOME`
- `HERMES_HOME`
- `LARK_CHANNEL`

这用于避免 lark-cli 误进入 OpenClaw 绑定流程。它不会修改系统环境、不会停止或重配 OpenClaw，也不会改变飞书 multi-agent 的身份策略。不要把 `lark-cli config bind` 放进常规启动流程；绑定会影响身份策略，应作为明确的运维操作单独执行。


## Codex Desktop 安全保护

codex-desktop stop 会关闭本机 Codex App。为避免误关当前工作中的 Codex，控制中心默认拒绝执行真实关闭动作；只有显式设置环境变量 AGENT_CONTROL_CENTER_ALLOW_CODEX_DESKTOP_STOP=1 时，才会调用系统关闭命令。常规 stack stop 不会停止 Codex Desktop。

## 隐私与公开仓库边界

公开仓库不应包含以下内容：

- 飞书 `open_id`、`chat_id`、机器人身份、用户身份、群聊 ID
- app secret、API key、MoonBridge 上游模型密钥
- OpenClaw gateway token
- Codex `auth file`、会话数据库、日志数据库、SQLite 状态文件
- 本机绝对路径中带个人目录、账号或私有项目结构的信息
- 运行日志、PID、控制 token、二维码、临时审计产物

本仓库提交的是控制中心代码、GUI、脚本、测试和脱敏模板。真实配置应放在：

```text
config/stack.settings.local.json
runtime/
外部组件自己的本机配置目录
```

提交前建议运行：

```bash
git status --short
git diff --cached
rg -n "<your sensitive patterns>" .
```

如果发现真实凭据已经进入 Git 历史，应立即轮换相关密钥，并视情况重写仓库历史。

## 移植到其他电脑

在新电脑上部署时，按这个顺序处理：

1. 安装 Python、Node.js、Git，以及需要的 Codex App、MoonBridge、OpenClaw、lark-cli。
2. 克隆本仓库。
3. 执行 `python -m pip install -e .[dev]`。
4. 复制 `config/stack.settings.example.json` 为 `config/stack.settings.local.json`。
5. 修改 local 配置中的路径、端口、模型名、Node/NPM、lark-cli home、Feishu Agent 路径。
6. 分别确认 OpenClaw、MoonBridge、Codex App、lark-cli 可以独立运行。
7. 运行 `python -m feishu_stack.cli doctor` 和 `python -m pytest -q`。
8. 启动 Control Center API / GUI。

迁移时不要复制旧机器的 `runtime/`、SQLite、日志、PID、Codex 登录态、飞书认证缓存，除非你明确知道这些状态可以在目标机器复用。

## 开发

运行测试：

```bash
python -m pytest -q
```

构建前端：

```bash
cd web
npm install
npm run build
```

查看 API：

```text
http://127.0.0.1:8765/docs
```

## 项目结构

- `src/feishu_stack/api/`：FastAPI 应用、路由和鉴权入口
- `src/feishu_stack/core/`：配置、模型、进程、日志、状态等基础设施
- `src/feishu_stack/services/`：CLI、诊断、操作锁、备份、指标和栈编排
- `src/feishu_stack/integrations/`：Codex、MoonBridge、OpenClaw、Typing Indicator 适配
- `src/feishu_stack/features/`：Agent 面板、配置编辑、线程迁移等功能域
- `src/feishu_stack/*.py`：旧导入路径兼容 wrapper
- `web/`：React/Tailwind GUI，按 `app/`、`features/`、`components/common/` 分类
- `scripts/`：Python 启动入口，桌面启动器由 `install-shortcut` 生成 `.pyw` 文件
- `config/`：脱敏配置模板和本机 local 配置位置
- `docs/`：规划、迁移和运维说明
- `runtime/`：本机运行态目录，只保留 `.gitkeep`
- `tests/`：按 api/core/services/integrations/features 分类的 Python 测试
- `typing-indicator/`：飞书输入状态辅助组件

## 下一步规划

短期：

- 继续收敛脚本与服务启动入口，让 Python、Node、lark-cli 等运行时都通过配置或环境变量解析。
- 给 Control Center 增加配置体检页面，明确提示 local 配置缺失、路径不存在、端口冲突和凭据状态。
- 增加“隐私扫描”命令，提交前检查 open_id、chat_id、token、密钥和本机绝对路径。

中期：

- 把 OpenClaw、MoonBridge、Feishu Agent、Codex App 的启动契约整理为插件式组件注册表。
- 增加配置向导，帮助新电脑生成 `stack.settings.local.json`。
- 将 MoonBridge 模型、Codex provider、Feishu Agent 参数做成可审计的变更记录。

长期：

- 支持多套 profile，例如 `local-dev`、`moonbridge-prod`、`native-codex`。
- 将敏感配置接入系统凭据库或 secret manager，而不是写入 JSON。
- 把控制中心发展为可迁移、可恢复、可审计的本机 Agent 运维面板。

## 清理规则

稳定运行后可以删除未跟踪的临时脚本、一次性审计产物、调试 JSON、旧日志和生成缓存。删除前确认它们没有被 Git 跟踪：

```bash
git status --short
```

保留源代码、测试、脱敏配置模板、运维文档和必要的 `.gitkeep`。不要删除外部组件自己的配置目录，例如 OpenClaw、MoonBridge、Codex home、Feishu Agent home，除非你正在做明确的迁移或卸载。
