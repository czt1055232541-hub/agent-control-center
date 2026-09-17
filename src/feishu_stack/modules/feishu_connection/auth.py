"""Feishu-owned read-only CLI authentication probe."""
import os
import time
from typing import Any
from feishu_stack.core.settings import StackConfig, load_config
from feishu_stack.core.process import run_capture

def _completed_result(name: str, started: float, returncode: int, stdout: str, stderr: str) -> dict[str, Any]:
    return {
        "name": name,
        "ok": returncode == 0,
        "returncode": returncode,
        "stdout": stdout,
        "stderr": stderr,
        "duration_ms": int((time.monotonic() - started) * 1000),
    }

def lark_auth_status(config: StackConfig | None = None) -> dict[str, Any]:
    cfg = config or load_config()
    started = time.monotonic()
    env = os.environ.copy()
    env["OPENCLAW_HOME"] = ""
    env["CLAW_HOME"] = ""
    try:
        completed = run_capture([str(cfg.lark_cli_bin), "auth", "status"], cwd=cfg.stack_root, env=env, timeout=45)
        return _completed_result("lark-auth-status", started, completed.returncode, completed.stdout, completed.stderr)
    except Exception as exc:
        return _completed_result("lark-auth-status", started, 1, "", str(exc))
