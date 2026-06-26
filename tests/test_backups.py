from __future__ import annotations

import unittest
from unittest.mock import ANY, patch

from feishu_stack.models import OperationResult


class BackupsCleanTests(unittest.TestCase):
    def test_clean_delegates(self):
        with patch('feishu_stack.backups.codex_config.clean_backups') as mock_clean:
            mock_clean.return_value = OperationResult(
                True, 'backups', 'clean', 'Removed 3 backups', duration_ms=10
            )
            from feishu_stack.backups import clean
            cfg = object()
            result = clean(cfg, keep=2)
            self.assertTrue(result.ok)
            self.assertEqual(result.message, 'Removed 3 backups')
            mock_clean.assert_called_once_with(cfg, 2)

    def test_clean_default_keep(self):
        with patch('feishu_stack.backups.codex_config.clean_backups') as mock_clean:
            mock_clean.return_value = OperationResult(
                True, 'backups', 'clean', 'Removed 0 backups', duration_ms=5
            )
            from feishu_stack.backups import clean
            result = clean()
            self.assertTrue(result.ok)
            mock_clean.assert_called_once_with(ANY, 1)
