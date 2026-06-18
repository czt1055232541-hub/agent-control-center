from __future__ import annotations

from feishu_stack import cli
from feishu_stack.models import OperationResult


def test_cli_routes_stack_action(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "load_config", lambda: object())
    monkeypatch.setattr(cli.stack_actions, "start_moonbridge", lambda: OperationResult(True, "stack", "start-moonbridge", "ok"))
    assert cli.main(["stack", "start-moonbridge", "--json"]) == 0
    assert '"component": "stack"' in capsys.readouterr().out


def test_cli_routes_backup_cleanup(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "load_config", lambda: object())
    monkeypatch.setattr(cli.backups, "clean", lambda: OperationResult(True, "backups", "clean", "ok"))
    assert cli.main(["backups", "clean", "--json"]) == 0
    assert '"component": "backups"' in capsys.readouterr().out
