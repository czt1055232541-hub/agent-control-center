from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from feishu_stack.core.settings import find_stack_root


CONFIG_DIR = Path("config") / "skill-tree-workshop"
MANIFEST_NAME = "manifest.json"
LEGACY_MANIFEST_NAME = "skill-tree-workshop-config.json"


def _stack_root() -> Path:
    return find_stack_root(Path(__file__))


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _resolve_repo_path(value: str, *, root: Path | None = None) -> Path:
    stack_root = root or _stack_root()
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = stack_root / candidate
    resolved = candidate.resolve()
    if not resolved.is_relative_to(stack_root.resolve()):
        raise ValueError(f"Skill tree config path is outside stack root: {value}")
    return resolved


def manifest_path(root: Path | None = None) -> Path:
    stack_root = root or _stack_root()
    preferred = stack_root / CONFIG_DIR / MANIFEST_NAME
    if preferred.exists():
        return preferred
    legacy = stack_root / LEGACY_MANIFEST_NAME
    if legacy.exists():
        return legacy
    raise FileNotFoundError(f"Missing skill tree manifest: {preferred}")


def load_manifest(root: Path | None = None) -> dict[str, Any]:
    path = manifest_path(root)
    data = _read_json(path)
    data["manifestPath"] = str(path)
    return data


def load_agent_tree(agent_id: str, root: Path | None = None) -> dict[str, Any]:
    stack_root = root or _stack_root()
    manifest = load_manifest(stack_root)
    for item in manifest.get("agentConfigs", []):
        if item.get("agentId") != agent_id:
            continue
        config_path = _resolve_repo_path(str(item.get("configPath", "")), root=stack_root)
        tree = _read_json(config_path)
        tree["configPath"] = str(config_path)
        return tree
    raise KeyError(agent_id)


def load_all_tree_configs(root: Path | None = None) -> dict[str, Any]:
    stack_root = root or _stack_root()
    manifest = load_manifest(stack_root)
    agents: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for item in manifest.get("agentConfigs", []):
        agent_id = str(item.get("agentId", ""))
        try:
            agents.append(load_agent_tree(agent_id, stack_root))
        except Exception as exc:
            errors.append({"agentId": agent_id, "error": str(exc)})
    return {
        "version": manifest.get("version", 1),
        "description": manifest.get("description", ""),
        "manifestPath": manifest.get("manifestPath"),
        "agents": agents,
        "errors": errors,
    }
