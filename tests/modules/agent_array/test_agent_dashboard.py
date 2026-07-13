from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from feishu_stack.modules.agent_array.skill_tree.agent_config_editor import backup_config, get_editable_config, rollback_latest, update_editable_config
from feishu_stack.modules.agent_array.skill_tree.agent_dashboard import dashboard_summary, explained_diagnostics, list_agents, list_infrastructure
from feishu_stack.modules.agent_array.skill_tree.agent_registry import load_registry
from feishu_stack.models import CodexDesktopStatus, ComponentStatus, ProviderStatus, StackStatus, to_dict


def _component(name: str, running: bool, port: int | None = None) -> ComponentStatus:
    return ComponentStatus(
        name=name,
        port=port,
        port_listening=running and port is not None,
        pid_file=None,
        pid=1234 if running else None,
        pid_running=running,
        process_name="python.exe" if running else None,
    )


def _status(*, openclaw: bool = True, agent: bool = True, moonbridge: bool = False, mode: str = "native") -> StackStatus:
    provider = ProviderStatus(model="gpt-5.5", provider="openai/default", mode=mode, config="E:/codeX/config.toml")
    agent_provider = ProviderStatus(
        model="deepseek-v4-flash" if mode == "moonbridge" else "gpt-5.5",
        provider="moonbridge" if mode == "moonbridge" else "openai/default",
        mode=mode,
        config="F:/ACC/agent-runtime/codex-home/config.toml",
    )
    return StackStatus(
        codex=provider,
        codex_app=provider,
        codex_agent_provider=agent_provider,
        openclaw=_component("openclaw", openclaw, 18789),
        moonbridge=_component("moonbridge", moonbridge, 38440),
        codex_agent=_component("codex-agent", agent),
        codex_agent_args="exec --skip-git-repo-check",
        codex_agent_follows_global_config=False,
        codex_agent_config_scope="independent",
        codex_desktop_running=True,
        codex_desktop=CodexDesktopStatus(True, 4321, 1, "Codex.exe"),
        stack_root="F:/1AI/Agent control center",
    )


def _write_openclaw(root: Path) -> None:
    config_dir = root / ".openclaw"
    config_dir.mkdir(parents=True)
    agent_rows = [
        ("main", "质量审计官", "质量审计 / 交付把关", "workspace"),
        ("orchestrator", "运维验证官", "运行 / 环境 / 复现 / 部署检查", "workspace-orchestrator"),
        ("coordinator", "项目调度官", "任务拆解 / 调度 / 进度管理", "workspace-coordinator"),
        ("archivist", "项目档案官", "记录 / 归档 / 交付资料整理", "workspace-archivist"),
    ]
    for agent_id, _, _, workspace in agent_rows:
        (config_dir / workspace).mkdir()
        sessions_dir = config_dir / "agents" / agent_id / "sessions"
        sessions_dir.mkdir(parents=True)
        (sessions_dir / "sessions.json").write_text(
            json.dumps(
                {
                    f"agent:{agent_id}:feishu:group:chat-id-secret": {
                        "sessionId": f"{agent_id}-session",
                        "updatedAt": 1782887389443,
                        "lastInteractionAt": 1782887357985,
                        "providerOverride": "deepseek",
                        "modelOverride": "deepseek-v4-flash",
                    }
                }
            ),
            encoding="utf-8",
        )
    config = {
        "agents": {
            "list": [
                {"id": agent_id, "workspace": str(config_dir / workspace), "identity": {"name": name, "theme": theme}}
                for agent_id, name, theme, workspace in agent_rows
            ]
        },
        "channels": {
            "feishu": {
                "accounts": {
                    "orchestrator": {"enabled": True, "connectionMode": "websocket", "appId": "cli_a", "appSecret": "secret"},
                    "coordinator": {"enabled": True, "connectionMode": "websocket", "appId": "cli_b", "appSecret": "secret"},
                    "archivist": {"enabled": True, "connectionMode": "websocket", "appId": "cli_c", "appSecret": "secret"},
                }
            }
        },
        "bindings": [
            {"agentId": "main", "match": {"channel": "feishu", "accountId": "open-id-secret"}},
            {"agentId": "orchestrator", "match": {"channel": "feishu", "accountId": "open-id-secret"}},
            {"agentId": "coordinator", "match": {"channel": "feishu", "accountId": "open-id-secret"}},
            {"agentId": "archivist", "match": {"channel": "feishu", "accountId": "open-id-secret"}},
        ],
    }
    (config_dir / "openclaw.json").write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")


