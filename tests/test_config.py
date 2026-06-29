from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from feishu_stack.config import load_config, resolve_codex_bin


class ConfigTests(unittest.TestCase):
    def test_load_config(self) -> None:
        config = load_config()
        self.assertEqual(config.codex_home.name, "codeX")
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
