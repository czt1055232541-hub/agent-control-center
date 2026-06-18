from __future__ import annotations

import os
import time

from .config import StackConfig, load_config
from .models import OperationResult
from .process import is_port_listening, start_process, stop_component, wait_for_port, write_pid


def start(config: StackConfig | None = None) -> OperationResult:
    cfg = config or load_config()
    started = time.monotonic()
    if is_port_listening(cfg.openclaw_port):
        return OperationResult(True, "openclaw", "start", "OpenClaw Gateway is already listening.", port=cfg.openclaw_port)
    env = os.environ.copy()
    env["OPENCLAW_HOME"] = str(cfg.openclaw_home)
    proc = start_process(
        ["cmd.exe", "/d", "/c", str(cfg.openclaw_gateway_cmd)],
        cwd=cfg.openclaw_home,
        stdout_log=cfg.openclaw_stdout_log,
        stderr_log=cfg.openclaw_stderr_log,
        env=env,
    )
    write_pid(cfg.pid_openclaw, proc.pid)
    ready = wait_for_port(cfg.openclaw_port, True)
    duration = int((time.monotonic() - started) * 1000)
    return OperationResult(
        ok=ready,
        component="openclaw",
        action="start",
        message="OpenClaw Gateway started." if ready else "OpenClaw Gateway did not become ready.",
        pid=proc.pid,
        port=cfg.openclaw_port,
        stdout_log=str(cfg.openclaw_stdout_log),
        stderr_log=str(cfg.openclaw_stderr_log),
        duration_ms=duration,
    )


def stop(config: StackConfig | None = None) -> OperationResult:
    cfg = config or load_config()
    env = os.environ.copy()
    env["OPENCLAW_HOME"] = str(cfg.openclaw_home)
    return stop_component(
        component="openclaw",
        pid_file=cfg.pid_openclaw,
        port=cfg.openclaw_port,
        pre_stop=["openclaw.cmd", "gateway", "stop"],
        pre_stop_cwd=cfg.openclaw_home,
        pre_stop_env=env,
    )


def restart(config: StackConfig | None = None) -> OperationResult:
    cfg = config or load_config()
    stop(cfg)
    result = start(cfg)
    result.action = "restart"
    return result
