from __future__ import annotations

import json
import os
import shutil
import socket
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


SHARED_FIELDS: tuple[str, ...] = (
    "codexHome",
    "codexBin",
    "codexConfig",
    "codexNativeModel",
    "codexDeepSeekModel",
    "codexSwitchScript",
    "deepseek.baseUrl",
    "deepseek.envKey",
    "openclaw.port",
    "agent.dir",
    "agent.larkCliBin",
)
SENSITIVE_PARTS = ("token", "secret", "password", "openId", "chatId", "appId")


def _get_dotted(data: dict[str, Any], dotted: str) -> Any:
    current: Any = data
    for part in dotted.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def redact_config(value: Any, key: str = "") -> Any:
    """Return a JSON-safe copy with credential and Feishu identifier values hidden."""
    if any(part.lower() in key.lower() for part in SENSITIVE_PARTS):
        return "<redacted>" if value not in (None, "") else value
    if isinstance(value, dict):
        return {item_key: redact_config(item, item_key) for item_key, item in value.items()}
    if isinstance(value, list):
        return [redact_config(item, key) for item in value]
    return value


def compare_shared_config(primary: dict[str, Any], peer: dict[str, Any]) -> list[dict[str, Any]]:
    """Describe differences in fields owned by the shared ACC/agent contract."""
    drift: list[dict[str, Any]] = []
    for field in SHARED_FIELDS:
        primary_value = _get_dotted(primary, field)
        peer_value = _get_dotted(peer, field)
        if primary_value != peer_value:
            drift.append(
                {
                    "field": field,
                    "control_plane": redact_config(primary_value, field),
                    "agent_runtime": redact_config(peer_value, field),
                }
            )
    return drift


def _port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.15)
        return sock.connect_ex(("127.0.0.1", port)) != 0


def validate_shared_config(raw: dict[str, Any], *, check_runtime: bool = False) -> dict[str, Any]:
    """Validate the stable cross-repository fields without exposing private values."""
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    required = ("codexHome", "codexBin", "codexConfig", "deepseek", "openclaw", "agent", "runtime")
    for field in required:
        if raw.get(field) in (None, "", {}):
            errors.append({"code": "MISSING_FIELD", "field": field, "message": f"Required field is missing: {field}"})

    ports: dict[str, int] = {}
    for field in ("openclaw.port",):
        value = _get_dotted(raw, field)
        try:
            port = int(value)
        except (TypeError, ValueError):
            errors.append({"code": "INVALID_PORT", "field": field, "message": f"Port must be an integer: {field}"})
            continue
        if not 1 <= port <= 65535:
            errors.append({"code": "INVALID_PORT", "field": field, "message": f"Port is outside 1-65535: {field}"})
            continue
        ports[field] = port
        if check_runtime and not _port_available(port):
            warnings.append({"code": "PORT_IN_USE", "field": field, "message": f"Configured port is already listening: {port}"})

    path_fields = (
        "codexHome",
        "codexBin",
        "codexConfig",
        "codexSwitchScript",
        "openclaw.home",
        "openclaw.gatewayCmd",
        "agent.dir",
        "agent.larkCliBin",
        "runtime.dir",
        "runtime.logs",
        "runtime.pids",
    )
    if check_runtime:
        for field in path_fields:
            value = _get_dotted(raw, field)
            if value and not Path(str(value)).exists():
                warnings.append({"code": "PATH_NOT_FOUND", "field": field, "message": f"Configured path does not exist: {field}"})

    return {
        "ok": not errors,
        "contract_version": 1,
        "errors": errors,
        "warnings": warnings,
        "ports": ports,
    }


def atomic_write_json(
    path: Path,
    payload: dict[str, Any],
    *,
    validator: Callable[[dict[str, Any]], Any] | None = None,
    backup_limit: int = 5,
) -> None:
    """Validate and atomically replace JSON, retaining a bounded set of backups."""
    if validator is not None:
        validator(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
            temporary_name = handle.name
        json.loads(Path(temporary_name).read_text(encoding="utf-8"))
        if path.exists():
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            shutil.copy2(path, path.with_name(f"{path.name}.bak-{stamp}"))
        Path(temporary_name).replace(path)
        temporary_name = None
        backups = sorted(path.parent.glob(f"{path.name}.bak-*"), key=lambda item: item.stat().st_mtime, reverse=True)
        for stale in backups[max(0, backup_limit):]:
            stale.unlink()
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)


def load_json_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"Configuration root must be an object: {path}")
    return data
