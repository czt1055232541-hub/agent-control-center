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
  "nodeExe": "__ROOT__\\\\node.exe",
  "npmExe": "__ROOT__\\\\npm.cmd",
  "codexHome": "__ROOT__\\\\codex",
  "codexBin": "__ROOT__\\\\codex\\\\codex.exe",
  "codexConfig": "__ROOT__\\\\codex\\\\config.toml",
  "codexNativeModel": "gpt-5.5",
  "codexDeepSeekModel": "deepseek-v4-pro",
  "codexDeepSeekModels": ["deepseek-v4-pro", "deepseek-v4-flash"],
  "deepseek": {
    "baseUrl": "https://api.deepseek.com",
    "envKey": "DEEPSEEK_API_KEY"
  },
  "codexSwitchScript": "__ROOT__\\\\codex\\\\Switch-CodexProvider.ps1",
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
  },
  "localTools": {
    "tools": [
      {
        "id": "demo-tool",
        "name": "Demo Tool",
        "dir": "__ROOT__\\\\projects\\\\demo-tool",
        "entry": "app.py",
        "host": "127.0.0.1",
        "port": 8123,
        "url": "http://127.0.0.1:8123",
        "healthPath": "/api/health",
        "tags": ["demo"]
      }
    ]
  }
}
""".replace("__ROOT__", str(root).replace("\\", "\\\\")).strip(),
                encoding="utf-8",
            )

            config = load_config(settings)

        self.assertEqual(config.openclaw_port, 18789)
        self.assertEqual(config.node_exe.name, "node.exe")
        self.assertEqual(config.npm_exe.name, "npm.cmd")
        self.assertEqual(config.pid_dir.name, "pids")
        self.assertEqual(config.migration_summary_dir.name, "summaries")
        self.assertEqual(config.codex.native_model, "gpt-5.5")
        self.assertEqual(config.deepseek.model, "deepseek-v4-pro")
        self.assertEqual(config.deepseek.env_key, "DEEPSEEK_API_KEY")
        self.assertEqual(config.agent.codex_agent_args, "exec --skip-git-repo-check")
        self.assertEqual(config.agent.codex_home, config.stack_root / "agent-runtime" / "codex-home")
        self.assertEqual(config.agent.codex_config, config.stack_root / "agent-runtime" / "codex-home" / "config.toml")
        self.assertEqual(config.deepseek.base_url, "https://api.deepseek.com")
        self.assertEqual(config.local_tools[0].id, "demo-tool")
        self.assertEqual(config.local_tools[0].command[-1], "app.py")
        self.assertEqual(config.local_tools[0].entry.name, "app.py")

    def test_local_tool_manifest_adapts_calendar_tool_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tool_dir = root / "TOOLS" / "calendar-tool"
            tool_dir.mkdir(parents=True)
            (tool_dir / "acc.local-tool.json").write_text(
                """
{
  "id": "calendar-tool",
  "name": "日历工具",
  "description": "本地日历、待办和时间线工具。",
  "runtime": "python",
  "entry": "calendar_app.py",
  "host": "127.0.0.1",
  "port": 8012,
  "healthPath": "/api/health",
  "openPath": "/calendar",
  "tags": ["calendar", "planning"],
  "env": {"CALENDAR_DATA_DIR": "data"}
}
""".strip(),
                encoding="utf-8",
            )
            settings = root / "stack.settings.json"
            settings.write_text(
                """
{
  "stackRoot": "__ROOT__",
  "pythonExe": "__ROOT__\\\\python.exe",
  "nodeExe": "__ROOT__\\\\node.exe",
  "npmExe": "__ROOT__\\\\npm.cmd",
  "codexHome": "__ROOT__\\\\codex",
  "codexBin": "__ROOT__\\\\codex\\\\codex.exe",
  "codexConfig": "__ROOT__\\\\codex\\\\config.toml",
  "codexNativeModel": "gpt-5.5",
  "codexDeepSeekModel": "deepseek-v4-pro",
  "deepseek": {"baseUrl": "https://api.deepseek.com", "envKey": "DEEPSEEK_API_KEY"},
  "codexSwitchScript": "__ROOT__\\\\codex\\\\Switch-CodexProvider.ps1",
  "openclaw": {"home": "__ROOT__\\\\openclaw", "gatewayCmd": "__ROOT__\\\\openclaw\\\\gateway.cmd", "port": 18789},
  "agent": {"dir": "__ROOT__\\\\agent", "entry": "dist\\\\src\\\\index.js", "larkCliBin": "__ROOT__\\\\agent\\\\lark-cli.exe"},
  "runtime": {"dir": "__ROOT__\\\\runtime", "logs": "__ROOT__\\\\runtime\\\\logs", "pids": "__ROOT__\\\\runtime\\\\pids"},
  "localTools": {"tools": [{"dir": "__ROOT__\\\\TOOLS\\\\calendar-tool", "port": 8013}]}
}
""".replace("__ROOT__", str(root).replace("\\", "\\\\")).strip(),
                encoding="utf-8",
            )

            config = load_config(settings)

        tool = config.local_tools[0]
        self.assertEqual(tool.id, "calendar-tool")
        self.assertEqual(tool.name, "日历工具")
        self.assertEqual(tool.port, 8013)
        self.assertEqual(tool.open_path, "/calendar")
        self.assertEqual(tool.entry, tool_dir / "calendar_app.py")
        self.assertEqual(tool.command[-1], "calendar_app.py")
        self.assertEqual(tool.env["CALENDAR_DATA_DIR"], "data")
        self.assertEqual(tool.source, "manifest")
        self.assertEqual(tool.manifest_path, tool_dir / "acc.local-tool.json")

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

    def test_business_code_does_not_access_raw_config(self) -> None:
        root = Path(__file__).resolve().parents[2]
        offenders = []
        for path in (root / "src" / "feishu_stack").rglob("*.py"):
            if path.name == "settings.py":
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if "cfg.raw" in text:
                offenders.append(str(path.relative_to(root)))
        self.assertEqual(offenders, [])
