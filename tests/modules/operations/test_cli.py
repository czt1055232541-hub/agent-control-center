from __future__ import annotations

from feishu_stack import cli
from feishu_stack.models import OperationResult, ThreadMigrationResult


def test_cli_routes_stack_action(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "load_config", lambda: object())
    monkeypatch.setattr(cli.stack_actions, "start_deepseek", lambda: OperationResult(True, "stack", "start-deepseek", "ok"))
    assert cli.main(["stack", "start-deepseek", "--json"]) == 0
    assert '"component": "stack"' in capsys.readouterr().out


def test_cli_routes_backup_cleanup(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "load_config", lambda: object())
    monkeypatch.setattr(cli.backups, "clean", lambda: OperationResult(True, "backups", "clean", "ok"))
    assert cli.main(["backups", "clean", "--json"]) == 0
    assert '"component": "backups"' in capsys.readouterr().out


def test_cli_routes_thread_migration(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "load_config", lambda: object())
    monkeypatch.setattr(
        cli.thread_migration,
        "migrate_thread",
        lambda session_id, target_provider, prompt: ThreadMigrationResult(
            True,
            "thread-migration",
            "migrate",
            "ok",
            source_session_id=session_id,
            target_provider=target_provider,
            target_model="deepseek-v4-pro",
            summary_path="F:/summary.txt",
            launch_mode="cli-session-fallback",
        ),
    )
    assert cli.main(["migrate-thread", "--session-id", "abc", "--target-provider", "deepseek", "--json"]) == 0
    output = capsys.readouterr().out
    assert '"component": "thread-migration"' in output
    assert '"source_session_id": "abc"' in output
