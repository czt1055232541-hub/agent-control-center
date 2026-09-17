"""Native ACC plugin adapter for routing rules."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from feishu_stack.plugin_sdk import AccPlugin, PluginCard
from feishu_stack.api.security import require_control_token

from . import router as service


class RoutingRuleSetRequest(BaseModel):
    rule_id: str = ""
    name: str = ""
    pattern: str = ""
    target: str = ""
    enabled: bool = True
    description: str = ""


class RoutingRuleBatchRequest(BaseModel):
    rules: list[dict]


def create_router() -> APIRouter:
    router = APIRouter(prefix="/api/routing-rules", tags=["Routing Rules"])

    @router.get("/list")
    def list_rules() -> dict:
        return {"rules": service.list_rules()}

    @router.get("/get/{rule_id}")
    def get_rule(rule_id: str) -> dict:
        item = service.get_rule(rule_id)
        if item is None:
            raise HTTPException(status_code=404, detail=f"Unknown routing rule: {rule_id}")
        return item

    @router.post("/set", dependencies=[Depends(require_control_token)])
    def set_rule(request: RoutingRuleSetRequest) -> dict:
        return service.set_rule(**request.model_dump())

    @router.delete("/delete/{rule_id}", dependencies=[Depends(require_control_token)])
    def delete_rule(rule_id: str) -> dict:
        if not service.delete_rule(rule_id):
            raise HTTPException(status_code=404, detail=f"Unknown routing rule: {rule_id}")
        return {"ok": True}

    @router.post("/batch", dependencies=[Depends(require_control_token)])
    def batch_rules(request: RoutingRuleBatchRequest) -> dict:
        return service.batch_import_rules(request.rules)

    return router


from feishu_stack.plugins.builtin_descriptors import create_routing_rules_plugin as create_plugin
