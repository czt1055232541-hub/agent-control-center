from __future__ import annotations

from types import SimpleNamespace

from feishu_stack.modules.feishu_connection import router


def _config():
    return SimpleNamespace(
        app_id="cli_private_application_id",
        app_name="Test App",
        agent=SimpleNamespace(
            a2a_bots=[{"name": "Agent", "openId": "ou_private_identifier", "description": "worker"}],
            a2a_relay=SimpleNamespace(group_chat_id="oc_private_group"),
        ),
    )


def test_connection_status_masks_app_id(monkeypatch) -> None:
    monkeypatch.setattr(router, "lark_auth_status", lambda _cfg: {"ok": False, "stdout": "", "stderr": "offline", "duration_ms": 1})
    result = router.get_connection_status(_config())
    assert result["appIdMasked"].endswith("****")
    assert "private_application_id" not in result["appIdMasked"]


def test_connection_accounts_never_return_raw_ids() -> None:
    result = router.get_connection_accounts(_config())
    serialized = str(result)
    assert "ou_private_identifier" not in serialized
    assert "oc_private_group" not in serialized
    assert result["accounts"][0]["bindingStatus"] == "bound"