def _write_codex_agent(root: Path) -> None:
    root.mkdir(parents=True)
    peers = [
        {"name": "项目调度官", "openId": "open-id-secret_1", "description": "coordinator"},
        {"name": "代码执行官", "openId": "open-id-secret_2", "description": "developer"},
        {"name": "运维验证官", "openId": "open-id-secret_3", "description": "ops-validation"},
        {"name": "质量审计官", "openId": "open-id-secret_4", "description": "quality-auditor"},
        {"name": "项目档案官", "openId": "open-id-secret_5", "description": "archivist"},
    ]
    (root / ".env").write_text(
        "\n".join(
            [
                "LARK_BOT_NAME=代码执行官",
                "AGENT_PROVIDER=codex",
                "CODEX_AGENT_ARGS=exec --skip-git-repo-check",
                "LARK_BOT_OPEN_ID=open-id-code-secret",
                f"A2A_BOTS={json.dumps(peers, ensure_ascii=False)}",
            ]
        ),
        encoding="utf-8",
    )


def _a2a_peers() -> list[dict[str, str]]:
    return [
        {"name": "coordinator", "openId": "open-id-secret_1", "description": "coordinator"},
        {"name": "developer", "openId": "open-id-secret_2", "description": "developer"},
        {"name": "ops-validation", "openId": "open-id-secret_3", "description": "ops-validation"},
        {"name": "quality-auditor", "openId": "open-id-secret_4", "description": "quality-auditor"},
        {"name": "archivist", "openId": "open-id-secret_5", "description": "archivist"},
    ]


def _config(tmp_path: Path) -> SimpleNamespace:
    openclaw_home = tmp_path / "openclaw"
    agent_dir = tmp_path / "codex-agent"
    agent_codex_home = tmp_path / "agent-codex"
    agent_codex_home.mkdir()
    agent_codex_config = agent_codex_home / "config.toml"
    agent_codex_config.write_text('model = "deepseek-v4-flash"\nmodel_provider = "moonbridge"\n', encoding="utf-8")
    _write_openclaw(openclaw_home)
    _write_codex_agent(agent_dir)
    return SimpleNamespace(
        raw={"agent": {"provider": "codex", "codexAgentArgs": "exec --skip-git-repo-check"}, "codexNativeModel": "gpt-5.5"},
        stack_root=tmp_path,
        agent=SimpleNamespace(
            provider="codex",
            codex_agent_args="exec --skip-git-repo-check",
            codex_home=agent_codex_home,
            codex_config=agent_codex_config,
            lark_bot_open_id="",
            a2a_bots=[],
        ),
        codex=SimpleNamespace(native_model="gpt-5.5"),
        openclaw=SimpleNamespace(home=openclaw_home),
        openclaw_home=openclaw_home,
        agent_dir=agent_dir,
        agent_entry=agent_dir / "dist" / "src" / "index.js",
        openclaw_gateway_cmd=openclaw_home / ".openclaw" / "gateway.cmd",
        moonbridge_config=tmp_path / "moonbridge.yml",
        moonbridge_model="deepseek-v4-pro",
        native_model="gpt-5.5",
        runtime_dir=tmp_path / "runtime",
    )


def test_registry_reads_real_openclaw_and_codex_roles(tmp_path: Path) -> None:
    agents = load_registry(_config(tmp_path), openclaw_status=_component("openclaw", True), codex_agent_status=_component("codex-agent", True))

    assert [agent.display_name for agent in agents] == ["项目调度官", "运维验证官", "质量审计官", "项目档案官", "代码执行官"]
    assert [agent.source for agent in agents] == ["openclaw", "openclaw", "openclaw", "openclaw", "codex-agent"]
    assert next(agent for agent in agents if agent.display_name == "代码执行官").a2a_peers[0]["hasOpenId"] is True


