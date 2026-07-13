from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from feishu_stack import app as app_module
from feishu_stack.api import app as api_app_module
from feishu_stack.models import AgentConfig, DashboardSummary, ExplainedDiagnosticItem, OperationResult, ThreadMigrationResult
from feishu_stack.operations import _lock


client = TestClient(app_module.app)


def _token() -> str:
    response = client.get("/api/session")
    assert response.status_code == 200
    return response.json()["token"]


def test_frontend_dist_path_points_to_repo_web_dist() -> None:
    expected = Path(__file__).resolve().parents[2] / "web" / "dist"
    assert app_module.web_dist == expected


def test_status_is_read_only_without_token() -> None:
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert "codex" in data
    assert "codex_app" in data
    assert "codex_agent_provider" in data
    assert "codex_desktop_running" in data


def test_provider_target_routes_call_switch_provider(monkeypatch) -> None:
    calls = []

    def fake_switch(mode, _cfg, moonbridge_model=None, reasoning_effort=None, target="app"):
        calls.append((mode, moonbridge_model, reasoning_effort, target))
        return OperationResult(True, f"codex-provider-{target}", f"switch-{mode}", "ok")

    def fake_switch_agent(mode, _cfg, moonbridge_model=None, reasoning_effort=None):
        calls.append((mode, moonbridge_model, reasoning_effort, "agent"))
        return OperationResult(True, "codex-provider-agent", f"switch-agent-{mode}", "ok")

    monkeypatch.setattr(api_app_module.provider_switch, "switch_provider", fake_switch)
    monkeypatch.setattr(api_app_module.stack_actions, "switch_agent_provider", fake_switch_agent)
    headers = {"X-Control-Token": _token()}

    assert client.post("/api/codex-provider/app/native", headers=headers).status_code == 200
    assert client.post(
        "/api/codex-provider/agent/moonbridge",
        headers=headers,
        json={"model": "bridge-model", "reasoning_effort": "xhigh"},
    ).status_code == 200

    assert calls == [
        ("native", None, None, "app"),
        ("moonbridge", "bridge-model", "xhigh", "agent"),
    ]


