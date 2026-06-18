from __future__ import annotations

import unittest

from feishu_stack.config import load_config
from feishu_stack.status import read_provider_status


class ProviderTests(unittest.TestCase):
    def test_read_provider_status(self) -> None:
        config = load_config()
        status = read_provider_status(config)
        self.assertTrue(status.model)
        self.assertTrue(status.provider)
        self.assertIn(status.mode, {"native", "moonbridge"})

