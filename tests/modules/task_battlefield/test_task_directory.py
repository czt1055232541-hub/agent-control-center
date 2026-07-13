from __future__ import annotations

import json
from types import SimpleNamespace

from feishu_stack.modules.task_battlefield import task_directory


def _config(tmp_path):
    agent_dir = tmp_path / "agent-runtime" / "agents" / "feishu-codex-agent"
    agent_dir.mkdir(parents=True)
    return SimpleNamespace(
        agent_dir=agent_dir,
        stack_root=tmp_path,
        projects_root=tmp_path / "projects",
    )


def _projects_root(cfg) -> object:
    return cfg.projects_root


def test_resolve_projects_root_prefers_configured_projects_root(tmp_path) -> None:
    cfg = _config(tmp_path)

    result = task_directory.resolve_projects_root(cfg)

    assert result == (tmp_path / "projects").resolve(strict=False)
    assert "agent-runtime" not in result.parts


def test_resolve_projects_root_falls_back_to_stack_root_projects(tmp_path) -> None:
    agent_dir = tmp_path / "agent-runtime" / "agents" / "feishu-codex-agent"
    cfg = SimpleNamespace(agent_dir=agent_dir, stack_root=tmp_path, projects_root=None)

    result = task_directory.resolve_projects_root(cfg)

    assert result == (tmp_path / "projects").resolve(strict=False)


