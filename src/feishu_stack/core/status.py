from __future__ import annotations

import re
import csv
import io
import json

from feishu_stack.core.settings import StackConfig, load_config
from feishu_stack.core.models import CodexDesktopStatus, ProviderStatus, StackStatus
from feishu_stack.core.process import component_status, process_info, read_pid


def read_provider_status(config: StackConfig) -> ProviderStatus:
    text = config.codex_config.read_text(encoding="utf-8", errors="replace") if config.codex_config.exists() else ""
    model_match = re.search(r'(?m)^\s*model\s*=\s*"([^"]+)"', text)
    provider_match = re.search(r'(?m)^\s*model_provider\s*=\s*"([^"]+)"', text)
    effort_match = re.search(r'(?m)^\s*model_reasoning_effort\s*=\s*"([^"]+)"', text)
    model = model_match.group(1) if model_match else "unknown"
    provider = provider_match.group(1) if provider_match else "openai/default"
    reasoning_effort = effort_match.group(1) if effort_match else "high"
    mode = "moonbridge" if provider == "moonbridge" else "native"
    return ProviderStatus(model=model, provider=provider, mode=mode, config=str(config.codex_config), reasoning_effort=reasoning_effort)


def is_codex_desktop_running() -> bool:
    return codex_desktop_status().running


def _codex_desktop_status_from_process_rows(rows: list[dict[str, str | None]]) -> CodexDesktopStatus:
    matches: list[dict[str, str | int | None]] = []
    for row in rows:
        name = str(row.get("Name") or "").strip()
        path = str(row.get("ExecutablePath") or "").strip() or None
        try:
            pid = int(str(row.get("ProcessId") or "0").strip())
        except ValueError:
            continue
        if pid <= 0 or name.lower() != "codex.exe":
            continue
        path_lower = (path or "").replace("/", "\\").lower()
        if path and "\\resources\\codex.exe" in path_lower:
            continue
        is_desktop_path = bool(path and "\\openai.codex_" in path_lower and path_lower.endswith("\\app\\codex.exe"))
        if path and not is_desktop_path and "\\app\\codex.exe" not in path_lower:
            continue
        matches.append({"pid": pid, "path": path, "is_desktop_path": is_desktop_path})
    if not matches:
        return CodexDesktopStatus(False, None, 0, None)
    main = next((row for row in matches if row.get("is_desktop_path")), matches[0])
    return CodexDesktopStatus(True, int(main["pid"]), len(matches), main.get("path") if isinstance(main.get("path"), str) else None)


def _process_rows_from_wmic() -> list[dict[str, str | None]]:
    import subprocess
    from feishu_stack.core.process import CREATE_NO_WINDOW

    completed = subprocess.run(
        ["wmic", "process", "get", "Name,ProcessId,ExecutablePath", "/format:csv"],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        creationflags=CREATE_NO_WINDOW,
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        return []
    return [
        {"Name": row.get("Name"), "ProcessId": row.get("ProcessId"), "ExecutablePath": row.get("ExecutablePath")}
        for row in csv.DictReader(io.StringIO(completed.stdout))
    ]


def _process_rows_from_powershell() -> list[dict[str, str | None]]:
    import subprocess
    from feishu_stack.core.process import CREATE_NO_WINDOW

    completed = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-CimInstance Win32_Process -Filter \"Name = 'Codex.exe'\" "
            "| Select-Object Name,ProcessId,ExecutablePath | ConvertTo-Json -Compress",
        ],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        creationflags=CREATE_NO_WINDOW,
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        return []
    payload = json.loads(completed.stdout)
    if isinstance(payload, dict):
        payload = [payload]
    if not isinstance(payload, list):
        return []
    return [
        {"Name": str(row.get("Name") or ""), "ProcessId": str(row.get("ProcessId") or ""), "ExecutablePath": row.get("ExecutablePath")}
        for row in payload
        if isinstance(row, dict)
    ]


def codex_desktop_status() -> CodexDesktopStatus:
    for loader in (_process_rows_from_wmic, _process_rows_from_powershell):
        try:
            status = _codex_desktop_status_from_process_rows(loader())
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if status.running:
            return status
    return CodexDesktopStatus(False, None, 0, None)


def get_status(config: StackConfig | None = None) -> StackStatus:
    cfg = config or load_config()
    desktop = codex_desktop_status()
    codex_agent_args = cfg.agent.codex_agent_args
    return StackStatus(
        codex=read_provider_status(cfg),
        openclaw=component_status("openclaw", cfg.openclaw_port, cfg.pid_openclaw),
        moonbridge=component_status("moonbridge", cfg.moonbridge_port, cfg.pid_moonbridge),
        codex_agent=component_status("codex-agent", None, cfg.pid_codex_agent),
        codex_agent_args=codex_agent_args,
        codex_agent_follows_global_config="--profile" not in codex_agent_args,
        codex_desktop_running=desktop.running,
        codex_desktop=desktop,
        stack_root=str(cfg.stack_root),
    )
