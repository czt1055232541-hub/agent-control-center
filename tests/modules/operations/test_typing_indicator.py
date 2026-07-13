from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from feishu_stack.models import OperationResult


def _fake_config(**overrides):
    c = MagicMock()
    c.pid_typing_indicator = Path(tempfile.gettempdir()) / 'pid' / 'typing-indicator.pid'
    c.typing_indicator_dir = Path(tempfile.gettempdir()) / 'ti'
    c.typing_indicator_launcher = c.typing_indicator_dir / 'launcher.py'
    c.typing_indicator_stdout_log = Path(tempfile.gettempdir()) / 'log' / 'ti-out.log'
    c.typing_indicator_stderr_log = Path(tempfile.gettempdir()) / 'log' / 'ti-err.log'
    c.python_exe = 'python.exe'
    c.lark_cli_bin = Path('lark-cli.exe')
    c.raw = {}
    for k, v in overrides.items():
        setattr(c, k, v)
    return c


class TypingIndicatorStartTests(unittest.TestCase):
    def test_already_running(self):
        cfg = _fake_config()
        with (
            patch('feishu_stack.modules.operations.typing_indicator.read_pid', return_value=123),
            patch('psutil.Process') as mock_psutil,
        ):
            mock_proc = MagicMock()
            mock_proc.is_running.return_value = True
            mock_psutil.return_value = mock_proc
            from feishu_stack.modules.operations.typing_indicator import start
            result = start(cfg)
            self.assertTrue(result.ok)
            self.assertIn('already running', result.message)

    def test_start_success(self):
        cfg = _fake_config()
        with (
            patch('feishu_stack.modules.operations.typing_indicator.read_pid', return_value=None),
            patch('feishu_stack.modules.operations.typing_indicator.start_process') as mock_sp,
            patch('feishu_stack.modules.operations.typing_indicator.write_pid'),
            patch('feishu_stack.modules.operations.typing_indicator.time.sleep'),
            patch('psutil.Process') as mock_psutil,
        ):
            mock_sp.return_value = MagicMock(pid=5678)
            mock_proc = MagicMock()
            mock_proc.is_running.return_value = True
            mock_psutil.return_value = mock_proc
            from feishu_stack.modules.operations.typing_indicator import start
            result = start(cfg)
            self.assertTrue(result.ok)
            self.assertEqual(result.pid, 5678)
            self.assertIn('started', result.message)
            env = mock_sp.call_args.kwargs['env']
            self.assertEqual(env['PYTHON_EXE'], str(cfg.python_exe))
            self.assertEqual(env['LARK_CLI_BIN'], str(cfg.lark_cli_bin))
            self.assertNotIn('OPENCLAW_HOME', env)

    def test_start_exits_during_startup(self):
        cfg = _fake_config()
        with (
            patch('feishu_stack.modules.operations.typing_indicator.read_pid', return_value=None),
            patch('feishu_stack.modules.operations.typing_indicator.start_process') as mock_sp,
            patch('feishu_stack.modules.operations.typing_indicator.write_pid'),
            patch('feishu_stack.modules.operations.typing_indicator.time.sleep'),
        ):
            mock_sp.return_value = MagicMock(pid=5678)
            from feishu_stack.modules.operations.typing_indicator import start
            import psutil
            with patch('psutil.Process', side_effect=psutil.NoSuchProcess(5678)):
                result = start(cfg)
                self.assertFalse(result.ok)
                self.assertIn('exited', result.message)


class TypingIndicatorStopTests(unittest.TestCase):
    def test_stop(self):
        cfg = _fake_config()
        with patch('feishu_stack.modules.operations.typing_indicator.stop_component') as mock_stop:
            mock_stop.return_value = OperationResult(True, 'typing-indicator', 'stop', 'stopped')
            from feishu_stack.modules.operations.typing_indicator import stop
            result = stop(cfg)
            self.assertTrue(result.ok)
            mock_stop.assert_called_once_with(
                'typing-indicator',
                cfg.pid_typing_indicator,
                None,
                expected_process_markers=('typing-indicator', 'launcher.py'),
            )


class TypingIndicatorRestartTests(unittest.TestCase):
    def test_restart(self):
        cfg = _fake_config()
        with (
            patch('feishu_stack.modules.operations.typing_indicator.stop') as mock_stop,
            patch('feishu_stack.modules.operations.typing_indicator.start') as mock_start,
        ):
            mock_stop.return_value = OperationResult(True, 'x', 'stop', 'ok')
            mock_start.return_value = OperationResult(True, 'x', 'start', 'ok')
            from feishu_stack.modules.operations.typing_indicator import restart
            result = restart(cfg)
            self.assertTrue(result.ok)
            self.assertEqual(result.action, 'restart')
