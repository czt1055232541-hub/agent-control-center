from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from feishu_stack.models import OperationResult


class SecurityTokenPathTests(unittest.TestCase):
    def test_token_path(self):
        cfg = MagicMock()
        cfg.runtime_dir = Path(tempfile.gettempdir()) / 'security_test'
        from feishu_stack.security import token_path
        p = token_path(cfg)
        self.assertEqual(p.name, 'control-token.txt')
        self.assertIn('security_test', str(p))


class SecurityGetOrCreateTokenTests(unittest.TestCase):
    def test_creates_new_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = MagicMock()
            cfg.runtime_dir = Path(tmp) / 'rt'
            from feishu_stack.security import token_path, get_or_create_token
            token_path_path = cfg.runtime_dir / 'control-token.txt'
            with patch('feishu_stack.security.token_path', return_value=token_path_path):
                token = get_or_create_token(cfg)
                self.assertTrue(token_path_path.exists())
                saved = token_path_path.read_text(encoding='ascii').strip()
                self.assertEqual(token, saved)
                self.assertGreater(len(token), 30)

    def test_returns_existing_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = MagicMock()
            cfg.runtime_dir = Path(tmp) / 'rt'
            token_path_path = cfg.runtime_dir / 'control-token.txt'
            cfg.runtime_dir.mkdir(parents=True, exist_ok=True)
            token_path_path.write_text('some-existing-token-value', encoding='ascii')
            from feishu_stack.security import get_or_create_token
            with patch('feishu_stack.security.token_path', return_value=token_path_path):
                token = get_or_create_token(cfg)
                self.assertEqual(token, 'some-existing-token-value')


class SecurityRequireControlTokenTests(unittest.TestCase):
    def test_missing_header(self):
        from fastapi import HTTPException
        with patch('feishu_stack.security.get_or_create_token', return_value='secret'):
            from feishu_stack.security import require_control_token
            with self.assertRaises(HTTPException) as ctx:
                require_control_token(None)
            self.assertEqual(ctx.exception.status_code, 401)

    def test_invalid_token(self):
        from fastapi import HTTPException
        with patch('feishu_stack.security.get_or_create_token', return_value='secret'):
            from feishu_stack.security import require_control_token
            with self.assertRaises(HTTPException) as ctx:
                require_control_token('wrong')
            self.assertEqual(ctx.exception.status_code, 403)

    def test_valid_token(self):
        with patch('feishu_stack.security.get_or_create_token', return_value='secret'):
            from feishu_stack.security import require_control_token
            require_control_token('secret')
