from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

from .config import StackConfig, load_config
from .log_manager import open_rotating
from .models import OperationResult
from .process import CREATE_NO_WINDOW, is_port_listening, process_info, read_pid, run_capture, terminate_pid, write_pid

PORT = 8765


def _web_dist_index(cfg: StackConfig) -> Path:
    return cfg.stack_root / "web" / "dist" / "index.html"


def _control_pid(cfg: StackConfig) -> Path:
    return cfg.pid_dir / "control-center-api.pid"


def start(config: StackConfig | None = None, open_browser: bool = False, build: bool = True) -> OperationResult:
    cfg = config or load_config()
    started = time.monotonic()
    if is_port_listening(PORT):
        if open_browser:
            os.startfile(f"http://127.0.0.1:{PORT}")
        return OperationResult(True, "control-center", "start", "Control Center API is already listening.", port=PORT, duration_ms=int((time.monotonic() - started) * 1000))
    control_dir = cfg.stack_root
    web_dir = control_dir / "web"
    if build and not _web_dist_index(cfg).exists():
        install = run_capture(["npm", "install"], cwd=web_dir, timeout=180)
        if install.returncode != 0:
            return OperationResult(False, "control-center", "start", install.stderr or install.stdout, duration_ms=int((time.monotonic() - started) * 1000))
        build_result = run_capture(["npm", "run", "build"], cwd=web_dir, timeout=180)
        if build_result.returncode != 0:
            return OperationResult(False, "control-center", "start", build_result.stderr or build_result.stdout, duration_ms=int((time.monotonic() - started) * 1000))
    proc = subprocess.Popen(
        [str(cfg.python_exe), "-m", "uvicorn", "feishu_stack.app:app", "--host", "127.0.0.1", "--port", str(PORT)],
        cwd=str(control_dir),
        stdin=subprocess.DEVNULL,
        stdout=open_rotating(cfg.log_dir / "control-center-api-out.log"),
        stderr=open_rotating(cfg.log_dir / "control-center-api-err.log"),
        creationflags=CREATE_NO_WINDOW,
    )
    write_pid(_control_pid(cfg), proc.pid)
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline and not is_port_listening(PORT):
        time.sleep(1)
    if open_browser:
        os.startfile(f"http://127.0.0.1:{PORT}")
    ready = is_port_listening(PORT)
    return OperationResult(
        ok=ready,
        component="control-center",
        action="start",
        message="Control Center API started." if ready else "Control Center API did not become ready.",
        pid=proc.pid,
        port=PORT,
        duration_ms=int((time.monotonic() - started) * 1000),
    )


def stop(config: StackConfig | None = None) -> OperationResult:
    cfg = config or load_config()
    started = time.monotonic()
    pid = read_pid(_control_pid(cfg))
    stopped = False
    if pid:
        running, name = process_info(pid)
        if running and name and "python" in name.lower():
            stopped = terminate_pid(pid)
    if _control_pid(cfg).exists():
        _control_pid(cfg).unlink(missing_ok=True)
    return OperationResult(
        ok=not is_port_listening(PORT),
        component="control-center",
        action="stop",
        message="Control Center API stopped." if stopped else "Control Center API stop requested.",
        pid=pid,
        port=PORT,
        duration_ms=int((time.monotonic() - started) * 1000),
    )


def status(config: StackConfig | None = None) -> dict:
    cfg = config or load_config()
    pid = read_pid(_control_pid(cfg))
    running, process_name = process_info(pid)
    return {
        "url": f"http://127.0.0.1:{PORT}",
        "port": PORT,
        "port_listening": is_port_listening(PORT),
        "pid": pid,
        "pid_running": running,
        "process_name": process_name,
        "gui_build": _web_dist_index(cfg).exists(),
        "stdout_log": str(cfg.log_dir / "control-center-api-out.log"),
        "stderr_log": str(cfg.log_dir / "control-center-api-err.log"),
    }


def install_shortcut(config: StackConfig | None = None) -> OperationResult:
    cfg = config or load_config()
    started = time.monotonic()
    desktop = Path.home() / "Desktop"
    cmd_path = desktop / "Agent Control Center.cmd"
    script = cfg.stack_root / "scripts" / "stack.py"
    cmd_path.write_text(
        f'@echo off\r\n"{sys.executable}" -X utf8 "{script}" serve-control-center --open\r\n',
        encoding="ascii",
    )
    return OperationResult(True, "control-center", "install-shortcut", f"Created shortcut command: {cmd_path}", duration_ms=int((time.monotonic() - started) * 1000))
