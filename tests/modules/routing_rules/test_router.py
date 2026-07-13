from __future__ import annotations

import pytest

from feishu_stack.modules.routing_rules import router


@pytest.fixture(autouse=True)
def clear_store():
    router._store.clear()
    yield
    router._store.clear()


def test_rule_crud_preserves_compatibility_shape() -> None:
    saved = router.set_rule("rule-1", "Coordinator", "@coord", "coordinator")
    assert saved["enabled"] is True
    assert router.get_rule("rule-1")["pattern"] == "@coord"
    assert router.list_rules()[0]["rule_id"] == "rule-1"
    assert router.delete_rule("rule-1") is True


def test_batch_import_generates_id_for_auto_rule() -> None:
    result = router.batch_import_rules([{"rule_id": "auto", "name": "Auto", "pattern": "*", "target": "default"}])
    assert result == {"imported": 1, "total": 1}
    assert router.list_rules()[0]["rule_id"] != "auto"
