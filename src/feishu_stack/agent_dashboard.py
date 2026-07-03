from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import diagnostics as diagnostics_module
from .agent_registry import RegistryAgent, load_registry
from .config import StackConfig, load_config
from .models import AgentConfig, ComponentStatus, DashboardSummary, ExplainedDiagnosticItem, StackStatus
from .operations import recent_operations
from .status import get_status


def _component_running(component: ComponentStatus) -> bool:
    return bool(component.pid_running or component.port_listening)


def _component_status(component: ComponentStatus) -> str:
    if _component_running(component):
        return "running"
    if component.pid is not None and not component.pid_running:
        return "warning"
    return "stopped"


def _last_error(component: str) -> str:
    for operation in recent_operations():
        if operation.component == component and not operation.ok:
            return operation.message
    return ""


def _last_called_at(component: str) -> str | None:
    for operation in recent_operations():
        if operation.component == component:
            return operation.timestamp
    return None


def _last_latency(component: str) -> int | None:
    for operation in recent_operations():
        if operation.component == component:
            return operation.duration_ms
    return None


def _today_stats(component: str) -> tuple[int, float | None]:
    today = datetime.now(timezone.utc).date()
    total = 0
    ok = 0
    for operation in recent_operations():
        if operation.component != component:
            continue
        try:
            when = datetime.fromisoformat(operation.timestamp).date()
        except ValueError:
            continue
        if when != today:
            continue
        total += 1
        if operation.ok:
            ok += 1
    return total, round(ok / total, 2) if total else None


def _tail_text(path: Path, max_bytes: int = 128_000) -> str:
    if not path.exists() or not path.is_file():
        return ""
    try:
        with path.open("rb") as handle:
            handle.seek(0, 2)
            size = handle.tell()
            handle.seek(max(0, size - max_bytes))
            return handle.read().decode("utf-8", errors="replace")
    except OSError:
        return ""


def _short_task(text: str, fallback: str) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    if not clean:
        return fallback
    return clean[:120] + ("..." if len(clean) > 120 else "")


def _codex_agent_activity(cfg: StackConfig) -> tuple[bool, str]:
    text = "\n".join(
        _tail_text(cfg.runtime_dir / "logs" / name)
        for name in ["codex-agent-err.log", "codex-agent-out.log"]
    )
    if not text:
        return False, "--"

    task = "--"
    last_event = -1
    for match in re.finditer(r'\[agent\] event .*? text="(?P<text>.*)"', text):
        last_event = match.start()
        task = _short_task(match.group("text"), "Codex Agent 正在生成回复")

    last_start = max((match.start() for match in re.finditer(r"\[agent\] draft provider=.*$", text, re.MULTILINE) if " completed" not in match.group(0) and " failed" not in match.group(0)), default=-1)
    last_end = max((match.start() for match in re.finditer(r"\[agent\] draft provider=.* (completed|failed)|\[agent\] replied", text)), default=-1)
    if last_start > last_end:
        return True, task if last_event <= last_start else "Codex Agent 正在生成回复"
    return False, "--"


def _openclaw_agent_activity(cfg: StackConfig, agent_id: str) -> tuple[bool, str]:
    text = "\n".join(
        _tail_text(cfg.runtime_dir / "logs" / name)
        for name in ["openclaw-gateway-out.log", "openclaw-gateway-err.log"]
    )
    if not text:
        return False, "--"

    prefix = re.escape(f"feishu[{agent_id}]")
    last_dispatch = max((match.start() for match in re.finditer(prefix + r": dispatching to agent", text)), default=-1)
    last_complete = max((match.start() for match in re.finditer(prefix + r": dispatch complete", text)), default=-1)
    if last_dispatch <= last_complete:
        return False, "--"

    task = "OpenClaw 正在生成回复"
    message_matches = list(re.finditer(prefix + r": Feishu\[" + re.escape(agent_id) + r"\] message .*?: (?P<text>.*)$", text, re.MULTILINE))
    previous_messages = [match for match in message_matches if match.start() < last_dispatch]
    if previous_messages:
        task = _short_task(previous_messages[-1].group("text"), task)
    return True, task


def _backend_action(
    key: str,
    label: str,
    *,
    endpoint: str | None = None,
    log_component: str | None = None,
    kind: str = "operation",
    enabled: bool = True,
    danger: bool = False,
) -> dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "endpoint": endpoint,
        "logComponent": log_component,
        "kind": kind,
        "enabled": enabled,
        "danger": danger,
    }


