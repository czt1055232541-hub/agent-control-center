from __future__ import annotations

from fastapi.testclient import TestClient

from feishu_stack import app as app_module
from feishu_stack.models import OperationResult
from feishu_stack.operations import _lock


client = TestClient(app_module.app)


def _token() -> str:
    response = client.get("/api/session")
    assert response.status_code == 200
    return response.json()["token"]


def test_status_is_read_only_without_token() -> None:
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert "codex" in data
    assert "codex_desktop_running" in data


def test_write_requires_token() -> None:
    response = client.post("/api/openclaw/start")
    assert response.status_code == 401


def test_write_rejects_bad_token() -> None:
    response = client.post("/api/openclaw/start", headers={"X-Control-Token": "bad"})
    assert response.status_code == 403


def test_operation_lock_returns_busy(monkeypatch) -> None:
    token = _token()

    def fake_start(_config):
        return OperationResult(True, "openclaw", "start", "started")

    monkeypatch.setattr(app_module.openclaw, "start", fake_start)
    assert _lock.acquire(blocking=False)
    try:
        response = client.post("/api/openclaw/start", headers={"X-Control-Token": token})
        assert response.status_code == 409
    finally:
        _lock.release()


def test_codex_desktop_stop_route_uses_mock(monkeypatch) -> None:
    token = _token()
    called = {"stop": False}

    def fake_stop(_config):
        called["stop"] = True
        return OperationResult(True, "codex-desktop", "stop", "mock stop")

    monkeypatch.setattr(app_module.codex_desktop, "stop", fake_stop)
    response = client.post("/api/codex-desktop/stop", headers={"X-Control-Token": token})
    assert response.status_code == 200
    assert response.json()["component"] == "codex-desktop"
    assert called["stop"] is True


def test_stack_stop_does_not_stop_codex_desktop(monkeypatch) -> None:
    token = _token()

    monkeypatch.setattr(app_module.stack_actions, "stop", lambda _config: OperationResult(True, "stack", "stop", "mock stack stop"))

    def fail_stop(_config):
        raise AssertionError("Codex Desktop stop must not be called by stack stop")

    monkeypatch.setattr(app_module.codex_desktop, "stop", fail_stop)
    response = client.post("/api/stack/stop", headers={"X-Control-Token": token})
    assert response.status_code == 200
    assert response.json()["component"] == "stack"
