from __future__ import annotations

import time

from feishu_stack.modules.model_provider import codex_config
from feishu_stack.core.settings import StackConfig, load_config
from feishu_stack.core.models import OperationResult


def switch_provider(
    mode: str,
    config: StackConfig | None = None,
    moonbridge_model: str | None = None,
    reasoning_effort: str | None = None,
) -> OperationResult:
    cfg = config or load_config()
    started = time.monotonic()
    result = codex_config.switch_provider(
        mode,
        cfg,
        moonbridge_model=moonbridge_model,
        reasoning_effort=reasoning_effort,
    )
    result.duration_ms = result.duration_ms or int((time.monotonic() - started) * 1000)
    return result
