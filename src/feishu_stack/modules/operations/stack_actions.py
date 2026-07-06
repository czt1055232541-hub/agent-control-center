from __future__ import annotations

import time

from feishu_stack.modules.model_provider import codex_agent, provider_switch
from feishu_stack.modules.model_provider import moonbridge
from feishu_stack.modules.model_provider import openclaw_gateway as openclaw
from feishu_stack.modules.operations import typing_indicator
from feishu_stack.core.settings import StackConfig, load_config
from feishu_stack.core.models import OperationResult


def _combine(action: str, results: list[OperationResult], started: float) -> OperationResult:
    ok = all(result.ok for result in results)
    message = " | ".join(f"{result.component}: {result.message}" for result in results)
    return OperationResult(
        ok=ok,
        component="stack",
        action=action,
        message=message,
        duration_ms=int((time.monotonic() - started) * 1000),
    )


def start_native(config: StackConfig | None = None) -> OperationResult:
    cfg = config or load_config()
    started = time.monotonic()
    results = [
        provider_switch.switch_provider("native", cfg),
        openclaw.start(cfg),
        codex_agent.start(cfg),
        typing_indicator.start(cfg),
    ]
    return _combine("start-native", results, started)


def start_moonbridge(config: StackConfig | None = None) -> OperationResult:
    cfg = config or load_config()
    started = time.monotonic()
    results = [
        moonbridge.start(cfg),
        provider_switch.switch_provider("moonbridge", cfg),
        openclaw.start(cfg),
        codex_agent.start(cfg),
        typing_indicator.start(cfg),
    ]
    return _combine("start-moonbridge", results, started)


def stop(config: StackConfig | None = None) -> OperationResult:
    cfg = config or load_config()
    started = time.monotonic()
    results = [
        typing_indicator.stop(cfg),
        codex_agent.stop(cfg),
        moonbridge.stop(cfg),
        openclaw.stop(cfg),
    ]
    return _combine("stop", results, started)
