from __future__ import annotations

from datetime import datetime
from pathlib import Path
import subprocess
import time

from feishu_stack.core.models import CurrentWatchdogStatus, OperationResult
from feishu_stack.core.process import CREATE_NO_WINDOW, process_info
from feishu_stack.core.settings import StackConfig, load_config

ACTIVE_STATUSES = {"launched", "waiting", "sending"}


def _candidate_watchdog_dirs(cfg: StackConfig) -> list[Path]:
    candidates: list[Path] = []
    if cfg.watchdog_state_dir is not None:
        candidates.append(cfg.watchdog_state_dir)
    candidates.extend(
        [
            cfg.agent_dir.parent / "runtime" / "watchdogs",
        ]
    )
    unique: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path.resolve(strict=False)).lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return unique


def resolve_watchdog_dir(config: StackConfig | None = None) -> Path:
    cfg = config or load_config()
    candidates = _candidate_watchdog_dirs(cfg)
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


def _read_state(path: Path) -> dict:
    try:
        import json

        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _state_sort_key(payload: dict) -> tuple[float, str]:
    timestamp = (
        _parse_timestamp(payload.get("updated_at"))
        or _parse_timestamp(payload.get("last_sent_at"))
        or _parse_timestamp(payload.get("next_check_at"))
        or _parse_timestamp(payload.get("started_at"))
    )
    return ((timestamp.timestamp() if timestamp else 0.0), str(payload.get("task_id") or ""))


def _pid_running(payload: dict) -> bool:
    pid = payload.get("pid")
    if not isinstance(pid, int):
        return False
    running, _name = process_info(pid)
    return running


def _countdown_seconds(payload: dict) -> int | None:
    next_check = _parse_timestamp(payload.get("next_check_at"))
    if next_check is None:
        return None
    remaining = int(next_check.timestamp() - time.time())
    return max(0, remaining)


def _is_active_state(payload: dict) -> bool:
    return str(payload.get("status") or "").strip().lower() in ACTIVE_STATUSES


def _to_status(payload: dict, state_file: Path) -> CurrentWatchdogStatus:
    pid_running = _pid_running(payload)
    enabled = _is_active_state(payload) and pid_running
    pid = payload.get("pid") if isinstance(payload.get("pid"), int) else None
    send_count = payload.get("send_count") if isinstance(payload.get("send_count"), int) else None
    return CurrentWatchdogStatus(
        enabled=enabled,
        status_light="green" if enabled else "gray",
        task_id=str(payload.get("task_id")) if payload.get("task_id") else None,
        assignee=str(payload.get("assignee")) if payload.get("assignee") else None,
        phase=str(payload.get("phase")) if payload.get("phase") else None,
        countdown_seconds=_countdown_seconds(payload),
        next_check_at=str(payload.get("next_check_at")) if payload.get("next_check_at") else None,
        send_count=send_count,
        state_file=str(state_file),
        pid=pid,
        pid_running=pid_running,
        status=str(payload.get("status") or "unknown"),
        log=str(payload.get("log")) if payload.get("log") else None,
    )


def current_watchdog(config: StackConfig | None = None) -> CurrentWatchdogStatus:
    watchdog_dir = resolve_watchdog_dir(config)
    if not watchdog_dir.exists():
        return CurrentWatchdogStatus(False, "gray", None, None, None, None, None, None, None, None, False, "missing", None)
    active_rows: list[tuple[dict, Path]] = []
    for path in watchdog_dir.glob("*.json"):
        payload = _read_state(path)
        if not payload or not _is_active_state(payload):
            continue
        active_rows.append((payload, path))
    if not active_rows:
        return CurrentWatchdogStatus(False, "gray", None, None, None, None, None, None, None, None, False, "inactive", None)
    payload, state_file = max(active_rows, key=lambda item: _state_sort_key(item[0]))
    return _to_status(payload, state_file)


def _stop_script_path(watchdog_dir: Path) -> Path:
    return watchdog_dir.parent.parent / "scripts" / "stop_scheduler_watchdog.py"


def force_stop_current(config: StackConfig | None = None) -> OperationResult:
    cfg = config or load_config()
    watchdog = current_watchdog(cfg)
    if not watchdog.enabled or not watchdog.task_id:
        raise FileNotFoundError("No active watchdog is currently running.")
    watchdog_dir = resolve_watchdog_dir(cfg)
    stop_script = _stop_script_path(watchdog_dir)
    if not stop_script.exists():
        raise FileNotFoundError(f"Watchdog stop script not found: {stop_script}")
    command = [str(cfg.python_exe), "-X", "utf8", str(stop_script), "--task-id", watchdog.task_id]
    if watchdog.assignee:
        command.extend(["--assignee", watchdog.assignee])
    if watchdog.phase:
        command.extend(["--phase", watchdog.phase])
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=str(stop_script.parent.parent),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=60,
        creationflags=CREATE_NO_WINDOW,
    )
    message = completed.stdout.strip() or completed.stderr.strip() or "Watchdog stop requested."
    return OperationResult(
        ok=completed.returncode == 0,
        component="watchdog",
        action="force-stop",
        message=message,
        pid=watchdog.pid,
        duration_ms=int((time.monotonic() - started) * 1000),
    )
