from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from feishu_stack.core.models import OperationResult, to_dict
from feishu_stack.core.process import (
    component_status,
    is_port_listening,
    remove_pid,
    start_process,
    stop_component,
    wait_for_port,
    write_pid,
)
from feishu_stack.core.settings import LocalToolSettings, StackConfig, find_stack_root, load_config, resolve_settings_path

MANIFEST_NAMES = ("acc.local-tool.json", "local-tool.json")


def _tool(cfg: StackConfig, tool_id: str) -> LocalToolSettings:
    for tool in cfg.local_tools:
        if tool.id == tool_id:
            return tool
    raise KeyError(tool_id)


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _manifest_path(tool_dir: Path, configured_manifest: str | None = None) -> Path | None:
    candidates: list[Path] = []
    if configured_manifest:
        manifest = Path(configured_manifest)
        candidates.append(manifest if manifest.is_absolute() else tool_dir / manifest)
    candidates.extend(tool_dir / name for name in MANIFEST_NAMES)
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def _candidate_from_dir(tool_dir: Path) -> dict[str, Any] | None:
    manifest_path = _manifest_path(tool_dir)
    manifest = _read_json_object(manifest_path) if manifest_path else {}
    if not manifest_path and not (tool_dir / "app.py").exists() and not (tool_dir / "package.json").exists():
        return None
    tool_id = str(manifest.get("id") or tool_dir.name).strip()
    runtime = str(manifest.get("runtime") or manifest.get("kind") or ("node" if (tool_dir / "package.json").exists() and not (tool_dir / "app.py").exists() else "python"))
    port = int(manifest.get("port") or 0)
    host = str(manifest.get("host") or "127.0.0.1")
    return {
        "id": tool_id,
        "name": str(manifest.get("name") or tool_id),
        "description": str(manifest.get("description") or ""),
        "dir": str(tool_dir),
        "manifest": str(manifest_path.name) if manifest_path else "",
        "manifest_path": str(manifest_path) if manifest_path else None,
        "runtime": runtime,
        "entry": str(manifest.get("entry") or ("app.py" if runtime != "node" else "index.js")),
        "host": host,
        "port": port,
        "url": str(manifest.get("url") or (f"http://{host}:{port}" if port else "")),
        "health_path": str(manifest.get("healthPath") or manifest.get("health_path") or "/api/health"),
        "open_path": str(manifest.get("openPath") or manifest.get("open_path") or "/"),
        "embed": bool(manifest.get("embed", True)),
        "enabled": bool(manifest.get("enabled", True)),
        "tags": [str(tag) for tag in manifest.get("tags", [])] if isinstance(manifest.get("tags", []), list) else [],
        "registered": False,
    }


def _default_scan_roots(cfg: StackConfig) -> list[Path]:
    roots = [cfg.stack_root / "TOOLS", cfg.stack_root / "tools", cfg.stack_root / "projects"]
    if cfg.projects_root:
        roots.append(cfg.projects_root)
    return list(dict.fromkeys(roots))


def scan(root: str | None = None, config: StackConfig | None = None) -> list[dict[str, Any]]:
    cfg = config or load_config()
    roots = [Path(root)] if root else _default_scan_roots(cfg)
    registered_dirs = {tool.dir.resolve() for tool in cfg.local_tools if tool.dir.exists()}
    registered_ids = {tool.id for tool in cfg.local_tools}
    candidates: list[dict[str, Any]] = []
    seen: set[Path] = set()
    for scan_root in roots:
        if not scan_root.is_absolute():
            scan_root = cfg.stack_root / scan_root
        if not scan_root.exists() or not scan_root.is_dir():
            continue
        dirs = [scan_root, *[item for item in scan_root.iterdir() if item.is_dir()]]
        for tool_dir in dirs:
            resolved = tool_dir.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            candidate = _candidate_from_dir(tool_dir)
            if not candidate:
                continue
            candidate["registered"] = resolved in registered_dirs or candidate["id"] in registered_ids
            candidates.append(candidate)
    return sorted(candidates, key=lambda item: (not item["registered"], item["name"].lower()))


def _writable_settings_path() -> Path:
    current = resolve_settings_path()
    stack_root = find_stack_root()
    local_path = stack_root / "config" / "stack.settings.local.json"
    if current.name == "stack.settings.example.json":
        local_path.parent.mkdir(parents=True, exist_ok=True)
        if not local_path.exists():
            local_path.write_text(current.read_text(encoding="utf-8-sig"), encoding="utf-8")
        return local_path
    return current


