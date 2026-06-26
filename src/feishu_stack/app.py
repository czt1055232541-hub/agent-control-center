from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
from pydantic import BaseModel

from . import (
    backups,
    codex_agent,
    codex_desktop,
    codex_provider,
    metrics,
    moonbridge,
    openclaw,
    stack_actions,
    thread_migration,
)
from . import diagnostics as diagnostics_module
from .config import StackConfig, load_config
from .logs import tail
from .models import ErrorResponse, OperationResult, ThreadMigrationResult, to_dict
from .operations import recent_operations, run_exclusive
from .security import get_or_create_token, require_control_token
from .status import get_status

from . import __version__  # noqa: F401

# ---------------------------------------------------------------------------
# Tag definitions for /docs
# ---------------------------------------------------------------------------
HEALTH_TAG = "Health"
STATUS_TAG = "Status"
OPERATIONS_TAG = "Operations"
LOGS_TAG = "Logs"
METRICS_TAG = "Metrics"
DIAGNOSTICS_TAG = "Diagnostics"
THREAD_MIGRATION_TAG = "Thread Migration"


_main_loop: asyncio.AbstractEventLoop | None = None

@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield


app = FastAPI(
    title="Feishu Codex Stack Control Center",
    description="Control center API for managing the Feishu Codex agent stack: "
    "start/stop/restart components, view status, tail logs, run diagnostics, "
    "and migrate threads between providers.",
    version=__version__,
    lifespan=lifespan,
    openapi_tags=[
        {"name": HEALTH_TAG, "description": "Health check and session endpoints"},
        {"name": STATUS_TAG, "description": "Stack status and recent operations"},
        {"name": OPERATIONS_TAG, "description": "Start / stop / restart stack components"},
        {"name": LOGS_TAG, "description": "Log level management and log tailing"},
        {"name": METRICS_TAG, "description": "Prometheus metrics endpoint"},
        {"name": DIAGNOSTICS_TAG, "description": "Debugging and diagnostics tools"},
        {"name": THREAD_MIGRATION_TAG, "description": "Cross-provider thread migration"},
    ],
)

# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class ThreadMigrationRequest(BaseModel):
    session_id: str
    target_provider: str
    prompt: str = thread_migration.DEFAULT_CONTINUATION_PROMPT


class ThreadMigrationFolderRequest(BaseModel):
    summary_path: str


class LogLevelSetRequest(BaseModel):
    logger: str = "root"
    level: str


class MoonBridgeModelSwitchRequest(BaseModel):
    model: str


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _run(component: str, action: str, fn: Callable[[StackConfig], OperationResult]) -> dict:
    result = to_dict(run_exclusive(component, action, fn))
    if _main_loop is not None:
        asyncio.run_coroutine_threadsafe(ws_manager.broadcast_status(), _main_loop)
    return result


# ---------------------------------------------------------------------------
# WebSocket connection manager
# ---------------------------------------------------------------------------


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.append(ws)
        try:
            await ws.send_json(to_dict(get_status()))
        except Exception:
            pass

    def disconnect(self, ws: WebSocket) -> None:
        try:
            self._connections.remove(ws)
        except ValueError:
            pass

    async def broadcast_status(self) -> None:
        if not self._connections:
            return
        metrics.set_ws_connections(len(self._connections))
        payload = to_dict(get_status())
        stale: list[WebSocket] = []
        for ws in self._connections:
            try:
                await ws.send_json(payload)
            except Exception:
                stale.append(ws)
        for ws in stale:
            self.disconnect(ws)


ws_manager = ConnectionManager()

LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


# ---------------------------------------------------------------------------
# Prometheus metrics middleware
# ---------------------------------------------------------------------------


@app.middleware("http")
async def metrics_middleware(request, call_next):
    start = time.monotonic()
    response = await call_next(request)
    duration = time.monotonic() - start
    metrics.record_api_request(
        endpoint=request.url.path,
        method=request.method,
        status_code=response.status_code,
        duration=duration,
    )
    return response


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


@app.get(
    "/metrics",
    summary="Prometheus metrics",
    description="Expose Prometheus-format metrics for http_requests_total, "
    "http_request_duration_seconds, agent_status, and acc_* metrics.",
    tags=[METRICS_TAG],
    response_class=Response,
)
def prometheus_metrics():
    return Response(
        content=metrics.render_metrics(),
        media_type="text/plain; charset=utf-8",
    )

# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------


