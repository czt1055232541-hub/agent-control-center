from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

from feishu_stack.core.settings import StackConfig, load_config
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


def moonbridge_models(config: StackConfig | None = None) -> dict[str, Any]:
    cfg = config or load_config()
    started = time.monotonic()
    url = cfg.moonbridge.base_url.rstrip("/") + "/models"
    try:
        with urllib.request.urlopen(url, timeout=8) as response:
            raw = response.read().decode("utf-8", errors="replace")
            data = json.loads(raw) if raw else {}
            models = [item.get("id", item) for item in data.get("data", [])] if isinstance(data, dict) else []
            return {
                "name": "moonbridge-models",
                "ok": 200 <= response.status < 300,
                "reachable": True,
                "status": response.status,
                "models": models,
                "raw": data,
                "error": "",
                "duration_ms": int((time.monotonic() - started) * 1000),
            }
    except urllib.error.HTTPError as exc:
        return {
            "name": "moonbridge-models",
            "ok": False,
            "reachable": True,
            "status": exc.code,
            "models": [],
            "raw": {},
            "error": str(exc),
            "duration_ms": int((time.monotonic() - started) * 1000),
        }
    except Exception as exc:
        return {
            "name": "moonbridge-models",
            "ok": False,
            "reachable": False,
            "status": None,
            "models": [],
            "raw": {},
            "error": str(exc),
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
        "moonbridge_models": moonbridge_models(cfg),
        "lark_auth_status": lark_auth_status(cfg),
    }
