from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from fastapi import Body, Depends, FastAPI, HTTPException, Query, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
from pydantic import BaseModel

from feishu_stack.modules.agent_array.skill_tree import agent_config_editor, agent_dashboard, skill_baseline, skill_registry, skill_drift, tree_config
from feishu_stack.modules.backup_migration import thread_migration
from feishu_stack.modules.model_provider import codex_agent, codex_desktop, provider_switch
from feishu_stack.modules.model_provider import moonbridge
from feishu_stack.modules.model_provider import openclaw_gateway as openclaw
from feishu_stack.modules.backup_migration import backups
from feishu_stack.modules.logs_diagnostics import metrics
from feishu_stack.modules.operations import control_center, stack_actions
from feishu_stack.modules.logs_diagnostics import diagnostics as diagnostics_module
from feishu_stack.modules.task_battlefield import task_directory, watchdog
from feishu_stack.core.settings import StackConfig, find_stack_root, load_config
from feishu_stack.core.logs import tail
from feishu_stack.core.models import ErrorResponse, OperationResult, ThreadMigrationResult, to_dict
from feishu_stack.modules.operations.operations import recent_operations, run_exclusive
from .security import get_or_create_token, require_control_token
from feishu_stack.core.status import get_status
from feishu_stack import __version__  # noqa: F401

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
        {"name": DASHBOARD_TAG, "description": "Read-only command dashboard aggregates"},
        {"name": TASK_BATTLEFIELD_TAG, "description": "Task battlefield directory and project workspace mapping"},
        {"name": THREAD_MIGRATION_TAG, "description": "Cross-provider thread migration"},
        {"name": SKILL_WORKSHOP_TAG, "description": "Skill tree workshop — scan, drift, and compare skills"},
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
    reasoning_effort: str | None = None


class AgentEditableConfigUpdateRequest(BaseModel):
    values: dict


class TaskDirectoryTaskRequest(BaseModel):
    taskId: str | None = None
    title: str | None = None
    parentProjectId: str | None = None
    parentProjectName: str | None = None
    workspacePath: str | None = None
    status: str | None = None
    phase: str | None = None
    assignee: str | None = None
    tags: list[str] | None = None
    source: str | None = None


class TaskClassifyRequest(BaseModel):
    description: str
    workspacePath: str | None = None


class SkillBaselineConfirmRequest(BaseModel):
    confirmText: str
    confirmedBy: str = "manual"


class SkillSnapshotRequest(BaseModel):
    confirmText: str
    createdBy: str = "manual"


class SkillRollbackRequest(BaseModel):
    confirmText: str
    confirmedBy: str = "manual"


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


@app.get(
    "/api/dashboard/summary",
    summary="Dashboard summary",
    description="Return the command dashboard top-level health and activity counters.",
    tags=[DASHBOARD_TAG],
)
def dashboard_summary() -> dict:
    return to_dict(agent_dashboard.dashboard_summary())


@app.get(
    "/api/agents",
    summary="Agent inventory",
    description="Return the v1 read-only agent inventory used by the command dashboard.",
    tags=[DASHBOARD_TAG],
)
def agents() -> dict:
    return {"agents": to_dict(agent_dashboard.list_agents())}


@app.get(
    "/api/infrastructure",
    summary="Infrastructure inventory",
    description="Return the real backend services that carry the agent roles.",
    tags=[DASHBOARD_TAG],
)
def infrastructure() -> dict:
    return {"agents": to_dict(agent_dashboard.list_infrastructure())}


@app.get(
    "/api/watchdog/current",
    summary="Current watchdog",
    description="Return the single active Feishu scheduler watchdog used by the dashboard card.",
    tags=[DASHBOARD_TAG],
)
def current_watchdog() -> dict:
    return to_dict(watchdog.current_watchdog())


@app.get(
    "/api/task-battlefield/directory",
    summary="Task battlefield directory",
    description="Return the task directory mapped to the Feishu agent projects workspace.",
    tags=[TASK_BATTLEFIELD_TAG],
)
def task_battlefield_directory() -> dict:
    return task_directory.load_directory()


