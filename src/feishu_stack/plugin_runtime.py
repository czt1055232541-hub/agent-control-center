"""Discovery, validation, and mounting for ACC feature plugins."""

from __future__ import annotations

from importlib import metadata
from contextlib import AsyncExitStack, asynccontextmanager
from typing import Iterable

from fastapi import FastAPI

from .plugin_sdk import AccPlugin


ENTRY_POINT_GROUP = "agent_control_center.plugins"


class PluginRegistry:
    """Validated collection of ACC plugins in dependency order."""

    def __init__(self, plugins: Iterable[AccPlugin] = (), *, disabled: Iterable[str] = ()) -> None:
        self._plugins: dict[str, AccPlugin] = {}
        self._disabled = frozenset(disabled)
        for plugin in plugins:
            self.register(plugin)

    def register(self, plugin: AccPlugin) -> None:
        """Register one plugin and reject ambiguous identities."""
        if not plugin.id or plugin.id.strip() != plugin.id:
            raise ValueError("plugin id must be a non-empty trimmed string")
        if plugin.id in self._plugins:
            raise ValueError(f"duplicate ACC plugin id: {plugin.id}")
        self._plugins[plugin.id] = plugin

    def resolve(self) -> tuple[AccPlugin, ...]:
        """Return a deterministic dependency order or fail on an invalid graph."""
        unknown = self._disabled.difference(self._plugins)
        if unknown:
            raise ValueError(f"Unknown disabled ACC plugins: {', '.join(sorted(unknown))}")
        for plugin_id in self._disabled:
            if self._plugins[plugin_id].kind == "framework":
                raise ValueError(f"Cannot disable ACC framework plugin: {plugin_id}")
        resolved: list[AccPlugin] = []
        visiting: list[str] = []
        visited: set[str] = set()

        def visit(plugin_id: str) -> None:
            if plugin_id in self._disabled:
                owner = visiting[-1] if visiting else "plugin graph"
                raise ValueError(f"ACC plugin {owner} requires disabled plugin {plugin_id}")
            if plugin_id in visited:
                return
            if plugin_id in visiting:
                cycle = " -> ".join((*visiting[visiting.index(plugin_id):], plugin_id))
                raise ValueError(f"ACC plugin dependency cycle: {cycle}")
            plugin = self._plugins.get(plugin_id)
            if plugin is None:
                owner = visiting[-1] if visiting else "plugin graph"
                raise ValueError(f"ACC plugin {owner} requires missing plugin {plugin_id}")
            visiting.append(plugin_id)
            for dependency in sorted(plugin.requires):
                visit(dependency)
            visiting.pop()
            visited.add(plugin_id)
            resolved.append(plugin)

        for plugin_id in sorted(self._plugins):
            if plugin_id not in self._disabled:
                visit(plugin_id)
        return tuple(resolved)

    @asynccontextmanager
    async def lifespan(self, app: FastAPI):
        """Start dependencies first and unwind in reverse order, even on failure."""
        async with AsyncExitStack() as stack:
            for plugin in self.resolve():
                if plugin.lifespan is not None:
                    await stack.enter_async_context(plugin.lifespan(app))
            yield

    def mount(self, app: FastAPI) -> tuple[AccPlugin, ...]:
        """Mount every native plugin router after validating the full graph."""
        plugins = self.resolve()
        for plugin in plugins:
            if plugin.router_factory is not None:
                app.include_router(plugin.router_factory())
        return plugins

    def inventory(self) -> list[dict[str, object]]:
        """Return a JSON-safe inventory for ACC and external hosts such as DSH."""
        return [
            {
                "id": plugin.id,
                "name": plugin.name,
                "version": plugin.version,
                "description": plugin.description,
                "kind": plugin.kind,
                "state": plugin.state,
                "requires": list(plugin.requires),
                "capabilities": list(plugin.capabilities),
                "cards": [
                    {
                        "id": card.id,
                        "title": card.title,
                        "description": card.description,
                        "page": card.page,
                        "icon": card.icon,
                        "order": card.order,
                    }
                    for card in sorted(plugin.cards, key=lambda item: (item.order, item.id))
                ],
            }
            for plugin in self.resolve()
        ]


def discover_entry_point_plugins() -> tuple[AccPlugin, ...]:
    """Load plugins installed through the public Python entry-point group."""
    discovered: list[AccPlugin] = []
    entry_points = metadata.entry_points()
    selected = entry_points.select(group=ENTRY_POINT_GROUP)
    for entry_point in sorted(selected, key=lambda item: item.name):
        candidate = entry_point.load()
        plugin = candidate() if callable(candidate) and not isinstance(candidate, AccPlugin) else candidate
        if not isinstance(plugin, AccPlugin):
            raise TypeError(
                f"ACC plugin entry point {entry_point.name!r} returned {type(plugin).__name__}, expected AccPlugin"
            )
        discovered.append(plugin)
    return tuple(discovered)
