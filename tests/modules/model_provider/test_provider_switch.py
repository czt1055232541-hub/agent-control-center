from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from feishu_stack.config import load_config
from feishu_stack.status import read_provider_status
from feishu_stack.models import OperationResult


class ProviderTests(unittest.TestCase):
    def test_read_provider_status(self) -> None:
        config = load_config()
        status = read_provider_status(config)
        self.assertTrue(status.model)
        self.assertTrue(status.provider)
        self.assertIn(status.mode, {"native", "moonbridge"})

    def test_switch_moonbridge_syncs_moonbridge_model_first(self) -> None:
        cfg = MagicMock()
        cfg.moonbridge_model = "deepseek-v4"
        cfg.moonbridge_reasoning_effort = "high"
        cfg.codex_config = Path("config.toml")
        current = MagicMock(mode="native")
        moonbridge_result = OperationResult(True, "moonbridge", "switch-model", "moonbridge synced")
        codex_result = OperationResult(True, "codex-provider", "switch-moonbridge", "codex synced")

        with (
            patch("feishu_stack.modules.model_provider.provider_switch.read_provider_status", return_value=current),
            patch("feishu_stack.modules.model_provider.provider_switch.moonbridge.switch_model", return_value=moonbridge_result) as mock_moonbridge,
            patch("feishu_stack.modules.model_provider.provider_switch.codex_config.switch_provider", return_value=codex_result) as mock_codex,
        ):
            from feishu_stack.modules.model_provider.provider_switch import switch_provider

            result = switch_provider("moonbridge", cfg, moonbridge_model="deepseek-r1", reasoning_effort="xhigh")

        self.assertTrue(result.ok)
        self.assertIn("MoonBridge: moonbridge synced", result.message)
        mock_moonbridge.assert_called_once_with("deepseek-r1", cfg, "xhigh")
        mock_codex.assert_called_once_with(
            "moonbridge",
            cfg,
            moonbridge_model="deepseek-r1",
            reasoning_effort="xhigh",
            target="app",
        )
