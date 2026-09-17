"""Native ACC plugin adapter for the Config Center feature."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from feishu_stack.core.config_contract import compare_shared_config, load_json_object, redact_config, validate_shared_config
from feishu_stack.core.settings import find_stack_root, resolve_settings_path
from feishu_stack.plugin_sdk import AccPlugin, PluginCard
from feishu_stack.api.security import require_control_token

from . import router as service


class ConfigCenterSetRequest(BaseModel):
    key: str
    value: str
    description: str = ""


class ConfigCenterImportRequest(BaseModel):
    configs: dict


def create_router() -> APIRouter:
    router = APIRouter(tags=["Config Center"])

    @router.get("/api/config-center/list")
    def list_configs() -> dict:
        return {"configs": service.list_configs()}

    @router.get("/api/config/status")
    def shared_config_status(check_runtime: bool = Query(default=False)) -> dict:
        primary_path = resolve_settings_path()
        primary = load_json_object(primary_path)
        validation = validate_shared_config(primary, check_runtime=check_runtime)
        explicit_peer = os.environ.get("FEISHU_AGENT_SETTINGS_PATH")
        peer_path = Path(explicit_peer) if explicit_peer else None
        drift: list[dict] = []
        peer_status = "merged" if (find_stack_root(Path(__file__)) / "agent-runtime").exists() and peer_path is None else "not_found"
        if peer_path is not None and peer_path.exists():
            try:
                peer = load_json_object(peer_path)
                drift = compare_shared_config(primary, peer)
                peer_status = "available"
            except (OSError, ValueError, TypeError):
                peer_status = "invalid"
        return {**validation, "source": "control-plane", "peer_status": peer_status, "drift": redact_config(drift)}

    @router.get("/api/config-center/get/{key}")
    def get_config(key: str) -> dict:
        item = service.get_config(key)
        if item is None:
            raise HTTPException(status_code=404, detail=f"Unknown config key: {key}")
        return item

    @router.post("/api/config-center/set", dependencies=[Depends(require_control_token)])
    def set_config(request: ConfigCenterSetRequest) -> dict:
        return service.set_config(request.key, request.value, request.description)

    @router.delete("/api/config-center/delete/{key}", dependencies=[Depends(require_control_token)])
    def delete_config(key: str) -> dict:
        if not service.delete_config(key):
            raise HTTPException(status_code=404, detail=f"Unknown config key: {key}")
        return {"ok": True}

    @router.post("/api/config-center/export", dependencies=[Depends(require_control_token)])
    def export_configs() -> dict:
        return service.export_configs()

    @router.post("/api/config-center/import", dependencies=[Depends(require_control_token)])
    def import_configs(request: ConfigCenterImportRequest) -> dict:
        return service.import_configs(request.configs)

    return router


from feishu_stack.plugins.builtin_descriptors import create_config_center_plugin as create_plugin
