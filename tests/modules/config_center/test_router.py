from __future__ import annotations

import pytest

from feishu_stack.modules.config_center import router


@pytest.fixture(autouse=True)
def clear_store():
    router._store.clear()
    yield
    router._store.clear()


def test_config_crud_and_export_are_deterministic() -> None:
    router.set_config("zeta", "2", "last")
    router.set_config("alpha", "1")
    assert [item["key"] for item in router.list_configs()] == ["alpha", "zeta"]
    assert router.get_config("alpha")["value"] == "1"
    assert router.export_configs()["configs"]["zeta"]["description"] == "last"
    assert router.delete_config("alpha") is True
    assert router.delete_config("alpha") is False


def test_import_reports_counts_and_normalizes_missing_values() -> None:
    result = router.import_configs({"one": {}, "two": {"value": "2"}})
    assert result == {"imported": 2, "total": 2}
    assert router.get_config("one")["value"] == ""
