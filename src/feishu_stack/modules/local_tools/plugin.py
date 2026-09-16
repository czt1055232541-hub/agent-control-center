from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from feishu_stack.api.security import require_control_token
from feishu_stack.api.operations import OperationRunner, operation_runner
from feishu_stack.core.models import to_dict
from feishu_stack.plugin_sdk import AccPlugin, PluginCard
from . import registry as local_tools

LOCAL_TOOLS_TAG = THREAD_MIGRATION_TAG = OPERATIONS_TAG = 'Local Tools'
router = APIRouter()

class LocalToolRegisterRequest(BaseModel):
    id: str | None = None
    name: str | None = None
    description: str | None = None
    dir: str
    manifest: str | None = None
    entry: str | None = None
    runtime: str | None = None
    host: str | None = None
    port: int | None = None
    url: str | None = None
    healthPath: str | None = None
    openPath: str | None = None
    enabled: bool = True
    embed: bool = True
    tags: list[str] = []
    env: dict[str, str] | None = None


@router.get(
    "/api/local-tools",
    summary="Local tool registry",
    description="Return local tools registered in stack settings with runtime status.",
    tags=[LOCAL_TOOLS_TAG],
)
def list_local_tools() -> dict:
    return {"tools": local_tools.list_tools()}


@router.get(
    "/api/local-tools/scan",
    summary="Scan local tools",
    description="Scan common local tool folders or a specified root for tool manifests.",
    tags=[LOCAL_TOOLS_TAG],
    dependencies=[Depends(require_control_token)],
)
def scan_local_tools(root: str | None = None) -> dict:
    return {"candidates": local_tools.scan(root)}


@router.post(
    "/api/local-tools/register",
    summary="Register local tool",
    description="Register a local tool into the writable stack settings file.",
    tags=[LOCAL_TOOLS_TAG],
    dependencies=[Depends(require_control_token)],
)
def register_local_tool(request: LocalToolRegisterRequest) -> dict:
    try:
        return local_tools.register(request.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/api/local-tools/{tool_id}",
    summary="Local tool status",
    description="Return one registered local tool with runtime status.",
    tags=[LOCAL_TOOLS_TAG],
)
def get_local_tool(tool_id: str) -> dict:
    try:
        return local_tools.get_tool_status(tool_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"local tool not found: {tool_id}") from exc


@router.post(
    "/api/local-tools/{tool_id}/start",
    summary="Start local tool",
    description="Start a registered local tool. Requires control token.",
    tags=[LOCAL_TOOLS_TAG],
    dependencies=[Depends(require_control_token)],
)
def start_local_tool(tool_id: str, runner: OperationRunner = Depends(operation_runner)) -> dict:
    try:
        return runner(f"local-tool:{tool_id}", "start", lambda cfg: local_tools.start(tool_id, cfg))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"local tool not found: {tool_id}") from exc


@router.post(
    "/api/local-tools/{tool_id}/stop",
    summary="Stop local tool",
    description="Stop a registered local tool. Requires control token.",
    tags=[LOCAL_TOOLS_TAG],
    dependencies=[Depends(require_control_token)],
)
def stop_local_tool(tool_id: str, runner: OperationRunner = Depends(operation_runner)) -> dict:
    try:
        return runner(f"local-tool:{tool_id}", "stop", lambda cfg: local_tools.stop(tool_id, cfg))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"local tool not found: {tool_id}") from exc


@router.post(
    "/api/local-tools/{tool_id}/restart",
    summary="Restart local tool",
    description="Restart a registered local tool. Requires control token.",
    tags=[LOCAL_TOOLS_TAG],
    dependencies=[Depends(require_control_token)],
)
def restart_local_tool(tool_id: str, runner: OperationRunner = Depends(operation_runner)) -> dict:
    try:
        return runner(f"local-tool:{tool_id}", "restart", lambda cfg: local_tools.restart(tool_id, cfg))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"local tool not found: {tool_id}") from exc

def create_plugin() -> AccPlugin:
    return AccPlugin(id='acc.local-tools', name='本地工具', version='1.0.0', description='Local Tools', requires=('acc.framework',), capabilities=('tools.manage',), cards=(PluginCard('acc.local-tools.overview', '本地工具', 'Local Tools', 'tools', icon='package-open', order=70),), router_factory=lambda: router)
