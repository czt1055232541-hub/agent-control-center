from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import StackConfig, load_config
from .models import ComponentStatus


REAL_OPENCLAW_AGENT_ORDER = ["coordinator", "orchestrator", "main", "archivist"]
OPENCLAW_ROLE_FALLBACKS = {
    "coordinator": ("项目调度官", "任务拆解、调度、进度管理"),
    "orchestrator": ("运维验证官", "运行、环境、部署和验证"),
    "main": ("质量审计官", "质量审计、返工意见与交付把关"),
    "archivist": ("项目档案官", "项目记录、文档归档和交付资料整理"),
}


@dataclass
class RegistryAgent:
    id: str
    source: str
    agent_id: str
    display_name: str
    role: str
    status: str
    provider: str
    model: str
    workspace_path: str
    config_path: str
    binding_status: str
    feishu_account_enabled: bool | None
    backing_component: str
    session_count: int
    last_interaction_at: str | None
    last_session_at: str | None
    a2a_peers: list[dict[str, Any]]
    tools: list[str]
    permission_level: str
    trigger_mode: str
    config_facts: dict[str, Any]
    backend_actions: list[dict[str, Any]]


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _iso_from_ms(value: Any) -> str | None:
    if not isinstance(value, (int, float)) or value <= 0:
        return None
    try:
        return datetime.fromtimestamp(value / 1000, timezone.utc).isoformat()
    except (OSError, OverflowError, ValueError):
        return None


def _component_running(component: ComponentStatus) -> bool:
    return bool(component.pid_running or component.port_listening)


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


def _openclaw_actions() -> list[dict[str, Any]]:
    return [
        _backend_action("open-ui", "Open UI", endpoint="/api/openclaw/open-ui", kind="open"),
        _backend_action("logs", "Gateway Logs", log_component="openclaw", kind="log"),
        _backend_action("workspace", "Open Workspace", kind="workspace", enabled=False),
        _backend_action("sessions", "View Sessions", kind="sessions", enabled=False),
        _backend_action("binding", "View Binding", kind="binding", enabled=True),
        _backend_action("detail", "详情", kind="detail"),
    ]


def _codex_actions() -> list[dict[str, Any]]:
    return [
        _backend_action("start", "Start", endpoint="/api/codex-agent/start"),
        _backend_action("stop", "Stop", endpoint="/api/codex-agent/stop", danger=True),
        _backend_action("restart", "Restart", endpoint="/api/codex-agent/restart"),
        _backend_action("logs", "Logs", log_component="codex-agent", kind="log"),
        _backend_action("codex-config", "View Codex Config", kind="config", enabled=True),
        _backend_action("a2a", "View A2A Bots", kind="a2a", enabled=True),
        _backend_action("detail", "详情", kind="detail"),
    ]


def _sessions_summary(sessions_path: Path, agent_id: str) -> tuple[int, str | None, str | None, str, str]:
    data = _read_json(sessions_path)
    entries = [value for key, value in data.items() if isinstance(value, dict) and f"agent:{agent_id}:" in str(key)]
    session_count = len(entries)
    latest = max(entries, key=lambda item: item.get("lastInteractionAt") or item.get("updatedAt") or 0, default={})
    last_interaction = _iso_from_ms(latest.get("lastInteractionAt") or latest.get("updatedAt"))
    last_session = _iso_from_ms(latest.get("updatedAt"))
    provider = str(latest.get("providerOverride") or latest.get("modelProvider") or "--")
    model = str(latest.get("modelOverride") or latest.get("model") or "--")
    return session_count, last_interaction, last_session, provider, model


def _binding_status(agent_id: str, bindings: list[Any], accounts: dict[str, Any]) -> tuple[str, bool | None, dict[str, Any]]:
    binding = next(
        (item for item in bindings if isinstance(item, dict) and item.get("agentId") == agent_id),
        None,
    )
    account = accounts.get(agent_id) if isinstance(accounts, dict) else None
    has_binding = bool(binding and isinstance(binding.get("match"), dict) and binding["match"].get("accountId"))
    enabled = account.get("enabled") if isinstance(account, dict) else None
    if has_binding and (enabled is True or agent_id == "main"):
        status = "bound"
    elif not has_binding:
        status = "missing-binding"
    elif enabled is False:
        status = "account-disabled"
    else:
        status = "partial"
    return status, enabled if isinstance(enabled, bool) else None, {
        "hasBinding": has_binding,
        "hasAccountId": has_binding,
        "accountKey": agent_id if account else ("default" if agent_id == "main" and has_binding else None),
        "connectionMode": account.get("connectionMode") if isinstance(account, dict) else None,
        "hasApplicationId": bool(account.get("appId")) if isinstance(account, dict) else None,
        "hasSecretConfigured": bool(account.get("appSecret")) if isinstance(account, dict) else None,
    }


def _openclaw_status(gateway: ComponentStatus, binding_status: str, sessions_path: Path) -> str:
    if not _component_running(gateway):
        return "stopped"
    if binding_status != "bound" or not sessions_path.exists():
        return "warning"
    return "running"


def _parse_a2a_bots(raw: str) -> list[dict[str, Any]]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    peers = []
    for item in data:
        if not isinstance(item, dict):
            continue
        peers.append(
            {
                "name": str(item.get("name") or "--"),
                "description": item.get("description"),
                "hasOpenId": bool(item.get("openId")),
            }
        )
    return peers


