from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import subprocess
import io
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WATCHDOG_DIR = REPO_ROOT / "runtime" / "watchdogs"


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def terminate_pid(pid: int) -> dict:
    if pid <= 0 or pid == os.getpid():
        return {"pid": pid, "terminated": False, "reason": "invalid_or_self"}
    result = subprocess.run(
        ["taskkill", "/PID", str(pid), "/T", "/F"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    missing = "not found" in (result.stderr or "").lower()
    return {
        "pid": pid,
        "terminated": result.returncode == 0 or missing,
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def process_snapshot() -> list[dict]:
    result = subprocess.run(
        ["wmic", "process", "get", "ProcessId,ParentProcessId,CommandLine", "/format:csv"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        return []
    rows: list[dict] = []
    for row in csv.DictReader(io.StringIO(result.stdout)):
        try:
            pid = int(row.get("ProcessId") or 0)
            parent_pid = int(row.get("ParentProcessId") or 0)
        except ValueError:
            continue
        if pid <= 0:
            continue
        rows.append({
            "pid": pid,
            "parent_pid": parent_pid,
            "command_line": row.get("CommandLine") or "",
        })
    return rows


def related_watchdog_pids(state: dict, state_path: Path) -> list[int]:
    seeds = {
        int(value)
        for value in (state.get("pid") or 0, state.get("launcher_pid") or 0)
        if str(value).isdigit() and int(value) > 0
    }
    snapshot = process_snapshot()
    state_text = str(state_path).lower()
    for process in snapshot:
        if state_text in process["command_line"].lower():
            seeds.add(process["pid"])
            if process["parent_pid"] > 0:
                seeds.add(process["parent_pid"])

    changed = True
    by_pid = {process["pid"]: process for process in snapshot}
    while changed:
        changed = False
        for process in snapshot:
            if process["parent_pid"] in seeds and process["pid"] not in seeds:
                seeds.add(process["pid"])
                changed = True
            parent = by_pid.get(process["parent_pid"])
            parent_command = (parent or {}).get("command_line", "").lower()
            parent_is_watchdog = "scheduler-watchdog" in parent_command or "scheduler_watchdog" in parent_command or state_text in parent_command
            if process["pid"] in seeds and process["parent_pid"] > 0 and process["parent_pid"] not in seeds and parent_is_watchdog:
                seeds.add(process["parent_pid"])
                changed = True
    return sorted(pid for pid in seeds if pid != os.getpid())


def matches(state: dict, task_id: str, assignee: str | None, phase: str | None) -> bool:
    if state.get("task_id") != task_id:
        return False
    if assignee and state.get("assignee") != assignee:
        return False
    if phase and state.get("phase") != phase:
        return False
    return state.get("status") not in {"sent", "send_failed", "cancelled", "superseded"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Cancel active scheduler watchdogs after an agent replies.")
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--assignee", default=None)
    parser.add_argument("--phase", default=None)
    args = parser.parse_args()

    WATCHDOG_DIR.mkdir(parents=True, exist_ok=True)
    cancelled = []
    for state_path in WATCHDOG_DIR.glob("*.json"):
        state = read_json(state_path)
        if not matches(state, args.task_id, args.assignee, args.phase):
            continue
        results = [terminate_pid(pid) for pid in related_watchdog_pids(state, state_path)]
        state.update({
            "status": "cancelled",
            "cancelled_at": dt.datetime.now().isoformat(timespec="seconds"),
            "cancel_reason": "agent_reply_received",
            "cancel_results": results,
            "cancel_result": results[0] if results else {"terminated": False, "reason": "no_matching_process"},
        })
        write_json(state_path, state)
        cancelled.append({"state": str(state_path), "results": results})

    print(json.dumps({
        "ok": True,
        "task_id": args.task_id,
        "assignee": args.assignee,
        "phase": args.phase,
        "cancelled": cancelled,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