def test_agent_api_shape_does_not_leak_sensitive_values(tmp_path: Path) -> None:
    agents = list_agents(_config(tmp_path), _status())
    payload = json.dumps(to_dict(agents), ensure_ascii=False)

    assert len(agents) == 5
    assert "open-id-secret" not in payload
    assert "appSecret" not in payload
    assert "token" not in payload.lower()


def test_openclaw_roles_do_not_expose_process_control(tmp_path: Path) -> None:
    agents = list_agents(_config(tmp_path), _status())
    coordinator = next(agent for agent in agents if agent.id == "openclaw-coordinator")
    endpoints = {action.get("endpoint") for action in (coordinator.backendActions or [])}

    assert "/api/openclaw/start" not in endpoints
    assert "/api/openclaw/stop" not in endpoints
    assert "/api/openclaw/open-ui" in endpoints


def test_code_agent_exposes_codex_agent_controls(tmp_path: Path) -> None:
    agents = list_agents(_config(tmp_path), _status())
    code_agent = next(agent for agent in agents if agent.id == "codex-code-agent")
    endpoints = {action.get("endpoint") for action in (code_agent.backendActions or [])}

    assert {"/api/codex-agent/start", "/api/codex-agent/stop", "/api/codex-agent/restart"} <= endpoints
    assert len(code_agent.a2aPeers or []) == 5
    assert code_agent.workspacePath == str((tmp_path / "workspaces" / "dev").resolve(strict=False))
    assert code_agent.provider == "moonbridge"
    assert code_agent.model == "deepseek-v4-flash"