@app.post(
    "/api/task-battlefield/tasks",
    summary="Add task directory entry",
    description="Add a manual task entry and workspace path. Requires control token.",
    tags=[TASK_BATTLEFIELD_TAG],
    dependencies=[Depends(require_control_token)],
)
def add_task_battlefield_task(request: TaskDirectoryTaskRequest) -> dict:
    try:
        return task_directory.add_task(request.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.put(
    "/api/task-battlefield/tasks/{task_id}",
    summary="Update task directory entry",
    description="Update task metadata or workspace path. Requires control token.",
    tags=[TASK_BATTLEFIELD_TAG],
    dependencies=[Depends(require_control_token)],
)
def update_task_battlefield_task(task_id: str, request: TaskDirectoryTaskRequest) -> dict:
    try:
        return task_directory.update_task(task_id, request.model_dump(exclude_none=True))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown task: {task_id}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete(
    "/api/task-battlefield/tasks/{task_id}",
    summary="Delete task directory entry",
    description="Hide a task entry from the directory. This does not delete the workspace folder. Requires control token.",
    tags=[TASK_BATTLEFIELD_TAG],
    dependencies=[Depends(require_control_token)],
)
def delete_task_battlefield_task(task_id: str) -> dict:
    try:
        return task_directory.delete_task(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown task: {task_id}") from exc


@app.post(
    "/api/task-battlefield/classify",
    summary="Classify task description",
    description="Suggest whether a task belongs to an existing parent project or needs a new workspace.",
    tags=[TASK_BATTLEFIELD_TAG],
)
def classify_task_battlefield_task(request: TaskClassifyRequest) -> dict:
    return task_directory.classify_task(request.description, request.workspacePath)


@app.get(
    "/api/agents/{agent_id}",
    summary="Agent detail",
    description="Return a single read-only agent configuration summary.",
    tags=[DASHBOARD_TAG],
)
def agent_detail(agent_id: str) -> dict:
    agent = agent_dashboard.get_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Unknown agent: {agent_id}")
    return to_dict(agent)


@app.get(
    "/api/agents/{agent_id}/editable-config",
    summary="Editable agent config",
    description="Return safe, editable configuration fields for a real agent.",
    tags=[DASHBOARD_TAG],
)
def agent_editable_config(agent_id: str) -> dict:
    try:
        return agent_config_editor.get_editable_config(agent_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get(
    "/api/agents/{agent_id}/config-preview",
    summary="Agent config preview",
    description="Return current safe config values and editing notes.",
    tags=[DASHBOARD_TAG],
)
def agent_config_preview(agent_id: str) -> dict:
    try:
        return agent_config_editor.preview_config(agent_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.put(
    "/api/agents/{agent_id}/editable-config",
    summary="Update editable agent config",
    description="Update whitelisted low-risk config fields. Requires control token.",
    tags=[DASHBOARD_TAG],
    dependencies=[Depends(require_control_token)],
)
def update_agent_editable_config(agent_id: str, request: AgentEditableConfigUpdateRequest) -> dict:
    try:
        return agent_config_editor.update_editable_config(agent_id, request.values)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post(
    "/api/agents/{agent_id}/config-backup",
    summary="Backup agent config",
    description="Create a backup for the editable config file. Requires control token.",
    tags=[DASHBOARD_TAG],
    dependencies=[Depends(require_control_token)],
)
def backup_agent_config(agent_id: str) -> dict:
    try:
        return agent_config_editor.backup_config(agent_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post(
    "/api/agents/{agent_id}/config-rollback-latest",
    summary="Rollback latest agent config backup",
    description="Restore the latest backup for the editable config file. Requires control token.",
    tags=[DASHBOARD_TAG],
    dependencies=[Depends(require_control_token)],
)
def rollback_agent_config(agent_id: str) -> dict:
    try:
        return agent_config_editor.rollback_latest(agent_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


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


@app.get(
    "/api/diagnostics/explained",
    summary="Explained diagnostics",
    description="Return Chinese, action-oriented diagnostics for the command dashboard.",
    tags=[DIAGNOSTICS_TAG],
)
def explained_diagnostics() -> dict:
    return {"items": to_dict(agent_dashboard.explained_diagnostics())}

# ---------------------------------------------------------------------------
# Skill Workshop helpers
# ---------------------------------------------------------------------------


def _to_workshop_skill(entry: skill_registry.SkillEntry, report: skill_drift.DriftReport | None = None) -> dict:
    """Transform a SkillEntry into the frontend SkillWorkshopSkill shape."""
    drift_status: str = "ok"
    drift_severity: str = "normal"
    drift_reasons: list[str] = []
    baseline_sha: str | None = None
    baseline_dir_sha: str | None = None
    baseline_version: str | None = None
    confirmed_at: str | None = None
    confirmed_by: str | None = None

    if report is not None:
        for d in report.drifts:
            raw = d.to_dict()
            if raw.get("details", {}).get("skillId") == entry.skill_id:
                drift_status = "drift" if d.severity in ("P0", "P1", "P2") else "no_baseline"
                drift_severity = {"P0": "critical", "P1": "warning", "P2": "warning", "info": "info"}.get(d.severity, "normal")
                drift_reasons.append(d.message)

    baseline_entry = _baseline_for_skill(entry.skill_id)
    if baseline_entry:
        baseline_info = baseline_entry.get("baseline", {})
        baseline_sha = baseline_info.get("skillMdSha256") or baseline_entry.get("version")
        baseline_dir_sha = baseline_info.get("directorySha256") or baseline_entry.get("dirHash")
        baseline_version = baseline_info.get("version") or baseline_entry.get("version")
        confirmed_at = baseline_info.get("confirmedAt")
        confirmed_by = baseline_info.get("confirmedBy")

    return {
        "skillId": entry.skill_id,
        "displayName": entry.name,
        "sourceAlias": entry.source_alias,
        "runtime": entry.source,
        "agentIds": entry.agent_visibility,
        "relativePath": entry.path,
        "loadPriority": 0,
        "updateMechanism": "manual",
        "actual": {
            "skillMdSha256": entry.version,
            "directorySha256": entry.dir_hash or "",
            "mtime": entry.mtime or "",
            "version": entry.version,
        },
        "baseline": {
            "skillMdSha256": baseline_sha or "",
            "directorySha256": baseline_dir_sha or "",
            "version": baseline_version or "",
            "confirmedAt": confirmed_at,
            "confirmedBy": confirmed_by,
        },
        "drift": {
            "status": drift_status,
            "severity": drift_severity,
            "reasons": drift_reasons,
        },
    }


def _baseline_for_skill(skill_id: str) -> dict | None:
    baseline = skill_baseline.load_baseline()
    if not baseline:
        return None
    for entry in baseline.get("skills", []):
        if isinstance(entry, dict) and entry.get("skillId") == skill_id:
            return entry
    return None


def _to_drift_report_dict(report: skill_drift.DriftReport, inventory: skill_registry.SkillInventory) -> dict:
    """Transform a DriftReport into the frontend SkillDriftReport shape."""
    items: list[dict] = []
    for d in report.drifts:
        raw = d.to_dict()
        sev = d.severity
        drift_status = "drift" if sev in ("P0", "P1", "P2") else "no_baseline"
        drift_severity = {"P0": "critical", "P1": "warning", "P2": "warning", "info": "info"}.get(sev, "normal")
        details = raw.get("details", {})
        actual_hash = details.get("actualVersion", details.get("version", ""))
        baseline_hash = details.get("baselineVersion")
        suggestion = details.get("recommendation", d.message)
        items.append({
            "skillId": raw.get("skillId", details.get("skillId", "")),
            "displayName": d.skill_name,
            "sourceAlias": d.source_alias,
            "runtime": d.source,
            "drift": {
                "status": drift_status,
                "severity": drift_severity,
                "reasons": [d.message],
            },
            "actualHash": actual_hash,
            "baselineHash": baseline_hash,
            "suggestion": suggestion,
        })
    return {
        "generatedAt": report.generated_at,
        "summary": {
            "totalSkills": inventory.total,
            "driftCount": report.total_drifts,
            "noBaselineCount": report.info_count,
            "p0Count": report.p0_count,
            "p1Count": report.p1_count,
            "p2Count": report.p2_count,
        },
        "items": items,
    }


# ---------------------------------------------------------------------------
# Skill Workshop
# ---------------------------------------------------------------------------


@app.get(
    "/api/skill-workshop/summary",
    summary="Skill workshop summary",
    description="Return skill counts, drift counts, P0/P1/P2, and last scan time.",
    tags=[SKILL_WORKSHOP_TAG],
)
def skill_workshop_summary() -> dict:
    inventory = skill_registry.get_inventory()
    report = skill_drift.detect_drift(inventory, baseline=skill_baseline.load_baseline())
    affected_agents = sorted(inventory.by_agent.keys()) if inventory.by_agent else []
    affected_runtimes = sorted(inventory.by_source.keys()) if inventory.by_source else []
    return {
        "totalSkills": inventory.total,
        "driftCount": report.total_drifts,
        "p0Count": report.p0_count,
        "p1Count": report.p1_count,
        "p2Count": report.p2_count,
        "lastScanTime": inventory.scan_metadata.scanned_at if inventory.scan_metadata else None,
        "affectedAgents": len(affected_agents),
        "affectedRuntimes": affected_runtimes,
    }


@app.get(
    "/api/skill-workshop/skills",
    summary="Skill inventory",
    description="Return the full skill inventory. Supports filtering by "
    "?agent_id=, ?runtime=, ?source=, ?status=.",
    tags=[SKILL_WORKSHOP_TAG],
)
def skill_workshop_skills(
    agent_id: str | None = None,
    runtime: str | None = None,
    source: str | None = None,
    status: str | None = None,
) -> dict:
    inventory = skill_registry.get_inventory()
    report = skill_drift.detect_drift(inventory, baseline=skill_baseline.load_baseline())
    skills = inventory.skills

    if agent_id:
        skills = [s for s in skills if agent_id in s.agent_visibility]
    if runtime:
        skills = [s for s in skills if s.source == runtime]
    if source:
        skills = [s for s in skills if s.source == source]
    if status:
        skills = [s for s in skills if s.status == status]

    return {
        "skills": [_to_workshop_skill(s, report) for s in skills],
        "total": len(skills),
        "totalInventory": inventory.total,
        "scanMetadata": inventory.scan_metadata.to_dict() if inventory.scan_metadata else None,
    }


@app.get(
    "/api/skill-workshop/tree-config",
    summary="Configured skill tree",
    description="Return the configured per-agent skill tree graph used by the integrated workshop page.",
    tags=[SKILL_WORKSHOP_TAG],
)
def skill_workshop_tree_config() -> dict:
    return tree_config.load_all_tree_configs()


@app.get(
    "/api/skill-workshop/tree-config/{agent_id}",
    summary="Configured agent skill tree",
    description="Return one configured agent skill tree graph.",
    tags=[SKILL_WORKSHOP_TAG],
)
def skill_workshop_agent_tree_config(agent_id: str) -> dict:
    try:
        return tree_config.load_agent_tree(agent_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown skill tree agent: {agent_id}") from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get(
    "/api/skill-workshop/skills/{skill_id}",
    summary="Skill detail",
    description="Return a single skill's details.",
    tags=[SKILL_WORKSHOP_TAG],
)
def skill_workshop_skill_detail(skill_id: str) -> dict:
    skill = skill_registry.get_skill_by_id(skill_id)
    if skill is None:
        raise HTTPException(status_code=404, detail=f"Unknown skill: {skill_id}")
    report = skill_drift.detect_drift(baseline=skill_baseline.load_baseline())
    return _to_workshop_skill(skill, report)


@app.get(
    "/api/skill-workshop/agents/{agent_id}/skills",
    summary="Agent skills",
    description="Return skills visible to a specific agent.",
    tags=[SKILL_WORKSHOP_TAG],
)
def skill_workshop_agent_skills(agent_id: str) -> dict:
    skills = skill_registry.get_agent_skills(agent_id)
    report = skill_drift.detect_drift(baseline=skill_baseline.load_baseline())
    return {"agentId": agent_id, "skills": [_to_workshop_skill(s, report) for s in skills], "total": len(skills)}


@app.get(
    "/api/skill-workshop/drift-report",
    summary="Drift report",
    description="Return the current skill drift report.",
    tags=[SKILL_WORKSHOP_TAG],
)
def skill_workshop_drift_report() -> dict:
    inventory = skill_registry.get_inventory()
    report = skill_drift.detect_drift(inventory, baseline=skill_baseline.load_baseline())
    return _to_drift_report_dict(report, inventory)


@app.get(
    "/api/skill-workshop/baseline/preview",
    summary="Baseline diff preview",
    description="Preview the changes that confirming the current scan as baseline would make.",
    tags=[SKILL_WORKSHOP_TAG],
)
def skill_workshop_baseline_preview() -> dict:
    return skill_baseline.preview_baseline_diff()


@app.post(
    "/api/skill-workshop/baseline/confirm",
    summary="Confirm skill baseline",
    description="Persist the current skill inventory as the manual baseline. Requires control token and confirmText.",
    tags=[SKILL_WORKSHOP_TAG],
    dependencies=[Depends(require_control_token)],
)
def skill_workshop_baseline_confirm(request: SkillBaselineConfirmRequest) -> dict:
    try:
        return skill_baseline.confirm_baseline(
            confirm_text=request.confirmText,
            confirmed_by=request.confirmedBy,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post(
    "/api/skill-workshop/snapshot",
    summary="Create skill snapshot",
    description="Create a skill inventory snapshot without changing baseline. Requires control token and confirmText.",
    tags=[SKILL_WORKSHOP_TAG],
    dependencies=[Depends(require_control_token)],
)
def skill_workshop_snapshot(request: SkillSnapshotRequest) -> dict:
    try:
        return skill_baseline.create_snapshot(
            confirm_text=request.confirmText,
            created_by=request.createdBy,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get(
    "/api/skill-workshop/history",
    summary="Skill workshop version history",
    description="List baseline changes and skill inventory snapshots.",
    tags=[SKILL_WORKSHOP_TAG],
)
def skill_workshop_history() -> dict:
    return skill_baseline.list_history()


@app.get(
    "/api/skill-workshop/history/{version_id}",
    summary="Skill workshop version detail",
    description="Return the stored skill state for a baseline or snapshot version.",
    tags=[SKILL_WORKSHOP_TAG],
)
def skill_workshop_history_detail(version_id: str) -> dict:
    try:
        return skill_baseline.get_version(version_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get(
    "/api/skill-workshop/compare",
    summary="Skill workshop version diff",
    description="Compare two stored skill workshop versions.",
    tags=[SKILL_WORKSHOP_TAG],
)
def skill_workshop_compare(from_: str = Query(default="", alias="from"), to: str = "") -> dict:
    if not from_:
        raise HTTPException(status_code=400, detail="Query parameter 'from' is required.")
    if not to:
        raise HTTPException(status_code=400, detail="Query parameter 'to' is required.")
    try:
        return skill_baseline.compare_versions(from_, to)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post(
    "/api/skill-workshop/rollback/{version_id}",
    summary="Rollback skill workshop baseline",
    description="Rollback workshop baseline state to a stored version. Requires control token and confirmText.",
    tags=[SKILL_WORKSHOP_TAG],
    dependencies=[Depends(require_control_token)],
)
def skill_workshop_rollback(version_id: str, request: SkillRollbackRequest) -> dict:
    try:
        return skill_baseline.rollback_to_version(
            version_id,
            confirm_text=request.confirmText,
            confirmed_by=request.confirmedBy,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get(
    "/api/skill-workshop/comparison",
    summary="Cross-runtime comparison",
    description="Compare a skill's versions across different runtimes.",
    tags=[SKILL_WORKSHOP_TAG],
)
def skill_workshop_comparison(skillId: str = "") -> dict:
    if not skillId:
        raise HTTPException(status_code=400, detail="Query parameter 'skillId' is required.")
    return skill_drift.build_comparison(skillId)


@app.post(
    "/api/skill-workshop/scan",
    summary="Trigger skill scan",
    description="Trigger a read-only skill scan. Requires control token.",
    tags=[SKILL_WORKSHOP_TAG],
    dependencies=[Depends(require_control_token)],
)
def skill_workshop_scan() -> dict:
    inventory = skill_registry.scan_skills(force_full=True)
    return {
        "ok": True,
        "totalSkills": inventory.total,
        "scanMetadata": inventory.scan_metadata.to_dict() if inventory.scan_metadata else None,
    }


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
    return _run("moonbridge", "switch-model", lambda cfg: moonbridge.switch_model(request.model, cfg, request.reasoning_effort))

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
    return _run("codex-provider", "switch-native", lambda cfg: provider_switch.switch_provider("native", cfg))

@app.post("/api/codex-provider/moonbridge", summary="Switch to MoonBridge provider", description="Switch the codex provider to the MoonBridge proxy backend.", tags=[OPERATIONS_TAG], dependencies=[Depends(require_control_token)])
def switch_moonbridge(request: MoonBridgeModelSwitchRequest | None = Body(default=None)) -> dict:
    return _run(
        "codex-provider",
        "switch-moonbridge",
        lambda cfg: provider_switch.switch_provider(
            "moonbridge",
            cfg,
            moonbridge_model=request.model if request else None,
            reasoning_effort=request.reasoning_effort if request else None,
        ),
    )

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


@app.post(
    "/api/watchdog/force-stop",
    summary="Force stop watchdog",
    description="Force stop the currently active Feishu scheduler watchdog. Requires control token.",
    tags=[OPERATIONS_TAG],
    dependencies=[Depends(require_control_token)],
)
def force_stop_watchdog() -> dict:
    try:
        return to_dict(watchdog.force_stop_current())
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post(
    "/api/control-center/shutdown",
    summary="Shutdown Control Center",
    description="Close Control Center API/launcher processes only. OpenClaw, Codex, and MoonBridge processes are excluded. Requires control token.",
    tags=[OPERATIONS_TAG],
    dependencies=[Depends(require_control_token)],
)
def shutdown_control_center() -> dict:
    return to_dict(control_center.request_shutdown())

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

web_dist = find_stack_root(Path(__file__)) / "web" / "dist"
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
