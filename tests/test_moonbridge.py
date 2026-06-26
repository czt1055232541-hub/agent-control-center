from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from feishu_stack.models import OperationResult


def _fake_config(**overrides):
    c = MagicMock()
    c.stack_root = Path(tempfile.gettempdir())
    c.moonbridge_config = c.stack_root / "moonbridge.yaml"
    c.moonbridge_port = 38440
    c.moonbridge_exe = Path("moonbridge.exe")
    c.moonbridge_dir = Path("moonbridge_dir")
    c.moonbridge_stdout_log = c.stack_root / "log" / "mb-out.log"
    c.moonbridge_stderr_log = c.stack_root / "log" / "mb-err.log"
    c.pid_moonbridge = c.stack_root / "pid" / "moonbridge.pid"
    for k, v in overrides.items():
        setattr(c, k, v)
    return c


class MoonBridgeGetModelsTests(unittest.TestCase):
    def test_get_available_models(self):
        yaml_data = {"models": {"gpt-4o": {}, "claude-sonnet": {}}}
        with patch("feishu_stack.moonbridge._read_moonbridge_yaml", return_value=yaml_data):
            from feishu_stack.moonbridge import get_available_models
            result = get_available_models(_fake_config())
            self.assertEqual(result, ["gpt-4o", "claude-sonnet"])

    def test_get_available_models_empty(self):
        with patch("feishu_stack.moonbridge._read_moonbridge_yaml", return_value={}):
            from feishu_stack.moonbridge import get_available_models
            result = get_available_models(_fake_config())
            self.assertEqual(result, [])


class MoonBridgeSwitchModelTests(unittest.TestCase):
    def test_switch_to_unknown_model(self):
        yaml_data = {"models": {"gpt-4o": {}}}
        with patch("feishu_stack.moonbridge._read_moonbridge_yaml", return_value=yaml_data):
            from feishu_stack.moonbridge import switch_model
            result = switch_model("claude-opus", _fake_config())
            self.assertFalse(result.ok)
            self.assertIn("Unknown model", result.message)

    def test_switch_to_same_model(self):
        yaml_data = {"models": {"gpt-4o": {}}, "routes": {"moonbridge": {"model": "gpt-4o"}}}
        with patch("feishu_stack.moonbridge._read_moonbridge_yaml", return_value=yaml_data):
            from feishu_stack.moonbridge import switch_model
            result = switch_model("gpt-4o", _fake_config())
            self.assertTrue(result.ok)
            self.assertIn("already", result.message)

    def test_switch_model_success(self):
        yaml_data = {"models": {"gpt-4o": {}, "claude-sonnet": {}}, "routes": {"moonbridge": {"model": "gpt-4o"}}}
        settings_path = Path(tempfile.gettempdir()) / "stack.settings.json"
        with (
            patch("feishu_stack.moonbridge._read_moonbridge_yaml", return_value=yaml_data) as mock_read,
            patch("feishu_stack.moonbridge._write_moonbridge_yaml") as mock_write,
            patch("feishu_stack.moonbridge._get_settings_path", return_value=settings_path),
            patch("feishu_stack.moonbridge.restart") as mock_restart,
            patch("feishu_stack.status.read_provider_status") as mock_prov_status,
        ):
            cfg = _fake_config()
            mock_restart.return_value = OperationResult(True, "moonbridge", "restart", "ok")
            mock_prov_status.return_value = MagicMock(mode="native")
            from feishu_stack.moonbridge import switch_model
            result = switch_model("claude-sonnet", cfg)
            self.assertTrue(result.ok)
            self.assertIn("Switched", result.message)
            mock_write.assert_called_once()
            mock_restart.assert_called_once_with(cfg)


class MoonBridgeStartStopTests(unittest.TestCase):
    def test_start_already_listening(self):
        with patch("feishu_stack.moonbridge.is_port_listening", return_value=True):
            from feishu_stack.moonbridge import start
            result = start(_fake_config())
            self.assertTrue(result.ok)
            self.assertIn("already", result.message)

    def test_start_fresh(self):
        with (
            patch("feishu_stack.moonbridge.is_port_listening", return_value=False),
            patch("feishu_stack.moonbridge.start_process") as mock_sp,
            patch("feishu_stack.moonbridge.write_pid"),
            patch("feishu_stack.moonbridge.wait_for_port", return_value=True),
        ):
            mock_sp.return_value = MagicMock(pid=12345)
            from feishu_stack.moonbridge import start
            result = start(_fake_config())
            self.assertTrue(result.ok)
            self.assertEqual(result.pid, 12345)

    def test_stop(self):
        with patch("feishu_stack.moonbridge.stop_component") as mock_stop:
            mock_stop.return_value = OperationResult(True, "moonbridge", "stop", "stopped")
            from feishu_stack.moonbridge import stop
            result = stop(_fake_config())
            self.assertTrue(result.ok)
            mock_stop.assert_called_once()

    def test_restart(self):
        with (
            patch("feishu_stack.moonbridge.stop") as mock_stop,
            patch("feishu_stack.moonbridge.start") as mock_start,
        ):
            mock_stop.return_value = OperationResult(True, "moonbridge", "stop", "stopped")
            mock_start.return_value = OperationResult(True, "moonbridge", "start", "started")
            from feishu_stack.moonbridge import restart
            result = restart(_fake_config())
            self.assertTrue(result.ok)
            self.assertEqual(result.action, "restart")
            mock_stop.assert_called_once()
            mock_start.assert_called_once()

    def test_start_not_ready(self):
        with (
            patch("feishu_stack.moonbridge.is_port_listening", return_value=False),
            patch("feishu_stack.moonbridge.start_process") as mock_sp,
            patch("feishu_stack.moonbridge.write_pid"),
            patch("feishu_stack.moonbridge.wait_for_port", return_value=False),
        ):
            mock_sp.return_value = MagicMock(pid=12345)
            from feishu_stack.moonbridge import start
            result = start(_fake_config())
            self.assertFalse(result.ok)
            self.assertIn("did not become ready", result.message)
