from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from pydantic import BaseModel as PydanticBaseModel, Field

class ErrorResponse(PydanticBaseModel):
    error_code: str = Field(..., description="Machine-readable error code, e.g. HTTP_404")
    message: str = Field(..., description="Human-readable error message")
    detail: Any = Field(default=None, description="Optional additional detail")

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
    reasoning_effort: str = "high"


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
    codex_agent_args: str
    codex_agent_follows_global_config: bool
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


@dataclass
class AgentConfig:
    id: str
    name: str
    role: str
    status: str
    provider: str
    model: str
    pid: int | None
    port: int | None
    uptime: str
    feishuBinding: str
    triggerMode: str
    tools: list[str]
    permissionLevel: str
    promptVersion: str
    configPath: str
    currentTask: str
    lastCalledAt: str | None
    lastLatencyMs: int | None
    lastError: str
    todayTaskCount: int | None
    successRate: float | None
    controlComponent: str | None = None
    logsComponent: str | None = None
    backendActions: list[dict[str, Any]] | None = None
    source: str = "unknown"
    agentId: str | None = None
    displayName: str | None = None
    bindingStatus: str = "unknown"
    feishuAccountEnabled: bool | None = None
    workspacePath: str | None = None
    backingComponent: str | None = None
    sessionCount: int | None = None
    lastInteractionAt: str | None = None
    a2aPeers: list[dict[str, Any]] | None = None
    configFacts: dict[str, Any] | None = None


@dataclass
class DashboardSummary:
    systemHealth: str
    provider: str
    feishuStatus: str
    onlineAgents: int
    totalAgents: int
    activeTasks: int | None
    todayMessages: int | None
    failedRequests: int


@dataclass
class ExplainedDiagnosticItem:
    id: str
    level: str
    title: str
    affectedModules: list[str]
    status: str
    rawError: str
    possibleCauses: list[str]
    suggestions: list[str]
    actions: list[dict[str, Any]]
    relatedLogs: list[str]


def to_dict(value: Any) -> Any:
    if isinstance(value, PydanticBaseModel):
        return value.model_dump()
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    if isinstance(value, list):
        return [to_dict(item) for item in value]
    if isinstance(value, dict):
        return {key: to_dict(item) for key, item in value.items()}
    return value
