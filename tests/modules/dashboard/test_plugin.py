"""Dashboard HTTP contributions must work without composing the ACC host."""

import subprocess
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient

from feishu_stack.modules.dashboard import plugin


def test_dashboard_is_independently_importable() -> None:
    subprocess.run(
        [sys.executable, "-c", (
            "import sys; "
            "from feishu_stack.modules.dashboard.plugin import create_plugin; "
            "assert create_plugin().router_factory().routes; "
            "assert 'feishu_stack.api.app' not in sys.modules"
        )],
        check=True,
    )


def test_dashboard_routes_on_isolated_host(monkeypatch) -> None:
    monkeypatch.setattr(plugin, "get_status", lambda: {"status": "fixture"})
    monkeypatch.setattr(plugin, "recent_operations", lambda: [])
    monkeypatch.setattr(plugin.agent_dashboard, "dashboard_summary", lambda: {"agents": 3})
    monkeypatch.setattr(plugin.agent_dashboard, "list_infrastructure", lambda: [])
    app = FastAPI()
    app.include_router(plugin.create_plugin().router_factory())
    client = TestClient(app)
    expected = {
        "/api/status": {"status": "fixture"},
        "/api/operations": {"operations": []},
        "/api/dashboard/summary": {"agents": 3},
        "/api/infrastructure": {"agents": []},
    }
    for path, body in expected.items():
        response = client.get(path)
        assert response.status_code == 200
        assert response.json() == body
    assert client.post("/api/dashboard/summary").status_code == 405
