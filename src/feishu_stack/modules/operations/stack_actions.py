from __future__ import annotations

import time

from feishu_stack.modules.model_provider import codex_agent, provider_switch
from feishu_stack.modules.model_provider import openclaw_gateway as openclaw
from feishu_stack.modules.operations import typing_indicator
from feishu_stack.core.settings import StackConfig, load_config
from feishu_stack.core.models import OperationResult
from feishu_stack.core.process import process_info, read_pid


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


def _codex_agent_running(cfg: StackConfig) -> bool:
    pid = read_pid(cfg.pid_codex_agent)
    running, _ = process_info(pid)
    return running


def switch_agent_provider(
    mode: str,
    config: StackConfig | None = None,
    deepseek_model: str | None = None,
    reasoning_effort: str | None = None,
) -> OperationResult:
    cfg = config or load_config()
    started = time.monotonic()
    switch_result = provider_switch.switch_provider(
        mode,
        cfg,
        deepseek_model=deepseek_model,
        reasoning_effort=reasoning_effort,
        target="agent",
    )
    if not switch_result.ok:
        switch_result.duration_ms = switch_result.duration_ms or int((time.monotonic() - started) * 1000)
        return switch_result
    if not _codex_agent_running(cfg):
        switch_result.message = f"{switch_result.message} Codex Agent is not running; the next start will use the selected provider."
        switch_result.duration_ms = switch_result.duration_ms or int((time.monotonic() - started) * 1000)
        return switch_result
    restart_result = codex_agent.restart(cfg)
    return _combine(f"switch-agent-{mode}", [switch_result, restart_result], started)


def start_native(config: StackConfig | None = None) -> OperationResult:
    cfg = config or load_config()
    started = time.monotonic()
    results = [
        provider_switch.switch_provider("native", cfg, target="agent"),
        openclaw.start(cfg),
        codex_agent.restart(cfg),
        typing_indicator.start(cfg),
    ]
    return _combine("start-native", results, started)


def start_deepseek(config: StackConfig | None = None) -> OperationResult:
    cfg = config or load_config()
    started = time.monotonic()
    results = [
        provider_switch.switch_provider("deepseek", cfg, target="agent"),
        openclaw.start(cfg),
        codex_agent.restart(cfg),
        typing_indicator.start(cfg),
    ]
    return _combine("start-deepseek", results, started)


def stop(config: StackConfig | None = None) -> OperationResult:
    cfg = config or load_config()
    started = time.monotonic()
    results = [
        typing_indicator.stop(cfg),
        codex_agent.stop(cfg),
        openclaw.stop(cfg),
    ]
    return _combine("stop", results, started)
