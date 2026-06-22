from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class ComponentStatus:
    name: str
    port: int | None
    port_listening: bool
    pid_file: str | None
    pid: int | None
    pid_running: bool
    process_name: str | None = None


@dataclass
class ProviderStatus:
    model: str
    provider: str
    mode: str
    config: str


@dataclass
class CodexDesktopStatus:
    running: bool
    pid: int | None
    process_count: int
    executable: str | None


@dataclass
class StackStatus:
    codex: ProviderStatus
    openclaw: ComponentStatus
    moonbridge: ComponentStatus
    codex_agent: ComponentStatus
    codex_desktop_running: bool
    codex_desktop: CodexDesktopStatus
    stack_root: str


@dataclass
class OperationResult:
    ok: bool
    component: str
    action: str
    message: str
    pid: int | None = None
    port: int | None = None
    stdout_log: str | None = None
    stderr_log: str | None = None
    duration_ms: int = 0


@dataclass
class ThreadMigrationResult(OperationResult):
    source_session_id: str | None = None
    source_title: str | None = None
    target_provider: str | None = None
    target_model: str | None = None
    summary_path: str | None = None
    summary_dir: str | None = None
    launched_command: str | None = None
    launch_mode: str | None = None


@dataclass
class ThreadListItem:
    session_id: str
    title: str
    provider: str
    model: str
    updated_at: str


@dataclass
class LogTail:
    path: str
    lines: list[str]


def to_dict(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    if isinstance(value, list):
        return [to_dict(item) for item in value]
    if isinstance(value, dict):
        return {key: to_dict(item) for key, item in value.items()}
    return value