@app.websocket("/ws/status")
async def ws_status(ws: WebSocket) -> None:
    await ws_manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get(
    "/api/session",
    summary="Session info",
    description="Return the control token, stack root path, and API base URL.",
    tags=[HEALTH_TAG],
)
def session() -> dict:
    cfg = load_config()
    return {
        "token": get_or_create_token(cfg),
        "stack_root": str(cfg.stack_root),
        "api_base": "/api",
    }


@app.get(
    "/api/health",
    summary="Health check",
    description="Return the current service status, timestamp, and version.",
    tags=[HEALTH_TAG],
)
def health() -> dict:
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": __version__,
    }

# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------


@app.get(
    "/api/status",
    summary="Stack status",
    description="Return the full stack status: openclaw, moonbridge, codex-agent, "
    "codex-desktop, and provider info.",
    tags=[STATUS_TAG],
)
def status() -> dict:
    return to_dict(get_status())


@app.get(
    "/api/operations",
    summary="Recent operations",
    description="Return the most recent control operations and their outcomes.",
    tags=[STATUS_TAG],
)
def operations() -> dict:
    return {"operations": to_dict(recent_operations())}


# ---------------------------------------------------------------------------
# Logs
# ---------------------------------------------------------------------------


@app.get(
    "/api/logs/level",
    summary="Get log level",
    description="Return the current log level for a given logger name.",
    tags=[LOGS_TAG],
)
def get_log_level(logger: str = "root") -> dict:
    log = logging.getLogger(logger)
    level_name = logging.getLevelName(log.getEffectiveLevel())
    return {"logger": logger, "level": level_name}


