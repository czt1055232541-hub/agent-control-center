from __future__ import annotations

import re

from .config import StackConfig, load_config
from .models import ProviderStatus, StackStatus
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
    # Codex Desktop has several Codex.exe children; any alive Codex.exe is enough for read-only presence.
    import subprocess
    from .process import CREATE_NO_WINDOW

    completed = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq Codex.exe", "/FO", "CSV", "/NH"],
        text=True,
        capture_output=True,
        creationflags=CREATE_NO_WINDOW,
    )
    output = completed.stdout.strip()
    return bool(output and "No tasks are running" not in output)


def get_status(config: StackConfig | None = None) -> StackStatus:
    cfg = config or load_config()
    return StackStatus(
        codex=read_provider_status(cfg),
        openclaw=component_status("openclaw", cfg.openclaw_port, cfg.pid_openclaw),
        moonbridge=component_status("moonbridge", cfg.moonbridge_port, cfg.pid_moonbridge),
        codex_agent=component_status("codex-agent", None, cfg.pid_codex_agent),
        codex_desktop_running=is_codex_desktop_running(),
        stack_root=str(cfg.stack_root),
    )

