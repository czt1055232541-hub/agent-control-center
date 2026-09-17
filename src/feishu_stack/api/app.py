from __future__ import annotations

import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from fastapi import Depends, FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse

from feishu_stack.core import metrics
from feishu_stack.modules.operations import control_center
from feishu_stack.core.settings import StackConfig, find_stack_root, load_config
from feishu_stack.core.models import ErrorResponse, OperationResult, to_dict
from feishu_stack.core.operations import run_exclusive
from .security import get_or_create_token, require_control_token
from feishu_stack.core.status import get_status
from feishu_stack import __version__  # noqa: F401
from feishu_stack.plugins import create_plugin_router, get_plugin_registry

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
DASHBOARD_TAG = "Dashboard"
TASK_BATTLEFIELD_TAG = "Task Battlefield"
SKILL_WORKSHOP_TAG = "Skill Workshop"
CONFIG_CENTER_TAG = "Config Center"
ROUTING_RULES_TAG = "Routing Rules"
FEISHU_CONNECTION_TAG = "Feishu Connection"
LOCAL_TOOLS_TAG = "Local Tools"


_main_loop: asyncio.AbstractEventLoop | None = None
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(_app: FastAPI):
    async with get_plugin_registry().lifespan(_app):
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
        {"name": DASHBOARD_TAG, "description": "Read-only command dashboard aggregates"},
        {"name": TASK_BATTLEFIELD_TAG, "description": "Task battlefield directory and project workspace mapping"},
        {"name": THREAD_MIGRATION_TAG, "description": "Cross-provider thread migration"},
        {"name": SKILL_WORKSHOP_TAG, "description": "Skill tree workshop — scan, drift, and compare skills"},
        {"name": CONFIG_CENTER_TAG, "description": "Config center CRUD and import/export endpoints"},
        {"name": ROUTING_RULES_TAG, "description": "Routing rules CRUD and batch import endpoints"},
        {"name": FEISHU_CONNECTION_TAG, "description": "Feishu/Lark connection status, accounts, permissions, and auth refresh"},
        {"name": LOCAL_TOOLS_TAG, "description": "Registry and process control for local embedded tools"},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^http://(127\.0\.0\.1|localhost)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# The framework inventory is the stable discovery surface for ACC's own Web
# client and external hosts. Existing feature routes remain in this module
# during their compatibility-preserving migration into native plugins.
app.include_router(create_plugin_router())

# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------
























# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _run(component: str, action: str, fn: Callable[[StackConfig], OperationResult]) -> dict:
    result = to_dict(run_exclusive(component, action, fn))
    if _main_loop is not None:
        asyncio.run_coroutine_threadsafe(ws_manager.broadcast_status(), _main_loop)
    return result


app.state.operation_runner = _run


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
    supplied_request_id = request.headers.get("X-Request-ID", "").strip()
    request_id = supplied_request_id if supplied_request_id and len(supplied_request_id) <= 128 else uuid.uuid4().hex
    request.state.request_id = request_id
    start = time.monotonic()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
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
    if not any(plugin.id == "acc.dashboard" for plugin in get_plugin_registry().resolve()):
        await ws.close(code=1008, reason="Dashboard plugin is disabled")
        return
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

















































# ---------------------------------------------------------------------------
# Logs
# ---------------------------------------------------------------------------











# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------











# ---------------------------------------------------------------------------
# Skill Workshop helpers
# ---------------------------------------------------------------------------








# ---------------------------------------------------------------------------
# Skill Workshop
# ---------------------------------------------------------------------------


































# ---------------------------------------------------------------------------
# Thread migration
# ---------------------------------------------------------------------------







# ---------------------------------------------------------------------------
# Operations - OpenClaw
# ---------------------------------------------------------------------------






# ---------------------------------------------------------------------------
# Operations - Codex Agent
# ---------------------------------------------------------------------------




# ---------------------------------------------------------------------------
# Operations - Codex Desktop
# ---------------------------------------------------------------------------




# ---------------------------------------------------------------------------
# Operations - Provider switch
# ---------------------------------------------------------------------------










# ---------------------------------------------------------------------------
# Operations - Stack (orchestrated)
# ---------------------------------------------------------------------------




# ---------------------------------------------------------------------------
# Operations - Maintenance
# ---------------------------------------------------------------------------





@app.post(
    "/api/control-center/shutdown",
    summary="Shutdown Control Center",
    description="Close Control Center API/launcher processes only. OpenClaw and Codex processes are excluded. Requires control token.",
    tags=[OPERATIONS_TAG],
    dependencies=[Depends(require_control_token)],
)
def shutdown_control_center() -> dict:
    return to_dict(control_center.request_shutdown())


# Mount independently defined feature contributions before the SPA fallback.
get_plugin_registry().mount(app)

# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    request_id = getattr(request.state, "request_id", None)
    detail = exc.detail
    if isinstance(detail, dict):
        message = str(detail.get("message") or detail.get("error") or "Request failed")
        error_code = str(detail.get("error_code") or f"HTTP_{exc.status_code}")
        structured_detail = detail
    else:
        message = str(detail)
        error_code = f"HTTP_{exc.status_code}"
        structured_detail = None
    logger.warning(
        "request_failed request_id=%s method=%s path=%s status=%s code=%s",
        request_id,
        request.method,
        request.url.path,
        exc.status_code,
        error_code,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(error_code=error_code, message=message, detail=structured_detail, request_id=request_id).model_dump(),
        headers={"X-Request-ID": request_id} if request_id else None,
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(error_code="VALIDATION_ERROR", message="Request validation failed", detail=[{"loc": e["loc"], "msg": e["msg"]} for e in exc.errors()], request_id=request_id).model_dump(),
        headers={"X-Request-ID": request_id} if request_id else None,
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", None)
    logger.exception(
        "unhandled_request_error request_id=%s method=%s path=%s",
        request_id,
        request.method,
        request.url.path,
    )
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error_code="INTERNAL_SERVER_ERROR",
            message="Internal server error",
            request_id=request_id,
        ).model_dump(),
        headers={"X-Request-ID": request_id} if request_id else None,
    )

# ---------------------------------------------------------------------------
# Frontend static files (must be last)
# ---------------------------------------------------------------------------

web_dist = find_stack_root(Path(__file__)) / "web" / "dist"
if web_dist.exists():
    assets_dir = web_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str) -> FileResponse:
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        target = web_dist / path
        if path and target.exists() and target.is_file():
            return FileResponse(target)
        return FileResponse(web_dist / "index.html")
