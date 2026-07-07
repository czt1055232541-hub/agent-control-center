from __future__ import annotations

import time

from feishu_stack.modules.model_provider import codex_config
from feishu_stack.modules.model_provider import moonbridge
from feishu_stack.core.settings import StackConfig, load_config
from feishu_stack.core.models import OperationResult
from feishu_stack.core.status import read_provider_status


def switch_provider(
    mode: str,
    config: StackConfig | None = None,
    moonbridge_model: str | None = None,
    reasoning_effort: str | None = None,
) -> OperationResult:
    cfg = config or load_config()
    started = time.monotonic()
    current = read_provider_status(cfg)
    target = "native" if mode == "toggle" and current.mode == "moonbridge" else "moonbridge" if mode == "toggle" else mode
    moonbridge_result: OperationResult | None = None
    if target == "moonbridge":
        target_model = moonbridge_model or cfg.moonbridge_model
        target_effort = reasoning_effort or cfg.moonbridge_reasoning_effort
        moonbridge_result = moonbridge.switch_model(target_model, cfg, target_effort)
        if not moonbridge_result.ok:
            moonbridge_result.component = "codex-provider"
            moonbridge_result.action = "switch-moonbridge"
            moonbridge_result.duration_ms = int((time.monotonic() - started) * 1000)
            return moonbridge_result
    result = codex_config.switch_provider(
        mode,
        cfg,
        moonbridge_model=moonbridge_model,
        reasoning_effort=reasoning_effort,
    )
    if moonbridge_result is not None and moonbridge_result.message:
        result.message = f"{result.message} MoonBridge: {moonbridge_result.message}"
    result.duration_ms = result.duration_ms or int((time.monotonic() - started) * 1000)
    return result
