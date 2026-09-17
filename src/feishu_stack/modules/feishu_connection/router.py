from __future__ import annotations

import logging
import os
import time
from typing import Any

from feishu_stack.core.settings import StackConfig, load_config
from feishu_stack.core.process import run_capture
from .auth import lark_auth_status

_log = logging.getLogger(__name__)


def _mask_app_id(raw: str) -> str:
    """Show only first 8 chars of App ID."""
    if len(raw) <= 8:
        return raw
    return raw[:8] + "****"


def _mask_id(raw: str) -> str:
    """Show only first 6 chars of open_id / chat_id."""
    if len(raw) <= 6:
        return raw
    return raw[:6] + "****"


def _completed_result(name: str, started: float, returncode: int, stdout: str, stderr: str) -> dict[str, Any]:
    return {
        "name": name,
        "ok": returncode == 0,
        "returncode": returncode,
        "stdout": stdout.strip(),
        "stderr": stderr.strip(),
        "duration_ms": int((time.monotonic() - started) * 1000),
    }


# ---------------------------------------------------------------------------
# GET /api/feishu/connection/status
# ---------------------------------------------------------------------------

def get_connection_status(config: StackConfig | None = None) -> dict[str, Any]:
    """Lark auth status + tenant name + app info (App ID first 8 chars masked)."""
    cfg = config or load_config()
    auth = lark_auth_status(cfg)

    # Parse tenant/app info from auth status output
    tenant_name: str | None = None
    app_name: str | None = None
    app_id_raw: str | None = None

    if auth.get("ok") and auth.get("stdout"):
        for line in auth["stdout"].splitlines():
            line_stripped = line.strip()
            if "租户" in line_stripped or "tenant" in line_stripped.lower():
                parts = line_stripped.split(":", 1)
                if len(parts) == 2:
                    tenant_name = parts[1].strip()
            if "app_id" in line_stripped.lower() or "App ID" in line_stripped:
                parts = line_stripped.split(":", 1)
                if len(parts) == 2:
                    app_id_raw = parts[1].strip()

    if not app_id_raw:
        app_id_raw = cfg.app_id
    if not app_name:
        app_name = cfg.app_name or "未知应用"

    return {
        "authenticated": auth.get("ok", False),
        "tenantName": tenant_name or "未知租户",
        "appName": app_name or "未知应用",
        "appIdMasked": _mask_app_id(app_id_raw) if app_id_raw else "未配置",
        "authDetail": auth.get("stdout", ""),
        "authError": auth.get("stderr", ""),
        "durationMs": auth.get("duration_ms", 0),
    }


# ---------------------------------------------------------------------------
# GET /api/feishu/connection/accounts
# ---------------------------------------------------------------------------

def get_connection_accounts(config: StackConfig | None = None) -> dict[str, Any]:
    """Agent binding list: feishuBinding, bindingStatus, group info (masked)."""
    cfg = config or load_config()
    a2a_bots = cfg.agent.a2a_bots

    accounts = []
    for bot in a2a_bots:
        name = bot.get("name", "未知")
        open_id = bot.get("openId", "")
        description = bot.get("description", "")
        accounts.append({
            "name": name,
            "openIdMasked": _mask_id(open_id) if open_id else "",
            "role": description,
            "bindingStatus": "bound" if open_id else "unbound",
            "feishuBinding": open_id and "enabled" or "disabled",
        })

    # Groups info from config (masked)
    group_chat_id = cfg.agent.a2a_relay.group_chat_id if cfg.agent.a2a_relay else ""
    groups = []
    if group_chat_id:
        groups.append({
            "chatIdMasked": _mask_id(group_chat_id),
            "groupName": "Agent 协作群",
        })

    return {
        "accounts": accounts,
        "groups": groups,
        "total": len(accounts),
    }


# ---------------------------------------------------------------------------
# GET /api/feishu/connection/permissions
# ---------------------------------------------------------------------------

def get_connection_permissions(config: StackConfig | None = None) -> dict[str, Any]:
    """Permission scope check, mark missing items."""
    cfg = config or load_config()

    # Run lark auth status to check scopes
    started = time.monotonic()
    env = os.environ.copy()
    env["OPENCLAW_HOME"] = ""
    env["CLAW_HOME"] = ""
    try:
        completed = run_capture(
            [str(cfg.lark_cli_bin), "auth", "status"],
            cwd=cfg.stack_root,
            env=env,
            timeout=45,
        )
        auth_raw = _completed_result("lark-auth-permissions", started, completed.returncode, completed.stdout, completed.stderr)
    except Exception as exc:
        auth_raw = _completed_result("lark-auth-permissions", started, 1, "", str(exc))

    # Define expected scopes
    expected_scopes = [
        "contact:user.base:readonly",
        "im:message:readonly",
        "im:message:send_as_bot",
        "im:chat:readonly",
        "drive:drive:readonly",
    ]

    # Parse stdout for scope info
    stdout_lower = (auth_raw.get("stdout") or "").lower()
    scopes = []
    for scope in expected_scopes:
        scope_short = scope.split(":")[-2] if ":" in scope else scope
        found = scope_short in stdout_lower or scope.split(":")[0] in stdout_lower
        scopes.append({
            "scope": scope,
            "granted": found,
        })

    return {
        "authenticated": auth_raw.get("ok", False),
        "scopes": scopes,
        "missingScopes": [s["scope"] for s in scopes if not s["granted"]],
        "authDetail": auth_raw.get("stdout", ""),
        "authError": auth_raw.get("stderr", ""),
        "suggestion": "请运行 `lark-cli auth login` 重新授权，确保所有必需 scope 已勾选。" if not auth_raw.get("ok") else "",
        "durationMs": auth_raw.get("duration_ms", 0),
    }


# ---------------------------------------------------------------------------
# POST /api/feishu/connection/refresh
# ---------------------------------------------------------------------------

def refresh_connection(config: StackConfig | None = None) -> dict[str, Any]:
    """Manually trigger Lark auth refresh."""
    cfg = config or load_config()
    started = time.monotonic()
    env = os.environ.copy()
    env["OPENCLAW_HOME"] = ""
    env["CLAW_HOME"] = ""
    try:
        completed = run_capture(
            [str(cfg.lark_cli_bin), "auth", "login", "--force"],
            cwd=cfg.stack_root,
            env=env,
            timeout=120,
        )
        result = _completed_result("lark-auth-refresh", started, completed.returncode, completed.stdout, completed.stderr)
    except Exception as exc:
        result = _completed_result("lark-auth-refresh", started, 1, "", str(exc))

    return {
        "ok": result.get("ok", False),
        "message": "认证刷新成功" if result.get("ok") else "认证刷新失败",
        "stdout": result.get("stdout", ""),
        "stderr": result.get("stderr", ""),
        "durationMs": result.get("duration_ms", 0),
    }
