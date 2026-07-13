"""Config center - in-memory configuration CRUD.

Provides thread-safe list / get / set / delete / export / import operations
backed by a plain dict.  No external database dependency.
"""

from __future__ import annotations

import threading
from typing import Any

_store: dict[str, dict[str, Any]] = {}
_lock = threading.Lock()


def list_configs() -> list[dict[str, Any]]:
    """Return all config entries sorted by key."""
    with _lock:
        return [{"key": k, "value": v["value"], "description": v.get("description", "")}
                for k, v in sorted(_store.items())]


def get_config(key: str) -> dict[str, Any] | None:
    """Return a single config entry or None."""
    with _lock:
        item = _store.get(key)
        if item is None:
            return None
        return {"key": key, "value": item["value"], "description": item.get("description", "")}


def set_config(key: str, value: str, description: str = "") -> dict[str, Any]:
    """Create or update a config entry."""
    with _lock:
        _store[key] = {"value": value, "description": description or ""}
        return {"key": key, "value": _store[key]["value"], "description": _store[key]["description"]}


def delete_config(key: str) -> bool:
    """Delete a config entry.  Returns True if the key existed."""
    with _lock:
        return _store.pop(key, None) is not None


def export_configs() -> dict[str, Any]:
    """Return the full config dict for export."""
    with _lock:
        return {"configs": {k: v for k, v in _store.items()}}


def import_configs(configs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Import config entries from a dict.  Returns import stats."""
    with _lock:
        count = 0
        for k, v in configs.items():
            _store[k] = {"value": v.get("value", ""), "description": v.get("description", "")}
            count += 1
        return {"imported": count, "total": len(_store)}
