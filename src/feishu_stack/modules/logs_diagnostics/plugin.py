from __future__ import annotations

from fastapi import APIRouter
from feishu_stack.plugin_sdk import AccPlugin, PluginCard
import asyncio
import logging
from pathlib import Path
from fastapi import Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from . import explanations
from feishu_stack.modules.logs_diagnostics import diagnostics as diagnostics_module
from feishu_stack.core.settings import load_config
from feishu_stack.core.logs import tail
from feishu_stack.core import codex_streams
from feishu_stack.core.models import to_dict
from feishu_stack.api.security import require_control_token

LOGS_TAG = "Logs"
DIAGNOSTICS_TAG = "Diagnostics"
logger = logging.getLogger(__name__)
LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
router = APIRouter()

class LogLevelSetRequest(BaseModel):
    logger: str = "root"
    level: str


@router.websocket("/ws/codex-agent/stream")
async def ws_codex_agent_stream(ws: WebSocket, run_id: str = "latest") -> None:
    await ws.accept()
    sent_count = 0
    active_path: Path | None = None
    try:
        while True:
            cfg = load_config()
            payload = codex_streams.read_stream(cfg, run_id)
            if payload is None:
                await ws.send_json({"type": "heartbeat", "run_id": run_id, "events": []})
                await asyncio.sleep(1)
                continue
            path = Path(payload["path"])
            events = payload["events"]
            if active_path != path:
                active_path = path
                sent_count = 0
            for event in events[sent_count:]:
                await ws.send_json({"type": "event", "run_id": payload["run_id"], "event": event})
            sent_count = len(events)
            await asyncio.sleep(0.75)
    except WebSocketDisconnect:
        return
    except Exception:
        logger.exception("Codex stream WebSocket failed")
        try:
            await ws.close()
        except Exception:
            pass


@router.get(
    "/api/logs/level",
    summary="Get log level",
    description="Return the current log level for a given logger name.",
    tags=[LOGS_TAG],
)
def get_log_level(logger: str = "root") -> dict:
    log = logging.getLogger(logger)
    level_name = logging.getLevelName(log.getEffectiveLevel())
    return {"logger": logger, "level": level_name}


@router.post(
    "/api/logs/level",
    summary="Set log level",
    description="Set the log level for a given logger. Requires a valid control token.",
    tags=[LOGS_TAG],
    dependencies=[Depends(require_control_token)],
)
def set_log_level(request: LogLevelSetRequest) -> dict:
    level_upper = request.level.upper()
    if level_upper not in LOG_LEVELS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid level '{request.level}'. Must be one of: {', '.join(LOG_LEVELS)}",
        )
    log = logging.getLogger(request.logger)
    log.setLevel(getattr(logging, level_upper))
    return {"logger": request.logger, "level": level_upper}


@router.get(
    "/api/logs/{component}",
    summary="Tail component logs",
    description="Return the last N lines of log files for a given component.",
    tags=[LOGS_TAG],
)
def logs(component: str, lines: int = 120) -> dict:
    cfg = load_config()
    if component == "codex-desktop":
        from feishu_stack.modules.model_provider import codex_desktop

        codex_desktop.log(cfg)
    table = {
        "openclaw": [cfg.openclaw_stdout_log, cfg.openclaw_stderr_log],
        "codex-agent": [cfg.codex_agent_stdout_log, cfg.codex_agent_stderr_log],
        "codex-desktop": [cfg.log_dir / "codex-desktop-status.log"],
        "control-center-api": [cfg.log_dir / "control-center-api-out.log", cfg.log_dir / "control-center-api-err.log"],
        "operations": [cfg.log_dir / "operations.jsonl"],
    }
    if component.startswith("local-tool:"):
        from feishu_stack.modules.local_tools import registry as local_tools

        tool_id = component.split(":", 1)[1]
        try:
            local_tools.get_tool_status(tool_id, cfg)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"Unknown local tool: {tool_id}") from exc
        table[component] = [cfg.local_tool_stdout_log(tool_id), cfg.local_tool_stderr_log(tool_id)]
    if component not in table:
        raise HTTPException(status_code=404, detail=f"Unknown log component: {component}")
    return {"component": component, "logs": [to_dict(tail(path, lines)) for path in table[component]]}


@router.get(
    "/api/codex-agent/streams",
    summary="List Codex Agent streams",
    description="Return recent Codex Agent subprocess stream runs.",
    tags=[LOGS_TAG],
)
def codex_agent_streams(limit: int = 20) -> dict:
    cfg = load_config()
    return {"streams": codex_streams.list_streams(cfg, limit=limit)}


@router.get(
    "/api/codex-agent/streams/{run_id}",
    summary="Read a Codex Agent stream",
    description="Return recorded JSONL events for a Codex Agent subprocess stream.",
    tags=[LOGS_TAG],
)
def codex_agent_stream(run_id: str) -> dict:
    cfg = load_config()
    payload = codex_streams.read_stream(cfg, run_id)
    if payload is None:
        raise HTTPException(status_code=404, detail=f"Unknown Codex Agent stream: {run_id}")
    return payload


@router.get(
    "/api/doctor/codex",
    summary="Codex doctor",
    description="Run the codex doctor diagnostic and return results.",
    tags=[DIAGNOSTICS_TAG],
)
def codex_doctor() -> dict:
    return diagnostics_module.codex_doctor()


@router.get(
    "/api/deepseek/env-status",
    summary="DeepSeek environment status",
    description="Check whether the configured DeepSeek API key environment variable is visible.",
    tags=[DIAGNOSTICS_TAG],
)
def deepseek_env_status() -> dict:
    return diagnostics_module.deepseek_env_status()


@router.get(
    "/api/lark/auth-status",
    summary="Lark auth status",
    description="Check the current lark-cli authentication status.",
    tags=[DIAGNOSTICS_TAG],
)
def lark_auth_status() -> dict:
    return diagnostics_module.lark_auth_status()


@router.get(
    "/api/diagnostics",
    summary="Full diagnostics",
    description="Run all diagnostics checks and return a comprehensive report.",
    tags=[DIAGNOSTICS_TAG],
)
def diagnostics() -> dict:
    return to_dict(diagnostics_module.diagnostics())


@router.get(
    "/api/diagnostics/explained",
    summary="Explained diagnostics",
    description="Return Chinese, action-oriented diagnostics for the command dashboard.",
    tags=[DIAGNOSTICS_TAG],
)
def explained_diagnostics() -> dict:
    return {"items": to_dict(explanations.explained_diagnostics())}

from feishu_stack.plugins.builtin_descriptors import create_logs_diagnostics_plugin as create_plugin