def _tool_config_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    tool_dir = Path(str(payload.get("dir") or "")).expanduser()
    if not str(tool_dir):
        raise ValueError("dir is required")
    manifest = str(payload.get("manifest") or "")
    discovered = _candidate_from_dir(tool_dir) or {}
    tool_id = str(payload.get("id") or discovered.get("id") or tool_dir.name).strip()
    if not tool_id:
        raise ValueError("id is required")
    item: dict[str, Any] = {
        "id": tool_id,
        "name": str(payload.get("name") or discovered.get("name") or tool_id),
        "description": str(payload.get("description") or discovered.get("description") or ""),
        "dir": str(tool_dir),
        "entry": str(payload.get("entry") or discovered.get("entry") or "app.py"),
        "runtime": str(payload.get("runtime") or discovered.get("runtime") or "python"),
        "host": str(payload.get("host") or discovered.get("host") or "127.0.0.1"),
        "port": int(payload.get("port") or discovered.get("port") or 0),
        "healthPath": str(payload.get("healthPath") or payload.get("health_path") or discovered.get("health_path") or "/api/health"),
        "openPath": str(payload.get("openPath") or payload.get("open_path") or discovered.get("open_path") or "/"),
        "enabled": bool(payload.get("enabled", discovered.get("enabled", True))),
        "embed": bool(payload.get("embed", discovered.get("embed", True))),
    }
    if manifest:
        item["manifest"] = manifest
    elif discovered.get("manifest"):
        item["manifest"] = discovered["manifest"]
    if payload.get("url") or discovered.get("url"):
        item["url"] = str(payload.get("url") or discovered.get("url"))
    tags = payload.get("tags", discovered.get("tags", []))
    if isinstance(tags, list):
        item["tags"] = [str(tag) for tag in tags]
    env = payload.get("env")
    if isinstance(env, dict):
        item["env"] = {str(key): str(value) for key, value in env.items()}
    return item


def register(payload: dict[str, Any]) -> dict[str, Any]:
    settings_path = _writable_settings_path()
    raw = _read_json_object(settings_path)
    if not raw:
        raise ValueError(f"settings file is not a JSON object: {settings_path}")
    item = _tool_config_from_payload(payload)
    local_tools = raw.setdefault("localTools", {})
    if not isinstance(local_tools, dict):
        local_tools = {}
        raw["localTools"] = local_tools
    tools = local_tools.setdefault("tools", [])
    if not isinstance(tools, list):
        tools = []
        local_tools["tools"] = tools
    replaced = False
    for index, existing in enumerate(tools):
        if not isinstance(existing, dict):
            continue
        if existing.get("id") == item["id"] or existing.get("dir") == item["dir"]:
            tools[index] = {**existing, **item}
            replaced = True
            break
    if not replaced:
        tools.append(item)
    settings_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"ok": True, "registered": item, "settings_path": str(settings_path), "updated": replaced}


def _health_url(tool: LocalToolSettings) -> str:
    path = tool.health_path if tool.health_path.startswith("/") else f"/{tool.health_path}"
    return f"{tool.url}{path}"


def _open_url(tool: LocalToolSettings) -> str:
    path = tool.open_path if tool.open_path.startswith("/") else f"/{tool.open_path}"
    return f"{tool.url}{path}"


def _health_ok(tool: LocalToolSettings, timeout: float = 0.8) -> bool:
    try:
        with urllib.request.urlopen(_health_url(tool), timeout=timeout) as response:
            return 200 <= response.status < 500
    except (OSError, urllib.error.URLError):
        return False


