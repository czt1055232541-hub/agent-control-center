from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from feishu_stack.config import load_config
from feishu_stack.models import OperationResult
from feishu_stack.status import read_provider_status


class ProviderTests(unittest.TestCase):
    def test_read_provider_status(self) -> None:
        config = load_config()
        status = read_provider_status(config)
        self.assertTrue(status.model)
        self.assertTrue(status.provider)
        self.assertIn(status.mode, {"native", "deepseek"})

    def test_switch_deepseek_writes_codex_config_directly(self) -> None:
        cfg = MagicMock()
        cfg.codex_config = Path("config.toml")
        current = MagicMock(mode="native")
        codex_result = OperationResult(True, "codex-provider", "switch-deepseek", "codex synced")

        with (
            patch("feishu_stack.modules.model_provider.provider_switch.read_provider_status", return_value=current),
            patch("feishu_stack.modules.model_provider.provider_switch.codex_config.switch_provider", return_value=codex_result) as mock_codex,
        ):
            from feishu_stack.modules.model_provider.provider_switch import switch_provider

            result = switch_provider("deepseek", cfg, deepseek_model="deepseek-v4-pro", reasoning_effort="xhigh")

        self.assertTrue(result.ok)
        mock_codex.assert_called_once_with(
            "deepseek",
            cfg,
            deepseek_model="deepseek-v4-pro",
            reasoning_effort="xhigh",
            target="app",
        )
