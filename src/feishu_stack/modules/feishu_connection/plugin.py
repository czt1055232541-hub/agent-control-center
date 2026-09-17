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


from feishu_stack.plugins.builtin_descriptors import create_feishu_connection_plugin as create_plugin
