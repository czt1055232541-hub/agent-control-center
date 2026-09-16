from __future__ import annotations

from pathlib import Path

from feishu_stack.config import StackConfig
from feishu_stack.modules.model_provider.codex_config import clean_backups, switch_provider


def make_config(tmp_path: Path) -> StackConfig:
    codex_home = tmp_path / "codex"
    stack_root = tmp_path / "stack"
    runtime = tmp_path / "runtime"
    codex_home.mkdir()
    stack_root.mkdir()
    agent_codex_home = tmp_path / "agent-codex"
    config_path = codex_home / "config.toml"
    config_path.write_text(
        "\n".join(
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
        raw={"deepseek": {"baseUrl": "https://api.deepseek.com", "envKey": "DEEPSEEK_API_KEY"}},
        stack_root=stack_root,
        codex_home=codex_home,
        codex_bin=codex_home / "bin" / "codex.exe",
        codex_config=config_path,
        codex_switch_script=stack_root / "codex" / "Switch-CodexProvider.ps1",
        native_model="gpt-5.5",
        native_reasoning_effort="high",
        deepseek_model="deepseek-v4-pro",
        deepseek_models=["deepseek-v4-pro", "deepseek-v4-flash"],
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
        deepseek_reasoning_effort="high",
    )


def test_switch_provider_to_deepseek_writes_direct_provider(tmp_path: Path) -> None:
    cfg = make_config(tmp_path)
    result = switch_provider("deepseek", cfg, deepseek_model="deepseek-v4-flash", reasoning_effort="xhigh")
    text = cfg.codex_config.read_text(encoding="utf-8")
    assert result.ok is True
    assert 'model = "deepseek-v4-flash"' in text
    assert 'model_provider = "deepseek"' in text
    assert 'model_reasoning_effort = "xhigh"' in text
    assert "[model_providers.deepseek]" in text
    assert 'base_url = "https://api.deepseek.com"' in text
    assert 'env_key = "DEEPSEEK_API_KEY"' in text
    assert 'wire_api = "responses"' in text
    assert "[model_providers.moonbridge]" not in text
    assert "model_catalog_json" not in text


def test_switch_provider_to_native_removes_provider_keys(tmp_path: Path) -> None:
    cfg = make_config(tmp_path)
    assert switch_provider("deepseek", cfg).ok is True
    assert switch_provider("native", cfg).ok is True
    text = cfg.codex_config.read_text(encoding="utf-8")
    assert 'model = "gpt-5.5"' in text
    assert 'model_reasoning_effort = "high"' in text
    assert "model_provider" not in text
    assert "[model_providers.deepseek]" not in text
    assert "[model_providers.moonbridge]" not in text
    assert len(list(cfg.codex_home.glob("config.toml.bak-switch-*"))) == 1


def test_switch_agent_provider_to_deepseek_does_not_modify_app_config(tmp_path: Path) -> None:
    cfg = make_config(tmp_path)
    original_app_text = cfg.codex_config.read_text(encoding="utf-8")
    result = switch_provider("deepseek", cfg, target="agent")

    assert result.ok is True
    assert cfg.codex_config.read_text(encoding="utf-8") == original_app_text
    agent_text = cfg.agent.codex_config.read_text(encoding="utf-8")
    assert 'model = "deepseek-v4-pro"' in agent_text
    assert 'model_provider = "deepseek"' in agent_text
    assert "[model_providers.deepseek]" in agent_text
    assert f"CODEX_HOME = '{str(cfg.agent.codex_home).replace(chr(92), chr(92) + chr(92))}'" in agent_text
    assert f"CODEX_CLI_PATH = '{str(cfg.codex_bin).replace(chr(92), chr(92) + chr(92))}'" in agent_text


def test_switch_app_provider_does_not_modify_agent_config(tmp_path: Path) -> None:
    cfg = make_config(tmp_path)
    cfg.agent.codex_home.mkdir(parents=True)
    cfg.agent.codex_config.write_text('model = "agent-native"\n', encoding="utf-8")

    result = switch_provider("deepseek", cfg, target="app")

    assert result.ok is True
    assert cfg.agent.codex_config.read_text(encoding="utf-8") == 'model = "agent-native"\n'
    assert 'model = "deepseek-v4-pro"' in cfg.codex_config.read_text(encoding="utf-8")


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
