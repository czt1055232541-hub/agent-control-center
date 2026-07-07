from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from feishu_stack.models import CodexDesktopStatus, OperationResult


def _fake_config(**overrides):
    c = MagicMock()
    c.codex_home = Path(tempfile.gettempdir()) / 'codex'
    c.codex_bin = Path('codex.exe')
    c.stack_root = Path(tempfile.gettempdir()) / 'stack'
    c.log_dir = Path(tempfile.gettempdir()) / 'log'
    c.runtime_dir = Path(tempfile.gettempdir()) / 'runtime'
    for k, v in overrides.items():
        setattr(c, k, v)
    return c


class CodexDesktopInstallLocationTests(unittest.TestCase):
    def test_found(self):
        with patch('feishu_stack.modules.model_provider.codex_desktop._install_location_from_registry', return_value=r'C:\Program Files\OpenAI.Codex'):
            from feishu_stack.modules.model_provider.codex_desktop import _install_location
            loc = _install_location()
            self.assertEqual(loc, r'C:\Program Files\OpenAI.Codex')

    def test_not_found(self):
        with (
            patch('feishu_stack.modules.model_provider.codex_desktop._install_location_from_registry', return_value=None),
            patch('feishu_stack.modules.model_provider.codex_desktop._install_location_from_appx_package', return_value=None),
            patch('feishu_stack.modules.model_provider.codex_desktop._install_location_from_windowsapps', return_value=None),
        ):
            from feishu_stack.modules.model_provider.codex_desktop import _install_location
            loc = _install_location()
            self.assertIsNone(loc)

    def test_appx_fallback(self):
        with (
            patch('feishu_stack.modules.model_provider.codex_desktop._install_location_from_registry', return_value=None),
            patch('feishu_stack.modules.model_provider.codex_desktop._install_location_from_appx_package', return_value=r'C:\Program Files\WindowsApps\OpenAI.Codex_1'),
        ):
            from feishu_stack.modules.model_provider.codex_desktop import _install_location
            loc = _install_location()
            self.assertEqual(loc, r'C:\Program Files\WindowsApps\OpenAI.Codex_1')


class CodexDesktopExecutablePathTests(unittest.TestCase):
    def test_from_status(self):
        status = CodexDesktopStatus(running=False, pid=None, process_count=0, executable=r'C:\Codex\app\Codex.exe')
        with patch('feishu_stack.modules.model_provider.codex_desktop.codex_desktop_status', return_value=status):
            from feishu_stack.modules.model_provider.codex_desktop import _executable_path
            exe = _executable_path()
            self.assertEqual(exe, r'C:\Codex\app\Codex.exe')

    def test_fallback_install_location(self):
        status = CodexDesktopStatus(running=False, pid=None, process_count=0, executable=None)
        with (
            patch('feishu_stack.modules.model_provider.codex_desktop.codex_desktop_status', return_value=status),
            patch('feishu_stack.modules.model_provider.codex_desktop._install_location', return_value=None),
        ):
            from feishu_stack.modules.model_provider.codex_desktop import _executable_path
            exe = _executable_path()
            self.assertIsNone(exe)

    def test_fallback_cached_executable(self):
        status = CodexDesktopStatus(running=False, pid=None, process_count=0, executable=None)
        with tempfile.TemporaryDirectory() as tmp:
            exe_path = Path(tmp) / 'Codex.exe'
            exe_path.write_text('stub', encoding='utf-8')
            cache_path = Path(tmp) / 'codex-desktop-executable.txt'
            cache_path.write_text(str(exe_path), encoding='utf-8')
            cfg = _fake_config(runtime_dir=Path(tmp))
            with (
                patch('feishu_stack.modules.model_provider.codex_desktop.codex_desktop_status', return_value=status),
                patch('feishu_stack.modules.model_provider.codex_desktop._install_location', return_value=None),
            ):
                from feishu_stack.modules.model_provider.codex_desktop import _executable_path
                exe = _executable_path(cfg)
                self.assertEqual(exe, str(exe_path))


