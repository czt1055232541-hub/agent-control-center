from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from feishu_stack.modules.agent_array.skill_tree.agent_registry import RegistryAgent, load_registry
from feishu_stack.core.settings import StackConfig, load_config
from feishu_stack.core.models import AgentConfig, ComponentStatus, DashboardSummary, ExplainedDiagnosticItem, StackStatus
from feishu_stack.modules.operations.operations import recent_operations
from feishu_stack.core.status import get_status


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
    provider_label = stack.codex_agent_provider.mode
    model = stack.codex_agent_provider.model
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
            feishu_binding=cfg.agent.lark_bot_open_id or "--",
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
            feishu_binding=str(cfg.openclaw.home or "--"),
            trigger_mode="本地 UI / API",
            backend_actions=_component_actions("openclaw", "openclaw", open_ui=True),
            source="infrastructure",
            backing_component="openclaw",
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
                _backend_action("switch-deepseek", "Switch DeepSeek", endpoint="/api/codex-provider/deepseek", kind="provider"),
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


def explained_diagnostics(config: StackConfig | None = None, diagnostic_data: dict[str, Any] | None = None) -> list[ExplainedDiagnosticItem]:
    """Compatibility entry; diagnostics implementation loads only on explicit use."""
    from feishu_stack.modules.logs_diagnostics.explanations import explained_diagnostics as explain
    return explain(config, diagnostic_data)
