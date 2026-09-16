from __future__ import annotations

import tempfile
import unittest
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from feishu_stack.models import OperationResult


def _fake_config(**overrides):
    c = MagicMock()
    c.agent_dir = Path(tempfile.gettempdir()) / 'agent'
    c.agent_entry = c.agent_dir / 'dist' / 'src' / 'index.js'
    c.pid_codex_agent = Path(tempfile.gettempdir()) / 'pid' / 'codex-agent.pid'
    c.codex_agent_stdout_log = Path(tempfile.gettempdir()) / 'log' / 'agent-out.log'
    c.codex_agent_stderr_log = Path(tempfile.gettempdir()) / 'log' / 'agent-err.log'
    c.codex_home = Path(tempfile.gettempdir()) / 'codex'
    c.codex_bin = Path('codex.exe')
    c.node_exe = Path('node.exe')
    c.npm_exe = Path('npm.cmd')
    c.stack_root = Path(tempfile.gettempdir()) / 'stack'
    c.lark_cli_bin = Path('lark-cli')
    c.lark_cli_home = Path(tempfile.gettempdir()) / '.home'
    c.agent = SimpleNamespace(
        provider="codex",
        codex_home=Path(tempfile.gettempdir()) / 'agent-codex',
        codex_config=Path(tempfile.gettempdir()) / 'agent-codex' / 'config.toml',
        codex_agent_args="exec --skip-git-repo-check",
        lark_bot_open_id="",
        a2a_bots=[],
        a2a_relay=SimpleNamespace(
            enabled=False,
            group_chat_id="",
            peer_name="",
            peer_open_id="",
            peer_cli_home="",
        ),
    )
    c.deepseek = SimpleNamespace(env_key="DEEPSEEK_API_KEY")
    c.raw = {}
    for k, v in overrides.items():
        setattr(c, k, v)
    return c


class CodexAgentBuildTests(unittest.TestCase):
    def test_already_built(self):
        cfg = _fake_config()
        with patch('feishu_stack.modules.model_provider.codex_agent._needs_build', return_value=(False, 'Codex Agent is already built.')):
            from feishu_stack.modules.model_provider.codex_agent import _build_if_needed
            ok, msg = _build_if_needed(cfg)
        self.assertTrue(ok)
        self.assertIn('already built', msg)

    def test_build_failure(self):
        import subprocess
        cfg = _fake_config()
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = subprocess.CompletedProcess([], 1, '', 'npm error')
            with patch('feishu_stack.modules.model_provider.codex_agent._needs_build', return_value=(True, 'missing')):
                from feishu_stack.modules.model_provider.codex_agent import _build_if_needed
                ok, msg = _build_if_needed(cfg)
            self.assertFalse(ok)
            self.assertIn('npm error', msg)

    def test_build_success(self):
        import subprocess
        cfg = _fake_config()
        cfg.agent_entry = MagicMock()
        cfg.agent_entry.exists.return_value = True
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = subprocess.CompletedProcess([], 0, '', '')
            with patch('feishu_stack.modules.model_provider.codex_agent._needs_build', return_value=(True, 'missing')):
                from feishu_stack.modules.model_provider.codex_agent import _build_if_needed
                ok, msg = _build_if_needed(cfg)
            self.assertTrue(ok)
            self.assertEqual(mock_run.call_count, 2)
            self.assertEqual(mock_run.call_args_list[0].args[0][0], str(cfg.npm_exe))

    def test_needs_build_when_source_is_newer(self):
        cfg = _fake_config()
        with tempfile.TemporaryDirectory() as tmp:
            cfg.agent_dir = Path(tmp)
            src = cfg.agent_dir / 'src'
            dist = cfg.agent_dir / 'dist' / 'src'
            src.mkdir()
            dist.mkdir(parents=True)
            cfg.agent_entry = dist / 'index.js'
            cfg.agent_entry.write_text('built', encoding='utf-8')
            (src / 'index.ts').write_text('source', encoding='utf-8')
            os.utime(cfg.agent_entry, (100, 100))
            os.utime(src / 'index.ts', (200, 200))

            from feishu_stack.modules.model_provider.codex_agent import _needs_build
            ok, msg = _needs_build(cfg)

        self.assertTrue(ok)
        self.assertIn('src', msg)


class CodexAgentEnvTests(unittest.TestCase):
    def test_build_agent_env_removes_agent_source_detection_vars(self):
        cfg = _fake_config(codex_bin=Path(r'C:\Codex\current\codex.exe'))
        with patch.dict(
            'os.environ',
            {
                'OPENCLAW_HOME': r'C:\openclaw',
                'CLAW_HOME': r'C:\openclaw',
                'HERMES_HOME': r'C:\hermes',
                'LARK_CHANNEL': 'enabled',
            },
            clear=False,
        ):
            from feishu_stack.modules.model_provider.codex_agent import _build_agent_env
            env = _build_agent_env(cfg)

        self.assertEqual(env['CODEX_CLI_BIN'], r'C:\Codex\current\codex.exe')
        self.assertEqual(env['CODEX_CLI_PATH'], r'C:\Codex\current\codex.exe')
        self.assertEqual(env['CODEX_HOME'], str(cfg.agent.codex_home))
        self.assertEqual(env['HOME'], str(cfg.lark_cli_home))
        self.assertEqual(env['LARK_CLI_CWD'], str(cfg.stack_root))
        self.assertNotIn('OPENCLAW_HOME', env)
        self.assertNotIn('CLAW_HOME', env)
        self.assertNotIn('HERMES_HOME', env)
        self.assertNotIn('LARK_CHANNEL', env)

    def test_build_agent_env_uses_windows_registry_fallback_for_deepseek_key(self):
        cfg = _fake_config(codex_bin=Path(r'C:\Codex\current\codex.exe'))
        with (
            patch.dict('os.environ', {}, clear=True),
            patch('feishu_stack.core.env._windows_registry_env_value', return_value='test-key'),
        ):
            from feishu_stack.modules.model_provider.codex_agent import _build_agent_env
            env = _build_agent_env(cfg)

        self.assertEqual(env['DEEPSEEK_API_KEY'], 'test-key')


