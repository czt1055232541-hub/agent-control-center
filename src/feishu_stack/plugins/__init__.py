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
from feishu_stack.modules.dashboard.plugin import create_plugin as create_dashboard_plugin
from feishu_stack.modules.local_tools.plugin import create_plugin as create_local_tools_plugin
from feishu_stack.modules.backup_migration.plugin import create_plugin as create_backup_migration_plugin
from feishu_stack.modules.agent_array.plugin import create_plugin as create_agent_array_plugin
from feishu_stack.modules.model_provider.plugin import create_plugin as create_model_provider_plugin
from feishu_stack.modules.logs_diagnostics.plugin import create_plugin as create_logs_diagnostics_plugin




BUILTIN_PLUGINS = (
    AccPlugin(
        id="acc.framework",
        name="ACC Framework",
        version="1.0.0",
        description="Plugin discovery, dependency validation, lifecycle, and contribution inventory.",
        kind="framework",
        capabilities=("acc.plugins.inventory",),
    ),
    create_dashboard_plugin(),
    create_agent_array_plugin(),
    create_task_battlefield_plugin(),
    create_feishu_connection_plugin(),
    create_model_provider_plugin(),
    create_routing_rules_plugin(),
    create_local_tools_plugin(),
    create_config_center_plugin(),
    create_logs_diagnostics_plugin(),
    create_backup_migration_plugin(),
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
