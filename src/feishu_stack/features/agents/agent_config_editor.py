from __future__ import annotations

import json
import re
import shutil
import time
from pathlib import Path
from typing import Any

from feishu_stack.features.agents.agent_registry import REAL_OPENCLAW_AGENT_ORDER
from feishu_stack.core.settings import StackConfig, load_config


CODEX_FIELDS = {
    "AGENT_PROVIDER",
    "CODEX_AGENT_ARGS",
    "CODEX_CLI_TIMEOUT_MS",
    "CODEX_PROGRESS_INITIAL_MS",
    "CODEX_PROGRESS_INTERVAL_MS",
}
PROVIDERS = {"codex", "local", "openai"}
OPENCLAW_ID_BY_AGENT = {
    f"openclaw-{agent_id}": agent_id for agent_id in REAL_OPENCLAW_AGENT_ORDER
}


def _timestamp() -> str:
    return time.strftime("%Y%m%d-%H%M%S") + f"-{int((time.time() % 1) * 1000):03d}"


def _backup_dir(cfg: StackConfig, group: str) -> Path:
    path = cfg.runtime_dir / "config-versions" / group
    path.mkdir(parents=True, exist_ok=True)
    return path


def _copy_backup(source: Path, cfg: StackConfig, group: str) -> Path:
    if not source.exists():
        raise FileNotFoundError(f"Config file not found: {source}")
    target = _backup_dir(cfg, group) / f"{source.name}.{_timestamp()}.bak"
    shutil.copy2(source, target)
    return target


def _latest_backup(cfg: StackConfig, group: str) -> Path | None:
    path = _backup_dir(cfg, group)
    backups = sorted(path.glob("*.bak"), key=lambda p: p.stat().st_mtime, reverse=True)
    return backups[0] if backups else None


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


def _write_env(path: Path, updates: dict[str, str]) -> None:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines() if path.exists() else []
    seen: set[str] = set()
    result: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            result.append(line)
            continue
        key, _value = stripped.split("=", 1)
        key = key.strip()
        if key in updates:
            result.append(f"{key}={updates[key]}")
            seen.add(key)
        else:
            result.append(line)
    for key, value in updates.items():
        if key not in seen:
            result.append(f"{key}={value}")
    path.write_text("\n".join(result) + "\n", encoding="utf-8")


def _parse_a2a(raw: str) -> list[dict[str, Any]]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return value if isinstance(value, list) else []


def _safe_a2a(raw: str) -> list[dict[str, Any]]:
    peers = []
    for item in _parse_a2a(raw):
        if not isinstance(item, dict):
            continue
        peers.append(
            {
                "name": str(item.get("name") or ""),
                "description": item.get("description") or "",
                "hasOpenId": bool(item.get("openId")),
            }
        )
    return peers


def _redacted_latest_backup(cfg: StackConfig, group: str) -> str | None:
    backup = _latest_backup(cfg, group)
    return str(backup) if backup else None


def _openclaw_config_path(cfg: StackConfig) -> Path:
    return cfg.openclaw_home / ".openclaw" / "openclaw.json"


