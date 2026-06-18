from __future__ import annotations

import time

from .config import StackConfig, load_config
from .models import OperationResult
from .process import run_capture


def clean(config: StackConfig | None = None, keep: int = 1) -> OperationResult:
    cfg = config or load_config()
    started = time.monotonic()
    script = cfg.stack_root / "codex" / "Clean-CodexBackups.ps1"
    completed = run_capture(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            "-Keep",
            str(keep),
        ],
        cwd=cfg.stack_root,
        timeout=60,
    )
    message = completed.stdout.strip() or completed.stderr.strip() or "Backup cleanup complete."
    return OperationResult(
        ok=completed.returncode == 0,
        component="backups",
        action="clean",
        message=message,
        duration_ms=int((time.monotonic() - started) * 1000),
    )
