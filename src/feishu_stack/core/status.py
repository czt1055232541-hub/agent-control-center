from __future__ import annotations

import re
import csv
import io

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


def codex_desktop_status() -> CodexDesktopStatus:
    import subprocess
    from feishu_stack.core.process import CREATE_NO_WINDOW

    try:
        completed = subprocess.run(
            ["wmic", "process", "where", "name='Codex.exe'", "get", "ProcessId,ExecutablePath", "/format:csv"],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            creationflags=CREATE_NO_WINDOW,
        )
    except OSError:
        return CodexDesktopStatus(False, None, 0, None)
    if completed.returncode != 0 or not completed.stdout.strip():
        return CodexDesktopStatus(False, None, 0, None)
    rows = []
    for row in csv.DictReader(io.StringIO(completed.stdout)):
        try:
            pid = int(row.get("ProcessId") or 0)
        except ValueError:
            continue
        if pid > 0:
            rows.append({"pid": pid, "path": row.get("ExecutablePath") or None})
    if not rows:
        return CodexDesktopStatus(False, None, 0, None)
    main = next((row for row in rows if row.get("path")), rows[0])
    return CodexDesktopStatus(True, main["pid"], len(rows), main.get("path"))


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
