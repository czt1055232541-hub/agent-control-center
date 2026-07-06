from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from feishu_stack.models import OperationResult


class DiagnosticsCompletedResultTests(unittest.TestCase):
    def test_success(self):
        from feishu_stack.diagnostics import _completed_result
        import time
        t0 = time.monotonic()
        r = _completed_result('test', t0, 0, 'out', '')
        self.assertTrue(r['ok'])
        self.assertEqual(r['returncode'], 0)
        self.assertEqual(r['stdout'], 'out')

    def test_failure(self):
        from feishu_stack.diagnostics import _completed_result
        import time
        t0 = time.monotonic()
        r = _completed_result('test', t0, 1, '', 'err msg')
        self.assertFalse(r['ok'])
        self.assertEqual(r['returncode'], 1)
        self.assertEqual(r['stderr'], 'err msg')


class DiagnosticsCodexDoctorTests(unittest.TestCase):
    def test_success(self):
        completed = MagicMock()
        completed.returncode = 0
        completed.stdout = 'all good'
        completed.stderr = ''
        with patch('feishu_stack.diagnostics.run_capture', return_value=completed):
            from feishu_stack.diagnostics import codex_doctor
            r = codex_doctor()
            self.assertTrue(r['ok'])
            self.assertEqual(r['stdout'], 'all good')

    def test_exception(self):
        with patch('feishu_stack.diagnostics.run_capture', side_effect=RuntimeError('boom')):
            from feishu_stack.diagnostics import codex_doctor
            r = codex_doctor()
            self.assertFalse(r['ok'])
            self.assertIn('boom', r['stderr'])


class DiagnosticsMoonbridgeModelsTests(unittest.TestCase):
    def test_success(self):
        import json
        data = {'data': [{'id': 'gpt-4o'}, {'id': 'claude-sonnet'}]}
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = json.dumps(data).encode()
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.__exit__.return_value = False

        with patch('feishu_stack.diagnostics.urllib.request.urlopen', return_value=mock_resp):
            from feishu_stack.diagnostics import moonbridge_models
            cfg = MagicMock()
            cfg.raw = {}
            cfg.moonbridge_port = 38440
            r = moonbridge_models(cfg)
            self.assertTrue(r['ok'], f'r={r}')
            self.assertEqual(r['models'], ['gpt-4o', 'claude-sonnet'])

    def test_http_error(self):
        import urllib.error
        with patch('feishu_stack.diagnostics.urllib.request.urlopen', side_effect=urllib.error.HTTPError('url', 500, 'err', {}, None)):
            from feishu_stack.diagnostics import moonbridge_models
            cfg = MagicMock()
            cfg.raw = {}
            cfg.moonbridge_port = 38440
            r = moonbridge_models(cfg)
            self.assertFalse(r['ok'])
            self.assertEqual(r['status'], 500)

    def test_connection_error(self):
        with patch('feishu_stack.diagnostics.urllib.request.urlopen', side_effect=ConnectionError('refused')):
            from feishu_stack.diagnostics import moonbridge_models
            cfg = MagicMock()
            cfg.raw = {}
            cfg.moonbridge_port = 38440
            r = moonbridge_models(cfg)
            self.assertFalse(r['ok'])
            self.assertFalse(r['reachable'])


class DiagnosticsLarkAuthTests(unittest.TestCase):
    def test_success(self):
        completed = MagicMock()
        completed.returncode = 0
        completed.stdout = 'authenticated'
        completed.stderr = ''
        with patch('feishu_stack.diagnostics.run_capture', return_value=completed):
            from feishu_stack.diagnostics import lark_auth_status
            cfg = MagicMock()
            cfg.lark_cli_bin = 'lark-cli'
            cfg.stack_root = '.'
            r = lark_auth_status(cfg)
            self.assertTrue(r['ok'])


class DiagnosticsSummaryTests(unittest.TestCase):
    def test_diagnostics_aggregates(self):
        with (
            patch('feishu_stack.diagnostics.get_status') as mock_gs,
            patch('feishu_stack.diagnostics.codex_doctor') as mock_cd,
            patch('feishu_stack.diagnostics.moonbridge_models') as mock_mm,
            patch('feishu_stack.diagnostics.lark_auth_status') as mock_la,
        ):
            mock_gs.return_value = {'ok': True}
            mock_cd.return_value = {'ok': True}
            mock_mm.return_value = {'ok': True}
            mock_la.return_value = {'ok': True}
            from feishu_stack.diagnostics import diagnostics
            r = diagnostics()
            self.assertIn('status', r)
            self.assertIn('codex_doctor', r)
            self.assertIn('moonbridge_models', r)
            self.assertIn('lark_auth_status', r)
