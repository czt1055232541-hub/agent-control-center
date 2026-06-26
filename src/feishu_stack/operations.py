from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Callable

from fastapi import HTTPException

from .config import StackConfig, load_config
from .log_manager import setup_logger
from .models import OperationResult, to_dict
from . import metrics


@dataclass
class OperationRecord:
    timestamp: str
    component: str
    action: str
    ok: bool
    message: str
    duration_ms: int


_lock = threading.Lock()
_records: list[OperationRecord] = []
_max_records = 50
_op_logger: logging.Logger | None = None


def recent_operations() -> list[OperationRecord]:
    return list(reversed(_records[-_max_records:]))


def _record(result: OperationResult, config: StackConfig) -> None:
    record = OperationRecord(
        timestamp=datetime.now(timezone.utc).isoformat(),
        component=result.component,
        action=result.action,
        ok=result.ok,
        message=result.message,
        duration_ms=result.duration_ms,
    )
    _records.append(record)
    del _records[:-_max_records]
    global _op_logger
    if _op_logger is None:
        _op_logger = setup_logger("operations", config.log_dir / "operations.jsonl")
        for handler in _op_logger.handlers:
            handler.setFormatter(logging.Formatter("%(message)s"))
    _op_logger.info(json.dumps(asdict(record), ensure_ascii=False))
    metrics.record_operation(record.component, record.action, record.ok)


def run_exclusive(component: str, action: str, fn: Callable[[StackConfig], OperationResult]) -> OperationResult:
    if not _lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Another control operation is already running.")
    cfg = load_config()
    started = time.monotonic()
    try:
        result = fn(cfg)
        if result.duration_ms == 0:
            result.duration_ms = int((time.monotonic() - started) * 1000)
        _record(result, cfg)
        return result
    except HTTPException:
        raise
    except Exception as exc:
        result = OperationResult(
            ok=False,
            component=component,
            action=action,
            message=str(exc),
            duration_ms=int((time.monotonic() - started) * 1000),
        )
        _record(result, cfg)
        raise HTTPException(status_code=500, detail=to_dict(result)) from exc
    finally:
        _lock.release()
