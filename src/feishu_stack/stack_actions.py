from __future__ import annotations

import time

from . import codex_agent, codex_provider, moonbridge, openclaw
from .config import StackConfig, load_config
from .models import OperationResult


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
        codex_provider.switch_provider("native", cfg),
        openclaw.start(cfg),
        codex_agent.start(cfg),
    ]
    return _combine("start-native", results, started)


def start_moonbridge(config: StackConfig | None = None) -> OperationResult:
    cfg = config or load_config()
    started = time.monotonic()
    results = [
        moonbridge.start(cfg),
        codex_provider.switch_provider("moonbridge", cfg),
        openclaw.start(cfg),
        codex_agent.start(cfg),
    ]
    return _combine("start-moonbridge", results, started)


def stop(config: StackConfig | None = None) -> OperationResult:
    cfg = config or load_config()
    started = time.monotonic()
    results = [
        codex_agent.stop(cfg),
        moonbridge.stop(cfg),
        openclaw.stop(cfg),
    ]
    return _combine("stop", results, started)