def get_editable_config(agent_id: str, config: StackConfig | None = None) -> dict[str, Any]:
    cfg = config or load_config()
    if agent_id == "codex-code-agent":
        env_path = cfg.agent_dir / ".env"
        env = _read_env(env_path)
        return {
            "agentId": agent_id,
            "source": "codex-agent",
            "configPath": str(env_path),
            "writableFields": sorted(CODEX_FIELDS | {"A2A_BOTS"}),
            "values": {
                "AGENT_PROVIDER": env.get("AGENT_PROVIDER") or "codex",
                "CODEX_AGENT_ARGS": env.get("CODEX_AGENT_ARGS") or "exec --skip-git-repo-check",
                "CODEX_CLI_TIMEOUT_MS": env.get("CODEX_CLI_TIMEOUT_MS") or "",
                "CODEX_PROGRESS_INITIAL_MS": env.get("CODEX_PROGRESS_INITIAL_MS") or "",
                "CODEX_PROGRESS_INTERVAL_MS": env.get("CODEX_PROGRESS_INTERVAL_MS") or "",
                "A2A_BOTS": _safe_a2a(env.get("A2A_BOTS", "")),
                "hasBotOpenId": bool(env.get("LARK_BOT_OPEN_ID")),
            },
            "latestBackup": _redacted_latest_backup(cfg, "codex-agent"),
        }

    openclaw_id = OPENCLAW_ID_BY_AGENT.get(agent_id)
    if openclaw_id:
        path = _openclaw_config_path(cfg)
        data = json.loads(path.read_text(encoding="utf-8-sig", errors="replace")) if path.exists() else {}
        agents = data.get("agents", {}).get("list", []) if isinstance(data, dict) else []
        row = next((item for item in agents if isinstance(item, dict) and item.get("id") == openclaw_id), {})
        identity = row.get("identity", {}) if isinstance(row.get("identity"), dict) else {}
        account = data.get("channels", {}).get("feishu", {}).get("accounts", {}).get(openclaw_id)
        return {
            "agentId": agent_id,
            "source": "openclaw",
            "configPath": str(path),
            "writableFields": ["identityTheme", "feishuAccountEnabled"],
            "values": {
                "identityTheme": identity.get("theme") or "",
                "feishuAccountEnabled": account.get("enabled") if isinstance(account, dict) else None,
                "hasFeishuAccount": isinstance(account, dict),
                "workspaceFiles": ["AGENTS.md", "IDENTITY.md", "SKILL.md", "TOOLS.md"],
            },
            "latestBackup": _redacted_latest_backup(cfg, "openclaw"),
        }
    raise ValueError(f"Unsupported editable agent: {agent_id}")


def preview_config(agent_id: str, config: StackConfig | None = None) -> dict[str, Any]:
    current = get_editable_config(agent_id, config)
    return {
        "agentId": agent_id,
        "current": current,
        "notes": [
            "Only listed writableFields can be changed.",
            "Sensitive identifiers are never returned or editable.",
            "Save operations create a backup before writing.",
        ],
    }


def backup_config(agent_id: str, config: StackConfig | None = None) -> dict[str, Any]:
    cfg = config or load_config()
    if agent_id == "codex-code-agent":
        backup = _copy_backup(cfg.agent_dir / ".env", cfg, "codex-agent")
    elif agent_id in OPENCLAW_ID_BY_AGENT:
        backup = _copy_backup(_openclaw_config_path(cfg), cfg, "openclaw")
    else:
        raise ValueError(f"Unsupported editable agent: {agent_id}")
    return {"ok": True, "backupPath": str(backup)}


def rollback_latest(agent_id: str, config: StackConfig | None = None) -> dict[str, Any]:
    cfg = config or load_config()
    if agent_id == "codex-code-agent":
        group = "codex-agent"
        target = cfg.agent_dir / ".env"
    elif agent_id in OPENCLAW_ID_BY_AGENT:
        group = "openclaw"
        target = _openclaw_config_path(cfg)
    else:
        raise ValueError(f"Unsupported editable agent: {agent_id}")
    backup = _latest_backup(cfg, group)
    if backup is None:
        raise FileNotFoundError(f"No backup found for {agent_id}")
    shutil.copy2(backup, target)
    return {"ok": True, "restoredFrom": str(backup), "target": str(target)}


def _validate_int_field(key: str, value: Any) -> str:
    text = str(value).strip()
    if not text:
        return ""
    if not re.fullmatch(r"[1-9][0-9]{2,8}", text):
        raise ValueError(f"{key} must be a positive integer string.")
    return text


