from __future__ import annotations

import time

from . import codex_config
from .config import StackConfig, load_config
from .models import OperationResult


def switch_provider(mode: str, config: StackConfig | None = None) -> OperationResult:
    cfg = config or load_config()
    started = time.monotonic()
    result = codex_config.switch_provider(mode, cfg)
    result.duration_ms = result.duration_ms or int((time.monotonic() - started) * 1000)
    return result
