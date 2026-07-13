# Task Directory Workflow

## Canonical Files

- Task directory: `{PROJECTS_ROOT}/task_directory.json`
- Legacy archive index: `{PROJECTS_ROOT}/projects_index.json`
- Default project root: `{PROJECTS_ROOT}`

`task_directory.json` is the source of truth for active task entries shown in Agent Control Center. `projects_index.json` remains an archive compatibility source and must not be treated as the only task list.

## Coordinator Rules

- Before dispatching a new task, 项目调度官 must check whether it belongs to an existing parent project in `task_directory.json`.
- If it belongs to an existing parent project, create or update a child task entry under that parent project.
- If it is a new parent project, create or reserve a new project folder under the default project root and add a task entry.
- If the user specifies a special workspace path, preserve that path in the task entry instead of forcing it under the default project root.
- Every dispatch must include `taskId`, parent project, child task title or phase, and `workspacePath`.

## Downstream Agent Rules

- 代码执行官、运维验证官、质量审计官、项目档案官 must use the `workspacePath` assigned by 项目调度官.
- Do not invent a new project path when the dispatch already contains `workspacePath`.
- If `workspacePath`, parent project, or taskId is missing, ask 项目调度官 to clarify before writing, validating, auditing, or archiving.
- Final reports must include `taskId`, parent project, child task or phase, actual artifact paths, and final status.

## Archivist Rules

- 项目档案官 updates archive artifacts and keeps `projects_index.json` compatible when needed.
- Completion, archive status, tags, and final artifact paths must also be reflected in `task_directory.json` through the task directory workflow.
- Deleting a task entry means hiding the directory record; it must not delete the workspace folder.
