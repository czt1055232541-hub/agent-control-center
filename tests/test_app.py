from __future__ import annotations

from fastapi.testclient import TestClient

from feishu_stack import app as app_module
from feishu_stack.models import OperationResult, ThreadMigrationResult
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


def test_openclaw_open_ui_route_uses_mock(monkeypatch) -> None:
    token = _token()
    called = {"open": False}

    def fake_open_ui(_config):
        called["open"] = True
        return OperationResult(True, "openclaw", "open-ui", "mock open ui", port=18789)

    monkeypatch.setattr(app_module.openclaw, "open_ui", fake_open_ui)
    response = client.post("/api/openclaw/open-ui", headers={"X-Control-Token": token})
    assert response.status_code == 200
    assert response.json()["component"] == "openclaw"
    assert response.json()["action"] == "open-ui"
    assert called["open"] is True


def test_diagnostics_endpoint_uses_mock(monkeypatch) -> None:
    monkeypatch.setattr(app_module.diagnostics_module, "diagnostics", lambda: {"codex_doctor": {"ok": True}})
    response = client.get("/api/diagnostics")
    assert response.status_code == 200
    assert response.json()["codex_doctor"]["ok"] is True


def test_codex_doctor_endpoint_uses_mock(monkeypatch) -> None:
    monkeypatch.setattr(app_module.diagnostics_module, "codex_doctor", lambda: {"ok": True, "stdout": "doctor"})
    response = client.get("/api/doctor/codex")
    assert response.status_code == 200
    assert response.json()["stdout"] == "doctor"


def test_moonbridge_models_endpoint_uses_mock(monkeypatch) -> None:
    monkeypatch.setattr(app_module.diagnostics_module, "moonbridge_models", lambda: {"ok": True, "models": ["moonbridge"]})
    response = client.get("/api/moonbridge/models")
    assert response.status_code == 200
    assert response.json()["models"] == ["moonbridge"]


def test_lark_auth_status_endpoint_uses_mock(monkeypatch) -> None:
    monkeypatch.setattr(app_module.diagnostics_module, "lark_auth_status", lambda: {"ok": True, "stdout": "logged in"})
    response = client.get("/api/lark/auth-status")
    assert response.status_code == 200
    assert response.json()["stdout"] == "logged in"


def test_backup_cleanup_requires_token() -> None:
    response = client.post("/api/backups/clean")
    assert response.status_code == 401
    response = client.post("/api/backups/clean", headers={"X-Control-Token": "bad"})
    assert response.status_code == 403


def test_backup_cleanup_route_uses_mock(monkeypatch) -> None:
    token = _token()
    called = {"clean": False}

    def fake_clean(_config):
        called["clean"] = True
        return OperationResult(True, "backups", "clean", "mock clean")

    monkeypatch.setattr(app_module.backups, "clean", fake_clean)
    response = client.post("/api/backups/clean", headers={"X-Control-Token": token})
    assert response.status_code == 200
    assert response.json()["component"] == "backups"
    assert called["clean"] is True


def test_control_center_log_route() -> None:
    response = client.get("/api/logs/control-center-api")
    assert response.status_code == 200
    assert response.json()["component"] == "control-center-api"


def test_thread_migration_requires_token() -> None:
    response = client.post("/api/thread-migration/migrate", json={"session_id": "abc", "target_provider": "moonbridge", "prompt": "continue"})
    assert response.status_code == 401
    response = client.post(
        "/api/thread-migration/migrate",
        headers={"X-Control-Token": "bad"},
        json={"session_id": "abc", "target_provider": "moonbridge", "prompt": "continue"},
    )
    assert response.status_code == 403


def test_thread_migration_route_uses_mock(monkeypatch) -> None:
    token = _token()
    called = {"migrate": False}

    def fake_migrate(session_id, target_provider, prompt, _config):
        called["migrate"] = True
        return ThreadMigrationResult(
            True,
            "thread-migration",
            "migrate",
            "mock migrate",
            source_session_id=session_id,
            source_title="Example Thread",
            target_provider=target_provider,
            target_model="moonbridge",
            summary_path="F:/summary.txt",
            summary_dir="F:/",
            launch_mode="cli-session-fallback",
        )

    monkeypatch.setattr(app_module.thread_migration, "migrate_thread", fake_migrate)
    response = client.post(
        "/api/thread-migration/migrate",
        headers={"X-Control-Token": token},
        json={"session_id": "abc", "target_provider": "moonbridge", "prompt": "continue"},
    )
    assert response.status_code == 200
    assert response.json()["component"] == "thread-migration"
    assert response.json()["source_session_id"] == "abc"
    assert called["migrate"] is True


def test_thread_migration_open_summary_folder_route_uses_mock(monkeypatch) -> None:
    token = _token()
    called = {"open": False}

    def fake_open(summary_path):
        called["open"] = True
        return ThreadMigrationResult(
            True,
            "thread-migration",
            "open-summary-folder",
            "opened",
            summary_path=summary_path,
            summary_dir="F:/summaries",
        )

    monkeypatch.setattr(app_module.thread_migration, "open_summary_folder", fake_open)
    response = client.post(
        "/api/thread-migration/open-summary-folder",
        headers={"X-Control-Token": token},
        json={"summary_path": "F:/summary.txt"},
    )
    assert response.status_code == 200
    assert response.json()["action"] == "open-summary-folder"
    assert called["open"] is True


def test_thread_migration_threads_route_uses_mock(monkeypatch) -> None:
    monkeypatch.setattr(
        app_module.thread_migration,
        "list_recent_threads",
        lambda limit=20: [
            {
                "session_id": "abc",
                "title": "Example Thread",
                "provider": "openai",
                "model": "gpt-5.5",
                "updated_at": "2026-06-21 10:00:00",
            }
        ],
    )
    response = client.get("/api/thread-migration/threads?limit=10")
    assert response.status_code == 200
    assert response.json()["threads"][0]["title"] == "Example Thread"
