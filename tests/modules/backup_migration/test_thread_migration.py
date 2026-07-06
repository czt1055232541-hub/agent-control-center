from __future__ import annotations

import json
from pathlib import Path

import pytest

from feishu_stack.config import StackConfig
from feishu_stack.modules.backup_migration.thread_migration import (
    DEFAULT_CONTINUATION_PROMPT,
    build_migration_summary,
    find_session_rollout,
    list_recent_threads,
    load_rollout_context,
    migrate_thread,
    open_summary_folder,
    start_migrated_session,
)


def make_config(tmp_path: Path) -> StackConfig:
    stack_root = tmp_path / "stack"
    codex_home = tmp_path / "codex-home"
    runtime_dir = stack_root / "runtime"
    log_dir = runtime_dir / "logs"
    pid_dir = runtime_dir / "pids"
    for path in (stack_root, codex_home, runtime_dir, log_dir, pid_dir):
        path.mkdir(parents=True, exist_ok=True)
    return StackConfig(
        raw={"moonBridgeBaseUrl": "http://127.0.0.1:38440/v1"},
        stack_root=stack_root,
        codex_home=codex_home,
        codex_bin=Path("E:/codeX/bin/codex.exe"),
        codex_config=codex_home / "config.toml",
        codex_switch_script=stack_root / "scripts" / "switch.ps1",
        native_model="gpt-5.5",
        native_reasoning_effort="high",
        moonbridge_model="moonbridge",
        moonbridge_dir=stack_root / "moonbridge",
        moonbridge_exe=stack_root / "moonbridge" / "moonbridge.exe",
        moonbridge_config=stack_root / "moonbridge" / "config.yml",
        moonbridge_port=38440,
        openclaw_home=stack_root / "openclaw",
        openclaw_gateway_cmd=stack_root / "openclaw" / "gateway.cmd",
        openclaw_port=18789,
        agent_dir=stack_root / "agent",
        agent_entry=stack_root / "agent" / "dist" / "src" / "index.js",
        lark_cli_bin=stack_root / "bin" / "lark-cli.cmd",
        lark_cli_home=stack_root / ".home",
        runtime_dir=runtime_dir,
        log_dir=log_dir,
       pid_dir=pid_dir,
        python_exe=Path("E:/Python/python.exe"),
   )


def write_rollout(cfg: StackConfig, session_id: str, provider: str = "openai", model: str = "gpt-5.5") -> Path:
    rollout_dir = cfg.codex_home / "sessions" / "2026" / "06" / "20"
    rollout_dir.mkdir(parents=True, exist_ok=True)
    rollout_path = rollout_dir / f"{session_id}.jsonl"
    lines = [
        json.dumps(
            {
                "type": "session_meta",
                "payload": {
                    "id": session_id,
                    "model_provider": provider,
                    "model": model,
                    "cwd": str(cfg.stack_root),
                    "first_user_message": "Migrate my context.",
                },
            },
            ensure_ascii=False,
        ),
        json.dumps(
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": f"Continue work in {cfg.stack_root}\\src\\main.py"}],
                },
            },
            ensure_ascii=False,
        ),
        json.dumps(
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": "Implemented API wiring and pending GUI work."}],
                },
            },
            ensure_ascii=False,
        ),
    ]
    rollout_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return rollout_path


def test_find_session_rollout_locates_matching_file(tmp_path: Path) -> None:
    cfg = make_config(tmp_path)
    path = write_rollout(cfg, "session-123")
    assert find_session_rollout("session-123", cfg) == path


