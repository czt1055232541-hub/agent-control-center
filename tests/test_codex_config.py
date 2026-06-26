from __future__ import annotations

from pathlib import Path

from feishu_stack.codex_config import clean_backups, switch_provider
from feishu_stack.config import StackConfig


def make_config(tmp_path: Path) -> StackConfig:
    codex_home = tmp_path / "codex"
    stack_root = tmp_path / "stack"
    runtime = tmp_path / "runtime"
    codex_home.mkdir()
    stack_root.mkdir()
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
        lark_cli_bin=tmp_path / "lark-cli.exe",
        runtime_dir=runtime,
        log_dir=runtime / "logs",
       pid_dir=runtime / "pids",
        python_exe=tmp_path / "python.exe",
   )


def test_switch_provider_to_moonbridge_preserves_sections(tmp_path: Path, monkeypatch) -> None:
    cfg = make_config(tmp_path)
    monkeypatch.setattr("feishu_stack.codex_config._moonbridge_ready", lambda _cfg: True)
    monkeypatch.setattr("feishu_stack.codex_config._moonbridge_has_model", lambda _cfg, _model: True)
    result = switch_provider("moonbridge", cfg)
    text = cfg.codex_config.read_text(encoding="utf-8")
    assert result.ok is True
    assert 'model = "moonbridge-flash"' in text
    assert 'model_provider = "moonbridge"' in text
    assert "[features]" in text
    assert "[model_providers.moonbridge]" in text
    assert len(list(cfg.codex_home.glob("config.toml.bak-switch-*"))) == 1


def test_switch_provider_to_native_removes_moonbridge_keys(tmp_path: Path, monkeypatch) -> None:
    cfg = make_config(tmp_path)
    monkeypatch.setattr("feishu_stack.codex_config._moonbridge_ready", lambda _cfg: True)
    monkeypatch.setattr("feishu_stack.codex_config._moonbridge_has_model", lambda _cfg, _model: True)
    assert switch_provider("moonbridge", cfg).ok is True
    assert switch_provider("native", cfg).ok is True
    text = cfg.codex_config.read_text(encoding="utf-8")
    assert 'model = "gpt-5.5"' in text
    assert "model_provider" not in text
    assert "[model_providers.moonbridge]" not in text
    assert len(list(cfg.codex_home.glob("config.toml.bak-switch-*"))) == 1


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
