from __future__ import annotations

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from feishu_stack.plugin_runtime import PluginRegistry
from feishu_stack.plugin_sdk import AccPlugin, PluginCard
from feishu_stack.plugins import create_plugin_router, get_plugin_registry


def plugin(plugin_id: str, *, requires: tuple[str, ...] = ()) -> AccPlugin:
    return AccPlugin(
        id=plugin_id,
        name=plugin_id,
        version="1.0.0",
        description=plugin_id,
        requires=requires,
    )


def test_registry_resolves_dependencies_before_consumers() -> None:
    registry = PluginRegistry((plugin("consumer", requires=("provider",)), plugin("provider")))
    assert [item.id for item in registry.resolve()] == ["provider", "consumer"]


@pytest.mark.parametrize("href", ["javascript:alert(1)", "https://example.org", "//example.org", "/\\example.org", "/\n/example.org"])
def test_card_links_reject_non_local_targets(href) -> None:
    with pytest.raises(ValueError, match="same-origin"):
        PluginRegistry([AccPlugin(
            id="bad-link", name="Bad", version="1", description="test",
            cards=(PluginCard("bad", "Bad", "Bad", "bad", href=href),),
        )])


def test_registry_rejects_duplicate_missing_and_cyclic_plugins() -> None:
    registry = PluginRegistry((plugin("one"),))
    with pytest.raises(ValueError, match="duplicate"):
        registry.register(plugin("one"))

    with pytest.raises(ValueError, match="missing"):
        PluginRegistry((plugin("consumer", requires=("missing",)),)).resolve()

    with pytest.raises(ValueError, match="cycle"):
        PluginRegistry((plugin("one", requires=("two",)), plugin("two", requires=("one",)))).resolve()


def test_registry_mounts_lazy_router_factory() -> None:
    calls: list[str] = []

    def router_factory() -> APIRouter:
        calls.append("created")
        router = APIRouter()

        @router.get("/provided")
        def provided() -> dict[str, bool]:
            return {"ok": True}

        return router

    registry = PluginRegistry((AccPlugin(
        id="provided",
        name="Provided",
        version="1.0.0",
        description="test",
        router_factory=router_factory,
    ),))
    app = FastAPI()
    registry.mount(app)
    assert calls == ["created"]
    assert TestClient(app).get("/provided").json() == {"ok": True}


def test_builtin_inventory_exposes_clickable_feature_cards() -> None:
    inventory = get_plugin_registry().inventory()
    assert inventory[0]["id"] == "acc.framework"
    feature_plugins = [item for item in inventory if item["kind"] == "feature"]
    assert feature_plugins
    assert all(item["cards"] for item in feature_plugins)

    app = FastAPI()
    app.include_router(create_plugin_router())
    response = TestClient(app).get("/api/plugins")
    assert response.status_code == 200
    assert response.json()["count"] == len(inventory)


def test_all_builtin_features_contribute_routers() -> None:
    plugins = {plugin.id: plugin for plugin in get_plugin_registry().resolve()}
    for plugin_id in (
        "acc.dashboard",
        "acc.agent-array",
        "acc.task-battlefield",
        "acc.feishu-connection",
        "acc.model-provider",
        "acc.routing-rules",
        "acc.local-tools",
        "acc.config-center",
        "acc.logs-diagnostics",
        "acc.backup-migration",
    ):
        assert plugins[plugin_id].state == "native"
        assert plugins[plugin_id].router_factory is not None


def test_builtin_feature_routes_are_contributed_by_plugins() -> None:
    plugins = {plugin.id: plugin for plugin in get_plugin_registry().resolve()}
    expected_paths = {
        "acc.dashboard": "/api/dashboard/summary",
        "acc.agent-array": "/api/agents",
        "acc.task-battlefield": "/api/task-battlefield/directory",
        "acc.model-provider": "/api/openclaw/start",
        "acc.local-tools": "/api/local-tools",
        "acc.logs-diagnostics": "/api/diagnostics",
        "acc.backup-migration": "/api/thread-migration/threads",
    }
    for plugin_id, expected_path in expected_paths.items():
        router = plugins[plugin_id].router_factory()
        assert expected_path in {route.path for route in router.routes}


def test_task_plugin_can_serve_without_application_composition(monkeypatch) -> None:
    from feishu_stack.modules.task_battlefield.plugin import create_plugin, task_directory

    monkeypatch.setattr(task_directory, "load_directory", lambda: {"tasks": []})
    isolated_app = FastAPI()
    isolated_app.include_router(create_plugin().router_factory())
    client = TestClient(isolated_app)
    response = client.get("/api/task-battlefield/directory")
    assert response.status_code == 200
    assert response.json() == {"tasks": []}
    assert client.post("/api/watchdog/force-stop").status_code in (401, 403)
