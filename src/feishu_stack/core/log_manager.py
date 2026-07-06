from __future__ import annotations

import io
import logging
import os
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import IO

MAX_BYTES = 10 * 1024 * 1024  # 10 MB
BACKUP_COUNT = 5

_log_lock = threading.Lock()


def setup_logger(name: str, log_file: Path, max_bytes: int = MAX_BYTES, backup_count: int = BACKUP_COUNT) -> logging.Logger:
    """Create a logger that writes to a rotating file."""
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not any(isinstance(h, RotatingFileHandler) and h.baseFilename == str(log_file.resolve()) for h in logger.handlers):
        handler = RotatingFileHandler(
            str(log_file),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(handler)
    return logger


def _rotate_file(target: Path, max_bytes: int, backup_count: int) -> None:
    """Rotate a log file in-place when it exceeds max_bytes."""
    if not target.exists():
        return
    if target.stat().st_size < max_bytes:
        return
    with _log_lock:
        if not target.exists() or target.stat().st_size < max_bytes:
            return
        for i in range(backup_count - 1, 0, -1):
            src = target.with_name(f"{target.name}.{i}")
            dst = target.with_name(f"{target.name}.{i + 1}")
            if src.exists():
                if dst.exists():
                    dst.unlink()
                src.rename(dst)
        backup = target.with_name(f"{target.name}.1")
        if backup.exists():
            backup.unlink()
        target.rename(backup)


class RotatingFileWriter(io.IOBase):
    """A file-like object that rotates the underlying file when it exceeds max_bytes.

    Thread-safe for writes.  Used as the stdout/stderr target for long-running
    subprocesses so that log rotation happens automatically without restarting
    the parent process.
    """

    def __init__(self, path: Path, max_bytes: int = MAX_BYTES, backup_count: int = BACKUP_COUNT) -> None:
        self._path = path
        self._max_bytes = max_bytes
        self._backup_count = backup_count
        self._handle: IO[str] | None = None
        self._lock = threading.Lock()
        self._written = 0
        self._open()

    def _open(self) -> None:
        path_str = str(self._path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = open(path_str, "a", encoding="utf-8", errors="replace")
        try:
            self._written = self._path.stat().st_size
        except OSError:
            self._written = 0

    def write(self, s: str) -> int:
        with self._lock:
            if self._handle is None:
                return 0
            self._handle.write(s)
            self._handle.flush()
            self._written += len(s.encode("utf-8", errors="replace"))
            if self._written >= self._max_bytes:
                self._handle.close()
                _rotate_file(self._path, self._max_bytes, self._backup_count)
                self._open()
            return len(s)

    def flush(self) -> None:
        with self._lock:
            if self._handle is not None:
                self._handle.flush()

    def close(self) -> None:
        with self._lock:
            if self._handle is not None:
                self._handle.flush()
                self._handle.close()
                self._handle = None

    @property
    def closed(self) -> bool:
        return self._handle is None or self._handle.closed

    def fileno(self) -> int:
        with self._lock:
            if self._handle is None:
                raise ValueError("I/O operation on closed file")
            return self._handle.fileno()

    def readable(self) -> bool:
        return False

    def seekable(self) -> bool:
        return False

    def writable(self) -> bool:
        return True


def open_rotating(path: Path, max_bytes: int = MAX_BYTES, backup_count: int = BACKUP_COUNT) -> RotatingFileWriter:
    """Open a path for writing with automatic rotation."""
    _rotate_file(path, max_bytes, backup_count)
    return RotatingFileWriter(path, max_bytes, backup_count)