def test_code_agent_uses_stack_config_a2a_when_env_is_missing(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    (cfg.agent_dir / ".env").unlink()
    cfg.agent = SimpleNamespace(
        provider="codex",
        codex_agent_args="exec --skip-git-repo-check",
        lark_bot_open_id="open-id-code-secret",
        a2a_bots=_a2a_peers(),
    )

    code_agent = next(
        agent
        for agent in load_registry(cfg, openclaw_status=_component("openclaw", True), codex_agent_status=_component("codex-agent", True))
        if agent.id == "codex-code-agent"
    )

    assert code_agent.status == "running"
    assert code_agent.binding_status == "bound"
    assert len(code_agent.a2a_peers) == 5
    assert code_agent.config_facts["workspaceExists"] is False


def test_dashboard_summary_counts_real_agents_only(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("feishu_stack.modules.agent_array.skill_tree.agent_dashboard.recent_operations", lambda: [])
    summary = dashboard_summary(_config(tmp_path), _status())

    assert summary.totalAgents == 5
    assert summary.onlineAgents == 5


def test_codex_agent_draft_log_marks_agent_executing(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    logs = cfg.runtime_dir / "logs"
    logs.mkdir(parents=True)
    (logs / "codex-agent-err.log").write_text(
        '\n'.join(
            [
                '[agent] event message_id=message-id-secret chat_id=chat-id-secret respond=true text="执行 Step 1.2 MODE 连通性验证"',
                "[agent] draft provider=codex",
            ]
        ),
        encoding="utf-8",
    )

    code_agent = next(agent for agent in list_agents(cfg, _status()) if agent.id == "codex-code-agent")

    assert code_agent.status == "executing"
    assert "MODE 连通性验证" in code_agent.currentTask


def test_codex_agent_completed_log_marks_agent_idle(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    logs = cfg.runtime_dir / "logs"
    logs.mkdir(parents=True)
    (logs / "codex-agent-err.log").write_text(
        '\n'.join(
            [
                '[agent] event message_id=message-id-secret chat_id=chat-id-secret respond=true text="执行 Step 1.2"',
                "[agent] draft provider=codex",
                "[agent] draft provider=codex completed",
                "[agent] replied chat_id=chat-id-secret",
            ]
        ),
        encoding="utf-8",
    )

    code_agent = next(agent for agent in list_agents(cfg, _status()) if agent.id == "codex-code-agent")

    assert code_agent.status == "running"
    assert code_agent.currentTask == "--"


def test_openclaw_dispatch_log_marks_role_executing(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    logs = cfg.runtime_dir / "logs"
    logs.mkdir(parents=True)
    (logs / "openclaw-gateway-out.log").write_text(
        "\n".join(
            [
                "2026-07-01 [feishu] feishu[coordinator]: Feishu[coordinator] message in group chat-id-secret: 继续拆解 Phase 1",
                "2026-07-01 [feishu] feishu[coordinator]: dispatching to agent (session=agent:coordinator:feishu:group:chat-id-secret)",
            ]
        ),
        encoding="utf-8",
    )

    coordinator = next(agent for agent in list_agents(cfg, _status()) if agent.id == "openclaw-coordinator")

    assert coordinator.status == "executing"
    assert "Phase 1" in coordinator.currentTask


def test_infrastructure_stays_separate_from_real_agents(tmp_path: Path) -> None:
    infra = list_infrastructure(_config(tmp_path), _status(mode="moonbridge", moonbridge=True))

    assert {agent.id for agent in infra} == {"feishu-codex-agent", "openclaw-gateway", "moonbridge", "codex-runtime"}
    assert all(agent.source == "infrastructure" for agent in infra)
    codex_agent = next(agent for agent in infra if agent.id == "feishu-codex-agent")
    assert codex_agent.provider == "moonbridge"
    assert codex_agent.model == "deepseek-v4-flash"


def test_explained_diagnostics_flags_missing_a2a(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    (cfg.agent_dir / ".env").write_text("LARK_BOT_NAME=代码执行官\nAGENT_PROVIDER=codex\n", encoding="utf-8")

    items = explained_diagnostics(
        cfg,
        {
            "status": _status(),
            "moonbridge_models": {"ok": True},
            "lark_auth_status": {"ok": True},
            "codex_doctor": {"ok": True},
        },
    )

    assert any(item.id == "codex-agent-a2a-warning" for item in items)


def test_codex_editable_config_updates_with_backup_and_rollback(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    before = get_editable_config("codex-code-agent", cfg)

    result = update_editable_config(
        "codex-code-agent",
        {
            "AGENT_PROVIDER": "local",
            "CODEX_AGENT_ARGS": "exec --skip-git-repo-check --sandbox read-only",
            "CODEX_CLI_TIMEOUT_MS": "700000",
            "A2A_BOTS": [{"name": "项目调度官", "description": "updated"}],
        },
        cfg,
    )

    assert result["ok"] is True
    after = get_editable_config("codex-code-agent", cfg)
    assert after["values"]["AGENT_PROVIDER"] == "local"
    assert after["values"]["CODEX_CLI_TIMEOUT_MS"] == "700000"
    assert next(peer for peer in after["values"]["A2A_BOTS"] if peer["name"] == "项目调度官")["description"] == "updated"
    assert "open-id-secret" not in json.dumps(after, ensure_ascii=False)

    rollback_latest("codex-code-agent", cfg)
    restored = get_editable_config("codex-code-agent", cfg)
    assert restored["values"]["AGENT_PROVIDER"] == before["values"]["AGENT_PROVIDER"]


def test_openclaw_editable_config_updates_with_backup(tmp_path: Path) -> None:
    cfg = _config(tmp_path)

    result = update_editable_config(
        "openclaw-coordinator",
        {"identityTheme": "新的项目调度职责", "feishuAccountEnabled": False},
        cfg,
    )

    assert result["ok"] is True
    edited = get_editable_config("openclaw-coordinator", cfg)
    assert edited["values"]["identityTheme"] == "新的项目调度职责"
    assert edited["values"]["feishuAccountEnabled"] is False
    assert Path(result["backupPath"]).exists()


def test_editable_config_rejects_unsupported_or_sensitive_fields(tmp_path: Path) -> None:
    cfg = _config(tmp_path)

    try:
        update_editable_config("codex-code-agent", {"LARK_BOT_OPEN_ID": "open-id-secret"}, cfg)
    except ValueError as exc:
        assert "Unsupported fields" in str(exc)
    else:
        raise AssertionError("sensitive field update should fail")


def test_manual_backup_and_rollback_for_openclaw(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    backup = backup_config("openclaw-coordinator", cfg)
    assert Path(backup["backupPath"]).exists()
    result = rollback_latest("openclaw-coordinator", cfg)
    assert result["ok"] is True
