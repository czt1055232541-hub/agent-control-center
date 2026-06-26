from __future__ import annotations

from pathlib import Path

from .models import LogTail


def tail(path: Path, lines: int = 80) -> LogTail:
    if not path.exists() and not any(path.parent.glob(f"{path.name}.*")):
        return LogTail(path=str(path), lines=[])
    all_lines: list[str] = []
    for candidate in sorted(path.parent.glob(f"{path.name}*"), key=lambda p: p.stat().st_mtime):
        if candidate.name == path.name or candidate.name.startswith(f"{path.name}."):
            candidate_lines = candidate.read_text(encoding="utf-8", errors="replace").splitlines()
            all_lines.extend(candidate_lines)
    return LogTail(path=str(path), lines=all_lines[-lines:])