class CodexDesktopStartTests(unittest.TestCase):
    def test_already_running(self):
        status = CodexDesktopStatus(running=True, pid=100, process_count=1, executable='codex.exe')
        with patch('feishu_stack.modules.model_provider.codex_desktop.codex_desktop_status', return_value=status):
            from feishu_stack.modules.model_provider.codex_desktop import start
            result = start(_fake_config())
            self.assertTrue(result.ok)
            self.assertIn('already running', result.message)

    def test_no_executable(self):
        status = CodexDesktopStatus(running=False, pid=None, process_count=0, executable=None)
        with (
            patch('feishu_stack.modules.model_provider.codex_desktop.codex_desktop_status', return_value=status),
            patch('feishu_stack.modules.model_provider.codex_desktop._executable_path', return_value=None),
        ):
            from feishu_stack.modules.model_provider.codex_desktop import start
            result = start(_fake_config())
            self.assertFalse(result.ok)
            self.assertIn('Could not locate', result.message)

    def test_start_becomes_ready(self):
        not_running = CodexDesktopStatus(running=False, pid=None, process_count=0, executable=None)
        running = CodexDesktopStatus(running=True, pid=200, process_count=1, executable='codex.exe')
        with (
            patch('feishu_stack.modules.model_provider.codex_desktop.codex_desktop_status', side_effect=[not_running, running]),
            patch('feishu_stack.modules.model_provider.codex_desktop._executable_path', return_value='C:\\Codex\\Codex.exe'),
            patch('subprocess.Popen') as mock_popen,
            patch('feishu_stack.modules.model_provider.codex_desktop.time.sleep'),
        ):
            from feishu_stack.modules.model_provider.codex_desktop import start
            cfg = _fake_config()
            result = start(cfg)
            self.assertTrue(result.ok)
            self.assertEqual(result.pid, 200)
            mock_popen.assert_called_once()

    def test_start_not_ready(self):
        status = CodexDesktopStatus(running=False, pid=None, process_count=0, executable=None)
        with (
            patch('feishu_stack.modules.model_provider.codex_desktop.codex_desktop_status', return_value=status),
            patch('feishu_stack.modules.model_provider.codex_desktop._executable_path', return_value='C:\\Codex\\Codex.exe'),
            patch('subprocess.Popen'),
            patch('feishu_stack.modules.model_provider.codex_desktop.time.sleep'),
        ):
            from feishu_stack.modules.model_provider.codex_desktop import start
            result = start(_fake_config())
            self.assertFalse(result.ok)
            self.assertIn('did not become ready', result.message)


class CodexDesktopStopTests(unittest.TestCase):
    def test_stop_success(self):
        import subprocess
        with (
            patch.dict('os.environ', {'AGENT_CONTROL_CENTER_ALLOW_CODEX_DESKTOP_STOP': '1'}),
            patch('subprocess.run') as mock_run,
            patch('feishu_stack.modules.model_provider.codex_desktop.is_codex_desktop_running', return_value=False),
        ):
            mock_run.return_value = subprocess.CompletedProcess([], 0, 'SUCCESS', '')
            from feishu_stack.modules.model_provider.codex_desktop import stop
            result = stop(_fake_config())
            self.assertTrue(result.ok)

    def test_stop_failure(self):
        import subprocess
        with (
            patch.dict('os.environ', {'AGENT_CONTROL_CENTER_ALLOW_CODEX_DESKTOP_STOP': '1'}),
            patch('subprocess.run') as mock_run,
            patch('feishu_stack.modules.model_provider.codex_desktop.is_codex_desktop_running', return_value=True),
        ):
            mock_run.return_value = subprocess.CompletedProcess([], 1, '', 'error')
            from feishu_stack.modules.model_provider.codex_desktop import stop
            result = stop(_fake_config())
            self.assertFalse(result.ok)


class CodexDesktopRestartTests(unittest.TestCase):
    def test_restart(self):
        cfg = _fake_config()
        with (
            patch('feishu_stack.modules.model_provider.codex_desktop.stop') as mock_stop,
            patch('feishu_stack.modules.model_provider.codex_desktop.start') as mock_start,
        ):
            mock_stop.return_value = OperationResult(True, 'x', 'stop', 'ok')
            mock_start.return_value = OperationResult(True, 'x', 'start', 'ok')
            from feishu_stack.modules.model_provider.codex_desktop import restart
            result = restart(cfg)
            self.assertTrue(result.ok)
            self.assertEqual(result.action, 'restart')


class CodexDesktopLogTests(unittest.TestCase):
    def test_log_writes_and_tails(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = _fake_config()
            cfg.log_dir = Path(tmp)
            status = CodexDesktopStatus(running=True, pid=100, process_count=1, executable=r'C:\Codex\Codex.exe')
            with patch('feishu_stack.modules.model_provider.codex_desktop.codex_desktop_status', return_value=status):
                from feishu_stack.modules.model_provider.codex_desktop import log
                result = log(cfg)
                self.assertIn('running=True', result.lines)
                self.assertIn('pid=100', result.lines)
