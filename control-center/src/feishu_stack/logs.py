from __future__ import annotations

from pathlib import Path

from .models import LogTail


def tail(path: Path, lines: int = 80) -> LogTail:
    if not path.exists():
        return LogTail(path=str(path), lines=[])
    content = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return LogTail(path=str(path), lines=content[-lines:])