def _component_actions(component: str | None, logs_component: str | None, *, open_ui: bool = False) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    if component:
        prefix = f"/api/{component}"
        actions.extend(
            [
                _backend_action("start", "Start", endpoint=f"{prefix}/start"),
                _backend_action("stop", "Stop", endpoint=f"{prefix}/stop", danger=True),
                _backend_action("restart", "Restart", endpoint=f"{prefix}/restart"),
            ]
        )
        if open_ui:
            actions.append(_backend_action("open-ui", "Open UI", endpoint=f"{prefix}/open-ui", kind="open"))
    if logs_component:
        actions.append(_backend_action("logs", "Logs", log_component=logs_component, kind="log"))
    actions.append(_backend_action("detail", "详情", kind="detail"))
    return actions


def _registry_agent_to_config(agent: RegistryAgent, cfg: StackConfig) -> AgentConfig:
    if agent.source == "codex-agent":
        executing, current_task = _codex_agent_activity(cfg)
    elif agent.source == "openclaw":
        executing, current_task = _openclaw_agent_activity(cfg, agent.agent_id)
    else:
        executing, current_task = False, "--"
    display_status = "executing" if executing and agent.status == "running" else agent.status
    return AgentConfig(
        id=agent.id,
        name=agent.display_name,
        role=agent.role,
        status=display_status,
        provider=agent.provider,
        model=agent.model,
        pid=None,
        port=None,
        uptime="--",
        feishuBinding=agent.binding_status,
        triggerMode=agent.trigger_mode,
        tools=agent.tools,
        permissionLevel=agent.permission_level,
        promptVersion="--",
        configPath=agent.config_path,
        currentTask=current_task,
        lastCalledAt=agent.last_interaction_at,
        lastLatencyMs=None,
        lastError="",
        todayTaskCount=None,
        successRate=None,
        controlComponent=agent.backing_component,
        logsComponent=agent.backing_component if agent.backing_component in {"openclaw", "codex-agent"} else None,
        backendActions=agent.backend_actions,
        source=agent.source,
        agentId=agent.agent_id,
        displayName=agent.display_name,
        bindingStatus=agent.binding_status,
        feishuAccountEnabled=agent.feishu_account_enabled,
        workspacePath=agent.workspace_path,
        backingComponent=agent.backing_component,
        sessionCount=agent.session_count,
        lastInteractionAt=agent.last_interaction_at,
        a2aPeers=agent.a2a_peers,
        configFacts=agent.config_facts,
    )


def _agent(
    *,
    id: str,
    name: str,
    role: str,
    status: str,
    provider: str,
    model: str,
    pid: int | None,
    port: int | None,
    config_path: str,
    tools: list[str],
    permission: str,
    control_component: str | None,
    logs_component: str | None,
    feishu_binding: str = "--",
    trigger_mode: str = "--",
    current_task: str = "--",
    backend_actions: list[dict[str, Any]] | None = None,
    source: str = "unknown",
    backing_component: str | None = None,
) -> AgentConfig:
    component = control_component or id
    today_count, success_rate = _today_stats(component)
    return AgentConfig(
        id=id,
        name=name,
        role=role,
        status=status,
        provider=provider,
        model=model,
        pid=pid,
        port=port,
        uptime="--",
        feishuBinding=feishu_binding,
        triggerMode=trigger_mode,
        tools=tools,
        permissionLevel=permission,
        promptVersion="--",
        configPath=config_path,
        currentTask=current_task,
        lastCalledAt=_last_called_at(component),
        lastLatencyMs=_last_latency(component),
        lastError=_last_error(component),
        todayTaskCount=today_count,
        successRate=success_rate,
        controlComponent=control_component,
        logsComponent=logs_component,
        backendActions=backend_actions if backend_actions is not None else _component_actions(control_component, logs_component),
        source=source,
        agentId=id,
        displayName=name,
        bindingStatus="unknown",
        feishuAccountEnabled=None,
        workspacePath=config_path,
        backingComponent=backing_component or control_component,
        sessionCount=None,
        lastInteractionAt=_last_called_at(component),
        a2aPeers=[],
        configFacts={},
    )


def list_agents(config: StackConfig | None = None, status: StackStatus | None = None) -> list[AgentConfig]:
    cfg = config or load_config()
    stack = status or get_status(cfg)
    return [
        _registry_agent_to_config(agent, cfg)
        for agent in load_registry(cfg, openclaw_status=stack.openclaw, codex_agent_status=stack.codex_agent)
    ]


