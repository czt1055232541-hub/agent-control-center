from __future__ import annotations

import time

from .config import StackConfig, load_config
from .models import OperationResult
from .process import CREATE_NO_WINDOW
from .status import is_codex_desktop_running


def stop(config: StackConfig | None = None) -> OperationResult:
    import subprocess

    config or load_config()
    started = time.monotonic()
    completed = subprocess.run(
        ["taskkill", "/IM", "Codex.exe", "/T", "/F"],
        text=True,
        capture_output=True,
        creationflags=CREATE_NO_WINDOW,
    )
    running = is_codex_desktop_running()
    output = completed.stdout.strip() or completed.stderr.strip()
    return OperationResult(
        ok=completed.returncode == 0 and not running,
        component="codex-desktop",
        action="stop",
        message=output or ("Codex Desktop stopped." if not running else "Codex Desktop may still be running."),
        duration_ms=int((time.monotonic() - started) * 1000),
    )