class CodexAgentStartTests(unittest.TestCase):
    def test_already_running(self):
        cfg = _fake_config()
        with (
            patch('feishu_stack.modules.model_provider.codex_agent.read_pid', return_value=123),
            patch('feishu_stack.modules.model_provider.codex_agent.process_info', return_value=(True, 'node.exe')),
        ):
            from feishu_stack.modules.model_provider.codex_agent import start
            result = start(cfg)
            self.assertTrue(result.ok)
            self.assertIn('already running', result.message)

    def test_build_fails(self):
        cfg = _fake_config()
        with (
            patch('feishu_stack.modules.model_provider.codex_agent.read_pid', return_value=None),
            patch('feishu_stack.modules.model_provider.codex_agent.process_info', return_value=(False, None)),
            patch('feishu_stack.modules.model_provider.codex_agent.codex_config._bootstrap_agent_config'),
            patch('feishu_stack.modules.model_provider.codex_agent._build_if_needed', return_value=(False, 'build error')),
        ):
            from feishu_stack.modules.model_provider.codex_agent import start
            result = start(cfg)
            self.assertFalse(result.ok)
            self.assertIn('build error', result.message)

    def test_start_success(self):
        cfg = _fake_config()
        with (
            patch('feishu_stack.modules.model_provider.codex_agent.read_pid', return_value=None),
            patch('feishu_stack.modules.model_provider.codex_agent.process_info', side_effect=[(False, None), (True, 'node.exe')]),
            patch('feishu_stack.modules.model_provider.codex_agent.codex_config._bootstrap_agent_config'),
            patch('feishu_stack.modules.model_provider.codex_agent._build_if_needed', return_value=(True, 'built')),
            patch('feishu_stack.modules.model_provider.codex_agent.start_process') as mock_sp,
            patch('feishu_stack.modules.model_provider.codex_agent.write_pid'),
            patch('feishu_stack.modules.model_provider.codex_agent.time.sleep'),
        ):
            mock_sp.return_value = MagicMock(pid=4567)
            from feishu_stack.modules.model_provider.codex_agent import start
            result = start(cfg)
            self.assertTrue(result.ok)
            self.assertEqual(result.pid, 4567)
            self.assertEqual(mock_sp.call_args.args[0][0], str(cfg.node_exe))
            env = mock_sp.call_args.kwargs['env']
            self.assertEqual(env['CODEX_CLI_BIN'], str(cfg.codex_bin))
            self.assertEqual(env['CODEX_CLI_PATH'], str(cfg.codex_bin))
            self.assertEqual(env['CODEX_HOME'], str(cfg.agent.codex_home))
            self.assertNotIn('OPENCLAW_HOME', env)

    def test_start_exits_during_startup(self):
        cfg = _fake_config()
        with (
            patch('feishu_stack.modules.model_provider.codex_agent.read_pid', return_value=None),
            patch('feishu_stack.modules.model_provider.codex_agent.process_info', side_effect=[(False, None), (False, None)]),
            patch('feishu_stack.modules.model_provider.codex_agent.codex_config._bootstrap_agent_config'),
            patch('feishu_stack.modules.model_provider.codex_agent._build_if_needed', return_value=(True, 'built')),
            patch('feishu_stack.modules.model_provider.codex_agent.start_process') as mock_sp,
            patch('feishu_stack.modules.model_provider.codex_agent.write_pid'),
            patch('feishu_stack.modules.model_provider.codex_agent.time.sleep'),
        ):
            mock_sp.return_value = MagicMock(pid=4567)
            from feishu_stack.modules.model_provider.codex_agent import start
            result = start(cfg)
            self.assertFalse(result.ok)
            self.assertIn('exited', result.message)


class CodexAgentStopTests(unittest.TestCase):
    def test_stop(self):
        cfg = _fake_config()
        with patch('feishu_stack.modules.model_provider.codex_agent.stop_component') as mock_stop:
            mock_stop.return_value = OperationResult(True, 'codex-agent', 'stop', 'stopped')
            from feishu_stack.modules.model_provider.codex_agent import stop
            result = stop(cfg)
            self.assertTrue(result.ok)
            mock_stop.assert_called_once_with(
                'codex-agent',
                cfg.pid_codex_agent,
                None,
                expected_process_markers=('feishu-codex-agent', 'dist\\src\\index.js', 'dist/src/index.js'),
            )


class CodexAgentRestartTests(unittest.TestCase):
    def test_restart(self):
        cfg = _fake_config()
        with (
            patch('feishu_stack.modules.model_provider.codex_agent.stop') as mock_stop,
            patch('feishu_stack.modules.model_provider.codex_agent.start') as mock_start,
        ):
            mock_stop.return_value = OperationResult(True, 'x', 'stop', 'ok')
            mock_start.return_value = OperationResult(True, 'x', 'start', 'ok')
            from feishu_stack.modules.model_provider.codex_agent import restart
            result = restart(cfg)
            self.assertTrue(result.ok)
            self.assertEqual(result.action, 'restart')
