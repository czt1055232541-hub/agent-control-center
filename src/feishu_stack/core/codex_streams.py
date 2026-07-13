from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from feishu_stack.core.settings import StackConfig


def stream_dir(cfg: StackConfig) -> Path:
    return cfg.runtime_dir / "streams" / "codex-agent"


def list_streams(cfg: StackConfig, limit: int = 20) -> list[dict[str, Any]]:
    directory = stream_dir(cfg)
    if not directory.exists():
        return []
    items: list[dict[str, Any]] = []
    for path in directory.glob("*.jsonl"):
        stat = path.stat()
        events = read_stream_file(path)
        first = events[0] if events else {}
        last = events[-1] if events else {}
        items.append(
            {
                "run_id": path.stem,
                "path": str(path),
                "mtime": stat.st_mtime,
                "size": stat.st_size,
                "event_count": len(events),
                "status": last.get("phase") or "unknown",
                "started_at": first.get("timestamp"),
                "updated_at": last.get("timestamp"),
                "message_id": first.get("message_id") or last.get("message_id"),
                "chat_type": first.get("chat_type") or last.get("chat_type"),
            }
        )
    return sorted(items, key=lambda item: float(item["mtime"]), reverse=True)[: max(1, min(limit, 100))]


def latest_stream_path(cfg: StackConfig) -> Path | None:
    streams = list_streams(cfg, limit=1)
    if not streams:
        return None
    return Path(streams[0]["path"])


def stream_path(cfg: StackConfig, run_id: str) -> Path | None:
    if run_id == "latest":
        return latest_stream_path(cfg)
    if not _valid_run_id(run_id):
        return None
    candidate = stream_dir(cfg) / f"{run_id}.jsonl"
    directory = stream_dir(cfg).resolve()
    resolved = candidate.resolve()
    if directory not in resolved.parents:
        return None
    return candidate if candidate.exists() else None


def read_stream(cfg: StackConfig, run_id: str) -> dict[str, Any] | None:
    path = stream_path(cfg, run_id)
    if path is None:
        return None
    return {"run_id": path.stem, "path": str(path), "events": read_stream_file(path)}


def read_stream_file(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                text = line.strip()
                if not text:
                    continue
                try:
                    value = json.loads(text)
                except json.JSONDecodeError:
                    value = {
                        "run_id": path.stem,
                        "timestamp": None,
                        "phase": "error",
                        "stream": "stage",
                        "text": "Malformed stream event skipped.",
                    }
                if isinstance(value, dict):
                    events.append(value)
    except OSError:
        return []
    return events


def _valid_run_id(value: str) -> bool:
    return bool(value) and all(ch.isalnum() or ch in {"-", "_"} for ch in value)
