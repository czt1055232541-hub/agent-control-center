"""Built-in ACC plugins and the process-wide plugin registry."""

from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter

from feishu_stack.plugin_runtime import PluginRegistry, discover_entry_point_plugins
from feishu_stack.plugin_sdk import AccPlugin, PluginCard
from feishu_stack.modules.config_center.plugin import create_plugin as create_config_center_plugin
from feishu_stack.modules.feishu_connection.plugin import create_plugin as create_feishu_connection_plugin
from feishu_stack.modules.routing_rules.plugin import create_plugin as create_routing_rules_plugin
from feishu_stack.modules.task_battlefield.plugin import create_plugin as create_task_battlefield_plugin
from feishu_stack.plugins.builtin_routers import (
    agent_array_router,
    backup_migration_router,
    dashboard_router,
    local_tools_router,
    logs_diagnostics_router,
    model_provider_router,
)


def _feature(
    plugin_id: str,
    name: str,
    description: str,
    page: str,
    *capabilities: str,
    order: int,
    icon: str,
    router: APIRouter,
) -> AccPlugin:
    return AccPlugin(
        id=plugin_id,
        name=name,
        version="1.0.0",
        description=description,
        state="transitional",
        requires=("acc.framework",),
        capabilities=capabilities,
        cards=(PluginCard(
            id=f"{plugin_id}.overview",
            title=name,
            description=description,
            page=page,
            icon=icon,
            order=order,
        ),),
        router_factory=lambda: router,
    )


BUILTIN_PLUGINS = (
    AccPlugin(
        id="acc.framework",
        name="ACC Framework",
        version="1.0.0",
        description="Plugin discovery, dependency validation, lifecycle, and contribution inventory.",
        kind="framework",
        capabilities=("acc.plugins.inventory",),
    ),
    _feature("acc.dashboard", "Dashboard 总览", "运行状态与关键指标总览。", "dashboard", "dashboard.read", order=10, icon="layout-dashboard", router=dashboard_router),
    _feature("acc.agent-array", "Agent 阵列", "Agent、技能树与运行记录管理。", "agents", "agents.read", "skills.manage", order=20, icon="swords", router=agent_array_router),
    create_task_battlefield_plugin(),
    create_feishu_connection_plugin(),
    _feature("acc.model-provider", "模型与 Provider", "模型提供方、Codex 与 OpenClaw 运行控制。", "provider", "providers.manage", order=50, icon="server-cog", router=model_provider_router),
    create_routing_rules_plugin(),
    _feature("acc.local-tools", "本地工具", "本地工具发现、注册与进程控制。", "tools", "tools.manage", order=70, icon="package-open", router=local_tools_router),
    create_config_center_plugin(),
    _feature("acc.logs-diagnostics", "日志与诊断", "日志、指标与诊断工具。", "diagnostics", "diagnostics.read", order=90, icon="file-text", router=logs_diagnostics_router),
    _feature("acc.backup-migration", "备份与迁移", "备份保留与跨 Provider 线程迁移。", "backup", "backups.manage", order=100, icon="archive", router=backup_migration_router),
)


@lru_cache(maxsize=1)
def get_plugin_registry() -> PluginRegistry:
    """Build the stable registry once per ACC process."""
    return PluginRegistry((*BUILTIN_PLUGINS, *discover_entry_point_plugins()))


def create_plugin_router() -> APIRouter:
    """Expose framework inventory without coupling callers to Python internals."""
    router = APIRouter(prefix="/api/plugins", tags=["Plugins"])

    @router.get("")
    def list_plugins() -> dict[str, object]:
        plugins = get_plugin_registry().inventory()
        return {"plugins": plugins, "count": len(plugins)}

    @router.get("/{plugin_id}")
    def get_plugin(plugin_id: str) -> dict[str, object]:
        for plugin in get_plugin_registry().inventory():
            if plugin["id"] == plugin_id:
                return plugin
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"ACC plugin not found: {plugin_id}")

    return router


__all__ = ["BUILTIN_PLUGINS", "create_plugin_router", "get_plugin_registry"]
