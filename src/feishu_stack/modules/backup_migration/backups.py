from __future__ import annotations

from feishu_stack.modules.model_provider import codex_config
from feishu_stack.core.settings import StackConfig, load_config
from feishu_stack.core.models import OperationResult


def clean(config: StackConfig | None = None, keep: int = 1) -> OperationResult:
    cfg = config or load_config()
    return codex_config.clean_backups(cfg, keep)
