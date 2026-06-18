from __future__ import annotations

import time

from .config import StackConfig, load_config
from .models import OperationResult
from .process import is_port_listening, start_process, stop_component, wait_for_port, write_pid


def start(config: StackConfig | None = None) -> OperationResult:
    cfg = config or load_config()
    started = time.monotonic()
    if is_port_listening(cfg.moonbridge_port):
        return OperationResult(True, "moonbridge", "start", "MoonBridge is already listening.", port=cfg.moonbridge_port)
    proc = start_process(
        [str(cfg.moonbridge_exe), "-config", str(cfg.moonbridge_config)],
        cwd=cfg.moonbridge_dir,
        stdout_log=cfg.moonbridge_stdout_log,
        stderr_log=cfg.moonbridge_stderr_log,
    )
    write_pid(cfg.pid_moonbridge, proc.pid)
    ready = wait_for_port(cfg.moonbridge_port, True)
    duration = int((time.monotonic() - started) * 1000)
    return OperationResult(
        ok=ready,
        component="moonbridge",
        action="start",
        message="MoonBridge started." if ready else "MoonBridge did not become ready.",
        pid=proc.pid,
        port=cfg.moonbridge_port,
        stdout_log=str(cfg.moonbridge_stdout_log),
        stderr_log=str(cfg.moonbridge_stderr_log),
        duration_ms=duration,
    )


def stop(config: StackConfig | None = None) -> OperationResult:
    cfg = config or load_config()
    return stop_component("moonbridge", cfg.pid_moonbridge, cfg.moonbridge_port)


def restart(config: StackConfig | None = None) -> OperationResult:
    cfg = config or load_config()
    stop(cfg)
    result = start(cfg)
    result.action = "restart"
    return result
