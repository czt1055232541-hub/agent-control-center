from __future__ import annotations

from . import codex_config
from .config import StackConfig, load_config
from .models import OperationResult


def clean(config: StackConfig | None = None, keep: int = 1) -> OperationResult:
    cfg = config or load_config()
    return codex_config.clean_backups(cfg, keep)
