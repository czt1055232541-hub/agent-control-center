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
CONFIRM_ROLLBACK_TEXT = "ROLLBACK WORKSHOP"


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


def _read_json_file(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _version_id_for_file(path: Path) -> str:
    return "baseline-current" if path.name == "baseline.json" else path.stem


def _history_files(config: StackConfig | None = None) -> list[Path]:
    files: list[Path] = []
    current = baseline_path(config)
    if current.is_file():
        files.append(current)
    snap_dir = snapshots_dir(config)
    files.extend(sorted(snap_dir.glob("baseline-*.json")))
    files.extend(sorted(snap_dir.glob("skill-snapshot-*.json")))
    return files


def _extract_skills(data: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(data.get("inventory"), dict):
        skills = data["inventory"].get("skills", [])
    else:
        skills = data.get("skills", [])
    return [entry for entry in skills if isinstance(entry, dict) and entry.get("skillId")]


def _version_type(data: dict[str, Any], path: Path) -> str:
    if path.name == "baseline.json":
        return "baseline-current"
    if data.get("snapshotType") == "skill-inventory" or path.name.startswith("skill-snapshot-"):
        return "snapshot"
    return "baseline-backup"


def _version_timestamp(data: dict[str, Any]) -> str | None:
    value = data.get("confirmedAt") or data.get("createdAt")
    return value if isinstance(value, str) else None


def _history_item(path: Path, data: dict[str, Any]) -> dict[str, Any]:
    skills = _extract_skills(data)
    return {
        "versionId": _version_id_for_file(path),
        "type": _version_type(data, path),
        "sourceFile": path.name,
        "timestamp": _version_timestamp(data),
        "createdBy": data.get("confirmedBy") or data.get("createdBy"),
        "skillCount": data.get("skillCount", len(skills)),
        "summary": (
            "Current baseline"
            if path.name == "baseline.json"
            else "Skill inventory snapshot"
            if data.get("snapshotType") == "skill-inventory"
            else "Baseline backup"
        ),
    }


def list_history(config: StackConfig | None = None) -> dict[str, Any]:
    versions: list[dict[str, Any]] = []
    for path in _history_files(config):
        data = _read_json_file(path)
        if data is not None:
            versions.append(_history_item(path, data))
    versions.sort(key=lambda item: item.get("timestamp") or item["versionId"], reverse=True)
    return {"versions": versions, "total": len(versions)}


def _load_version(version_id: str, config: StackConfig | None = None) -> tuple[Path, dict[str, Any]]:
    for path in _history_files(config):
        if _version_id_for_file(path) == version_id:
            data = _read_json_file(path)
            if data is None:
                raise ValueError(f"Version {version_id!r} is unreadable")
            return path, data
    raise FileNotFoundError(f"Unknown skill workshop version: {version_id}")


def get_version(version_id: str, config: StackConfig | None = None) -> dict[str, Any]:
    path, data = _load_version(version_id, config)
    item = _history_item(path, data)
    return {**item, "skills": _extract_skills(data), "rawType": data.get("snapshotType") or "baseline"}


def compare_versions(
    from_version: str,
    to_version: str,
    config: StackConfig | None = None,
) -> dict[str, Any]:
    from_data = get_version(from_version, config)
    to_data = get_version(to_version, config)
    from_skills = {entry["skillId"]: entry for entry in from_data["skills"]}
    to_skills = {entry["skillId"]: entry for entry in to_data["skills"]}
    from_ids = set(from_skills)
    to_ids = set(to_skills)
    changed: list[dict[str, Any]] = []

    for skill_id in sorted(from_ids & to_ids):
        left = from_skills[skill_id]
        right = to_skills[skill_id]
        left_version = left.get("version")
        right_version = right.get("version")
        left_dir = left.get("dirHash") or left.get("baseline", {}).get("directorySha256")
        right_dir = right.get("dirHash") or right.get("baseline", {}).get("directorySha256")
        if left_version != right_version or left_dir != right_dir:
            changed.append(
                {
                    "skillId": skill_id,
                    "displayName": right.get("name") or left.get("name") or skill_id,
                    "sourceAlias": right.get("sourceAlias") or left.get("sourceAlias") or "",
                    "runtime": right.get("source") or left.get("source") or "",
                    "fromVersion": left_version,
                    "toVersion": right_version,
                    "fromDirectorySha256": left_dir,
                    "toDirectorySha256": right_dir,
                }
            )

    return {
        "fromVersion": from_data["versionId"],
        "toVersion": to_data["versionId"],
        "addedSkillIds": sorted(to_ids - from_ids),
        "removedSkillIds": sorted(from_ids - to_ids),
        "changed": changed,
        "summary": {
            "added": len(to_ids - from_ids),
            "removed": len(from_ids - to_ids),
            "changed": len(changed),
        },
    }


def _skills_to_baseline(skills: list[dict[str, Any]], *, confirmed_by: str) -> dict[str, Any]:
    now = _utc_now()
    baseline_skills: list[dict[str, Any]] = []
    for entry in skills:
        item = dict(entry)
        item["baseline"] = {
            "skillMdSha256": item.get("version", ""),
            "directorySha256": item.get("dirHash") or item.get("baseline", {}).get("directorySha256") or "",
            "version": item.get("version", ""),
            "confirmedAt": now,
            "confirmedBy": confirmed_by or "manual",
        }
        baseline_skills.append(item)
    return {
        "schemaVersion": BASELINE_SCHEMA_VERSION,
        "confirmedAt": now,
        "confirmedBy": confirmed_by or "manual",
        "skillCount": len(baseline_skills),
        "skills": baseline_skills,
    }


def rollback_to_version(
    version_id: str,
    *,
    confirm_text: str,
    confirmed_by: str = "manual",
    config: StackConfig | None = None,
) -> dict[str, Any]:
    if confirm_text != CONFIRM_ROLLBACK_TEXT:
        raise ValueError(f"confirmText must be {CONFIRM_ROLLBACK_TEXT!r}")
    path, data = _load_version(version_id, config)
    skills = _extract_skills(data)
    if not skills:
        raise ValueError(f"Version {version_id!r} does not contain a skill state")
    backup_name = backup_existing_baseline(config)
    baseline = _skills_to_baseline(skills, confirmed_by=confirmed_by)
    target = baseline_path(config)
    target.write_text(json.dumps(baseline, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "ok": True,
        "rolledBackTo": _version_id_for_file(path),
        "sourceFile": path.name,
        "baselineFile": target.name,
        "previousBaselineSnapshot": backup_name,
        "skillCount": len(skills),
        "confirmedAt": baseline["confirmedAt"],
        "confirmedBy": baseline["confirmedBy"],
    }
