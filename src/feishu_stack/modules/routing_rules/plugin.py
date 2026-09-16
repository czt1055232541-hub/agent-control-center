"""Native ACC plugin adapter for routing rules."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from feishu_stack.plugin_sdk import AccPlugin, PluginCard

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

    @router.post("/set")
    def set_rule(request: RoutingRuleSetRequest) -> dict:
        return service.set_rule(**request.model_dump())

    @router.delete("/delete/{rule_id}")
    def delete_rule(rule_id: str) -> dict:
        if not service.delete_rule(rule_id):
            raise HTTPException(status_code=404, detail=f"Unknown routing rule: {rule_id}")
        return {"ok": True}

    @router.post("/batch")
    def batch_rules(request: RoutingRuleBatchRequest) -> dict:
        return service.batch_import_rules(request.rules)

    return router


def create_plugin() -> AccPlugin:
    return AccPlugin(
        id="acc.routing-rules",
        name="路由规则",
        version="1.0.0",
        description="消息与任务路由规则管理。",
        requires=("acc.framework",),
        capabilities=("routing.manage",),
        cards=(PluginCard("acc.routing-rules.overview", "路由规则", "消息与任务路由规则管理。", "routing", "route", 60),),
        router_factory=create_router,
    )
