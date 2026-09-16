from __future__ import annotations

import time
import unittest
from unittest.mock import MagicMock, patch

from feishu_stack.models import OperationResult


class StackActionsCombineTests(unittest.TestCase):
    def test_all_ok(self):
        from feishu_stack.modules.operations.stack_actions import _combine

        t0 = time.monotonic()
        results = [
            OperationResult(True, "a", "start", "a ok"),
            OperationResult(True, "b", "start", "b ok"),
        ]
        r = _combine("start-native", results, t0)
        self.assertTrue(r.ok)
        self.assertEqual(r.action, "start-native")
        self.assertIn("a ok", r.message)
        self.assertIn("b ok", r.message)

    def test_one_fails(self):
        from feishu_stack.modules.operations.stack_actions import _combine

        t0 = time.monotonic()
        results = [
            OperationResult(True, "a", "start", "a ok"),
            OperationResult(False, "b", "start", "b fail"),
        ]
        r = _combine("start-native", results, t0)
        self.assertFalse(r.ok)


class StackActionsStartNativeTests(unittest.TestCase):
    def test_start_native(self):
        with (
            patch("feishu_stack.modules.operations.stack_actions.provider_switch.switch_provider") as mock_sp,
            patch("feishu_stack.modules.operations.stack_actions.openclaw.start") as mock_oc,
            patch("feishu_stack.modules.operations.stack_actions.codex_agent.restart") as mock_ca,
            patch("feishu_stack.modules.operations.stack_actions.typing_indicator.start") as mock_ti,
        ):
            mock_sp.return_value = OperationResult(True, "provider", "switch", "ok")
            mock_oc.return_value = OperationResult(True, "openclaw", "start", "ok")
            mock_ca.return_value = OperationResult(True, "codex-agent", "start", "ok")
            mock_ti.return_value = OperationResult(True, "typing", "start", "ok")

            from feishu_stack.modules.operations.stack_actions import start_native

            cfg = MagicMock()
            result = start_native(cfg)
            self.assertTrue(result.ok)
            self.assertEqual(result.action, "start-native")
            mock_sp.assert_called_once_with("native", cfg, target="agent")


class StackActionsStartDeepSeekTests(unittest.TestCase):
    def test_start_deepseek(self):
        with (
            patch("feishu_stack.modules.operations.stack_actions.provider_switch.switch_provider") as mock_sp,
            patch("feishu_stack.modules.operations.stack_actions.openclaw.start") as mock_oc,
            patch("feishu_stack.modules.operations.stack_actions.codex_agent.restart") as mock_ca,
            patch("feishu_stack.modules.operations.stack_actions.typing_indicator.start") as mock_ti,
        ):
            mock_sp.return_value = OperationResult(True, "provider", "switch", "ok")
            mock_oc.return_value = OperationResult(True, "openclaw", "start", "ok")
            mock_ca.return_value = OperationResult(True, "codex-agent", "start", "ok")
            mock_ti.return_value = OperationResult(True, "typing", "start", "ok")

            from feishu_stack.modules.operations.stack_actions import start_deepseek

            cfg = MagicMock()
            result = start_deepseek(cfg)
            self.assertTrue(result.ok)
            self.assertEqual(result.action, "start-deepseek")
            mock_sp.assert_called_once_with("deepseek", cfg, target="agent")


class StackActionsSwitchAgentProviderTests(unittest.TestCase):
    def test_switch_restarts_running_codex_agent(self):
        with (
            patch("feishu_stack.modules.operations.stack_actions.provider_switch.switch_provider") as mock_sp,
            patch("feishu_stack.modules.operations.stack_actions.read_pid", return_value=123),
            patch("feishu_stack.modules.operations.stack_actions.process_info", return_value=(True, "node.exe")),
            patch("feishu_stack.modules.operations.stack_actions.codex_agent.restart") as mock_restart,
        ):
            mock_sp.return_value = OperationResult(True, "codex-provider-agent", "switch-deepseek", "switched")
            mock_restart.return_value = OperationResult(True, "codex-agent", "restart", "restarted")

            from feishu_stack.modules.operations.stack_actions import switch_agent_provider

            cfg = MagicMock()
            result = switch_agent_provider("deepseek", cfg, deepseek_model="deepseek-v4-pro", reasoning_effort="xhigh")

            self.assertTrue(result.ok)
            self.assertEqual(result.action, "switch-agent-deepseek")
            mock_sp.assert_called_once_with(
                "deepseek",
                cfg,
                deepseek_model="deepseek-v4-pro",
                reasoning_effort="xhigh",
                target="agent",
            )
            mock_restart.assert_called_once_with(cfg)

    def test_switch_does_not_start_stopped_codex_agent(self):
        with (
            patch("feishu_stack.modules.operations.stack_actions.provider_switch.switch_provider") as mock_sp,
            patch("feishu_stack.modules.operations.stack_actions.read_pid", return_value=None),
            patch("feishu_stack.modules.operations.stack_actions.process_info", return_value=(False, None)),
            patch("feishu_stack.modules.operations.stack_actions.codex_agent.restart") as mock_restart,
        ):
            mock_sp.return_value = OperationResult(True, "codex-provider-agent", "switch-native", "switched")

            from feishu_stack.modules.operations.stack_actions import switch_agent_provider

            cfg = MagicMock()
            result = switch_agent_provider("native", cfg)

            self.assertTrue(result.ok)
            self.assertIn("next start", result.message)
            mock_restart.assert_not_called()


class StackActionsStopTests(unittest.TestCase):
    def test_stop(self):
        with (
            patch("feishu_stack.modules.operations.stack_actions.typing_indicator.stop") as mock_ti,
            patch("feishu_stack.modules.operations.stack_actions.codex_agent.stop") as mock_ca,
            patch("feishu_stack.modules.operations.stack_actions.openclaw.stop") as mock_oc,
        ):
            mock_ti.return_value = OperationResult(True, "typing", "stop", "ok")
            mock_ca.return_value = OperationResult(True, "codex-agent", "stop", "ok")
            mock_oc.return_value = OperationResult(True, "openclaw", "stop", "ok")

            from feishu_stack.modules.operations.stack_actions import stop

            cfg = MagicMock()
            result = stop(cfg)
            self.assertTrue(result.ok)
            self.assertEqual(result.action, "stop")
