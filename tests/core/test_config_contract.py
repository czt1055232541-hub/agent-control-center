from __future__ import annotations

import json
from pathlib import Path

import pytest

from feishu_stack.core.config_contract import atomic_write_json, compare_shared_config, redact_config, validate_shared_config


def _config(root: Path, *, openclaw_port: int = 18789) -> dict:
    return {
        "codexHome": str(root / "codex"),
        "codexBin": str(root / "codex" / "codex.exe"),
        "codexConfig": str(root / "codex" / "config.toml"),
        "codexNativeModel": "native",
        "codexMoonBridgeModel": "bridge",
        "codexSwitchScript": str(root / "switch.py"),
        "moonbridge": {"dir": str(root / "bridge"), "exe": str(root / "bridge.exe"), "config": str(root / "bridge.yml"), "port": 38440},
        "openclaw": {"home": str(root / "claw"), "gatewayCmd": str(root / "gateway.cmd"), "port": openclaw_port, "token": "private"},
        "agent": {"dir": str(root / "agent"), "larkCliBin": str(root / "lark.exe"), "larkBotOpenId": "ou_private"},
        "runtime": {"dir": str(root / "runtime"), "logs": str(root / "runtime/logs"), "pids": str(root / "runtime/pids")},
    }


def test_validation_rejects_invalid_port(tmp_path: Path) -> None:
    raw = _config(tmp_path, openclaw_port=70000)
    result = validate_shared_config(raw)
    assert result["ok"] is False
    assert any(item["field"] == "openclaw.port" for item in result["errors"])


def test_redaction_hides_nested_feishu_identifiers(tmp_path: Path) -> None:
    redacted = redact_config(_config(tmp_path))
    assert redacted["openclaw"]["token"] == "<redacted>"
    assert redacted["agent"]["larkBotOpenId"] == "<redacted>"
    assert "private" not in json.dumps(redacted)


def test_drift_is_limited_to_shared_fields(tmp_path: Path) -> None:
    primary = _config(tmp_path, openclaw_port=18789)
    peer = _config(tmp_path, openclaw_port=18790)
    peer["agent"]["larkBotOpenId"] = "ou_other"
    drift = compare_shared_config(primary, peer)
    assert [item["field"] for item in drift] == ["openclaw.port"]


def test_atomic_write_preserves_valid_file_when_validation_fails(tmp_path: Path) -> None:
    target = tmp_path / "stack.json"
    target.write_text('{"version": 1}\n', encoding="utf-8")

    def reject(_payload: dict) -> None:
        raise ValueError("invalid")

    with pytest.raises(ValueError):
        atomic_write_json(target, {"version": 2}, validator=reject)
    assert json.loads(target.read_text(encoding="utf-8")) == {"version": 1}


def test_atomic_write_retains_bounded_backups(tmp_path: Path) -> None:
    target = tmp_path / "stack.json"
    atomic_write_json(target, {"version": 0}, backup_limit=2)
    for version in range(1, 5):
        atomic_write_json(target, {"version": version}, backup_limit=2)
    assert json.loads(target.read_text(encoding="utf-8")) == {"version": 4}
    assert len(list(tmp_path.glob("stack.json.bak-*"))) == 2