@app.post(
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


@app.get(
    "/api/logs/{component}",
    summary="Tail component logs",
    description="Return the last N lines of log files for a given component.",
    tags=[LOGS_TAG],
)
def logs(component: str, lines: int = 120) -> dict:
    cfg = load_config()
    if component == "codex-desktop":
        codex_desktop.log(cfg)
    table = {
        "openclaw": [cfg.openclaw_stdout_log, cfg.openclaw_stderr_log],
        "moonbridge": [cfg.moonbridge_stdout_log, cfg.moonbridge_stderr_log],
        "codex-agent": [cfg.codex_agent_stdout_log, cfg.codex_agent_stderr_log],
        "codex-desktop": [cfg.log_dir / "codex-desktop-status.log"],
        "control-center-api": [cfg.log_dir / "control-center-api-out.log", cfg.log_dir / "control-center-api-err.log"],
        "operations": [cfg.log_dir / "operations.jsonl"],
    }
    if component not in table:
        raise HTTPException(status_code=404, detail=f"Unknown log component: {component}")
    return {"component": component, "logs": [to_dict(tail(path, lines)) for path in table[component]]}

# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------


@app.get(
    "/api/doctor/codex",
    summary="Codex doctor",
    description="Run the codex doctor diagnostic and return results.",
    tags=[DIAGNOSTICS_TAG],
)
def codex_doctor() -> dict:
    return diagnostics_module.codex_doctor()


@app.get(
    "/api/moonbridge/models",
    summary="Moonbridge models",
    description="Query the moonbridge endpoint for available models.",
    tags=[DIAGNOSTICS_TAG],
)
def moonbridge_models() -> dict:
    return diagnostics_module.moonbridge_models()


@app.get(
    "/api/lark/auth-status",
    summary="Lark auth status",
    description="Check the current lark-cli authentication status.",
    tags=[DIAGNOSTICS_TAG],
)
def lark_auth_status() -> dict:
    return diagnostics_module.lark_auth_status()


@app.get(
    "/api/diagnostics",
    summary="Full diagnostics",
    description="Run all diagnostics checks and return a comprehensive report.",
    tags=[DIAGNOSTICS_TAG],
)
def diagnostics() -> dict:
    return to_dict(diagnostics_module.diagnostics())

# ---------------------------------------------------------------------------
# Thread migration
# ---------------------------------------------------------------------------


@app.get(
    "/api/thread-migration/threads",
    summary="List recent threads",
    description="List recent codex sessions available for thread migration.",
    tags=[THREAD_MIGRATION_TAG],
)
def thread_migration_threads(limit: int = 20) -> dict:
    return {"threads": to_dict(thread_migration.list_recent_threads(limit=limit))}


@app.post(
    "/api/thread-migration/migrate",
    summary="Migrate thread",
    description="Migrate a codex session from one provider to another.",
    tags=[THREAD_MIGRATION_TAG],
    dependencies=[Depends(require_control_token)],
)
def migrate_thread(request: ThreadMigrationRequest) -> dict:
    return _run(
        "thread-migration",
        "migrate",
        lambda cfg: thread_migration.migrate_thread(
            request.session_id,
            request.target_provider,
            request.prompt,
            cfg,
        ),
    )


@app.post(
    "/api/thread-migration/open-summary-folder",
    summary="Open summary folder",
    description="Open the summary folder for a thread migration in the file explorer.",
    tags=[THREAD_MIGRATION_TAG],
    dependencies=[Depends(require_control_token)],
)
def open_thread_migration_summary_folder(request: ThreadMigrationFolderRequest) -> dict:
    return _run(
        "thread-migration",
        "open-summary-folder",
        lambda _cfg: thread_migration.open_summary_folder(request.summary_path),
    )

# ---------------------------------------------------------------------------
# Operations - OpenClaw
# ---------------------------------------------------------------------------

@app.post("/api/openclaw/start", summary="Start OpenClaw", description="Start the OpenClaw gateway service.", tags=[OPERATIONS_TAG], dependencies=[Depends(require_control_token)])
def start_openclaw() -> dict:
    return _run("openclaw", "start", openclaw.start)

@app.post("/api/openclaw/stop", summary="Stop OpenClaw", description="Stop the OpenClaw gateway service.", tags=[OPERATIONS_TAG], dependencies=[Depends(require_control_token)])
def stop_openclaw() -> dict:
    return _run("openclaw", "stop", openclaw.stop)

@app.post("/api/openclaw/restart", summary="Restart OpenClaw", description="Restart the OpenClaw gateway service.", tags=[OPERATIONS_TAG], dependencies=[Depends(require_control_token)])
def restart_openclaw() -> dict:
    return _run("openclaw", "restart", openclaw.restart)

@app.post("/api/openclaw/open-ui", summary="Open OpenClaw UI", description="Open the OpenClaw web UI in the default browser.", tags=[OPERATIONS_TAG], dependencies=[Depends(require_control_token)])
def open_openclaw_ui() -> dict:
    return _run("openclaw", "open-ui", openclaw.open_ui)

# ---------------------------------------------------------------------------
# Operations - MoonBridge
# ---------------------------------------------------------------------------

@app.post("/api/moonbridge/start", summary="Start MoonBridge", description="Start the MoonBridge API proxy service.", tags=[OPERATIONS_TAG], dependencies=[Depends(require_control_token)])
def start_moonbridge() -> dict:
    return _run("moonbridge", "start", moonbridge.start)

@app.post("/api/moonbridge/stop", summary="Stop MoonBridge", description="Stop the MoonBridge API proxy service.", tags=[OPERATIONS_TAG], dependencies=[Depends(require_control_token)])
def stop_moonbridge() -> dict:
    return _run("moonbridge", "stop", moonbridge.stop)

@app.post("/api/moonbridge/restart", summary="Restart MoonBridge", description="Restart the MoonBridge API proxy service.", tags=[OPERATIONS_TAG], dependencies=[Depends(require_control_token)])
def restart_moonbridge() -> dict:
    return _run("moonbridge", "restart", moonbridge.restart)

@app.get("/api/moonbridge/available-models", summary="Available MoonBridge models", description="Return the list of available moonbridge models.", tags=[OPERATIONS_TAG])
def available_moonbridge_models() -> dict:
    models = moonbridge.get_available_models()
    return {"models": models}

@app.post("/api/moonbridge/model/switch", summary="Switch MoonBridge model", description="Switch the active model used by MoonBridge.", tags=[OPERATIONS_TAG], dependencies=[Depends(require_control_token)])
def switch_moonbridge_model(request: MoonBridgeModelSwitchRequest) -> dict:
    return _run("moonbridge", "switch-model", lambda cfg: moonbridge.switch_model(request.model, cfg))

# ---------------------------------------------------------------------------
# Operations - Codex Agent
# ---------------------------------------------------------------------------

@app.post("/api/codex-agent/start", summary="Start Codex Agent", description="Start the codex-agent service.", tags=[OPERATIONS_TAG], dependencies=[Depends(require_control_token)])
def start_codex_agent() -> dict:
    return _run("codex-agent", "start", codex_agent.start)

@app.post("/api/codex-agent/stop", summary="Stop Codex Agent", description="Stop the codex-agent service.", tags=[OPERATIONS_TAG], dependencies=[Depends(require_control_token)])
def stop_codex_agent() -> dict:
    return _run("codex-agent", "stop", codex_agent.stop)

@app.post("/api/codex-agent/restart", summary="Restart Codex Agent", description="Restart the codex-agent service.", tags=[OPERATIONS_TAG], dependencies=[Depends(require_control_token)])
def restart_codex_agent() -> dict:
    return _run("codex-agent", "restart", codex_agent.restart)

# ---------------------------------------------------------------------------
# Operations - Codex Desktop
# ---------------------------------------------------------------------------

@app.post("/api/codex-desktop/start", summary="Start Codex Desktop", description="Start the Codex Desktop application.", tags=[OPERATIONS_TAG], dependencies=[Depends(require_control_token)])
def start_codex_desktop() -> dict:
    return _run("codex-desktop", "start", codex_desktop.start)

@app.post("/api/codex-desktop/stop", summary="Stop Codex Desktop", description="Stop the Codex Desktop application.", tags=[OPERATIONS_TAG], dependencies=[Depends(require_control_token)])
def stop_codex_desktop() -> dict:
    return _run("codex-desktop", "stop", codex_desktop.stop)

@app.post("/api/codex-desktop/restart", summary="Restart Codex Desktop", description="Restart the Codex Desktop application.", tags=[OPERATIONS_TAG], dependencies=[Depends(require_control_token)])
def restart_codex_desktop() -> dict:
    return _run("codex-desktop", "restart", codex_desktop.restart)

# ---------------------------------------------------------------------------
# Operations - Provider switch
# ---------------------------------------------------------------------------

@app.post("/api/codex-provider/native", summary="Switch to native provider", description="Switch the codex provider to the native OpenAI backend.", tags=[OPERATIONS_TAG], dependencies=[Depends(require_control_token)])
def switch_native() -> dict:
    return _run("codex-provider", "switch-native", lambda cfg: codex_provider.switch_provider("native", cfg))

@app.post("/api/codex-provider/moonbridge", summary="Switch to MoonBridge provider", description="Switch the codex provider to the MoonBridge proxy backend.", tags=[OPERATIONS_TAG], dependencies=[Depends(require_control_token)])
def switch_moonbridge() -> dict:
    return _run("codex-provider", "switch-moonbridge", lambda cfg: codex_provider.switch_provider("moonbridge", cfg))

# ---------------------------------------------------------------------------
# Operations - Stack (orchestrated)
# ---------------------------------------------------------------------------

@app.post("/api/stack/start-native", summary="Start stack (native)", description="Start the full stack using the native OpenAI provider.", tags=[OPERATIONS_TAG], dependencies=[Depends(require_control_token)])
def stack_start_native() -> dict:
    return _run("stack", "start-native", stack_actions.start_native)

@app.post("/api/stack/start-moonbridge", summary="Start stack (MoonBridge)", description="Start the full stack using the MoonBridge proxy provider.", tags=[OPERATIONS_TAG], dependencies=[Depends(require_control_token)])
def stack_start_moonbridge() -> dict:
    return _run("stack", "start-moonbridge", stack_actions.start_moonbridge)

@app.post("/api/stack/stop", summary="Stop stack", description="Stop all stack components (openclaw, moonbridge, codex-agent).", tags=[OPERATIONS_TAG], dependencies=[Depends(require_control_token)])
def stack_stop() -> dict:
    return _run("stack", "stop", stack_actions.stop)

# ---------------------------------------------------------------------------
# Operations - Maintenance
# ---------------------------------------------------------------------------

@app.post("/api/backups/clean", summary="Clean backups", description="Remove old backup files per retention policy.", tags=[OPERATIONS_TAG], dependencies=[Depends(require_control_token)])
def clean_backups() -> dict:
    return _run("backups", "clean", backups.clean)

# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(error_code=f"HTTP_{exc.status_code}", message=exc.detail if isinstance(exc.detail, str) else str(exc.detail)).model_dump(),
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(error_code="VALIDATION_ERROR", message="Request validation failed", detail=[{"loc": e["loc"], "msg": e["msg"]} for e in exc.errors()]).model_dump(),
    )

# ---------------------------------------------------------------------------
# Frontend static files (must be last)
# ---------------------------------------------------------------------------

web_dist = Path(__file__).resolve().parents[2] / "web" / "dist"
if web_dist.exists():
    assets_dir = web_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str) -> FileResponse:
        target = web_dist / path
        if path and target.exists() and target.is_file():
            return FileResponse(target)
        return FileResponse(web_dist / "index.html")
