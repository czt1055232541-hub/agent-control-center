"""Routing rules - in-memory routing rule CRUD.

Provides thread-safe list / get / set / delete / batch operations
backed by a plain dict.  No external database dependency.

Each rule has:
  - rule_id (str): user-defined or auto-generated
  - name (str): rule display name
  - pattern (str): matching pattern (e.g. mention patterns like @项目调度官)
  - target (str): target module/agent
  - enabled (bool): whether the rule is active
  - description (str, optional): human-readable description
"""

from __future__ import annotations

import threading
import uuid
from typing import Any

_store: dict[str, dict[str, Any]] = {}
_lock = threading.Lock()


def list_rules() -> list[dict[str, Any]]:
    """Return all routing rules sorted by rule_id."""
    with _lock:
        return [
            {
                "rule_id": k,
                "name": v["name"],
                "pattern": v["pattern"],
                "target": v["target"],
                "enabled": v["enabled"],
                "description": v.get("description", ""),
            }
            for k, v in sorted(_store.items())
        ]


def get_rule(rule_id: str) -> dict[str, Any] | None:
    """Return a single routing rule or None."""
    with _lock:
        item = _store.get(rule_id)
        if item is None:
            return None
        return {
            "rule_id": rule_id,
            "name": item["name"],
            "pattern": item["pattern"],
            "target": item["target"],
            "enabled": item["enabled"],
            "description": item.get("description", ""),
        }


def set_rule(
    rule_id: str,
    name: str,
    pattern: str,
    target: str,
    enabled: bool = True,
    description: str = "",
) -> dict[str, Any]:
    """Create or update a routing rule.

    If rule_id is empty or "auto", a UUID is generated automatically.
    Returns the saved rule dict.
    """
    resolved_id = rule_id
    if not resolved_id or resolved_id == "auto":
        resolved_id = uuid.uuid4().hex[:12]
    with _lock:
        _store[resolved_id] = {
            "name": name,
            "pattern": pattern,
            "target": target,
            "enabled": enabled,
            "description": description or "",
        }
        return {
            "rule_id": resolved_id,
            "name": _store[resolved_id]["name"],
            "pattern": _store[resolved_id]["pattern"],
            "target": _store[resolved_id]["target"],
            "enabled": _store[resolved_id]["enabled"],
            "description": _store[resolved_id].get("description", ""),
        }


def delete_rule(rule_id: str) -> bool:
    """Delete a routing rule.  Returns True if the rule_id existed."""
    with _lock:
        return _store.pop(rule_id, None) is not None


def batch_import_rules(
    rules: list[dict[str, Any]],
) -> dict[str, Any]:
    """Import multiple routing rules at once.

    Each item may have: rule_id (optional), name, pattern, target, enabled, description.
    If rule_id is omitted or "auto", a UUID is generated.
    Returns import stats.
    """
    imported = 0
    with _lock:
        for item in rules:
            rid = item.get("rule_id", "")
            if not rid or rid == "auto":
                rid = uuid.uuid4().hex[:12]
            _store[rid] = {
                "name": item.get("name", ""),
                "pattern": item.get("pattern", ""),
                "target": item.get("target", ""),
                "enabled": item.get("enabled", True),
                "description": item.get("description", ""),
            }
            imported += 1
        return {"imported": imported, "total": len(_store)}
