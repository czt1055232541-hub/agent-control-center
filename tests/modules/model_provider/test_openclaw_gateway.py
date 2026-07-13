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
        moonbridge_model="moonbridge",
        moonbridge_dir=tmp_path / "moonbridge",
        moonbridge_exe=tmp_path / "moonbridge" / "moonbridge.exe",
        moonbridge_config=tmp_path / "moonbridge" / "config.yml",
        moonbridge_port=38440,
        openclaw_home=openclaw_home,
        openclaw_gateway_cmd=openclaw_home / ".openclaw" / "gateway.cmd",
        openclaw_port=18789,
        agent_dir=tmp_path / "agent",
        agent_entry=tmp_path / "agent" / "dist" / "src" / "index.js",
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


def test_gateway_command_uses_hidden_runtime_wrapper(tmp_path) -> None:
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

    command = openclaw._gateway_command(cfg)
    wrapper = Path(command[-1])
    text = wrapper.read_text(encoding="utf-8")

    assert wrapper == cfg.runtime_dir / "openclaw" / "gateway.hidden.cmd"
    assert 'start "" /B E:\\node\\node.exe' in text
    assert "feishu_agent" not in text
