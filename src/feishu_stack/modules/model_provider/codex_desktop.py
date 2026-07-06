from __future__ import annotations

import os
import time
from pathlib import Path

from feishu_stack.core.settings import StackConfig, load_config
from feishu_stack.core.logs import tail
from feishu_stack.core.models import LogTail, OperationResult
from feishu_stack.core.process import CREATE_NO_WINDOW
from feishu_stack.core.status import codex_desktop_status, is_codex_desktop_running


def _install_location_from_registry() -> str | None:
    try:
        import winreg
    except ImportError:
        return None
    roots = [
        (winreg.HKEY_CURRENT_USER, r"Software\Classes\Local Settings\Software\Microsoft\Windows\CurrentVersion\AppModel\Repository\Packages"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Classes\Local Settings\Software\Microsoft\Windows\CurrentVersion\AppModel\Repository\Packages"),
    ]
    for hive, key_name in roots:
        try:
            with winreg.OpenKey(hive, key_name) as key:
                for index in range(winreg.QueryInfoKey(key)[0]):
                    package_name = winreg.EnumKey(key, index)
                    if not package_name.startswith("OpenAI.Codex"):
                        continue
                    with winreg.OpenKey(key, package_name) as package_key:
                        value, _ = winreg.QueryValueEx(package_key, "Path")
                        if value:
                            return str(value)
        except OSError:
            continue
    return None


def _install_location() -> str | None:
    return _install_location_from_registry()


def _executable_path() -> str | None:
    status = codex_desktop_status()
    if status.executable:
        return status.executable
    install = _install_location()
    if install:
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
    if os.environ.get("AGENT_CONTROL_CENTER_ALLOW_CODEX_DESKTOP_STOP") != "1":
        return OperationResult(
            False,
            "codex-desktop",
            "stop",
            "Refusing to stop Codex Desktop unless AGENT_CONTROL_CENTER_ALLOW_CODEX_DESKTOP_STOP=1 is set.",
            duration_ms=int((time.monotonic() - started) * 1000),
        )
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
