from __future__ import annotations

import os
import socket
import subprocess
import time
from pathlib import Path

from .log_manager import open_rotating

from .models import ComponentStatus, OperationResult

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


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
    completed = subprocess.run(
        ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
        text=True,
        capture_output=True,
        creationflags=CREATE_NO_WINDOW,
    )
    output = completed.stdout.strip()
    if not output or "No tasks are running" in output or not output.startswith('"'):
        return False, None
    first = output.splitlines()[0].strip()
    process_name = first.split('","')[0].strip('"') if first else None
    return True, process_name


def pids_by_port(port: int) -> list[int]:
    completed = subprocess.run(
        ["netstat", "-ano"],
        text=True,
        capture_output=True,
        creationflags=CREATE_NO_WINDOW,
    )
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
            creationflags=CREATE_NO_WINDOW,
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
    )


def terminate_pid(pid: int) -> bool:
    command = ["taskkill", "/PID", str(pid), "/T", "/F"] if os.name == "nt" else ["kill", str(pid)]
    completed = subprocess.run(command, text=True, capture_output=True, creationflags=CREATE_NO_WINDOW)
    return completed.returncode == 0


def stop_component(
    component: str,
    pid_file: Path,
    port: int | None,
    action: str = "stop",
    pre_stop: list[str] | None = None,
    pre_stop_cwd: Path | None = None,
    pre_stop_env: dict[str, str] | None = None,
) -> OperationResult:
    started = time.monotonic()
    messages: list[str] = []
    if pre_stop:
        completed = run_capture(pre_stop, cwd=pre_stop_cwd, env=pre_stop_env, timeout=30)
        if completed.stdout.strip():
            messages.append(completed.stdout.strip())
        if completed.stderr.strip():
            messages.append(completed.stderr.strip())
    pid = read_pid(pid_file)
    stopped = False
    if pid is not None:
        running, _ = process_info(pid)
        if running:
            stopped = terminate_pid(pid) or stopped
        remove_pid(pid_file)
    if port is not None:
        for port_pid in pids_by_port(port):
            stopped = terminate_pid(port_pid) or stopped
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
    return OperationResult(ok=ok, component=component, action=action, message=message, pid=pid, port=port, duration_ms=duration)


def wait_for_port(port: int, desired: bool, timeout: int = 25) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if is_port_listening(port) == desired:
            return True
        time.sleep(1)
    return is_port_listening(port) == desired