def test_load_directory_bootstraps_from_legacy_index_and_top_level_folders(tmp_path) -> None:
    cfg = _config(tmp_path)
    projects = _projects_root(cfg)
    (projects / "Alpha Project" / "phase-one").mkdir(parents=True)
    (projects / "Beta Task").mkdir()
    (projects / "projects_index.json").write_text(
        json.dumps(
            [
                {
                    "project_id": "alpha-project",
                    "project_name": "Alpha Project",
                    "version": "v1",
                    "status": "已完成",
                    "archive_date": "2026-07-01",
                    "phase": "Phase 1",
                    "tags": ["alpha"],
                    "file_paths": [str(projects / "Alpha Project" / "README.md")],
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = task_directory.load_directory(cfg)

    assert {task["title"] for task in result["tasks"]} == {"Alpha Project", "Beta Task", "Phase 1"}
    alpha = next(task for task in result["tasks"] if task["title"] == "Alpha Project")
    assert alpha["status"] == "已完成"
    assert alpha["phase"] == "Phase 1"
    assert alpha["tags"] == ["alpha"]
    assert (projects / "task_directory.json").exists()


def test_legacy_rows_are_loaded_as_child_tasks_under_parent_project(tmp_path) -> None:
    cfg = _config(tmp_path)
    projects = _projects_root(cfg)
    (projects / "Alpha Project").mkdir(parents=True)
    (projects / "projects_index.json").write_text(
        json.dumps(
            [
                {
                    "project_id": "alpha-project",
                    "project_name": "Alpha Project",
                    "version": "v1",
                    "status": "已完成",
                    "archive_date": "2026-07-01",
                    "phase": "Phase 1",
                    "tags": ["alpha", "phase1"],
                    "file_paths": [str(projects / "Alpha Project" / "one.md")],
                },
                {
                    "project_id": "alpha-project",
                    "project_name": "Alpha Project",
                    "version": "v2",
                    "status": "已归档",
                    "archive_date": "2026-07-02",
                    "phase": "Phase 2",
                    "tags": ["phase2"],
                    "file_paths": [str(projects / "Alpha Project" / "two.md")],
                },
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = task_directory.load_directory(cfg)

    child_tasks = [task for task in result["tasks"] if task["parentProjectName"] == "Alpha Project"]
    assert {task["taskId"] for task in child_tasks} >= {"alpha-project-v1", "alpha-project-v2"}
    assert {task["title"] for task in child_tasks} >= {"Phase 1", "Phase 2"}


def test_legacy_row_uses_top_level_folder_as_parent_when_path_is_inside_project(tmp_path) -> None:
    cfg = _config(tmp_path)
    projects = _projects_root(cfg)
    (projects / "agent-evolution" / "phase1-health-monitor").mkdir(parents=True)
    (projects / "projects_index.json").write_text(
        json.dumps(
            [
                {
                    "project_id": "phase1-agent-health-monitor",
                    "project_name": "Phase 1 — Agent 健康监控面板",
                    "version": "v1",
                    "status": "已归档",
                    "archive_date": "2026-07-01",
                    "phase": "方案规划",
                    "tags": ["phase1"],
                    "file_paths": [str(projects / "agent-evolution" / "phase1-health-monitor" / "health_check.py")],
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = task_directory.load_directory(cfg)
    child = next(task for task in result["tasks"] if task["taskId"] == "phase1-agent-health-monitor-v1")

    assert child["parentProjectId"] == "agent-evolution"
    assert child["parentProjectName"] == "agent-evolution"
    assert child["title"] == "方案规划"


def test_load_directory_synchronizes_missing_top_level_folder_without_recursive_children(tmp_path) -> None:
    cfg = _config(tmp_path)
    projects = _projects_root(cfg)
    (projects / "Known Task").mkdir(parents=True)
    (projects / "New Task" / "archive").mkdir(parents=True)
    (projects / "task_directory.json").write_text(
        json.dumps(
            {
                "version": 1,
                "projectsRoot": str(projects),
                "updatedAt": "2026-07-01T00:00:00+00:00",
                "tasks": [
                    {
                        "taskId": "known-task",
                        "title": "Known Task",
                        "parentProjectId": "known-task",
                        "parentProjectName": "Known Task",
                        "workspacePath": str(projects / "Known Task"),
                        "status": "进行中",
                        "phase": "独立任务",
                        "assignee": "",
                        "updatedAt": "2026-07-01T00:00:00+00:00",
                        "tags": [],
                        "source": "manual",
                        "hidden": False,
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = task_directory.load_directory(cfg)

    assert {task["title"] for task in result["tasks"]} == {"Known Task", "New Task"}
    assert "archive" not in {task["title"] for task in result["tasks"]}
    assert result["sync"]["addedFolders"] == ["New Task"]


def test_manual_external_path_can_be_saved(tmp_path) -> None:
    cfg = _config(tmp_path)
    projects = _projects_root(cfg)
    projects.mkdir(parents=True)
    external = tmp_path / "external-workspace"

    result = task_directory.add_task(
        {
            "taskId": "external-task",
            "title": "External Task",
            "parentProjectName": "External Project",
            "workspacePath": str(external),
            "tags": ["manual"],
        },
        cfg,
    )

    task = next(task for task in result["tasks"] if task["taskId"] == "external-task")
    assert task["workspacePath"] == str(external.resolve(strict=False))
    assert task["parentProjectName"] == "External Project"


def test_update_task_persists_tags(tmp_path) -> None:
    cfg = _config(tmp_path)
    projects = _projects_root(cfg)
    projects.mkdir(parents=True)
    task_directory.add_task(
        {
            "taskId": "tagged-task",
            "title": "Tagged Task",
            "parentProjectName": "Tagged Project",
            "workspacePath": str(projects / "Tagged Task"),
            "tags": ["old"],
        },
        cfg,
    )

    result = task_directory.update_task("tagged-task", {"tags": ["new", "重点"]}, cfg)
    reloaded = task_directory.load_directory(cfg)

    assert next(task for task in result["tasks"] if task["taskId"] == "tagged-task")["tags"] == ["new", "重点"]
    assert next(task for task in reloaded["tasks"] if task["taskId"] == "tagged-task")["tags"] == ["new", "重点"]


def test_delete_hides_directory_entry_without_deleting_folder_or_resyncing_it(tmp_path) -> None:
    cfg = _config(tmp_path)
    projects = _projects_root(cfg)
    folder = projects / "Delete Me"
    folder.mkdir(parents=True)
    initial = task_directory.load_directory(cfg)
    task_id = next(task["taskId"] for task in initial["tasks"] if task["title"] == "Delete Me")

    after_delete = task_directory.delete_task(task_id, cfg)
    after_reload = task_directory.load_directory(cfg)

    assert folder.exists()
    assert task_id not in {task["taskId"] for task in after_delete["tasks"]}
    assert task_id not in {task["taskId"] for task in after_reload["tasks"]}
