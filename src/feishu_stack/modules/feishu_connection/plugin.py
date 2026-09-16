"""Native ACC plugin adapter for Feishu connection management."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from feishu_stack.api.security import require_control_token
from feishu_stack.plugin_sdk import AccPlugin, PluginCard

from . import router as service


def create_router() -> APIRouter:
    router = APIRouter(prefix="/api/feishu/connection", tags=["Feishu Connection"])

    @router.get("/status")
    def status() -> dict:
        return service.get_connection_status()

    @router.get("/accounts")
    def accounts() -> dict:
        return service.get_connection_accounts()

    @router.get("/permissions")
    def permissions() -> dict:
        return service.get_connection_permissions()

    @router.post("/refresh", dependencies=[Depends(require_control_token)])
    def refresh() -> dict:
        return service.refresh_connection()

    return router


def create_plugin() -> AccPlugin:
    return AccPlugin(
        id="acc.feishu-connection",
        name="飞书连接",
        version="1.0.0",
        description="飞书账号、权限与授权状态。",
        requires=("acc.framework",),
        capabilities=("feishu.inspect",),
        cards=(PluginCard("acc.feishu-connection.overview", "飞书连接", "飞书账号、权限与授权状态。", "feishu", "send", 40),),
        router_factory=create_router,
    )
