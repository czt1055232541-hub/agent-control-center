from __future__ import annotations

import time

from .config import StackConfig, load_config
from .logs import tail
from .models import LogTail, OperationResult
from .process import CREATE_NO_WINDOW, run_capture
from .status import codex_desktop_status, is_codex_desktop_running


def _install_location() -> str | None:
    completed = run_capture(
        [
            "powershell.exe",
            "-NoProfile",
            "-Command",
            "(Get-AppxPackage OpenAI.Codex | Select-Object -First 1 -ExpandProperty InstallLocation)",
        ],
        timeout=30,
    )
    text = completed.stdout.strip()
    return text or None


def _executable_path() -> str | None:
    status = codex_desktop_status()
    if status.executable:
        return status.executable
    install = _install_location()
    if install:
        from pathlib import Path

        candidate = Path(install) / "app" / "Codex.exe"
        if candidate.exists():
            return str(candidate)
    return None


def start(config: StackConfig | None = None) -> OperationResult:
    import subprocess

    config or load_config()
    started = time.monotonic()
    status = codex_desktop_status()
    if status.running:
        return OperationResult(True, "codex-desktop", "start", "Codex Desktop is already running.", pid=status.pid, duration_ms=int((time.monotonic() - started) * 1000))
    executable = _executable_path()
    if not executable:
        return OperationResult(False, "codex-desktop", "start", "Could not locate Codex Desktop executable.", duration_ms=int((time.monotonic() - started) * 1000))
    subprocess.Popen([executable], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=CREATE_NO_WINDOW)
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        status = codex_desktop_status()
        if status.running:
            break
        time.sleep(1)
    return OperationResult(
        ok=status.running,
        component="codex-desktop",
        action="start",
        message="Codex Desktop started." if status.running else "Codex Desktop did not become ready.",
        pid=status.pid,
        duration_ms=int((time.monotonic() - started) * 1000),
    )


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


def restart(config: StackConfig | None = None) -> OperationResult:
    cfg = config or load_config()
    started = time.monotonic()
    stop(cfg)
    result = start(cfg)
    result.action = "restart"
    result.duration_ms = int((time.monotonic() - started) * 1000)
    return result


def log(config: StackConfig | None = None) -> LogTail:
    cfg = config or load_config()
    status = codex_desktop_status()
    lines = [
        f"running={status.running}",
        f"pid={status.pid}",
        f"process_count={status.process_count}",
        f"executable={status.executable}",
    ]
    path = cfg.log_dir / "codex-desktop-status.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return tail(path, 80)
