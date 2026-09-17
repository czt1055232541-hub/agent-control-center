import os
import subprocess
import sys
from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from feishu_stack.plugin_sdk import AccPlugin
from feishu_stack.plugin_runtime import PluginRegistry


def feature(name, **kwargs):
    return AccPlugin(id=name, name=name, version="1", description=name, **kwargs)


@pytest.mark.parametrize("fail", [False, True])
def test_lifecycle_order_and_partial_startup_cleanup(fail):
    events = []

    @asynccontextmanager
    async def dependency(app):
        events.append("start dependency")
        try:
            yield
        finally:
            events.append("stop dependency")

    @asynccontextmanager
    async def consumer(app):
        events.append("start consumer")
        if fail:
            raise RuntimeError("startup failure")
        try:
            yield
        finally:
            events.append("stop consumer")

    registry = PluginRegistry([
        feature("consumer", requires=("dependency",), lifespan=consumer),
        feature("dependency", lifespan=dependency),
    ])
    app = FastAPI(lifespan=registry.lifespan)
    if fail:
        with pytest.raises(RuntimeError, match="startup failure"):
            with TestClient(app):
                pytest.fail("failed startup must not serve")
        assert events == ["start dependency", "start consumer", "stop dependency"]
    else:
        with TestClient(app):
            assert events == ["start dependency", "start consumer"]
        assert events == ["start dependency", "start consumer", "stop consumer", "stop dependency"]


def test_disabled_dependencies_and_unknown_ids_fail_explicitly():
    with pytest.raises(ValueError, match="requires disabled"):
        PluginRegistry([feature("one"), feature("two", requires=("one",))], disabled=["one"]).resolve()
    with pytest.raises(ValueError, match="Unknown disabled"):
        PluginRegistry([feature("one")], disabled=["typo"]).resolve()
    with pytest.raises(ValueError, match="Cannot disable"):
        PluginRegistry([feature("core", kind="framework")], disabled=["core"]).resolve()


def test_disabled_plugin_is_absent_from_real_host_routes_and_inventory():
    program = """
from fastapi.testclient import TestClient
from feishu_stack.api.app import app
with TestClient(app) as client:
    response = client.get('/api/plugins')
    assert response.status_code == 200
    assert 'acc.task-battlefield' not in {p['id'] for p in response.json()['plugins']}
    assert client.get('/api/task-battlefield/directory').status_code == 404
    assert client.get('/api/health').status_code == 200
"""
    subprocess.run([sys.executable, "-c", program], check=True,
                   env={**os.environ, "ACC_DISABLED_PLUGINS": "acc.task-battlefield"})
