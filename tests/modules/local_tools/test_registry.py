from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch
import json

from feishu_stack.core.models import ComponentStatus
from feishu_stack.core.settings import LocalToolSettings
from feishu_stack.modules.local_tools import registry


def _cfg(tmp_path: Path):
    cfg = MagicMock()
    cfg.local_tools = [
        LocalToolSettings(
            id="demo-tool",
            name="Demo Tool",
            description="Demo",
            dir=tmp_path,
            entry=tmp_path / "app.py",
            command=["python", "app.py"],
            host="127.0.0.1",
            port=8123,
            url="http://127.0.0.1:8123",
            health_path="/api/health",
            tags=["demo"],
        )
    ]
    cfg.local_tool_pid.side_effect = lambda tool_id: tmp_path / f"{tool_id}.pid"
    cfg.local_tool_stdout_log.side_effect = lambda tool_id: tmp_path / f"{tool_id}-out.log"
    cfg.local_tool_stderr_log.side_effect = lambda tool_id: tmp_path / f"{tool_id}-err.log"
    return cfg


def test_list_tools_returns_registered_tool(tmp_path):
    cfg = _cfg(tmp_path)
    with (
        patch("feishu_stack.modules.local_tools.registry.is_port_listening", return_value=False),
        patch("feishu_stack.modules.local_tools.registry.component_status") as mock_status,
    ):
        mock_status.return_value = ComponentStatus(
            name="local-tool:demo-tool",
            port=8123,
            port_listening=False,
            pid_file=str(tmp_path / "demo-tool.pid"),
            pid=None,
            pid_running=False,
            process_name=None,
        )
        tools = registry.list_tools(cfg)

    assert tools[0]["id"] == "demo-tool"
    assert tools[0]["name"] == "Demo Tool"
    assert tools[0]["url"] == "http://127.0.0.1:8123"


def test_start_uses_registered_command_and_writes_pid(tmp_path):
    cfg = _cfg(tmp_path)
    with (
        patch("feishu_stack.modules.local_tools.registry.is_port_listening", return_value=False),
        patch("feishu_stack.modules.local_tools.registry.start_process") as mock_start,
        patch("feishu_stack.modules.local_tools.registry.write_pid") as mock_write_pid,
        patch("feishu_stack.modules.local_tools.registry.wait_for_port", return_value=True),
    ):
        mock_start.return_value = MagicMock(pid=1234)
        result = registry.start("demo-tool", cfg)

    assert result.ok is True
    assert result.pid == 1234
    mock_start.assert_called_once()
    assert mock_start.call_args.args[0] == ["python", "app.py"]
    mock_write_pid.assert_called_once()


def test_stop_delegates_to_stop_component(tmp_path):
    cfg = _cfg(tmp_path)
    with patch("feishu_stack.modules.local_tools.registry.stop_component") as mock_stop:
        mock_stop.return_value = MagicMock(ok=True, component="local-tool:demo-tool", action="stop", message="stopped")
        result = registry.stop("demo-tool", cfg)

    assert result.ok is True
    assert result.component == "local-tool:demo-tool"
    assert result.action == "stop"
    mock_stop.assert_called_once()
    call_args = mock_stop.call_args
    assert call_args.args[0] == "local-tool:demo-tool"
    assert call_args.args[1] == cfg.local_tool_pid("demo-tool")


def test_restart_stops_then_starts(tmp_path):
    cfg = _cfg(tmp_path)
    with (
        patch("feishu_stack.modules.local_tools.registry.stop") as mock_stop,
        patch("feishu_stack.modules.local_tools.registry.start") as mock_start,
    ):
        mock_stop.return_value = MagicMock(ok=True, component="local-tool:demo-tool", message="stopped")
        mock_start.return_value = MagicMock(ok=True, component="local-tool:demo-tool", pid=5678, port=8123, message="started")
        result = registry.restart("demo-tool", cfg)

    assert result.ok is True
    assert result.component == "local-tool:demo-tool"
    mock_stop.assert_called_once()
    mock_start.assert_called_once()


