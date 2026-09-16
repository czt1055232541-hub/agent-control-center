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
