from __future__ import annotations

import time

from .config import StackConfig, load_config
from .models import OperationResult
from .process import run_capture
from .status import read_provider_status


def switch_provider(mode: str, config: StackConfig | None = None) -> OperationResult:
    if mode not in {"native", "moonbridge"}:
        raise ValueError(f"Unsupported provider mode: {mode}")
    cfg = config or load_config()
    started = time.monotonic()
    completed = run_capture(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(cfg.codex_switch_script), "-Mode", mode],
        cwd=cfg.stack_root,
        timeout=180,
    )
    provider = read_provider_status(cfg)
    ok = completed.returncode == 0 and provider.mode == mode
    duration = int((time.monotonic() - started) * 1000)
    message = completed.stdout.strip() or completed.stderr.strip() or f"Switched provider to {mode}."
    return OperationResult(
        ok=ok,
        component="codex-provider",
        action=f"switch-{mode}",
        message=message,
        duration_ms=duration,
    )

