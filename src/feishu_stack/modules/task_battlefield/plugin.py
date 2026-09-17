from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from feishu_stack.api.security import require_control_token
from feishu_stack.core.models import to_dict
from feishu_stack.plugin_sdk import AccPlugin, PluginCard
from . import task_directory, watchdog

DASHBOARD_TAG = TASK_BATTLEFIELD_TAG = OPERATIONS_TAG = 'Task Battlefield'
router = APIRouter()

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


@router.get(
    "/api/watchdog/current",
    summary="Current watchdog",
    description="Return the single active Feishu scheduler watchdog used by the dashboard card.",
    tags=[DASHBOARD_TAG],
)
def current_watchdog() -> dict:
    return to_dict(watchdog.current_watchdog())


@router.get(
    "/api/task-battlefield/directory",
    summary="Task battlefield directory",
    description="Return the task directory mapped to the Feishu agent projects workspace.",
    tags=[TASK_BATTLEFIELD_TAG],
)
def task_battlefield_directory() -> dict:
    return task_directory.load_directory()


@router.post(
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


@router.put(
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


@router.delete(
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


@router.post(
    "/api/task-battlefield/classify",
    summary="Classify task description",
    description="Suggest whether a task belongs to an existing parent project or needs a new workspace.",
    tags=[TASK_BATTLEFIELD_TAG],
)
def classify_task_battlefield_task(request: TaskClassifyRequest) -> dict:
    return task_directory.classify_task(request.description, request.workspacePath)


@router.post(
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

from feishu_stack.plugins.builtin_descriptors import create_task_battlefield_plugin as create_plugin
