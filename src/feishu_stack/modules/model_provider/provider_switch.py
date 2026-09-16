from __future__ import annotations

import time

from feishu_stack.modules.model_provider import codex_config
from feishu_stack.core.settings import StackConfig, load_config
from feishu_stack.core.models import OperationResult
from feishu_stack.core.status import read_provider_status


def switch_provider(
    mode: str,
    config: StackConfig | None = None,
    deepseek_model: str | None = None,
    reasoning_effort: str | None = None,
    target: str = "app",
) -> OperationResult:
    cfg = config or load_config()
    started = time.monotonic()
    config_path = cfg.agent.codex_config if target == "agent" else cfg.codex_config
    current = read_provider_status(cfg, config_path)
    target_mode = "native" if mode == "toggle" and current.mode != "native" else "deepseek" if mode == "toggle" else mode
    result = codex_config.switch_provider(
        target_mode,
        cfg,
        deepseek_model=deepseek_model,
        reasoning_effort=reasoning_effort,
        target=target,
    )
    result.duration_ms = result.duration_ms or int((time.monotonic() - started) * 1000)
    return result
