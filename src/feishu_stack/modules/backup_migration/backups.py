from __future__ import annotations
import time
from feishu_stack.core.settings import StackConfig, load_config
from feishu_stack.core.models import OperationResult
from .retention import _cleanup_backups

def clean(config: StackConfig | None = None, keep: int = 1) -> OperationResult:
    cfg = config or load_config()
    started = time.monotonic()
    removed_switch = _cleanup_backups(cfg.codex_home, "config.toml.bak-switch-*", keep)
    removed_restore = _cleanup_backups(cfg.codex_home, "config.toml.bak-restore-native-*", keep)
    return OperationResult(
        ok=True,
        component="backups",
        action="clean",
        message=f"Removed switch backups: {removed_switch}; removed restore backups: {removed_restore}; goal backups preserved.",
        duration_ms=int((time.monotonic() - started) * 1000),
    )