def load_registry(
    config: StackConfig | None = None,
    *,
    openclaw_status: ComponentStatus | None = None,
    codex_agent_status: ComponentStatus | None = None,
) -> list[RegistryAgent]:
    cfg = config or load_config()
    gateway_status = openclaw_status
    code_agent_status = codex_agent_status
    if gateway_status is None or code_agent_status is None:
        from .status import get_status

        stack = get_status(cfg)
        gateway_status = gateway_status or stack.openclaw
        code_agent_status = code_agent_status or stack.codex_agent

    openclaw_config = cfg.openclaw_home / ".openclaw" / "openclaw.json"
    openclaw_root = openclaw_config.parent
    openclaw_data = _read_json(openclaw_config)
    agents_config = openclaw_data.get("agents", {}) if isinstance(openclaw_data.get("agents"), dict) else {}
    agent_rows = agents_config.get("list", []) if isinstance(agents_config.get("list"), list) else []
    by_agent_id = {str(item.get("id")): item for item in agent_rows if isinstance(item, dict) and item.get("id")}
    bindings = openclaw_data.get("bindings", []) if isinstance(openclaw_data.get("bindings"), list) else []
    accounts = (
        openclaw_data.get("channels", {})
        .get("feishu", {})
        .get("accounts", {})
        if isinstance(openclaw_data.get("channels"), dict)
        else {}
    )

    result: list[RegistryAgent] = []
    for agent_id in REAL_OPENCLAW_AGENT_ORDER:
        row = by_agent_id.get(agent_id, {})
        fallback_name, fallback_role = OPENCLAW_ROLE_FALLBACKS[agent_id]
        identity = row.get("identity", {}) if isinstance(row.get("identity"), dict) else {}
        display_name = str(identity.get("name") or row.get("name") or fallback_name)
        role = str(identity.get("theme") or row.get("description") or fallback_role)
        workspace = Path(str(row.get("workspace") or (openclaw_root / f"workspace-{agent_id}")))
        if agent_id == "main" and not row.get("workspace"):
            workspace = openclaw_root / "workspace"
        sessions_path = openclaw_root / "agents" / agent_id / "sessions" / "sessions.json"
        session_count, last_interaction, last_session, provider, model = _sessions_summary(sessions_path, agent_id)
        binding_status, account_enabled, binding_facts = _binding_status(agent_id, bindings, accounts)
        result.append(
            RegistryAgent(
                id=f"openclaw-{agent_id}",
                source="openclaw",
                agent_id=agent_id,
                display_name=display_name,
                role=role,
                status=_openclaw_status(gateway_status, binding_status, sessions_path),
                provider=provider,
                model=model,
                workspace_path=str(workspace),
                config_path=str(openclaw_config),
                binding_status=binding_status,
                feishu_account_enabled=account_enabled,
                backing_component="openclaw",
                session_count=session_count,
                last_interaction_at=last_interaction,
                last_session_at=last_session,
                a2a_peers=[],
                tools=["OpenClaw Gateway", "Agent Workspace", "Feishu Binding"],
                permission_level="OpenClaw 逻辑 Agent",
                trigger_mode="飞书 @ / OpenClaw Gateway 路由",
                config_facts={
                    "workspaceExists": workspace.exists(),
                    "sessionsPathExists": sessions_path.exists(),
                    "binding": binding_facts,
                    "hasIdentity": bool(identity),
                },
                backend_actions=_openclaw_actions(),
            )
        )

    env_path = cfg.agent_dir / ".env"
    env = _read_env(env_path)
    peers = _parse_a2a_bots(env.get("A2A_BOTS", ""))
    provider = env.get("AGENT_PROVIDER") or cfg.raw.get("agent", {}).get("provider") or "codex"
    code_running = _component_running(code_agent_status)
    code_status = "running" if code_running and provider == "codex" and env_path.exists() else "warning" if code_running else "stopped"
    result.append(
        RegistryAgent(
            id="codex-code-agent",
            source="codex-agent",
            agent_id="codex-agent",
            display_name=env.get("LARK_BOT_NAME") or "代码执行官",
            role="代码实现、修复和本地测试",
            status=code_status,
            provider=str(provider),
            model=str(cfg.raw.get("codexNativeModel") or cfg.native_model),
            workspace_path=str(cfg.agent_dir),
            config_path=str(env_path),
            binding_status="bound" if env.get("LARK_BOT_OPEN_ID") else "missing-binding",
            feishu_account_enabled=None,
            backing_component="codex-agent",
            session_count=0,
            last_interaction_at=None,
            last_session_at=None,
            a2a_peers=peers,
            tools=["Codex CLI", "lark-cli", "A2A Mentions"],
            permission_level="可执行命令",
            trigger_mode="@代码执行官 / Codex Agent",
            config_facts={
                "envExists": env_path.exists(),
                "hasBotOpenId": bool(env.get("LARK_BOT_OPEN_ID")),
                "agentProvider": provider,
                "codexAgentArgs": env.get("CODEX_AGENT_ARGS") or cfg.raw.get("agent", {}).get("codexAgentArgs"),
                "a2aPeerCount": len(peers),
                "a2aPeerNames": [peer["name"] for peer in peers],
            },
            backend_actions=_codex_actions(),
        )
    )
    return result
