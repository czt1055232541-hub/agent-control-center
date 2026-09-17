import pytest
from fastapi import HTTPException


def test_legacy_operation_alias_shares_lock_and_records():
    from feishu_stack.core import operations
    from feishu_stack.modules.operations import operations as legacy
    assert legacy is operations
    assert legacy._records is operations._records
    assert operations._lock.acquire(blocking=False)
    try:
        with pytest.raises(HTTPException) as exc:
            legacy.run_exclusive('test', 'read', lambda cfg: None)
        assert exc.value.status_code == 409
    finally:
        operations._lock.release()


def test_configuration_failure_releases_operation_lock(monkeypatch):
    from feishu_stack.core import operations
    def fail():
        raise RuntimeError('test configuration failure')
    monkeypatch.setattr(operations, 'load_config', fail)
    with pytest.raises(RuntimeError, match='test configuration failure'):
        operations.run_exclusive('test', 'read', lambda cfg: None)
    assert operations._lock.acquire(blocking=False)
    operations._lock.release()
