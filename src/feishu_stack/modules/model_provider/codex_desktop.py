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


def _install_location_from_appx_package() -> str | None:
    import subprocess

    try:
        completed = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-AppxPackage -Name OpenAI.Codex "
                "| Sort-Object Version -Descending "
                "| Select-Object -First 1 -ExpandProperty InstallLocation",
            ],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            creationflags=CREATE_NO_WINDOW,
        )
    except OSError:
        return None
    if completed.returncode != 0:
        return None
    value = completed.stdout.strip()
    return value or None


def _install_location_from_windowsapps() -> str | None:
    root = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "WindowsApps"
    try:
        candidates = sorted(
            (path for path in root.glob("OpenAI.Codex_*") if (path / "app" / "Codex.exe").exists()),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
    except OSError:
        return None
    return str(candidates[0]) if candidates else None


def _install_location() -> str | None:
    return (
        _install_location_from_registry()
        or _install_location_from_appx_package()
        or _install_location_from_windowsapps()
    )


def _cached_executable_file(config: StackConfig | None = None) -> Path | None:
    runtime_dir = getattr(config, "runtime_dir", None)
    if runtime_dir is None:
        return None
    return Path(runtime_dir) / "codex-desktop-executable.txt"


def _read_cached_executable(config: StackConfig | None = None) -> str | None:
    cache = _cached_executable_file(config)
    if not cache or not cache.exists():
        return None
    try:
        value = cache.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None
    if value and Path(value).exists():
        return value
    return None


def _write_cached_executable(executable: str | None, config: StackConfig | None = None) -> None:
    if not executable or not Path(executable).exists():
        return
    cache = _cached_executable_file(config)
    if not cache:
        return
    try:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(str(executable) + "\n", encoding="utf-8")
    except OSError:
        return


def _executable_from_install_location(install: str | None) -> str | None:
    if not install:
        return None
    candidate = Path(install) / "app" / "Codex.exe"
    return str(candidate) if candidate.exists() else None


def _executable_path(config: StackConfig | None = None) -> str | None:
    status = codex_desktop_status()
    if status.executable:
        _write_cached_executable(status.executable, config)
        return status.executable
    return _executable_from_install_location(_install_location()) or _read_cached_executable(config)


def start(config: StackConfig | None = None) -> OperationResult:
    import subprocess

    cfg = config or load_config()
    started = time.monotonic()
    status = codex_desktop_status()
    if status.running:
        _write_cached_executable(status.executable, cfg)
        return OperationResult(True, "codex-desktop", "start", "Codex Desktop is already running.", pid=status.pid, duration_ms=int((time.monotonic() - started) * 1000))
    executable = _executable_path(cfg)
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
    _write_cached_executable(status.executable, cfg)
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
