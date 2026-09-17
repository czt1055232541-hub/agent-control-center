from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch


class DiagnosticsCompletedResultTests(unittest.TestCase):
    def test_success(self):
        from feishu_stack.modules.logs_diagnostics.diagnostics import _completed_result
        import time

        t0 = time.monotonic()
        r = _completed_result("test", t0, 0, "out", "")
        self.assertTrue(r["ok"])
        self.assertEqual(r["returncode"], 0)
        self.assertEqual(r["stdout"], "out")

    def test_failure(self):
        from feishu_stack.modules.logs_diagnostics.diagnostics import _completed_result
        import time

        t0 = time.monotonic()
        r = _completed_result("test", t0, 1, "", "err msg")
        self.assertFalse(r["ok"])
        self.assertEqual(r["returncode"], 1)
        self.assertEqual(r["stderr"], "err msg")


class DiagnosticsCodexDoctorTests(unittest.TestCase):
    def test_success(self):
        completed = MagicMock()
        completed.returncode = 0
        completed.stdout = "all good"
        completed.stderr = ""
        with patch("feishu_stack.modules.logs_diagnostics.diagnostics.run_capture", return_value=completed):
            from feishu_stack.modules.logs_diagnostics.diagnostics import codex_doctor

            r = codex_doctor()
            self.assertTrue(r["ok"])
            self.assertEqual(r["stdout"], "all good")

    def test_exception(self):
        with patch("feishu_stack.modules.logs_diagnostics.diagnostics.run_capture", side_effect=RuntimeError("boom")):
            from feishu_stack.modules.logs_diagnostics.diagnostics import codex_doctor

            r = codex_doctor()
            self.assertFalse(r["ok"])
            self.assertIn("boom", r["stderr"])


class DiagnosticsDeepSeekEnvTests(unittest.TestCase):
    def test_present(self):
        from feishu_stack.modules.logs_diagnostics.diagnostics import deepseek_env_status

        cfg = MagicMock()
        cfg.deepseek.env_key = "DEEPSEEK_API_KEY"
        cfg.deepseek.base_url = "https://api.deepseek.com"
        cfg.deepseek.models = ["deepseek-v4-pro"]
        with patch.dict("os.environ", {"DEEPSEEK_API_KEY": "test-key"}, clear=False):
            r = deepseek_env_status(cfg)
        self.assertTrue(r["ok"])
        self.assertTrue(r["present"])
        self.assertEqual(r["env_key"], "DEEPSEEK_API_KEY")
        self.assertEqual(r["source"], "process")

    def test_present_from_windows_registry_fallback(self):
        from feishu_stack.modules.logs_diagnostics.diagnostics import deepseek_env_status

        cfg = MagicMock()
        cfg.deepseek.env_key = "DEEPSEEK_API_KEY"
        cfg.deepseek.base_url = "https://api.deepseek.com"
        cfg.deepseek.models = ["deepseek-v4-pro"]
        with (
            patch.dict("os.environ", {}, clear=True),
            patch("feishu_stack.core.env._windows_registry_env_value", return_value="test-key"),
        ):
            r = deepseek_env_status(cfg)
        self.assertTrue(r["ok"])
        self.assertTrue(r["present"])
        self.assertEqual(r["source"], "windows-registry")

    def test_missing(self):
        from feishu_stack.modules.logs_diagnostics.diagnostics import deepseek_env_status

        cfg = MagicMock()
        cfg.deepseek.env_key = "DEEPSEEK_API_KEY"
        cfg.deepseek.base_url = "https://api.deepseek.com"
        cfg.deepseek.models = ["deepseek-v4-pro"]
        with (
            patch.dict("os.environ", {}, clear=True),
            patch("feishu_stack.core.env._windows_registry_env_value", return_value=None),
        ):
            r = deepseek_env_status(cfg)
        self.assertFalse(r["ok"])
        self.assertFalse(r["present"])
        self.assertIn("DEEPSEEK_API_KEY", r["error"])


class DiagnosticsLarkAuthTests(unittest.TestCase):
    def test_success(self):
        completed = MagicMock()
        completed.returncode = 0
        completed.stdout = "authenticated"
        completed.stderr = ""
        with patch("feishu_stack.modules.feishu_connection.auth.run_capture", return_value=completed):
            from feishu_stack.modules.logs_diagnostics.diagnostics import lark_auth_status

            cfg = MagicMock()
            cfg.lark_cli_bin = "lark-cli"
            cfg.stack_root = "."
            r = lark_auth_status(cfg)
            self.assertTrue(r["ok"])


class DiagnosticsSummaryTests(unittest.TestCase):
    def test_diagnostics_aggregates(self):
        with (
            patch("feishu_stack.modules.logs_diagnostics.diagnostics.get_status") as mock_gs,
            patch("feishu_stack.modules.logs_diagnostics.diagnostics.codex_doctor") as mock_cd,
            patch("feishu_stack.modules.logs_diagnostics.diagnostics.deepseek_env_status") as mock_ds,
            patch("feishu_stack.modules.logs_diagnostics.diagnostics.lark_auth_status") as mock_la,
        ):
            mock_gs.return_value = {"ok": True}
            mock_cd.return_value = {"ok": True}
            mock_ds.return_value = {"ok": True}
            mock_la.return_value = {"ok": True}
            from feishu_stack.modules.logs_diagnostics.diagnostics import diagnostics

            r = diagnostics()
            self.assertIn("status", r)
            self.assertIn("codex_doctor", r)
            self.assertIn("deepseek_env", r)
            self.assertIn("lark_auth_status", r)
