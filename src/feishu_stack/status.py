from __future__ import annotations

import re

from .config import StackConfig, load_config
from .models import CodexDesktopStatus, ProviderStatus, StackStatus
from .process import component_status, process_info, read_pid


def read_provider_status(config: StackConfig) -> ProviderStatus:
    text = config.codex_config.read_text(encoding="utf-8", errors="replace") if config.codex_config.exists() else ""
    model_match = re.search(r'(?m)^\s*model\s*=\s*"([^"]+)"', text)
    provider_match = re.search(r'(?m)^\s*model_provider\s*=\s*"([^"]+)"', text)
    model = model_match.group(1) if model_match else "unknown"
    provider = provider_match.group(1) if provider_match else "openai/default"
    mode = "moonbridge" if provider == "moonbridge" else "native"
    return ProviderStatus(model=model, provider=provider, mode=mode, config=str(config.codex_config))


def is_codex_desktop_running() -> bool:
    return codex_desktop_status().running


def codex_desktop_status() -> CodexDesktopStatus:
    import subprocess
    from .process import CREATE_NO_WINDOW

    try:
        completed = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                "Get-Process -Name Codex -ErrorAction SilentlyContinue | Select-Object Id,Path | ConvertTo-Json -Compress",
            ],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            creationflags=CREATE_NO_WINDOW,
        )
    except OSError:
        return CodexDesktopStatus(False, None, 0, None)
    output = completed.stdout.strip()
    if not output:
        return CodexDesktopStatus(False, None, 0, None)
    try:
        import json

        data = json.loads(output)
        rows = data if isinstance(data, list) else [data]
        rows = [row for row in rows if isinstance(row, dict)]
        main = next((row for row in rows if row.get("Path")), rows[0] if rows else {})
        return CodexDesktopStatus(
            running=bool(rows),
            pid=int(main["Id"]) if main.get("Id") is not None else None,
            process_count=len(rows),
            executable=main.get("Path"),
        )
    except Exception:
        return CodexDesktopStatus(True, None, 1, None)


def get_status(config: StackConfig | None = None) -> StackStatus:
    cfg = config or load_config()
    desktop = codex_desktop_status()
    agent_settings = cfg.raw.get("agent", {})
    codex_agent_args = str(agent_settings.get("codexAgentArgs") or "exec --skip-git-repo-check")
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
