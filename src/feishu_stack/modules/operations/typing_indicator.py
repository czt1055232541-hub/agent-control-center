from __future__ import annotations

import os
import time

from feishu_stack.core.settings import StackConfig, load_config
from feishu_stack.core.models import OperationResult
from feishu_stack.core.process import (
    CREATE_NO_WINDOW,
    read_pid,
    start_process,
    stop_component,
    write_pid,
)


def start(config: StackConfig | None = None) -> OperationResult:
    cfg = config or load_config()
    started = time.monotonic()
    pid = read_pid(cfg.pid_typing_indicator)
    running = False
    if pid:
        import psutil
        try:
            p = psutil.Process(pid)
            running = p.is_running()
        except psutil.NoSuchProcess:
            pass
    if running:
        return OperationResult(True, "typing-indicator", "start", "Typing Indicator is already running.", pid=pid)
    env = os.environ.copy()
    for key in list(env):
        if key.startswith("OPENCLAW_") or key in ("CODEX_HOME", "CLAW_HOME"):
            env.pop(key, None)
    env["PYTHON_EXE"] = str(cfg.python_exe)
    env["LARK_CLI_BIN"] = str(cfg.lark_cli_bin)
    if cfg.agent.lark_cli_profile:
        env["LARK_CLI_PROFILE"] = cfg.agent.lark_cli_profile
    proc = start_process(
        [cfg.python_exe, str(cfg.typing_indicator_launcher)],
        cwd=cfg.typing_indicator_dir,
        stdout_log=cfg.typing_indicator_stdout_log,
        stderr_log=cfg.typing_indicator_stderr_log,
        env=env,
    )
    write_pid(cfg.pid_typing_indicator, proc.pid)
    time.sleep(2)
    import psutil
    try:
        p = psutil.Process(proc.pid)
        running = p.is_running()
    except psutil.NoSuchProcess:
        running = False
    duration = int((time.monotonic() - started) * 1000)
    return OperationResult(
        ok=running,
        component="typing-indicator",
        action="start",
        message="Typing Indicator started." if running else "Typing Indicator exited during startup.",
        pid=proc.pid,
        stdout_log=str(cfg.typing_indicator_stdout_log),
        stderr_log=str(cfg.typing_indicator_stderr_log),
        duration_ms=duration,
    )


def stop(config: StackConfig | None = None) -> OperationResult:
    cfg = config or load_config()
    return stop_component("typing-indicator", cfg.pid_typing_indicator, None)


def restart(config: StackConfig | None = None) -> OperationResult:
    cfg = config or load_config()
    stop(cfg)
    result = start(cfg)
    result.action = "restart"
    return result