def list_infrastructure(config: StackConfig | None = None, status: StackStatus | None = None) -> list[AgentConfig]:
    cfg = config or load_config()
    stack = status or get_status(cfg)
    provider_label = stack.codex.mode
    model = stack.codex.model
    agent_settings = cfg.raw.get("agent", {})
    openclaw_settings = cfg.raw.get("openclaw", {})

    codex_runtime_running = bool(stack.codex_desktop.running)
    return [
        _agent(
            id="feishu-codex-agent",
            name="Feishu Codex Agent",
            role="飞书消息入口与主控代理",
            status=_component_status(stack.codex_agent),
            provider=provider_label,
            model=model,
            pid=stack.codex_agent.pid,
            port=stack.codex_agent.port,
            config_path=str(cfg.agent_entry),
            tools=["lark-cli", "Codex CLI", "本机日志"],
            permission="可执行命令",
            control_component="codex-agent",
            logs_component="codex-agent",
            feishu_binding=str(agent_settings.get("larkBotOpenId") or "--"),
            trigger_mode="@机器人 / 飞书消息",
            backend_actions=_component_actions("codex-agent", "codex-agent"),
            source="infrastructure",
            backing_component="codex-agent",
        ),
        _agent(
            id="openclaw-gateway",
            name="OpenClaw Gateway",
            role="本机 Agent 网关与 UI 入口",
            status=_component_status(stack.openclaw),
            provider="local",
            model="--",
            pid=stack.openclaw.pid,
            port=stack.openclaw.port,
            config_path=str(cfg.openclaw_gateway_cmd),
            tools=["OpenClaw Gateway", "本机端口"],
            permission="可执行命令",
            control_component="openclaw",
            logs_component="openclaw",
            feishu_binding=str(openclaw_settings.get("home") or "--"),
            trigger_mode="本地 UI / API",
            backend_actions=_component_actions("openclaw", "openclaw", open_ui=True),
            source="infrastructure",
            backing_component="openclaw",
        ),
        _agent(
            id="moonbridge",
            name="MoonBridge",
            role="模型 Provider 代理",
            status=_component_status(stack.moonbridge),
            provider="moonbridge",
            model=cfg.moonbridge_model,
            pid=stack.moonbridge.pid,
            port=stack.moonbridge.port,
            config_path=str(cfg.moonbridge_config),
            tools=["模型代理", "OpenAI 兼容接口"],
            permission="网络访问",
            control_component="moonbridge",
            logs_component="moonbridge",
            trigger_mode="Provider 路由",
            backend_actions=[
                *_component_actions("moonbridge", "moonbridge"),
                _backend_action("switch-provider", "Switch Provider", endpoint="/api/codex-provider/moonbridge", kind="provider"),
            ],
            source="infrastructure",
            backing_component="moonbridge",
        ),
        _agent(
            id="codex-runtime",
            name="Codex Runtime",
            role="本机 Codex Desktop / CLI 运行时",
            status="running" if codex_runtime_running else "stopped",
            provider=provider_label,
            model=model,
            pid=stack.codex_desktop.pid,
            port=None,
            config_path=stack.codex.config,
            tools=["Codex Desktop", "Codex CLI", "Provider 配置"],
            permission="可执行命令",
            control_component="codex-desktop",
            logs_component="codex-desktop",
            trigger_mode="本地 UI / Codex CLI",
            backend_actions=[
                *_component_actions("codex-desktop", "codex-desktop"),
                _backend_action("switch-native", "Switch Native", endpoint="/api/codex-provider/native", kind="provider"),
                _backend_action("switch-moonbridge", "Switch MoonBridge", endpoint="/api/codex-provider/moonbridge", kind="provider"),
            ],
            source="infrastructure",
            backing_component="codex-desktop",
        ),
    ]


def get_agent(agent_id: str, config: StackConfig | None = None) -> AgentConfig | None:
    for agent in list_agents(config):
        if agent.id == agent_id:
            return agent
    return None


def dashboard_summary(config: StackConfig | None = None, status: StackStatus | None = None) -> DashboardSummary:
    cfg = config or load_config()
    stack = status or get_status(cfg)
    agents = list_agents(cfg, stack)
    failed = sum(1 for operation in recent_operations() if not operation.ok)
    online = sum(1 for agent in agents if agent.status in {"running", "executing"})
    core_problem = any(
        agent.status in {"warning", "error", "stopped"}
        for agent in agents
        if agent.id in {"feishu-codex-agent", "openclaw-gateway"}
    )
    health = "warning" if core_problem else "normal"
    if stack.codex.mode == "moonbridge" and not _component_running(stack.moonbridge):
        health = "error"
    return DashboardSummary(
        systemHealth=health,
        provider=f"{stack.codex.mode} / {stack.codex.model}",
        feishuStatus="unknown",
        onlineAgents=online,
        totalAgents=len(agents),
        activeTasks=None,
        todayMessages=None,
        failedRequests=failed,
    )


