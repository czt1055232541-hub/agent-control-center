from pathlib import Path

def _cleanup_backups(codex_home: Path, pattern: str, keep: int, keep_path: Path | None = None) -> int:
    files = sorted(codex_home.glob(pattern), key=lambda path: path.stat().st_mtime, reverse=True)
    removed = 0
    kept = 0
    for path in files:
        if keep_path and path.resolve() == keep_path.resolve():
            kept += 1
            continue
        if kept < keep:
            kept += 1
            continue
        path.unlink(missing_ok=True)
        removed += 1
    return removed
