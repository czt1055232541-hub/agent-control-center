from __future__ import annotations

import json
from pathlib import Path

from feishu_stack.modules.model_provider import openclaw_gateway as openclaw
from feishu_stack.config import StackConfig


def _config(tmp_path: Path) -> StackConfig:
    openclaw_home = tmp_path / "openclaw"
    log_dir = tmp_path / "runtime" / "logs"
    pid_dir = tmp_path / "runtime" / "pids"
    return StackConfig(
        raw={},
        stack_root=tmp_path,
        codex_home=tmp_path / "codex",
        codex_bin=tmp_path / "codex" / "bin" / "codex.exe",
        codex_config=tmp_path / "codex" / "config.toml",
        codex_switch_script=tmp_path / "codex" / "Switch-CodexProvider.ps1",
        native_model="gpt-5.5",
        native_reasoning_effort="high",
        deepseek_model="deepseek-v4-pro",
        deepseek_models=["deepseek-v4-pro"],
        openclaw_home=openclaw_home,
        openclaw_gateway_cmd=openclaw_home / ".openclaw" / "gateway.cmd",
        openclaw_port=18789,
        agent_dir=tmp_path / "agent",
        agent_entry=tmp_path / "agent" / "dist" / "src" / "index.js",
        agent_codex_home=tmp_path / "agent-codex",
        agent_codex_config=tmp_path / "agent-codex" / "config.toml",
        lark_cli_bin=tmp_path / "agent" / "lark-cli.cmd",
        runtime_dir=tmp_path / "runtime",
        log_dir=log_dir,
        pid_dir=pid_dir,
       lark_cli_home=tmp_path / ".home",
        python_exe=tmp_path / "python.exe",
   )


def test_openclaw_ui_url_uses_gateway_token_fragment(tmp_path) -> None:
    cfg = _config(tmp_path)
    config_path = cfg.openclaw_home / ".openclaw" / "openclaw.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        json.dumps({"gateway": {"auth": {"token": "secret-token"}}}),
        encoding="utf-8",
    )

    assert openclaw.ui_url(cfg) == "http://127.0.0.1:18789/#token=secret-token"


def test_openclaw_ui_url_without_token_falls_back_to_plain_url(tmp_path) -> None:
    cfg = _config(tmp_path)

    assert openclaw.ui_url(cfg) == "http://127.0.0.1:18789/"


def test_openclaw_open_ui_uses_python_startfile(monkeypatch, tmp_path) -> None:
    cfg = _config(tmp_path)
    config_path = cfg.openclaw_home / ".openclaw" / "openclaw.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        json.dumps({"gateway": {"auth": {"token": "secret-token"}}}),
        encoding="utf-8",
    )
    calls = []

    def fake_startfile(url):
        calls.append(url)

    monkeypatch.setattr(openclaw.os, "startfile", fake_startfile)

    result = openclaw.open_ui(cfg)

    assert result.ok is True
    assert result.component == "openclaw"
    assert result.action == "open-ui"
    assert calls == ["http://127.0.0.1:18789/#token=secret-token"]


def test_gateway_node_commands_strip_cmd_start_and_legacy_env(tmp_path) -> None:
    cfg = _config(tmp_path)
    cfg.openclaw_gateway_cmd.parent.mkdir(parents=True)
    cfg.openclaw_gateway_cmd.write_text(
        "\n".join(
            [
                "@echo off",
                r'for /f "usebackq delims=" %%A in (`python F:\1AI\feishu_agent\scripts\print_a2a_bots_env.py`) do set "OPENCLAW_FEISHU_A2A_BOTS=%%A"',
                r'start "OpenClaw-Proxy" E:\node\node.exe E:\openclaw\clawclaw\.openclaw\proxy.js',
                r'E:\node\node.exe E:\openclaw\npm\node_modules\openclaw\dist\index.js gateway --port 18790',
            ]
        ),
        encoding="utf-8",
    )

    commands = openclaw._gateway_node_commands(cfg)

    assert commands == [
        r"E:\node\node.exe E:\openclaw\clawclaw\.openclaw\proxy.js",
        r"E:\node\node.exe E:\openclaw\npm\node_modules\openclaw\dist\index.js gateway --port 18790",
    ]
    assert all("feishu_agent" not in command for command in commands)


def test_internal_gateway_port_is_read_from_cmd(tmp_path) -> None:
    cfg = _config(tmp_path)
    cfg.openclaw_gateway_cmd.parent.mkdir(parents=True)
    cfg.openclaw_gateway_cmd.write_text('set "OPENCLAW_GATEWAY_PORT=18790"\n', encoding="utf-8")

    assert openclaw._internal_gateway_port(cfg) == 18790