def test_list_recent_threads_returns_title_and_session_id(tmp_path: Path) -> None:
    cfg = make_config(tmp_path)
    write_rollout(cfg, "session-threads")
    db_path = cfg.codex_home / "state_5.sqlite"
    import sqlite3

    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            """
            create table threads (
                id text primary key,
                rollout_path text,
                created_at integer,
                updated_at integer,
                source text,
                model_provider text,
                cwd text,
                title text,
                sandbox_policy text,
                approval_mode text,
                tokens_used integer,
                has_user_event integer,
                archived integer,
                archived_at integer,
                git_sha text,
                git_branch text,
                git_origin_url text,
                cli_version text,
                first_user_message text,
                agent_nickname text,
                agent_role text,
                memory_mode text,
                model text,
                reasoning_effort text,
                agent_path text,
                created_at_ms integer,
                updated_at_ms integer,
                thread_source text,
                preview text
            )
            """
        )
        conn.execute(
            """
            insert into threads (
                id, rollout_path, created_at, updated_at, source, model_provider, cwd, title,
                sandbox_policy, approval_mode, tokens_used, has_user_event, archived, cli_version,
                first_user_message, memory_mode, model, updated_at_ms, preview
            ) values (?, '', 0, 0, 'desktop', 'openai', ?, ?, 'workspace-write', 'never', 0, 1, 0, '', '', 'enabled', 'gpt-5.5', ?, '')
            """,
            ("session-threads", str(cfg.stack_root), "Visible Thread", 1750000000000),
        )
        conn.commit()
    threads = list_recent_threads(limit=10, config=cfg)
    assert threads
    assert threads[0].session_id == "session-threads"
    assert threads[0].title == "Visible Thread"


def test_find_session_rollout_raises_for_missing_session(tmp_path: Path) -> None:
    cfg = make_config(tmp_path)
    with pytest.raises(FileNotFoundError):
        find_session_rollout("missing-session", cfg)


def test_load_rollout_context_parses_meta_and_tail(tmp_path: Path) -> None:
    cfg = make_config(tmp_path)
    write_rollout(cfg, "session-parse")
    context = load_rollout_context("session-parse", cfg)
    assert context.source_provider == "openai"
    assert context.source_model == "gpt-5.5"
    assert context.first_user_message == "Migrate my context."
    assert context.recent_user_messages
    assert context.recent_assistant_messages
    assert any(path.endswith("src\\main.py") for path in context.important_files)


def test_build_migration_summary_uses_stable_template(tmp_path: Path) -> None:
    cfg = make_config(tmp_path)
    write_rollout(cfg, "session-summary")
    artifacts = build_migration_summary("session-summary", "moonbridge", "moonbridge", DEFAULT_CONTINUATION_PROMPT, cfg)
    summary = artifacts.summary_path.read_text(encoding="utf-8")
    assert summary.startswith("Migrated Codex thread context")
    assert "- Source thread title:" in summary
    assert "- Source session id: session-summary" in summary
    assert "- Target provider/model: moonbridge/moonbridge" in summary
    assert "- User continuation prompt: Continue this work from the migrated context." in summary
    assert artifacts.summary_path.parent == cfg.migration_summary_dir
    assert artifacts.excerpt_path.exists()
    assert artifacts.prompt_path.exists()
    assert "session-summary" not in artifacts.summary_path.name


def test_start_migrated_session_returns_manual_summary_result(tmp_path: Path) -> None:
    cfg = make_config(tmp_path)
    write_rollout(cfg, "session-launch")
    result = start_migrated_session("session-launch", "moonbridge", DEFAULT_CONTINUATION_PROMPT, cfg)
    assert result.ok is True
    assert result.launch_mode == "summary-only-manual"
    assert result.target_provider == "moonbridge"
    assert result.source_title == "Migrate my context."
    assert Path(result.summary_path or "").exists()
    assert result.summary_dir


def test_open_summary_folder_invokes_explorer(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cfg = make_config(tmp_path)
    write_rollout(cfg, "session-folder")
    result = start_migrated_session("session-folder", "native", DEFAULT_CONTINUATION_PROMPT, cfg)
    called: list[list[str]] = []

    class DummyProc:
        pass

    def fake_popen(command, creationflags=0):
        called.append(command)
        return DummyProc()

    monkeypatch.setattr("feishu_stack.modules.backup_migration.thread_migration.subprocess.Popen", fake_popen)
    open_result = open_summary_folder(result.summary_path or "")
    assert open_result.ok is True
    assert open_result.action == "open-summary-folder"
    assert called
    assert called[0][0].lower() == "explorer.exe"


def test_migrate_thread_rejects_unknown_provider(tmp_path: Path) -> None:
    cfg = make_config(tmp_path)
    with pytest.raises(ValueError):
        migrate_thread("session", "unknown", config=cfg)
