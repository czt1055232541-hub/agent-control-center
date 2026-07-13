from __future__ import annotations

import os
import socket
import subprocess
import time
from pathlib import Path

from feishu_stack.core.log_manager import open_rotating

from feishu_stack.core.models import ComponentStatus, OperationResult

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0
DETACHED_PROCESS = 0x00000008 if os.name == "nt" else 0
WINDOWLESS_PROCESS_FLAGS = CREATE_NO_WINDOW | DETACHED_PROCESS


def _hidden_startupinfo() -> subprocess.STARTUPINFO | None:
    if os.name != "nt":
        return None
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = 0
    return startupinfo


def _run_system(command: list[str], timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=timeout,
        creationflags=CREATE_NO_WINDOW,
        startupinfo=_hidden_startupinfo(),
    )


def is_port_listening(port: int, host: str = "127.0.0.1", timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def read_pid(pid_file: Path) -> int | None:
    try:
        text = pid_file.read_text(encoding="ascii").strip()
        return int(text) if text else None
    except (OSError, ValueError):
        return None


def write_pid(pid_file: Path, pid: int) -> None:
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(str(pid), encoding="ascii")


def remove_pid(pid_file: Path) -> None:
    try:
        pid_file.unlink()
    except FileNotFoundError:
        pass


def process_info(pid: int | None) -> tuple[bool, str | None]:
    if pid is None:
        return False, None
    if os.name != "nt":
        try:
            os.kill(pid, 0)
            return True, None
        except OSError:
            return False, None
    try:
        completed = _run_system(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"], timeout=10)
    except subprocess.TimeoutExpired:
        return False, None
    output = completed.stdout.strip()
    if not output or "No tasks are running" in output or not output.startswith('"'):
        return False, None
    first = output.splitlines()[0].strip()
    process_name = first.split('","')[0].strip('"') if first else None
    return True, process_name


def pids_by_port(port: int) -> list[int]:
    try:
        completed = _run_system(["netstat", "-ano"], timeout=10)
    except subprocess.TimeoutExpired:
        return []
    pids: set[int] = set()
    marker = f":{port}"
    for line in completed.stdout.splitlines():
        if marker not in line or "LISTENING" not in line:
            continue
        parts = line.split()
        if parts:
            try:
                pids.add(int(parts[-1]))
            except ValueError:
                pass
    return sorted(pids)


def process_matches(pid: int, expected_markers: tuple[str, ...]) -> bool:
    """Confirm a PID belongs to the expected component before termination."""
    if not expected_markers:
        return False
    try:
        import psutil

        process = psutil.Process(pid)
        text = " ".join(
            [
                process.name() or "",
                process.exe() or "",
                " ".join(process.cmdline() or []),
                process.cwd() or "",
            ]
        ).lower()
    except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
        return False
    return any(marker.lower() in text for marker in expected_markers)


def component_status(name: str, port: int | None, pid_file: Path | None) -> ComponentStatus:
    pid = read_pid(pid_file) if pid_file else None
    running, process_name = process_info(pid)
    return ComponentStatus(
        name=name,
        port=port,
        port_listening=is_port_listening(port) if port else False,
        pid_file=str(pid_file) if pid_file else None,
        pid=pid,
        pid_running=running,
        process_name=process_name,
    )


def start_process(
    command: list[str],
    cwd: Path,
    stdout_log: Path,
    stderr_log: Path,
    env: dict[str, str] | None = None,
) -> subprocess.Popen[str]:
    stdout_log.parent.mkdir(parents=True, exist_ok=True)
    stderr_log.parent.mkdir(parents=True, exist_ok=True)
    stdout_handle = open_rotating(stdout_log)
    stderr_handle = open_rotating(stderr_log)
    try:
        return subprocess.Popen(
            command,
            cwd=str(cwd),
            stdout=stdout_handle,
            stderr=stderr_handle,
            stdin=subprocess.DEVNULL,
            text=True,
            env=env,
            creationflags=WINDOWLESS_PROCESS_FLAGS,
            startupinfo=_hidden_startupinfo(),
        )
    except Exception:
        stdout_handle.close()
        stderr_handle.close()
        raise


def run_capture(command: list[str], cwd: Path | None = None, env: dict[str, str] | None = None, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=timeout,
        creationflags=CREATE_NO_WINDOW,
        startupinfo=_hidden_startupinfo(),
    )


def terminate_pid(pid: int) -> bool:
    command = ["taskkill", "/PID", str(pid), "/T", "/F"] if os.name == "nt" else ["kill", str(pid)]
    try:
        completed = _run_system(command, timeout=15)
        return completed.returncode == 0
    except subprocess.TimeoutExpired:
        return False


def stop_component(
    component: str,
    pid_file: Path,
    port: int | None,
    action: str = "stop",
    pre_stop: list[str] | None = None,
    pre_stop_cwd: Path | None = None,
    pre_stop_env: dict[str, str] | None = None,
    expected_process_markers: tuple[str, ...] | None = None,
) -> OperationResult:
    started = time.monotonic()
    messages: list[str] = []
    if pre_stop:
        try:
            completed = run_capture(pre_stop, cwd=pre_stop_cwd, env=pre_stop_env, timeout=30)
            if completed.stdout.strip():
                messages.append(completed.stdout.strip())
            if completed.stderr.strip():
                messages.append(completed.stderr.strip())
        except subprocess.TimeoutExpired:
            messages.append(f"pre-stop command timed out after 30s: {' '.join(pre_stop)}")
    pid = read_pid(pid_file)
    stopped = False
    markers = expected_process_markers or (component,)
    skipped_pids: list[int] = []
    if pid is not None:
        running, _ = process_info(pid)
        if running and process_matches(pid, markers):
            stopped = terminate_pid(pid) or stopped
        elif running:
            skipped_pids.append(pid)
        remove_pid(pid_file)
    if port is not None:
        for port_pid in pids_by_port(port):
            if process_matches(port_pid, markers):
                stopped = terminate_pid(port_pid) or stopped
            else:
                skipped_pids.append(port_pid)
    duration = int((time.monotonic() - started) * 1000)
    still_listening = is_port_listening(port) if port else False
    ok = not still_listening
    if ok and not stopped:
        message = f"{component} was already stopped."
    elif ok:
        message = f"{component} stopped."
    else:
        message = f"{component} may still be running."
    if messages:
        message = message + " " + " ".join(messages)
    if skipped_pids:
        message += f" Refused to terminate unverified PIDs: {', '.join(str(item) for item in sorted(set(skipped_pids)))}."
    return OperationResult(ok=ok, component=component, action=action, message=message, pid=pid, port=port, duration_ms=duration)


def wait_for_port(port: int, desired: bool, timeout: int = 25) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if is_port_listening(port) == desired:
            return True
        time.sleep(1)
    return is_port_listening(port) == desired
