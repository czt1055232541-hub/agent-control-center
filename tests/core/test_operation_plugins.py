"""Plugin isolation and host-injected operation dispatch contracts."""

import subprocess
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from feishu_stack.api.security import require_control_token
from feishu_stack.modules.local_tools.plugin import create_plugin as local_tools_plugin
from feishu_stack.modules.backup_migration.plugin import create_plugin as backup_plugin


@pytest.mark.parametrize("module", ["local_tools", "backup_migration"])
def test_operation_plugin_import_does_not_load_host(module) -> None:
    subprocess.run([sys.executable, "-c", (
        "import sys; "
        f"from feishu_stack.modules.{module}.plugin import create_plugin; "
        "assert create_plugin().router_factory().routes; "
        "assert 'feishu_stack.api.app' not in sys.modules"
    )], check=True)


@pytest.mark.parametrize("factory,path,body,component,action", [
    (local_tools_plugin, "/api/local-tools/demo/start", None, "local-tool:demo", "start"),
    (backup_plugin, "/api/backups/clean", None, "backups", "clean"),
    (backup_plugin, "/api/thread-migration/migrate", {
        "session_id": "test-session", "target_provider": "native"
    }, "thread-migration", "migrate"),
])
def test_write_routes_require_auth_and_use_host_runner(factory, path, body, component, action) -> None:
    calls = []

    def runner(owner, operation, fn):
        calls.append((owner, operation))
        assert callable(fn)
        return {"ok": True, "component": owner, "action": operation}

    app = FastAPI()
    app.state.operation_runner = runner
    app.include_router(factory().router_factory())
    client = TestClient(app)
    assert client.post(path, json=body).status_code in (401, 403)
    assert calls == []
    app.dependency_overrides[require_control_token] = lambda: None
    response = client.post(path, json=body)
    assert response.status_code == 200
    assert response.json() == {"ok": True, "component": component, "action": action}
    assert calls == [(component, action)]
