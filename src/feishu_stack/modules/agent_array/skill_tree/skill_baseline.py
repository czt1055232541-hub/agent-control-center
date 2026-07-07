from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from feishu_stack.core.settings import StackConfig, load_config
from feishu_stack.modules.agent_array.skill_tree.skill_registry import SkillInventory, get_inventory


BASELINE_SCHEMA_VERSION = 1
CONFIRM_BASELINE_TEXT = "CONFIRM BASELINE"
CONFIRM_SNAPSHOT_TEXT = "CREATE SNAPSHOT"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _workshop_dir(config: StackConfig | None = None) -> Path:
    cfg = config or load_config()
    path = cfg.runtime_dir / "skill-workshop"
    path.mkdir(parents=True, exist_ok=True)
    return path


def baseline_path(config: StackConfig | None = None) -> Path:
    return _workshop_dir(config) / "baseline.json"


def snapshots_dir(config: StackConfig | None = None) -> Path:
    path = _workshop_dir(config) / "snapshots"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _safe_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def load_baseline(config: StackConfig | None = None) -> dict[str, Any] | None:
    path = baseline_path(config)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _inventory_to_baseline(
    inventory: SkillInventory,
    *,
    confirmed_by: str,
) -> dict[str, Any]:
    now = _utc_now()
    skills: list[dict[str, Any]] = []
    for skill in inventory.skills:
        item = skill.to_dict()
        item["baseline"] = {
            "skillMdSha256": skill.version,
            "directorySha256": skill.dir_hash or "",
            "version": skill.version,
            "confirmedAt": now,
            "confirmedBy": confirmed_by or "manual",
        }
        skills.append(item)
    return {
        "schemaVersion": BASELINE_SCHEMA_VERSION,
        "confirmedAt": now,
        "confirmedBy": confirmed_by or "manual",
        "skillCount": len(skills),
        "skills": skills,
    }


def backup_existing_baseline(config: StackConfig | None = None) -> str | None:
    current = baseline_path(config)
    if not current.is_file():
        return None
    target = snapshots_dir(config) / f"baseline-{_safe_timestamp()}.json"
    shutil.copy2(current, target)
    return target.name


def preview_baseline_diff(
    inventory: SkillInventory | None = None,
    config: StackConfig | None = None,
) -> dict[str, Any]:
    inv = inventory or get_inventory(config)
    baseline = load_baseline(config)
    actual_ids = {skill.skill_id for skill in inv.skills}
    baseline_skills = {
        entry.get("skillId"): entry
        for entry in (baseline or {}).get("skills", [])
        if isinstance(entry, dict) and entry.get("skillId")
    }
    baseline_ids = set(baseline_skills.keys())
    changed: list[dict[str, Any]] = []
    added: list[str] = sorted(actual_ids - baseline_ids)
    removed: list[str] = sorted(baseline_ids - actual_ids)

    for skill in inv.skills:
        previous = baseline_skills.get(skill.skill_id)
        if previous and previous.get("version") != skill.version:
            changed.append(
                {
                    "skillId": skill.skill_id,
                    "displayName": skill.name,
                    "sourceAlias": skill.source_alias,
                    "runtime": skill.source,
                    "baselineVersion": previous.get("version"),
                    "actualVersion": skill.version,
                }
            )

    return {
        "hasBaseline": baseline is not None,
        "actualSkillCount": inv.total,
        "baselineSkillCount": len(baseline_ids),
        "addedSkillIds": added,
        "removedSkillIds": removed,
        "changed": changed,
        "confirmText": CONFIRM_BASELINE_TEXT,
    }


def confirm_baseline(
    *,
    confirm_text: str,
    confirmed_by: str = "manual",
    inventory: SkillInventory | None = None,
    config: StackConfig | None = None,
) -> dict[str, Any]:
    if confirm_text != CONFIRM_BASELINE_TEXT:
        raise ValueError(f"confirmText must be {CONFIRM_BASELINE_TEXT!r}")
    inv = inventory or get_inventory(config)
    backup_name = backup_existing_baseline(config)
    data = _inventory_to_baseline(inv, confirmed_by=confirmed_by)
    path = baseline_path(config)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "ok": True,
        "baselineFile": path.name,
        "previousBaselineSnapshot": backup_name,
        "skillCount": inv.total,
        "confirmedAt": data["confirmedAt"],
        "confirmedBy": data["confirmedBy"],
    }


def create_snapshot(
    *,
    confirm_text: str,
    created_by: str = "manual",
    inventory: SkillInventory | None = None,
    config: StackConfig | None = None,
) -> dict[str, Any]:
    if confirm_text != CONFIRM_SNAPSHOT_TEXT:
        raise ValueError(f"confirmText must be {CONFIRM_SNAPSHOT_TEXT!r}")
    inv = inventory or get_inventory(config)
    data = {
        "schemaVersion": BASELINE_SCHEMA_VERSION,
        "snapshotType": "skill-inventory",
        "createdAt": _utc_now(),
        "createdBy": created_by or "manual",
        "skillCount": inv.total,
        "inventory": inv.to_dict(),
    }
    path = snapshots_dir(config) / f"skill-snapshot-{_safe_timestamp()}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "ok": True,
        "snapshotFile": path.name,
        "skillCount": inv.total,
        "createdAt": data["createdAt"],
        "createdBy": data["createdBy"],
    }