def test_response_has_request_id() -> None:
    response = client.get("/api/health", headers={"X-Request-ID": "test-request-123"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "test-request-123"


def test_http_error_is_structured_and_correlated() -> None:
    response = client.get("/api/agents/missing-request-id")
    assert response.status_code == 404
    data = response.json()
    assert data["error_code"] == "HTTP_404"
    assert data["message"]
    assert data["request_id"] == response.headers["X-Request-ID"]


def test_config_status_reports_redacted_drift(tmp_path, monkeypatch) -> None:
    primary = {
        "codexHome": "C:/codex", "codexBin": "C:/codex.exe", "codexConfig": "C:/config.toml",
        "codexNativeModel": "native", "codexMoonBridgeModel": "bridge", "codexSwitchScript": "C:/switch.py",
        "moonbridge": {"port": 38440},
        "openclaw": {"port": 18789, "token": "must-not-leak"},
        "agent": {"dir": "C:/agent", "larkCliBin": "C:/lark.exe", "larkBotOpenId": "ou_private"},
        "runtime": {"dir": "C:/runtime", "logs": "C:/runtime/logs", "pids": "C:/runtime/pids"},
    }
    peer = {**primary, "openclaw": {"port": 18790, "token": "peer-secret"}}
    primary_path = tmp_path / "control" / "config" / "stack.json"
    peer_path = tmp_path / "agent" / "stack.json"
    primary_path.parent.mkdir(parents=True)
    peer_path.parent.mkdir(parents=True)
    primary_path.write_text(__import__("json").dumps(primary), encoding="utf-8")
    peer_path.write_text(__import__("json").dumps(peer), encoding="utf-8")
    monkeypatch.setattr(api_app_module, "resolve_settings_path", lambda: primary_path)
    monkeypatch.setenv("FEISHU_AGENT_SETTINGS_PATH", str(peer_path))
    response = client.get("/api/config/status")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["drift"][0]["field"] == "openclaw.port"
    assert "must-not-leak" not in response.text
    assert "ou_private" not in response.text


def test_dashboard_summary_is_read_only_without_token(monkeypatch) -> None:
    monkeypatch.setattr(
        app_module.agent_dashboard,
        "dashboard_summary",
        lambda: DashboardSummary("normal", "native / gpt-5.5", "unknown", 3, 4, None, None, 0),
    )
    response = client.get("/api/dashboard/summary")
    assert response.status_code == 200
    assert response.json()["systemHealth"] == "normal"


def test_agents_route_is_read_only_without_token(monkeypatch) -> None:
    monkeypatch.setattr(
        app_module.agent_dashboard,
        "list_agents",
        lambda: [
            AgentConfig(
                id="moonbridge",
                name="MoonBridge",
                role="Provider proxy",
                status="running",
                provider="moonbridge",
                model="deepseek-v4-pro",
                pid=123,
                port=38440,
                uptime="--",
                feishuBinding="--",
                triggerMode="Provider",
                tools=["models"],
                permissionLevel="network",
                promptVersion="--",
                configPath="E:/moonbridge/config.yml",
                currentTask="--",
                lastCalledAt=None,
                lastLatencyMs=None,
                lastError="",
                todayTaskCount=0,
                successRate=None,
                controlComponent="moonbridge",
                logsComponent="moonbridge",
            )
        ],
    )
    response = client.get("/api/agents")
    assert response.status_code == 200
    assert response.json()["agents"][0]["id"] == "moonbridge"


def test_infrastructure_route_is_read_only_without_token(monkeypatch) -> None:
    monkeypatch.setattr(app_module.agent_dashboard, "list_infrastructure", lambda: [])
    response = client.get("/api/infrastructure")
    assert response.status_code == 200
    assert response.json()["agents"] == []


def test_current_watchdog_route_is_read_only_without_token(monkeypatch) -> None:
    monkeypatch.setattr(
        app_module.watchdog,
        "current_watchdog",
        lambda: {
            "enabled": True,
            "status_light": "green",
            "task_id": "TASK-1",
            "assignee": "代码执行官",
            "phase": "开发实现",
            "countdown_seconds": 120,
            "next_check_at": "2026-07-09T12:00:00",
            "send_count": 2,
            "state_file": "F:/watchdogs/task.json",
            "pid": 1234,
            "pid_running": True,
            "status": "waiting",
            "log": "F:/watchdogs/task.log",
        },
    )
    response = client.get("/api/watchdog/current")
    assert response.status_code == 200
    assert response.json()["enabled"] is True
    assert response.json()["status_light"] == "green"


def test_task_battlefield_directory_is_read_only_without_token(monkeypatch) -> None:
    monkeypatch.setattr(
        app_module.task_directory,
        "load_directory",
        lambda: {
            "version": 1,
            "directoryFile": "F:/projects/task_directory.json",
            "projectsRoot": "F:/projects",
            "updatedAt": "2026-07-09T00:00:00+00:00",
            "tasks": [{"taskId": "task-1", "title": "Task 1"}],
            "groups": [{"projectId": "task-1", "projectName": "Task 1", "taskCount": 1}],
            "sync": {"addedFolders": [], "missingWorkspaces": []},
        },
    )
    response = client.get("/api/task-battlefield/directory")
    assert response.status_code == 200
    assert response.json()["tasks"][0]["taskId"] == "task-1"


def test_task_battlefield_write_routes_require_token() -> None:
    response = client.post("/api/task-battlefield/tasks", json={"taskId": "task-1", "title": "Task 1"})
    assert response.status_code == 401
    response = client.put("/api/task-battlefield/tasks/task-1", json={"title": "Task 1"})
    assert response.status_code == 401
    response = client.delete("/api/task-battlefield/tasks/task-1")
    assert response.status_code == 401


def test_task_battlefield_write_route_uses_mock(monkeypatch) -> None:
    token = _token()
    called = {"add": False}

    def fake_add(payload):
        called["add"] = True
        return {"tasks": [payload], "groups": [], "sync": {"addedFolders": [], "missingWorkspaces": []}}

    monkeypatch.setattr(app_module.task_directory, "add_task", fake_add)
    response = client.post(
        "/api/task-battlefield/tasks",
        headers={"X-Control-Token": token},
        json={"taskId": "task-1", "title": "Task 1"},
    )
    assert response.status_code == 200
    assert called["add"] is True
    assert response.json()["tasks"][0]["taskId"] == "task-1"


def test_task_battlefield_update_tags_uses_mock(monkeypatch) -> None:
    token = _token()
    called = {"payload": None}

    def fake_update(task_id, payload):
        called["payload"] = payload
        return {
            "tasks": [{"taskId": task_id, "title": "Task 1", "tags": payload["tags"]}],
            "groups": [],
            "sync": {"addedFolders": [], "missingWorkspaces": []},
        }

    monkeypatch.setattr(app_module.task_directory, "update_task", fake_update)
    response = client.put(
        "/api/task-battlefield/tasks/task-1",
        headers={"X-Control-Token": token},
        json={"tags": ["new", "重点"]},
    )
    assert response.status_code == 200
    assert called["payload"]["tags"] == ["new", "重点"]
    assert response.json()["tasks"][0]["tags"] == ["new", "重点"]


def test_task_battlefield_classify_is_read_only_without_token(monkeypatch) -> None:
    monkeypatch.setattr(
        app_module.task_directory,
        "classify_task",
        lambda description, workspace_path=None: {
            "decision": "existing_project",
            "project": {"projectId": "alpha", "projectName": "Alpha", "taskCount": 1},
            "candidates": [],
            "suggestedWorkspacePath": "F:/projects/Alpha",
        },
    )
    response = client.post("/api/task-battlefield/classify", json={"description": "Alpha 新任务"})
    assert response.status_code == 200
    assert response.json()["decision"] == "existing_project"


def test_agent_detail_route_handles_unknown_agent(monkeypatch) -> None:
    monkeypatch.setattr(app_module.agent_dashboard, "get_agent", lambda agent_id: None)
    response = client.get("/api/agents/missing")
    assert response.status_code == 404


def test_agent_editable_config_route_is_read_only_without_token(monkeypatch) -> None:
    monkeypatch.setattr(
        app_module.agent_config_editor,
        "get_editable_config",
        lambda agent_id: {"agentId": agent_id, "values": {"AGENT_PROVIDER": "codex"}},
    )
    response = client.get("/api/agents/codex-code-agent/editable-config")
    assert response.status_code == 200
    assert response.json()["values"]["AGENT_PROVIDER"] == "codex"


def test_agent_editable_config_write_requires_token() -> None:
    response = client.put("/api/agents/codex-code-agent/editable-config", json={"values": {"AGENT_PROVIDER": "local"}})
    assert response.status_code == 401
    response = client.post("/api/agents/codex-code-agent/config-backup")
    assert response.status_code == 401
    response = client.post("/api/agents/codex-code-agent/config-rollback-latest")
    assert response.status_code == 401


def test_agent_editable_config_update_uses_mock(monkeypatch) -> None:
    token = _token()
    called = {"update": False}

    def fake_update(agent_id, values):
        called["update"] = True
        return {"ok": True, "agentId": agent_id, "values": values}

    monkeypatch.setattr(app_module.agent_config_editor, "update_editable_config", fake_update)
    response = client.put(
        "/api/agents/codex-code-agent/editable-config",
        headers={"X-Control-Token": token},
        json={"values": {"AGENT_PROVIDER": "local"}},
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert called["update"] is True


def test_explained_diagnostics_route_is_read_only_without_token(monkeypatch) -> None:
    monkeypatch.setattr(
        app_module.agent_dashboard,
        "explained_diagnostics",
        lambda: [
            ExplainedDiagnosticItem(
                id="system-normal",
                level="normal",
                title="核心链路暂无异常",
                affectedModules=["Stack"],
                status="正常",
                rawError="",
                possibleCauses=[],
                suggestions=["继续观察"],
                actions=[],
                relatedLogs=["operations"],
            )
        ],
    )
    response = client.get("/api/diagnostics/explained")
    assert response.status_code == 200
    assert response.json()["items"][0]["level"] == "normal"


def test_skill_tree_config_route_is_read_only_without_token(monkeypatch) -> None:
    monkeypatch.setattr(
        app_module.tree_config,
        "load_all_tree_configs",
        lambda: {
            "version": 2,
            "description": "mock",
            "manifestPath": "F:/repo/config/skill-tree-workshop/manifest.json",
            "agents": [
                {
                    "version": 3,
                    "agent": {"id": "coordinator", "name": "项目调度官"},
                    "nodes": [{"id": "model_base", "label": "模型基座", "nodeType": "model"}],
                    "edges": [],
                }
            ],
            "errors": [],
        },
    )
    response = client.get("/api/skill-workshop/tree-config")
    assert response.status_code == 200
    assert response.json()["agents"][0]["agent"]["id"] == "coordinator"


def test_skill_tree_agent_config_route_handles_unknown_agent(monkeypatch) -> None:
    def fake_load_agent_tree(agent_id):
        raise KeyError(agent_id)

    monkeypatch.setattr(app_module.tree_config, "load_agent_tree", fake_load_agent_tree)
    response = client.get("/api/skill-workshop/tree-config/missing")
    assert response.status_code == 404


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


def test_control_center_shutdown_requires_token() -> None:
    response = client.post("/api/control-center/shutdown")
    assert response.status_code == 401
    response = client.post("/api/control-center/shutdown", headers={"X-Control-Token": "bad"})
    assert response.status_code == 403


def test_watchdog_force_stop_requires_token() -> None:
    response = client.post("/api/watchdog/force-stop")
    assert response.status_code == 401
    response = client.post("/api/watchdog/force-stop", headers={"X-Control-Token": "bad"})
    assert response.status_code == 403


def test_watchdog_force_stop_route_uses_mock(monkeypatch) -> None:
    token = _token()
    called = {"stop": False}

    def fake_force_stop():
        called["stop"] = True
        return OperationResult(True, "watchdog", "force-stop", "mock stop", pid=456)

    monkeypatch.setattr(app_module.watchdog, "force_stop_current", fake_force_stop)
    response = client.post("/api/watchdog/force-stop", headers={"X-Control-Token": token})
    assert response.status_code == 200
    assert response.json()["component"] == "watchdog"
    assert response.json()["action"] == "force-stop"
    assert called["stop"] is True


def test_control_center_shutdown_route_uses_mock(monkeypatch) -> None:
    token = _token()
    called = {"shutdown": False}

    def fake_shutdown():
        called["shutdown"] = True
        return OperationResult(True, "control-center", "shutdown", "mock shutdown", pid=123, port=8765)

    monkeypatch.setattr(app_module.control_center, "request_shutdown", fake_shutdown)
    response = client.post("/api/control-center/shutdown", headers={"X-Control-Token": token})
    assert response.status_code == 200
    assert response.json()["component"] == "control-center"
    assert response.json()["action"] == "shutdown"
    assert called["shutdown"] is True


def test_control_center_log_route() -> None:
    response = client.get("/api/logs/control-center-api")
    assert response.status_code == 200
    assert response.json()["component"] == "control-center-api"


def test_codex_agent_stream_routes(monkeypatch, tmp_path) -> None:
    stream_dir = tmp_path / "runtime" / "streams" / "codex-agent"
    stream_dir.mkdir(parents=True)
    run_path = stream_dir / "run-1.jsonl"
    run_path.write_text(
        "\n".join(
            [
                json.dumps({"run_id": "run-1", "timestamp": "2026-07-13T00:00:00Z", "phase": "start", "stream": "stage", "text": "started", "message_id": "om_test", "chat_type": "group"}),
                json.dumps({"run_id": "run-1", "timestamp": "2026-07-13T00:00:01Z", "phase": "stdout", "stream": "stdout", "text": "hello"}),
                json.dumps({"run_id": "run-1", "timestamp": "2026-07-13T00:00:02Z", "phase": "complete", "stream": "stage", "text": "done"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(api_app_module, "load_config", lambda: SimpleNamespace(runtime_dir=tmp_path / "runtime"))

    listed = client.get("/api/codex-agent/streams")
    assert listed.status_code == 200
    assert listed.json()["streams"][0]["run_id"] == "run-1"
    assert listed.json()["streams"][0]["status"] == "complete"

    read = client.get("/api/codex-agent/streams/run-1")
    assert read.status_code == 200
    assert [event["phase"] for event in read.json()["events"]] == ["start", "stdout", "complete"]

    missing = client.get("/api/codex-agent/streams/missing")
    assert missing.status_code == 404


def test_codex_agent_stream_websocket_latest(monkeypatch, tmp_path) -> None:
    stream_dir = tmp_path / "runtime" / "streams" / "codex-agent"
    stream_dir.mkdir(parents=True)
    (stream_dir / "run-2.jsonl").write_text(
        json.dumps({"run_id": "run-2", "timestamp": "2026-07-13T00:00:00Z", "phase": "start", "stream": "stage", "text": "started"}) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(api_app_module, "load_config", lambda: SimpleNamespace(runtime_dir=tmp_path / "runtime"))

    with client.websocket_connect("/ws/codex-agent/stream?run_id=latest") as websocket:
        message = websocket.receive_json()
        assert message["type"] == "event"
        assert message["run_id"] == "run-2"
        assert message["event"]["phase"] == "start"


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


def test_get_log_level_default() -> None:
    response = client.get("/api/logs/level")
    assert response.status_code == 200
    data = response.json()
    assert "logger" in data
    assert "level" in data


def test_get_log_level_specific() -> None:
    response = client.get("/api/logs/level?logger=uvicorn")
    assert response.status_code == 200
    data = response.json()
    assert data["logger"] == "uvicorn"
    assert data["level"] in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


def test_set_log_level_requires_token() -> None:
    response = client.post("/api/logs/level", json={"level": "DEBUG"})
    assert response.status_code == 401


def test_set_log_level_invalid_value() -> None:
    token = _token()
    response = client.post(
        "/api/logs/level",
        headers={"X-Control-Token": token},
        json={"level": "VERBOSE"},
    )
    assert response.status_code == 400


def test_set_log_level_success() -> None:
    token = _token()
    response = client.post(
        "/api/logs/level",
        headers={"X-Control-Token": token},
        json={"level": "DEBUG"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["level"] == "DEBUG"


def test_error_response_format() -> None:
    response = client.post("/api/openclaw/start")
    assert response.status_code == 401
    data = response.json()
    assert "error_code" in data
    assert "message" in data
    assert data["error_code"] == "HTTP_401"


def test_validation_error_format() -> None:
    token = _token()
    response = client.post(
        "/api/thread-migration/migrate",
        headers={"X-Control-Token": token},
        json={"bad_key": "no_session_id"},
    )
    assert response.status_code == 422
    data = response.json()
    assert data["error_code"] == "VALIDATION_ERROR"
    assert isinstance(data["detail"], list)