def _update_a2a_descriptions(existing_raw: str, incoming: Any) -> str:
    existing = _parse_a2a(existing_raw)
    if incoming is None:
        return existing_raw
    if not isinstance(incoming, list):
        raise ValueError("A2A_BOTS must be a list.")
    descriptions: dict[str, str] = {}
    for item in incoming:
        if not isinstance(item, dict):
            raise ValueError("A2A_BOTS entries must be objects.")
        name = str(item.get("name") or "")
        if not name:
            raise ValueError("A2A_BOTS entry name is required.")
        descriptions[name] = str(item.get("description") or "")
    for item in existing:
        if isinstance(item, dict) and item.get("name") in descriptions:
            item["description"] = descriptions[str(item.get("name"))]
    return json.dumps(existing, ensure_ascii=False, separators=(",", ":"))


def update_editable_config(agent_id: str, payload: dict[str, Any], config: StackConfig | None = None) -> dict[str, Any]:
    cfg = config or load_config()
    if agent_id == "codex-code-agent":
        allowed = CODEX_FIELDS | {"A2A_BOTS"}
        extra = set(payload) - allowed
        if extra:
            raise ValueError(f"Unsupported fields: {', '.join(sorted(extra))}")
        env_path = cfg.agent_dir / ".env"
        env = _read_env(env_path)
        updates: dict[str, str] = {}
        if "AGENT_PROVIDER" in payload:
            provider = str(payload["AGENT_PROVIDER"]).strip()
            if provider not in PROVIDERS:
                raise ValueError("AGENT_PROVIDER must be codex, local, or openai.")
            updates["AGENT_PROVIDER"] = provider
        if "CODEX_AGENT_ARGS" in payload:
            value = str(payload["CODEX_AGENT_ARGS"]).strip()
            if not value:
                raise ValueError("CODEX_AGENT_ARGS cannot be empty.")
            updates["CODEX_AGENT_ARGS"] = value
        for key in ["CODEX_CLI_TIMEOUT_MS", "CODEX_PROGRESS_INITIAL_MS", "CODEX_PROGRESS_INTERVAL_MS"]:
            if key in payload:
                updates[key] = _validate_int_field(key, payload[key])
        if "A2A_BOTS" in payload:
            updates["A2A_BOTS"] = _update_a2a_descriptions(env.get("A2A_BOTS", ""), payload.get("A2A_BOTS"))
        backup = _copy_backup(env_path, cfg, "codex-agent")
        _write_env(env_path, updates)
        return {"ok": True, "backupPath": str(backup), "config": get_editable_config(agent_id, cfg)}

    openclaw_id = OPENCLAW_ID_BY_AGENT.get(agent_id)
    if openclaw_id:
        allowed = {"identityTheme", "feishuAccountEnabled"}
        extra = set(payload) - allowed
        if extra:
            raise ValueError(f"Unsupported fields: {', '.join(sorted(extra))}")
        path = _openclaw_config_path(cfg)
        data = json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
        agents = data.get("agents", {}).get("list", [])
        row = next((item for item in agents if isinstance(item, dict) and item.get("id") == openclaw_id), None)
        if row is None:
            raise ValueError(f"OpenClaw agent not found: {openclaw_id}")
        if "identityTheme" in payload:
            theme = str(payload["identityTheme"]).strip()
            if not theme:
                raise ValueError("identityTheme cannot be empty.")
            row.setdefault("identity", {})["theme"] = theme
        if "feishuAccountEnabled" in payload:
            enabled = payload["feishuAccountEnabled"]
            if not isinstance(enabled, bool):
                raise ValueError("feishuAccountEnabled must be boolean.")
            accounts = data.setdefault("channels", {}).setdefault("feishu", {}).setdefault("accounts", {})
            account = accounts.get(openclaw_id)
            if not isinstance(account, dict):
                raise ValueError(f"OpenClaw Feishu account not editable for {openclaw_id}.")
            account["enabled"] = enabled
        backup = _copy_backup(path, cfg, "openclaw")
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
        return {"ok": True, "backupPath": str(backup), "config": get_editable_config(agent_id, cfg)}

    raise ValueError(f"Unsupported editable agent: {agent_id}")