def _action(id: str, label: str, endpoint: str | None = None, log_component: str | None = None, danger: bool = False) -> dict[str, Any]:
    return {
        "id": id,
        "label": label,
        "endpoint": endpoint,
        "logComponent": log_component,
        "danger": danger,
    }


def explained_diagnostics(config: StackConfig | None = None, diagnostic_data: dict[str, Any] | None = None) -> list[ExplainedDiagnosticItem]:
    cfg = config or load_config()
    data = diagnostic_data or diagnostics_module.diagnostics(cfg)
    stack = data.get("status") or get_status(cfg)
    if isinstance(stack, dict):
        provider_mode = stack.get("codex", {}).get("mode", "unknown")
        moonbridge_running = bool(stack.get("moonbridge", {}).get("pid_running") or stack.get("moonbridge", {}).get("port_listening"))
        openclaw_running = bool(stack.get("openclaw", {}).get("pid_running") or stack.get("openclaw", {}).get("port_listening"))
        codex_agent_running = bool(stack.get("codex_agent", {}).get("pid_running") or stack.get("codex_agent", {}).get("port_listening"))
    else:
        provider_mode = stack.codex.mode
        moonbridge_running = _component_running(stack.moonbridge)
        openclaw_running = _component_running(stack.openclaw)
        codex_agent_running = _component_running(stack.codex_agent)

    items: list[ExplainedDiagnosticItem] = []
    moonbridge_diag = data.get("moonbridge_models", {})
    if provider_mode == "moonbridge" and (not moonbridge_diag.get("ok") or not moonbridge_running):
        items.append(
            ExplainedDiagnosticItem(
                id="moonbridge-unavailable",
                level="error",
                title="MoonBridge 连接失败",
                affectedModules=["MoonBridge", "Provider", "Codex Runtime"],
                status="需要处理",
                rawError=str(moonbridge_diag.get("error") or moonbridge_diag.get("status") or "MoonBridge 未就绪"),
                possibleCauses=["MoonBridge 服务未启动", "端口 38440 不可访问", "Provider 已切到 MoonBridge 但代理不可用", "本机网络或防火墙阻止连接"],
                suggestions=["启动 MoonBridge", "临时切换到 Native Provider", "查看 MoonBridge 日志", "重启 MoonBridge Stack"],
                actions=[
                    _action("start-moonbridge", "Start MoonBridge", "/api/moonbridge/start"),
                    _action("switch-native", "Switch Native", "/api/codex-provider/native"),
                    _action("view-moonbridge-logs", "View Logs", log_component="moonbridge"),
                ],
                relatedLogs=["moonbridge", "operations"],
            )
        )
    elif provider_mode == "moonbridge":
        items.append(
            ExplainedDiagnosticItem(
                id="moonbridge-ok",
                level="normal",
                title="MoonBridge Provider 正常",
                affectedModules=["MoonBridge", "Provider"],
                status="正常",
                rawError="",
                possibleCauses=[],
                suggestions=["保持当前 Provider 配置"],
                actions=[_action("view-moonbridge-logs", "View Logs", log_component="moonbridge")],
                relatedLogs=["moonbridge"],
            )
        )

    lark_diag = data.get("lark_auth_status", {})
    if lark_diag and not lark_diag.get("ok"):
        items.append(
            ExplainedDiagnosticItem(
                id="lark-auth-error",
                level="warning",
                title="飞书认证状态异常",
                affectedModules=["Feishu Codex Agent", "lark-cli"],
                status="需要检查",
                rawError=str(lark_diag.get("stderr") or lark_diag.get("stdout") or "lark-cli auth status failed"),
                possibleCauses=["lark-cli 未登录", "认证缓存失效", "当前 profile 与 Agent 配置不一致"],
                suggestions=["重新检查 lark-cli auth status", "查看 Codex Agent 日志", "确认本机飞书 Agent 配置"],
                actions=[_action("view-agent-logs", "View Logs", log_component="codex-agent")],
                relatedLogs=["codex-agent"],
            )
        )

    if not codex_agent_running:
        items.append(
            ExplainedDiagnosticItem(
                id="codex-agent-stopped",
                level="warning",
                title="Feishu Codex Agent 未运行",
                affectedModules=["Feishu Codex Agent"],
                status="已停止",
                rawError="codex-agent pid 或进程未检测到",
                possibleCauses=["Agent 尚未启动", "启动脚本失败", "Codex CLI 或飞书认证异常"],
                suggestions=["启动 Codex Agent", "查看 Agent 日志", "运行全量诊断"],
                actions=[
                    _action("start-codex-agent", "Start Agent", "/api/codex-agent/start"),
                    _action("view-agent-logs", "View Logs", log_component="codex-agent"),
                ],
                relatedLogs=["codex-agent", "operations"],
            )
        )

    if not openclaw_running:
        items.append(
            ExplainedDiagnosticItem(
                id="openclaw-stopped",
                level="warning",
                title="OpenClaw Gateway 未监听",
                affectedModules=["OpenClaw Gateway"],
                status="已停止",
                rawError="OpenClaw Gateway 端口未监听",
                possibleCauses=["OpenClaw 未启动", "gateway 命令路径不可用", "端口被占用或启动失败"],
                suggestions=["启动 OpenClaw Gateway", "查看 OpenClaw 日志", "确认配置中的 gatewayCmd"],
                actions=[
                    _action("start-openclaw", "Start OpenClaw", "/api/openclaw/start"),
                    _action("view-openclaw-logs", "View Logs", log_component="openclaw"),
                ],
                relatedLogs=["openclaw", "operations"],
            )
        )
    else:
        try:
            if isinstance(stack, dict):
                registry_agents = load_registry(cfg)
            else:
                registry_agents = load_registry(cfg, openclaw_status=stack.openclaw, codex_agent_status=stack.codex_agent)
        except Exception:
            registry_agents = []
        for agent in registry_agents:
            if agent.source == "openclaw" and agent.status == "warning":
                items.append(
                    ExplainedDiagnosticItem(
                        id=f"openclaw-agent-{agent.agent_id}-warning",
                        level="warning",
                        title=f"{agent.display_name} 配置不完整",
                        affectedModules=[agent.display_name, "OpenClaw"],
                        status=agent.binding_status,
                        rawError="OpenClaw Agent binding、Feishu account 或 session 文件未完整就绪",
                        possibleCauses=["openclaw.json 中 binding 缺失", "Feishu account 未启用", "sessions.json 缺失或不可读"],
                        suggestions=["检查 OpenClaw 配置", "查看 Gateway 日志", "确认该角色的 Feishu account 已启用"],
                        actions=[
                            _action("view-openclaw-logs", "View Logs", log_component="openclaw"),
                            _action("open-openclaw-ui", "Open UI", "/api/openclaw/open-ui"),
                        ],
                        relatedLogs=["openclaw", "operations"],
                    )
                )
            if agent.source == "codex-agent" and (agent.binding_status != "bound" or len(agent.a2a_peers) < 5):
                items.append(
                    ExplainedDiagnosticItem(
                        id="codex-agent-a2a-warning",
                        level="warning",
                        title="代码执行官 A2A 配置不完整",
                        affectedModules=["Feishu Codex Agent", "A2A_BOTS"],
                        status=agent.binding_status,
                        rawError="Codex Agent .env 中 LARK_BOT_OPEN_ID 或 A2A_BOTS 未完整配置",
                        possibleCauses=[".env 缺失机器人 open_id", "A2A_BOTS 少于 5 个团队机器人", "Agent provider 不是 codex"],
                        suggestions=["检查 Codex Agent .env", "查看 Codex Agent 日志", "确认代码执行官在 A2A_BOTS 中"],
                        actions=[_action("view-agent-logs", "View Logs", log_component="codex-agent")],
                        relatedLogs=["codex-agent"],
                    )
                )

    codex_diag = data.get("codex_doctor", {})
    if codex_diag and not codex_diag.get("ok"):
        items.append(
            ExplainedDiagnosticItem(
                id="codex-doctor-error",
                level="warning",
                title="Codex Runtime 诊断未通过",
                affectedModules=["Codex Runtime"],
                status="需要检查",
                rawError=str(codex_diag.get("stderr") or codex_diag.get("stdout") or "codex doctor failed"),
                possibleCauses=["Codex CLI 配置异常", "Provider 配置不可用", "Codex 登录态或本机路径异常"],
                suggestions=["查看 Codex doctor 输出", "检查 Provider 设置", "查看 Codex Desktop 日志"],
                actions=[_action("view-codex-logs", "View Logs", log_component="codex-desktop")],
                relatedLogs=["codex-desktop", "control-center-api"],
            )
        )

    if not items:
        items.append(
            ExplainedDiagnosticItem(
                id="system-normal",
                level="normal",
                title="核心链路暂无异常",
                affectedModules=["Stack"],
                status="正常",
                rawError="",
                possibleCauses=[],
                suggestions=["继续观察 Operation Log 和组件日志"],
                actions=[_action("view-operations", "View Operations", log_component="operations")],
                relatedLogs=["operations"],
            )
        )
    return items
