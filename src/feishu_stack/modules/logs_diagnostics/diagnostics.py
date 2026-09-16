from __future__ import annotations

import os
import time
from typing import Any

from feishu_stack.core.settings import StackConfig, load_config
from feishu_stack.core.env import ensure_env_var
from feishu_stack.core.process import run_capture
from feishu_stack.core.status import get_status


def _completed_result(name: str, started: float, returncode: int, stdout: str, stderr: str) -> dict[str, Any]:
    return {
        "name": name,
        "ok": returncode == 0,
        "returncode": returncode,
        "stdout": stdout,
        "stderr": stderr,
        "duration_ms": int((time.monotonic() - started) * 1000),
    }


def codex_doctor(config: StackConfig | None = None) -> dict[str, Any]:
    cfg = config or load_config()
    started = time.monotonic()
    try:
        completed = run_capture([str(cfg.codex_bin), "doctor", "--summary"], cwd=cfg.codex_home, timeout=90)
        return _completed_result("codex-doctor", started, completed.returncode, completed.stdout, completed.stderr)
    except Exception as exc:
        return _completed_result("codex-doctor", started, 1, "", str(exc))


def deepseek_env_status(config: StackConfig | None = None) -> dict[str, Any]:
    cfg = config or load_config()
    started = time.monotonic()
    env_key = cfg.deepseek.env_key
    present, source = ensure_env_var(env_key)
    return {
        "name": "deepseek-env",
        "ok": present,
        "env_key": env_key,
        "present": present,
        "source": source,
        "base_url": cfg.deepseek.base_url,
        "models": cfg.deepseek.models,
        "error": "" if present else f"Environment variable {env_key} is not visible to the current ACC process or Windows environment registry.",
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


def diagnostics(config: StackConfig | None = None) -> dict[str, Any]:
    cfg = config or load_config()
    return {
        "status": get_status(cfg),
        "codex_doctor": codex_doctor(cfg),
        "deepseek_env": deepseek_env_status(cfg),
        "lark_auth_status": lark_auth_status(cfg),
    }
