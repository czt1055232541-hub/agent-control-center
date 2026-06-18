from __future__ import annotations

import unittest

from feishu_stack.config import load_config


class ConfigTests(unittest.TestCase):
    def test_load_config(self) -> None:
        config = load_config()
        self.assertEqual(config.codex_home.name, "codeX")
        self.assertEqual(config.openclaw_port, 18789)
        self.assertEqual(config.moonbridge_port, 38440)
        self.assertEqual(config.pid_dir.name, "pids")

