from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from feishu_stack.api.security import require_control_token
from feishu_stack.api.operations import OperationRunner, operation_runner
from feishu_stack.core.models import to_dict
from feishu_stack.plugin_sdk import AccPlugin, PluginCard
from . import backups, thread_migration

LOCAL_TOOLS_TAG = THREAD_MIGRATION_TAG = OPERATIONS_TAG = 'Backup Migration'
router = APIRouter()

class ThreadMigrationRequest(BaseModel):
    session_id: str
    target_provider: str
    prompt: str = thread_migration.DEFAULT_CONTINUATION_PROMPT


class ThreadMigrationFolderRequest(BaseModel):
    summary_path: str


@router.get(
    "/api/thread-migration/threads",
    summary="List recent threads",
    description="List recent codex sessions available for thread migration.",
    tags=[THREAD_MIGRATION_TAG],
)
def thread_migration_threads(limit: int = 20) -> dict:
    return {"threads": to_dict(thread_migration.list_recent_threads(limit=limit))}


@router.post(
    "/api/thread-migration/migrate",
    summary="Migrate thread",
    description="Migrate a codex session from one provider to another.",
    tags=[THREAD_MIGRATION_TAG],
    dependencies=[Depends(require_control_token)],
)
def migrate_thread(request: ThreadMigrationRequest, runner: OperationRunner = Depends(operation_runner)) -> dict:
    return runner(
        "thread-migration",
        "migrate",
        lambda cfg: thread_migration.migrate_thread(
            request.session_id,
            request.target_provider,
            request.prompt,
            cfg,
        ),
    )


@router.post(
    "/api/thread-migration/open-summary-folder",
    summary="Open summary folder",
    description="Open the summary folder for a thread migration in the file explorer.",
    tags=[THREAD_MIGRATION_TAG],
    dependencies=[Depends(require_control_token)],
)
def open_thread_migration_summary_folder(request: ThreadMigrationFolderRequest, runner: OperationRunner = Depends(operation_runner)) -> dict:
    return runner(
        "thread-migration",
        "open-summary-folder",
        lambda _cfg: thread_migration.open_summary_folder(request.summary_path),
    )


@router.post("/api/backups/clean", summary="Clean backups", description="Remove old backup files per retention policy.", tags=[OPERATIONS_TAG], dependencies=[Depends(require_control_token)])
def clean_backups(runner: OperationRunner = Depends(operation_runner)) -> dict:
    return runner("backups", "clean", backups.clean)

def create_plugin() -> AccPlugin:
    return AccPlugin(id='acc.backup-migration', name='备份与迁移', version='1.0.0', description='Backup Migration', requires=('acc.framework',), capabilities=('backups.manage',), cards=(PluginCard('acc.backup-migration.overview', '备份与迁移', 'Backup Migration', 'backup', icon='archive', order=100),), router_factory=lambda: router)