def _status(tool: LocalToolSettings, cfg: StackConfig) -> dict:
    pid_file = cfg.local_tool_pid(tool.id)
    base = to_dict(component_status(f"local-tool:{tool.id}", tool.port or None, pid_file))
    port_listening = is_port_listening(tool.port, tool.host) if tool.port else False
    if base.get("pid") is not None and not base.get("pid_running") and not port_listening:
        remove_pid(pid_file)
        base["pid"] = None
        base["pid_running"] = False
    base.update(
        {
            "id": tool.id,
            "name": tool.name,
            "description": tool.description,
            "enabled": tool.enabled,
            "embed": tool.embed,
            "tags": tool.tags,
            "url": tool.url,
            "open_url": _open_url(tool),
            "health_url": _health_url(tool),
            "dir": str(tool.dir),
            "entry": str(tool.entry),
            "command": tool.command,
            "runtime": tool.runtime,
            "source": tool.source,
            "manifest_path": str(tool.manifest_path) if tool.manifest_path else None,
            "port_listening": port_listening,
            "health_ok": _health_ok(tool) if port_listening else False,
            "stdout_log": str(cfg.local_tool_stdout_log(tool.id)),
            "stderr_log": str(cfg.local_tool_stderr_log(tool.id)),
        }
    )
    return base


def list_tools(config: StackConfig | None = None) -> list[dict]:
    cfg = config or load_config()
    return [_status(tool, cfg) for tool in cfg.local_tools]


def get_tool_status(tool_id: str, config: StackConfig | None = None) -> dict:
    cfg = config or load_config()
    return _status(_tool(cfg, tool_id), cfg)


def start(tool_id: str, config: StackConfig | None = None) -> OperationResult:
    cfg = config or load_config()
    tool = _tool(cfg, tool_id)
    started = time.monotonic()
    if not tool.enabled:
        return OperationResult(False, f"local-tool:{tool.id}", "start", "tool is disabled")
    if tool.port and is_port_listening(tool.port, tool.host):
        return OperationResult(
            True,
            f"local-tool:{tool.id}",
            "start",
            f"{tool.name} is already listening on {tool.host}:{tool.port}",
            port=tool.port,
            duration_ms=int((time.monotonic() - started) * 1000),
        )
    if not tool.dir.exists():
        return OperationResult(False, f"local-tool:{tool.id}", "start", f"tool dir not found: {tool.dir}")
    env = os.environ.copy()
    env.update(tool.env)
    env.setdefault("ACC_TOOL_ID", tool.id)
    env.setdefault("ACC_TOOL_NAME", tool.name)
    env.setdefault("ACC_TOOL_HOST", tool.host)
    env.setdefault("ACC_TOOL_URL", tool.url)
    env.setdefault("ACC_TOOL_DIR", str(tool.dir))
    env.setdefault("ACC_TOOL_ENTRY", str(tool.entry))
    env.setdefault("PLANNING_HOST", tool.host)
    if tool.port:
        env.setdefault("ACC_TOOL_PORT", str(tool.port))
        env.setdefault("PLANNING_PORT", str(tool.port))
    proc = start_process(
        tool.command,
        cwd=tool.dir,
        stdout_log=cfg.local_tool_stdout_log(tool.id),
        stderr_log=cfg.local_tool_stderr_log(tool.id),
        env=env,
    )
    write_pid(cfg.local_tool_pid(tool.id), proc.pid)
    if tool.port and not wait_for_port(tool.port, True, timeout=12):
        return OperationResult(
            False,
            f"local-tool:{tool.id}",
            "start",
            f"started {tool.name}, but {tool.host}:{tool.port} did not become reachable",
            pid=proc.pid,
            port=tool.port,
            duration_ms=int((time.monotonic() - started) * 1000),
        )
    return OperationResult(
        True,
        f"local-tool:{tool.id}",
        "start",
        f"started {tool.name}",
        pid=proc.pid,
        port=tool.port or None,
        duration_ms=int((time.monotonic() - started) * 1000),
    )


def stop(tool_id: str, config: StackConfig | None = None) -> OperationResult:
    cfg = config or load_config()
    tool = _tool(cfg, tool_id)
    return stop_component(
        f"local-tool:{tool.id}",
        cfg.local_tool_pid(tool.id),
        tool.port or None,
        expected_process_markers=(tool.id, str(tool.dir), tool.command[-1] if tool.command else ""),
    )


def restart(tool_id: str, config: StackConfig | None = None) -> OperationResult:
    cfg = config or load_config()
    started = time.monotonic()
    stopped = stop(tool_id, cfg)
    launched = start(tool_id, cfg)
    return OperationResult(
        ok=stopped.ok and launched.ok,
        component=f"local-tool:{tool_id}",
        action="restart",
        message=f"{stopped.message} | {launched.message}",
        pid=launched.pid,
        port=launched.port,
        duration_ms=int((time.monotonic() - started) * 1000),
    )
