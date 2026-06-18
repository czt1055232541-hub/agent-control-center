from __future__ import annotations

from pathlib import Path
from typing import Callable

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import backups, codex_agent, codex_desktop, codex_provider, diagnostics as diagnostics_module, moonbridge, openclaw, stack_actions
from .config import StackConfig, load_config
from .logs import tail
from .models import OperationResult, to_dict
from .operations import recent_operations, run_exclusive
from .security import get_or_create_token, require_control_token
from .status import get_status

app = FastAPI(title="Feishu Codex Stack Control Center")


def _run(component: str, action: str, fn: Callable[[StackConfig], OperationResult]) -> dict:
    return to_dict(run_exclusive(component, action, fn))


@app.get("/api/session")
def session() -> dict:
    cfg = load_config()
    return {
        "token": get_or_create_token(cfg),
        "stack_root": str(cfg.stack_root),
        "api_base": "/api",
    }


@app.get("/api/status")
def status() -> dict:
    return to_dict(get_status())


@app.get("/api/operations")
def operations() -> dict:
    return {"operations": to_dict(recent_operations())}


@app.get("/api/logs/{component}")
def logs(component: str, lines: int = 120) -> dict:
    cfg = load_config()
    if component == "codex-desktop":
        codex_desktop.log(cfg)
    table = {
        "openclaw": [cfg.openclaw_stdout_log, cfg.openclaw_stderr_log],
        "moonbridge": [cfg.moonbridge_stdout_log, cfg.moonbridge_stderr_log],
        "codex-agent": [cfg.codex_agent_stdout_log, cfg.codex_agent_stderr_log],
        "codex-desktop": [cfg.log_dir / "codex-desktop-status.log"],
        "control-center-api": [cfg.log_dir / "control-center-api-out.log", cfg.log_dir / "control-center-api-err.log"],
        "operations": [cfg.log_dir / "operations.jsonl"],
    }
    if component not in table:
        raise HTTPException(status_code=404, detail=f"Unknown log component: {component}")
    return {"component": component, "logs": [to_dict(tail(path, lines)) for path in table[component]]}


@app.get("/api/doctor/codex")
def codex_doctor() -> dict:
    return diagnostics_module.codex_doctor()


@app.get("/api/moonbridge/models")
def moonbridge_models() -> dict:
    return diagnostics_module.moonbridge_models()


@app.get("/api/lark/auth-status")
def lark_auth_status() -> dict:
    return diagnostics_module.lark_auth_status()


@app.get("/api/diagnostics")
def diagnostics() -> dict:
    return to_dict(diagnostics_module.diagnostics())


@app.post("/api/openclaw/start", dependencies=[Depends(require_control_token)])
def start_openclaw() -> dict:
    return _run("openclaw", "start", openclaw.start)


@app.post("/api/openclaw/stop", dependencies=[Depends(require_control_token)])
def stop_openclaw() -> dict:
    return _run("openclaw", "stop", openclaw.stop)


@app.post("/api/openclaw/restart", dependencies=[Depends(require_control_token)])
def restart_openclaw() -> dict:
    return _run("openclaw", "restart", openclaw.restart)


@app.post("/api/moonbridge/start", dependencies=[Depends(require_control_token)])
def start_moonbridge() -> dict:
    return _run("moonbridge", "start", moonbridge.start)


@app.post("/api/moonbridge/stop", dependencies=[Depends(require_control_token)])
def stop_moonbridge() -> dict:
    return _run("moonbridge", "stop", moonbridge.stop)


@app.post("/api/moonbridge/restart", dependencies=[Depends(require_control_token)])
def restart_moonbridge() -> dict:
    return _run("moonbridge", "restart", moonbridge.restart)


@app.post("/api/codex-agent/start", dependencies=[Depends(require_control_token)])
def start_codex_agent() -> dict:
    return _run("codex-agent", "start", codex_agent.start)


@app.post("/api/codex-agent/stop", dependencies=[Depends(require_control_token)])
def stop_codex_agent() -> dict:
    return _run("codex-agent", "stop", codex_agent.stop)


@app.post("/api/codex-agent/restart", dependencies=[Depends(require_control_token)])
def restart_codex_agent() -> dict:
    return _run("codex-agent", "restart", codex_agent.restart)


@app.post("/api/codex-desktop/start", dependencies=[Depends(require_control_token)])
def start_codex_desktop() -> dict:
    return _run("codex-desktop", "start", codex_desktop.start)


@app.post("/api/codex-provider/native", dependencies=[Depends(require_control_token)])
def switch_native() -> dict:
    return _run("codex-provider", "switch-native", lambda cfg: codex_provider.switch_provider("native", cfg))


@app.post("/api/codex-provider/moonbridge", dependencies=[Depends(require_control_token)])
def switch_moonbridge() -> dict:
    return _run("codex-provider", "switch-moonbridge", lambda cfg: codex_provider.switch_provider("moonbridge", cfg))


@app.post("/api/stack/start-native", dependencies=[Depends(require_control_token)])
def stack_start_native() -> dict:
    return _run("stack", "start-native", stack_actions.start_native)


@app.post("/api/stack/start-moonbridge", dependencies=[Depends(require_control_token)])
def stack_start_moonbridge() -> dict:
    return _run("stack", "start-moonbridge", stack_actions.start_moonbridge)


@app.post("/api/stack/stop", dependencies=[Depends(require_control_token)])
def stack_stop() -> dict:
    return _run("stack", "stop", stack_actions.stop)


@app.post("/api/codex-desktop/stop", dependencies=[Depends(require_control_token)])
def stop_codex_desktop() -> dict:
    return _run("codex-desktop", "stop", codex_desktop.stop)


@app.post("/api/codex-desktop/restart", dependencies=[Depends(require_control_token)])
def restart_codex_desktop() -> dict:
    return _run("codex-desktop", "restart", codex_desktop.restart)


@app.post("/api/backups/clean", dependencies=[Depends(require_control_token)])
def clean_backups() -> dict:
    return _run("backups", "clean", backups.clean)


web_dist = Path(__file__).resolve().parents[2] / "web" / "dist"
if web_dist.exists():
    assets_dir = web_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str) -> FileResponse:
        target = web_dist / path
        if path and target.exists() and target.is_file():
            return FileResponse(target)
        return FileResponse(web_dist / "index.html")