def test_get_tool_status_returns_tool_info(tmp_path):
    cfg = _cfg(tmp_path)
    with (
        patch("feishu_stack.modules.local_tools.registry.is_port_listening", return_value=False),
        patch("feishu_stack.modules.local_tools.registry.component_status") as mock_status,
    ):
        mock_status.return_value = ComponentStatus(
            name="local-tool:demo-tool", port=8123, port_listening=False,
            pid_file=str(tmp_path / "demo-tool.pid"), pid=None, pid_running=False, process_name=None,
        )
        status = registry.get_tool_status("demo-tool", cfg)

    assert status["id"] == "demo-tool"
    assert status["name"] == "Demo Tool"
    assert status["port"] == 8123
    assert status["url"] == "http://127.0.0.1:8123"


def test_start_disabled_tool_returns_error(tmp_path):
    cfg = _cfg(tmp_path)
    cfg.local_tools[0] = LocalToolSettings(
        id="disabled-tool", name="Disabled", description="Nope",
        dir=tmp_path, entry=tmp_path / "app.py", command=["python", "app.py"],
        host="127.0.0.1", port=9999, url="http://127.0.0.1:9999",
        health_path="/health", enabled=False, tags=[],
    )
    with patch("feishu_stack.modules.local_tools.registry.is_port_listening", return_value=False):
        result = registry.start("disabled-tool", cfg)

    assert result.ok is False
    assert "disabled" in result.message


def test_start_injects_acc_tool_environment(tmp_path):
    cfg = _cfg(tmp_path)
    with (
        patch("feishu_stack.modules.local_tools.registry.is_port_listening", return_value=False),
        patch("feishu_stack.modules.local_tools.registry.start_process") as mock_start,
        patch("feishu_stack.modules.local_tools.registry.write_pid"),
        patch("feishu_stack.modules.local_tools.registry.wait_for_port", return_value=True),
    ):
        mock_start.return_value = MagicMock(pid=4321)
        registry.start("demo-tool", cfg)

    env = mock_start.call_args.kwargs["env"]
    assert env["ACC_TOOL_ID"] == "demo-tool"
    assert env["ACC_TOOL_HOST"] == "127.0.0.1"
    assert env["ACC_TOOL_PORT"] == "8123"
    assert env["ACC_TOOL_ENTRY"] == str(tmp_path / "app.py")


def test_scan_finds_manifest_candidate(tmp_path):
    tool_dir = tmp_path / "TOOLS" / "calendar-tool"
    tool_dir.mkdir(parents=True)
    (tool_dir / "acc.local-tool.json").write_text(
        json.dumps({"id": "calendar-tool", "name": "日历工具", "entry": "app.py", "port": 8010}, ensure_ascii=False),
        encoding="utf-8",
    )
    cfg = MagicMock()
    cfg.stack_root = tmp_path
    cfg.projects_root = None
    cfg.local_tools = []

    candidates = registry.scan(config=cfg)

    assert candidates[0]["id"] == "calendar-tool"
    assert candidates[0]["manifest"] == "acc.local-tool.json"
    assert candidates[0]["registered"] is False


def test_register_writes_local_tool_to_settings(tmp_path):
    settings = tmp_path / "config" / "stack.settings.local.json"
    settings.parent.mkdir(parents=True)
    settings.write_text(json.dumps({"stackRoot": str(tmp_path)}, ensure_ascii=False), encoding="utf-8")
    tool_dir = tmp_path / "TOOLS" / "calendar-tool"
    tool_dir.mkdir(parents=True)

    with patch("feishu_stack.modules.local_tools.registry.resolve_settings_path", return_value=settings):
        result = registry.register(
            {
                "id": "calendar-tool",
                "name": "日历工具",
                "dir": str(tool_dir),
                "entry": "app.py",
                "port": 8010,
                "manifest": "acc.local-tool.json",
            }
        )

    data = json.loads(settings.read_text(encoding="utf-8"))
    assert result["ok"] is True
    assert data["localTools"]["tools"][0]["id"] == "calendar-tool"
    assert data["localTools"]["tools"][0]["dir"] == str(tool_dir)
