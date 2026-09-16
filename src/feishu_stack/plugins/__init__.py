"""Built-in ACC plugins and the process-wide plugin registry."""

from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter

from feishu_stack.plugin_runtime import PluginRegistry, discover_entry_point_plugins
from feishu_stack.plugin_sdk import AccPlugin, PluginCard


def _feature(
    plugin_id: str,
    name: str,
    description: str,
    page: str,
    *capabilities: str,
    order: int,
    icon: str,
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
    _feature("acc.dashboard", "Dashboard 总览", "运行状态与关键指标总览。", "dashboard", "dashboard.read", order=10, icon="layout-dashboard"),
    _feature("acc.agent-array", "Agent 阵列", "Agent、技能树与运行记录管理。", "agents", "agents.read", "skills.manage", order=20, icon="swords"),
    _feature("acc.task-battlefield", "任务战场", "任务目录、工作区映射与看门狗。", "tasks", "tasks.manage", order=30, icon="calendar-clock"),
    _feature("acc.feishu-connection", "飞书连接", "飞书账号、权限与授权状态。", "feishu", "feishu.inspect", order=40, icon="send"),
    _feature("acc.model-provider", "模型与 Provider", "模型提供方、Codex 与 OpenClaw 运行控制。", "provider", "providers.manage", order=50, icon="server-cog"),
    _feature("acc.routing-rules", "路由规则", "消息与任务路由规则管理。", "routing", "routing.manage", order=60, icon="route"),
    _feature("acc.local-tools", "本地工具", "本地工具发现、注册与进程控制。", "tools", "tools.manage", order=70, icon="package-open"),
    _feature("acc.config-center", "配置中心", "配置校验、导入和导出。", "config", "config.manage", order=80, icon="file-cog"),
    _feature("acc.logs-diagnostics", "日志与诊断", "日志、指标与诊断工具。", "diagnostics", "diagnostics.read", order=90, icon="file-text"),
    _feature("acc.backup-migration", "备份与迁移", "备份保留与跨 Provider 线程迁移。", "backup", "backups.manage", order=100, icon="archive"),
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
