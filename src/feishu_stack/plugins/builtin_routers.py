"""Route contribution points for ACC's built-in feature plugins."""

from fastapi import APIRouter, FastAPI


agent_array_router = APIRouter()
model_provider_router = APIRouter()
local_tools_router = APIRouter()
logs_diagnostics_router = APIRouter()
backup_migration_router = APIRouter()


_ROUTE_OWNERS = (
    (agent_array_router, ("/api/agents", "/api/skill-workshop")),
    (
        model_provider_router,
        ("/api/openclaw", "/api/deepseek", "/api/codex-agent", "/api/codex-desktop", "/api/codex-provider", "/api/stack"),
    ),
    (local_tools_router, ("/api/local-tools",)),
    (logs_diagnostics_router, ("/api/logs", "/api/doctor", "/api/lark", "/api/diagnostics")),
    (backup_migration_router, ("/api/backups", "/api/thread-migration")),
)


def adopt_builtin_feature_routes(app: FastAPI) -> None:
    """Transfer stable legacy paths to their plugin-owned routers."""
    remaining = []
    for route in app.router.routes:
        path = getattr(route, "path", "")
        owner = next(
            (
                router
                for router, prefixes in _ROUTE_OWNERS
                if any(path == prefix or path.startswith(f"{prefix}/") for prefix in prefixes)
            ),
            None,
        )
        if owner is None:
            remaining.append(route)
        else:
            owner.routes.append(route)
    app.router.routes[:] = remaining


__all__ = [
    "agent_array_router",
    "backup_migration_router",
    "local_tools_router",
    "logs_diagnostics_router",
    "model_provider_router",
    "adopt_builtin_feature_routes",
]
