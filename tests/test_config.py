from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from feishu_stack.config import load_config, resolve_codex_bin, resolve_settings_path


class ConfigTests(unittest.TestCase):
    def test_load_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            settings = root / "stack.settings.json"
            settings.write_text(
                """
{
  "stackRoot": "__ROOT__",
  "pythonExe": "__ROOT__\\\\python.exe",
  "codexHome": "__ROOT__\\\\codex",
  "codexBin": "__ROOT__\\\\codex\\\\codex.exe",
  "codexConfig": "__ROOT__\\\\codex\\\\config.toml",
  "codexNativeModel": "gpt-5.5",
  "codexMoonBridgeModel": "moonbridge",
  "codexSwitchScript": "__ROOT__\\\\codex\\\\Switch-CodexProvider.ps1",
  "moonbridge": {
    "dir": "__ROOT__\\\\moonbridge",
    "exe": "__ROOT__\\\\moonbridge\\\\moonbridge.exe",
    "config": "__ROOT__\\\\moonbridge\\\\config.yml",
    "port": 38440
  },
  "openclaw": {
    "home": "__ROOT__\\\\openclaw",
    "gatewayCmd": "__ROOT__\\\\openclaw\\\\gateway.cmd",
    "port": 18789
  },
  "agent": {
    "dir": "__ROOT__\\\\agent",
    "entry": "dist\\\\src\\\\index.js",
    "larkCliBin": "__ROOT__\\\\agent\\\\lark-cli.exe"
  },
  "runtime": {
    "dir": "__ROOT__\\\\runtime",
    "logs": "__ROOT__\\\\runtime\\\\logs",
    "pids": "__ROOT__\\\\runtime\\\\pids",
    "summaries": "__ROOT__\\\\runtime\\\\summaries"
  }
}
""".replace("__ROOT__", str(root).replace("\\", "\\\\")).strip(),
                encoding="utf-8",
            )

            config = load_config(settings)

        self.assertEqual(config.openclaw_port, 18789)
        self.assertEqual(config.moonbridge_port, 38440)
        self.assertEqual(config.pid_dir.name, "pids")
        self.assertEqual(config.migration_summary_dir.name, "summaries")

    def test_resolve_codex_bin_prefers_app_managed_cli_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            configured = root / "old" / "codex.exe"
            configured.parent.mkdir()
            configured.write_text("", encoding="utf-8")
            current = root / "app" / "codex.exe"
            current.parent.mkdir()
            current.write_text("", encoding="utf-8")
            config = root / "config.toml"
            escaped = str(current).replace("\\", "\\\\")
            config.write_text(
                "\n".join(
                    [
                        'model = "gpt-5.5"',
                        "",
                        "[mcp_servers.node_repl.env]",
                        f'CODEX_CLI_PATH = "{escaped}"',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            self.assertEqual(resolve_codex_bin(str(configured), config), current)

    def test_resolve_codex_bin_falls_back_when_app_path_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            configured = root / "old" / "codex.exe"
            config = root / "config.toml"
            config.write_text(
                "\n".join(
                    [
                        "[mcp_servers.node_repl.env]",
                        'CODEX_CLI_PATH = "C:\\\\missing\\\\codex.exe"',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            self.assertEqual(resolve_codex_bin(str(configured), config), configured)

    def test_resolve_settings_path_prefers_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            expected = Path(tmp) / "custom.json"
            with patch.dict("os.environ", {"STACK_SETTINGS_PATH": str(expected)}):
                self.assertEqual(resolve_settings_path(), expected)
