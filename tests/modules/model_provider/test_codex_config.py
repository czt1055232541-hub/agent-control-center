from __future__ import annotations

from pathlib import Path

from feishu_stack.modules.model_provider.codex_config import clean_backups, switch_provider
from feishu_stack.config import StackConfig


def make_config(tmp_path: Path) -> StackConfig:
    codex_home = tmp_path / "codex"
    stack_root = tmp_path / "stack"
    runtime = tmp_path / "runtime"
    codex_home.mkdir()
    stack_root.mkdir()
    agent_codex_home = tmp_path / "agent-codex"
    (codex_home / "models_catalog.json").write_text("{}", encoding="utf-8")
    config_path = codex_home / "config.toml"
    config_path.write_text(
        '\n'.join(
            [
                'service_tier = "default"',
                'model = "gpt-5.5"',
                "",
                "[features]",
                "multi_agent = true",
                "",
                "[mcp_servers.node_repl.env]",
                f"CODEX_HOME = '{str(codex_home).replace(chr(92), chr(92) + chr(92))}'",
                "CODEX_CLI_PATH = 'C:\\\\old\\\\codex.exe'",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return StackConfig(
        raw={"moonBridgeBaseUrl": "http://127.0.0.1:38440/v1"},
        stack_root=stack_root,
        codex_home=codex_home,
        codex_bin=codex_home / "bin" / "codex.exe",
        codex_config=config_path,
        codex_switch_script=stack_root / "codex" / "Switch-CodexProvider.ps1",
        native_model="gpt-5.5",
        native_reasoning_effort="high",
        moonbridge_model="moonbridge-flash",
        moonbridge_dir=tmp_path,
        moonbridge_exe=tmp_path / "moonbridge.exe",
        moonbridge_config=tmp_path / "config.yml",
        moonbridge_port=38440,
        openclaw_home=tmp_path,
        openclaw_gateway_cmd=tmp_path / "gateway.cmd",
        openclaw_port=18789,
        agent_dir=tmp_path,
        agent_entry=tmp_path / "dist" / "src" / "index.js",
        agent_codex_home=agent_codex_home,
        agent_codex_config=agent_codex_home / "config.toml",
        lark_cli_bin=tmp_path / "lark-cli.exe",
        runtime_dir=runtime,
        log_dir=runtime / "logs",
       pid_dir=runtime / "pids",
        python_exe=tmp_path / "python.exe",
   )


def test_switch_provider_to_moonbridge_preserves_sections(tmp_path: Path, monkeypatch) -> None:
    cfg = make_config(tmp_path)
    monkeypatch.setattr("feishu_stack.modules.model_provider.codex_config._moonbridge_ready", lambda _cfg: True)
    monkeypatch.setattr("feishu_stack.modules.model_provider.codex_config._moonbridge_has_model", lambda _cfg, _model: True)
    result = switch_provider("moonbridge", cfg)
    text = cfg.codex_config.read_text(encoding="utf-8")
    assert result.ok is True
    assert 'model = "moonbridge-flash"' in text
    assert 'model_provider = "moonbridge"' in text
    assert 'model_reasoning_effort = "high"' in text
    assert "[features]" in text
    assert "[model_providers.moonbridge]" in text
    assert len(list(cfg.codex_home.glob("config.toml.bak-switch-*"))) == 1


def test_switch_provider_to_moonbridge_accepts_requested_model_and_effort(tmp_path: Path, monkeypatch) -> None:
    cfg = make_config(tmp_path)
    monkeypatch.setattr("feishu_stack.modules.model_provider.codex_config._moonbridge_ready", lambda _cfg: True)
    monkeypatch.setattr("feishu_stack.modules.model_provider.codex_config._moonbridge_has_model", lambda _cfg, _model: True)
    result = switch_provider("moonbridge", cfg, moonbridge_model="moonbridge-pro", reasoning_effort="xhigh")
    text = cfg.codex_config.read_text(encoding="utf-8")
    assert result.ok is True
    assert 'model = "moonbridge-pro"' in text
    assert 'model_provider = "moonbridge"' in text
    assert 'model_reasoning_effort = "xhigh"' in text


def test_switch_provider_to_native_removes_moonbridge_keys(tmp_path: Path, monkeypatch) -> None:
    cfg = make_config(tmp_path)
    monkeypatch.setattr("feishu_stack.modules.model_provider.codex_config._moonbridge_ready", lambda _cfg: True)
    monkeypatch.setattr("feishu_stack.modules.model_provider.codex_config._moonbridge_has_model", lambda _cfg, _model: True)
    assert switch_provider("moonbridge", cfg).ok is True
    assert switch_provider("native", cfg).ok is True
    text = cfg.codex_config.read_text(encoding="utf-8")
    assert 'model = "gpt-5.5"' in text
    assert 'model_reasoning_effort = "high"' in text
    assert "model_provider" not in text
    assert "[model_providers.moonbridge]" not in text
    assert len(list(cfg.codex_home.glob("config.toml.bak-switch-*"))) == 1


def test_switch_agent_provider_does_not_modify_app_config(tmp_path: Path, monkeypatch) -> None:
    cfg = make_config(tmp_path)
    monkeypatch.setattr("feishu_stack.modules.model_provider.codex_config._moonbridge_ready", lambda _cfg: True)
    monkeypatch.setattr("feishu_stack.modules.model_provider.codex_config._moonbridge_has_model", lambda _cfg, _model: True)

    original_app_text = cfg.codex_config.read_text(encoding="utf-8")
    result = switch_provider("moonbridge", cfg, target="agent")

    assert result.ok is True
    assert cfg.codex_config.read_text(encoding="utf-8") == original_app_text
    agent_text = cfg.agent.codex_config.read_text(encoding="utf-8")
    assert 'model = "moonbridge-flash"' in agent_text
    assert 'model_provider = "moonbridge"' in agent_text
    assert f"CODEX_HOME = '{str(cfg.agent.codex_home).replace(chr(92), chr(92) + chr(92))}'" in agent_text
    assert f"CODEX_CLI_PATH = '{str(cfg.codex_bin).replace(chr(92), chr(92) + chr(92))}'" in agent_text


def test_switch_app_provider_does_not_modify_agent_config(tmp_path: Path, monkeypatch) -> None:
    cfg = make_config(tmp_path)
    cfg.agent.codex_home.mkdir(parents=True)
    cfg.agent.codex_config.write_text('model = "agent-native"\n', encoding="utf-8")
    monkeypatch.setattr("feishu_stack.modules.model_provider.codex_config._moonbridge_ready", lambda _cfg: True)
    monkeypatch.setattr("feishu_stack.modules.model_provider.codex_config._moonbridge_has_model", lambda _cfg, _model: True)

    result = switch_provider("moonbridge", cfg, target="app")

    assert result.ok is True
    assert cfg.agent.codex_config.read_text(encoding="utf-8") == 'model = "agent-native"\n'
    assert 'model = "moonbridge-flash"' in cfg.codex_config.read_text(encoding="utf-8")


def test_clean_backups_preserves_goal_backups(tmp_path: Path) -> None:
    cfg = make_config(tmp_path)
    for index in range(3):
        (cfg.codex_home / f"config.toml.bak-switch-{index}").write_text("", encoding="utf-8")
        (cfg.codex_home / f"config.toml.bak-restore-native-{index}").write_text("", encoding="utf-8")
    (cfg.codex_home / "config.toml.bak-goal-keep").write_text("", encoding="utf-8")
    result = clean_backups(cfg, keep=1)
    assert result.ok is True
    assert len(list(cfg.codex_home.glob("config.toml.bak-switch-*"))) == 1
    assert len(list(cfg.codex_home.glob("config.toml.bak-restore-native-*"))) == 1
    assert len(list(cfg.codex_home.glob("config.toml.bak-goal-*"))) == 1
