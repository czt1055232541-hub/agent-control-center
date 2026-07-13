from __future__ import annotations

import json
import os
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from feishu_stack.core.settings import StackConfig, load_config

DIRECTORY_VERSION = 1
DIRECTORY_FILENAME = "task_directory.json"
LEGACY_INDEX_FILENAME = "projects_index.json"
DEFAULT_STATUS = "进行中"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean_string(value: object, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return deepcopy(default)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _normal_path(value: object) -> str:
    text = _clean_string(value)
    if not text:
        return ""
    return str(Path(text).resolve(strict=False))


def _dedupe_strings(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _clean_string(value)
        key = text.lower()
        if text and key not in seen:
            seen.add(key)
            result.append(text)
    return result


def _slug(value: str) -> str:
    text = value.strip().lower()
    text = re.sub(r"[^\w\u4e00-\u9fff]+", "-", text, flags=re.UNICODE).strip("-_")
    return text or "task"


def resolve_projects_root(config: StackConfig | None = None) -> Path:
    override = os.environ.get("TASK_BATTLEFIELD_PROJECTS_ROOT")
    if override:
        return Path(override).resolve(strict=False)
    cfg = config or load_config()
    configured = getattr(cfg, "projects_root", None)
    if configured:
        return Path(configured).resolve(strict=False)
    stack_root = getattr(cfg, "stack_root", None)
    if stack_root:
        return (Path(stack_root) / "projects").resolve(strict=False)
    return (cfg.agent_dir.parents[2] / "projects").resolve(strict=False)


def resolve_directory_file(projects_root: Path) -> Path:
    return projects_root / DIRECTORY_FILENAME


def _is_inside(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except ValueError:
        return False


def _top_folder_from_path(path_text: str, projects_root: Path) -> str | None:
    if not path_text:
        return None
    path = Path(path_text.replace("\\\\", "\\")).resolve(strict=False)
    try:
        rel = path.relative_to(projects_root.resolve(strict=False))
    except ValueError:
        return None
    return rel.parts[0] if rel.parts else None


def _latest_legacy_by_folder(projects_root: Path) -> dict[str, dict[str, Any]]:
    legacy_path = projects_root / LEGACY_INDEX_FILENAME
    rows = _read_json(legacy_path, [])
    if not isinstance(rows, list):
        return {}
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        candidates: set[str] = set()
        project_name = _clean_string(row.get("project_name"))
        if project_name:
            candidates.add(project_name)
        for file_path in row.get("file_paths") or []:
            top = _top_folder_from_path(_clean_string(file_path), projects_root)
            if top:
                candidates.add(top)
        for folder in candidates:
            previous = latest.get(folder)
            if previous is None or _clean_string(row.get("archive_date")) >= _clean_string(previous.get("archive_date")):
                latest[folder] = row
    return latest


def _folder_task(folder: Path, legacy: dict[str, Any] | None = None) -> dict[str, Any]:
    row = legacy or {}
    project_id = _clean_string(row.get("project_id"), _slug(folder.name))
    project_name = _clean_string(row.get("project_name"), folder.name)
    return {
        "taskId": _slug(project_id),
        "title": project_name,
        "parentProjectId": _slug(project_id),
        "parentProjectName": project_name,
        "workspacePath": str(folder.resolve(strict=False)),
        "status": _clean_string(row.get("status"), DEFAULT_STATUS),
        "phase": _clean_string(row.get("phase"), "独立任务"),
        "assignee": "",
        "updatedAt": _clean_string(row.get("archive_date"), _now()),
        "tags": _dedupe_strings(row.get("tags")),
        "source": "projects_index" if legacy else "filesystem",
        "hidden": False,
    }


def _legacy_row_task(row: dict[str, Any], projects_root: Path) -> dict[str, Any]:
    project_id = _clean_string(row.get("project_id"), "legacy-project")
    project_name = _clean_string(row.get("project_name"), project_id)
    version = _clean_string(row.get("version"))
    phase = _clean_string(row.get("phase"), "历史任务")
    task_id_source = f"{project_id}-{version}" if version else f"{project_id}-{phase}"
    file_paths = _dedupe_strings(row.get("file_paths"))
    workspace = ""
    parent_project_id = _slug(project_id)
    parent_project_name = project_name
    folders_by_slug = {_slug(path.name): path.name for path in projects_root.iterdir() if path.is_dir()} if projects_root.exists() else {}
    for file_path in file_paths:
        top = _top_folder_from_path(file_path, projects_root)
        if top:
            parent_project_id = _slug(top)
            parent_project_name = top
            top_path = projects_root / top
            candidate = Path(file_path.replace("\\\\", "\\")).resolve(strict=False)
            workspace = str(candidate.parent if candidate.suffix else candidate)
            if not _is_inside(Path(workspace), top_path):
                workspace = str(top_path.resolve(strict=False))
            break
    if parent_project_id in folders_by_slug and parent_project_name == project_name:
        parent_project_name = folders_by_slug[parent_project_id]
    if not workspace and file_paths:
        workspace = _normal_path(file_paths[0])
    if not workspace:
        workspace = str((projects_root / parent_project_name).resolve(strict=False))
    return {
        "taskId": _slug(task_id_source),
        "title": phase if phase != "历史任务" else project_name,
        "parentProjectId": parent_project_id,
        "parentProjectName": parent_project_name,
        "workspacePath": workspace,
        "status": _clean_string(row.get("status"), DEFAULT_STATUS),
        "phase": phase,
        "assignee": "",
        "updatedAt": _clean_string(row.get("archive_date"), _now()),
        "tags": _dedupe_strings(row.get("tags")),
        "source": "projects_index",
        "hidden": False,
    }


def _legacy_tasks(projects_root: Path, existing_ids: set[str]) -> list[dict[str, Any]]:
    rows = _read_json(projects_root / LEGACY_INDEX_FILENAME, [])
    if not isinstance(rows, list):
        return []
    tasks: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        task = _legacy_row_task(row, projects_root)
        if task["taskId"] in existing_ids:
            continue
        existing_ids.add(task["taskId"])
        tasks.append(task)
    return tasks


def _normal_task(raw: dict[str, Any], projects_root: Path) -> dict[str, Any]:
    task_id = _clean_string(raw.get("taskId") or raw.get("task_id") or raw.get("project_id"))
    title = _clean_string(raw.get("title") or raw.get("project_name") or task_id, "未命名任务")
    if not task_id:
        task_id = _slug(title)
    parent_name = _clean_string(raw.get("parentProjectName") or raw.get("parent_project") or raw.get("project_name"), title)
    parent_id = _clean_string(raw.get("parentProjectId") or raw.get("project_id"), _slug(parent_name))
    workspace = _normal_path(raw.get("workspacePath") or raw.get("workspace_path") or raw.get("artifactPath"))
    if not workspace:
        workspace = str((projects_root / title).resolve(strict=False))
    return {
        "taskId": _slug(task_id),
        "title": title,
        "parentProjectId": _slug(parent_id),
        "parentProjectName": parent_name,
        "workspacePath": workspace,
        "status": _clean_string(raw.get("status"), DEFAULT_STATUS),
        "phase": _clean_string(raw.get("phase"), "独立任务"),
        "assignee": _clean_string(raw.get("assignee")),
        "updatedAt": _clean_string(raw.get("updatedAt") or raw.get("updated") or raw.get("archive_date"), _now()),
        "tags": _dedupe_strings(raw.get("tags")),
        "source": _clean_string(raw.get("source"), "manual"),
        "hidden": bool(raw.get("hidden", False)),
    }


def _new_directory(projects_root: Path) -> dict[str, Any]:
    legacy = _latest_legacy_by_folder(projects_root)
    tasks: list[dict[str, Any]] = []
    existing_ids: set[str] = set()
    if projects_root.exists():
        for folder in sorted((p for p in projects_root.iterdir() if p.is_dir()), key=lambda p: p.name.lower()):
            task = _folder_task(folder, legacy.get(folder.name))
            suffix = 2
            base_id = task["taskId"]
            while task["taskId"] in existing_ids:
                task["taskId"] = f"{base_id}-{suffix}"
                suffix += 1
            existing_ids.add(task["taskId"])
            tasks.append(task)
    tasks.extend(_legacy_tasks(projects_root, existing_ids))
    return {
        "version": DIRECTORY_VERSION,
        "projectsRoot": str(projects_root),
        "updatedAt": _now(),
        "tasks": tasks,
    }


def _sync_filesystem_tasks(directory: dict[str, Any], projects_root: Path) -> tuple[dict[str, Any], list[str]]:
    tasks = [_normal_task(task, projects_root) for task in directory.get("tasks", []) if isinstance(task, dict)]
    by_workspace = {task["workspacePath"].lower(): task for task in tasks}
    by_title = {task["title"].lower(): task for task in tasks}
    legacy = _latest_legacy_by_folder(projects_root)
    added: list[str] = []
    existing_ids = {task["taskId"] for task in tasks}
    if projects_root.exists():
        for folder in sorted((p for p in projects_root.iterdir() if p.is_dir()), key=lambda p: p.name.lower()):
            workspace = str(folder.resolve(strict=False))
            if workspace.lower() in by_workspace or folder.name.lower() in by_title:
                continue
            task = _folder_task(folder, legacy.get(folder.name))
            suffix = 2
            base_id = task["taskId"]
            while task["taskId"] in existing_ids:
                task["taskId"] = f"{base_id}-{suffix}"
                suffix += 1
            existing_ids.add(task["taskId"])
            tasks.append(task)
            added.append(folder.name)
    for task in _legacy_tasks(projects_root, existing_ids):
        existing_ids.add(task["taskId"])
        tasks.append(task)
        added.append(task["taskId"])
    directory = {
        "version": DIRECTORY_VERSION,
        "projectsRoot": str(projects_root),
        "updatedAt": _now(),
        "tasks": tasks,
    }
    return directory, added


def _groups(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for task in tasks:
        key = task["parentProjectId"] or _slug(task["parentProjectName"])
        if key not in grouped:
            grouped[key] = {
                "projectId": key,
                "projectName": task["parentProjectName"] or task["title"],
                "taskCount": 0,
            }
        grouped[key]["taskCount"] += 1
    return sorted(grouped.values(), key=lambda item: item["projectName"].lower())


def load_directory(config: StackConfig | None = None, *, persist: bool = True) -> dict[str, Any]:
    projects_root = resolve_projects_root(config)
    directory_file = resolve_directory_file(projects_root)
    if directory_file.exists():
        raw = _read_json(directory_file, {})
        directory = raw if isinstance(raw, dict) else {}
    else:
        directory = _new_directory(projects_root)
    directory, added = _sync_filesystem_tasks(directory, projects_root)
    if persist:
        _write_json(directory_file, directory)
    return _response_from_directory(directory, projects_root, directory_file, added)


def _response_from_directory(
    directory: dict[str, Any],
    projects_root: Path,
    directory_file: Path,
    added: list[str] | None = None,
) -> dict[str, Any]:
    visible = [task for task in directory["tasks"] if not task.get("hidden")]
    missing = [
        task["taskId"]
        for task in visible
        if task.get("workspacePath") and _is_inside(Path(task["workspacePath"]), projects_root) and not Path(task["workspacePath"]).exists()
    ]
    return {
        "version": DIRECTORY_VERSION,
        "directoryFile": str(directory_file),
        "projectsRoot": str(projects_root),
        "updatedAt": directory["updatedAt"],
        "tasks": visible,
        "groups": _groups(visible),
        "sync": {
            "addedFolders": added or [],
            "missingWorkspaces": missing,
        },
    }


def _save_tasks(projects_root: Path, tasks: list[dict[str, Any]]) -> dict[str, Any]:
    directory = {
        "version": DIRECTORY_VERSION,
        "projectsRoot": str(projects_root),
        "updatedAt": _now(),
        "tasks": tasks,
    }
    directory_file = resolve_directory_file(projects_root)
    _write_json(directory_file, directory)
    return _response_from_directory(directory, projects_root, directory_file)


def _load_all_tasks(config: StackConfig | None, projects_root: Path) -> list[dict[str, Any]]:
    load_directory(config, persist=True)
    raw = _read_json(resolve_directory_file(projects_root), {})
    rows = raw.get("tasks", []) if isinstance(raw, dict) else []
    return [_normal_task(task, projects_root) for task in rows if isinstance(task, dict)]


def add_task(payload: dict[str, Any], config: StackConfig | None = None) -> dict[str, Any]:
    projects_root = resolve_projects_root(config)
    tasks = _load_all_tasks(config, projects_root)
    task = _normal_task({**payload, "source": payload.get("source") or "manual"}, projects_root)
    for index, existing in enumerate(tasks):
        if existing["taskId"] != task["taskId"]:
            continue
        if not existing.get("hidden"):
            raise ValueError(f"Task already exists: {task['taskId']}")
        tasks[index] = task
        return _save_tasks(projects_root, tasks)
    tasks.append(task)
    return _save_tasks(projects_root, tasks)


def update_task(task_id: str, payload: dict[str, Any], config: StackConfig | None = None) -> dict[str, Any]:
    projects_root = resolve_projects_root(config)
    tasks = _load_all_tasks(config, projects_root)
    normalized_id = _slug(task_id)
    for index, task in enumerate(tasks):
        if task["taskId"] != normalized_id:
            continue
        merged = {**task, **payload, "taskId": payload.get("taskId") or task["taskId"], "updatedAt": _now()}
        updated = _normal_task(merged, projects_root)
        if updated["taskId"] != task["taskId"] and any(other["taskId"] == updated["taskId"] for other in tasks):
            raise ValueError(f"Task already exists: {updated['taskId']}")
        tasks[index] = updated
        return _save_tasks(projects_root, tasks)
    raise KeyError(task_id)


def delete_task(task_id: str, config: StackConfig | None = None) -> dict[str, Any]:
    projects_root = resolve_projects_root(config)
    tasks = _load_all_tasks(config, projects_root)
    normalized_id = _slug(task_id)
    for task in tasks:
        if task["taskId"] == normalized_id:
            task["hidden"] = True
            task["updatedAt"] = _now()
            return _save_tasks(projects_root, tasks)
    raise KeyError(task_id)


def classify_task(description: str, workspace_path: str | None = None, config: StackConfig | None = None) -> dict[str, Any]:
    directory = load_directory(config, persist=True)
    projects_root = Path(directory["projectsRoot"])
    text = description.lower()
    specified = _normal_path(workspace_path)
    scored: list[tuple[int, dict[str, Any]]] = []
    for group in directory["groups"]:
        score = 0
        name = str(group["projectName"])
        if name and name.lower() in text:
            score += 5
        project_id = str(group["projectId"])
        if project_id and project_id.lower() in text:
            score += 3
        for task in directory["tasks"]:
            if task["parentProjectId"] != group["projectId"]:
                continue
            if specified and task.get("workspacePath") and specified.lower().startswith(str(task["workspacePath"]).lower()):
                score += 6
            for tag in task.get("tags") or []:
                if str(tag).lower() in text:
                    score += 2
        if score:
            scored.append((score, group))
    scored.sort(key=lambda item: (-item[0], item[1]["projectName"].lower()))
    if scored:
        best = scored[0][1]
        return {
            "decision": "existing_project",
            "project": best,
            "candidates": [{"score": score, **group} for score, group in scored[:5]],
            "suggestedWorkspacePath": specified or str((projects_root / best["projectName"]).resolve(strict=False)),
        }
    title = description.strip().splitlines()[0][:48].strip() or "new-task"
    return {
        "decision": "new_task",
        "project": None,
        "candidates": [],
        "suggestedWorkspacePath": specified or str((projects_root / _slug(title)).resolve(strict=False)),
    }
