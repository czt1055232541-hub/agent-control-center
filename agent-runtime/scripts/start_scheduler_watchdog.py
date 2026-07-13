from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from a2a_workflow_config import default_chat_id, require_role_open_id

AGENT_RUNTIME_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = AGENT_RUNTIME_ROOT.parent
LARK_CLI = AGENT_RUNTIME_ROOT / ".npm-global" / "node_modules" / "@larksuite" / "cli" / "bin" / "lark-cli.exe"
AGENT_HOME = AGENT_RUNTIME_ROOT / ".home"
SCRIPT = AGENT_RUNTIME_ROOT / "scripts" / "scheduler_watchdog.py"
LOG_DIR = REPO_ROOT / "runtime" / "logs"
WATCHDOG_DIR = REPO_ROOT / "runtime" / "watchdogs"


def safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in value)


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


def lark_env() -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if key.upper() in {"PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC", "TEMP", "TMP"}
    }
    home = str(AGENT_HOME)
    env["USERPROFILE"] = home
    env["HOME"] = home
    env["LARK_CLI_HOME"] = str(AGENT_HOME / ".lark-cli")
    env["LARK_CLI_CWD"] = str(REPO_ROOT)
    env["LARK_CLI_OUTPUT_ENCODING"] = "utf-8"
    return env


def redact_sensitive(value: str) -> str:
    redacted = re.sub(r"\bou_[A-Za-z0-9_-]+\b", "ou_***", value or "")
    redacted = re.sub(r"\boc_[A-Za-z0-9_-]+\b", "oc_***", redacted)
    redacted = re.sub(r"\bcli_[A-Za-z0-9_-]+\b", "cli_***", redacted)
    return redacted


def send_dispatch_message(task_id: str, assignee: str, phase: str | None, task_text: str, dry_run: bool) -> dict:
    content = {
        "zh_cn": {
            "content": [[
                {"tag": "at", "user_id": require_role_open_id(assignee), "user_name": assignee},
                {
                    "tag": "text",
                    "text": "\n".join([
                        f" {task_id} 派发任务",
                        f"阶段：{phase or '未命名阶段'}",
                        "",
                        task_text.strip(),
                    ]),
                },
            ]]
        }
    }
    command = [
        str(LARK_CLI),
        "im",
        "+messages-send",
        "--chat-id",
        default_chat_id(),
        "--content",
        json.dumps(content, ensure_ascii=True),
        "--msg-type",
        "post",
        "--as",
        "user",
        "--format",
        "json",
    ]
    if dry_run:
        command.append("--dry-run")
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        env=lark_env(),
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    return {
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "stdout_preview": redact_sensitive(result.stdout or "")[:500],
        "stderr_preview": redact_sensitive(result.stderr or "")[:500],
    }


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
    return {
        "pid": pid,
        "terminated": result.returncode == 0,
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


def cancel_existing(task_id: str) -> list[dict]:
    WATCHDOG_DIR.mkdir(parents=True, exist_ok=True)
    cancelled = []
    for state_path in WATCHDOG_DIR.glob("*.json"):
        state = read_json(state_path)
        if state.get("task_id") != task_id:
            continue
        if state.get("status") in {"sent", "send_failed", "cancelled", "superseded"}:
            continue
        results = [terminate_pid(pid) for pid in related_watchdog_pids(state, state_path)]
        state.update({
            "status": "superseded",
            "superseded_at": dt.datetime.now().isoformat(timespec="seconds"),
            "supersede_results": results,
            "supersede_result": results[0] if results else {"terminated": False, "reason": "no_matching_process"},
        })
        write_json(state_path, state)
        cancelled.append({"state": str(state_path), "results": results})
    return cancelled


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Start scheduler watchdog in the background.")
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--task-text", required=True)
    parser.add_argument("--assignee", required=True)
    parser.add_argument("--phase", default=None)
    parser.add_argument("--delay-seconds", type=int, default=None)
    parser.add_argument("--delay-minutes", type=float, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--keep-existing", action="store_true", help="Do not cancel earlier watchdogs for the same task.")
    parser.add_argument("--no-dispatch", action="store_true", help="Compatibility no-op: watchdog launch never sends the assignment unless --dispatch-as-user is set.")
    parser.add_argument(
        "--dispatch-as-user",
        action="store_true",
        help="Legacy recovery mode: send the assignee assignment as the authenticated user before launching the watchdog.",
    )
    args = parser.parse_args(argv)

    command = [sys.executable, "-X", "utf8", str(SCRIPT)]
    command.extend([
        "--task-id",
        args.task_id,
        "--task-text",
        args.task_text,
        "--assignee",
        args.assignee,
    ])
    if args.phase:
        command.extend(["--phase", args.phase])
    if args.delay_seconds is not None:
        command.extend(["--delay-seconds", str(args.delay_seconds)])
    if args.delay_minutes is not None:
        command.extend(["--delay-minutes", str(args.delay_minutes)])
    if args.dry_run:
        command.append("--dry-run")
        command.append("--no-wait")

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    WATCHDOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_task = safe_name(args.task_id)
    safe_assignee = safe_name(args.assignee)
    log_path = LOG_DIR / f"{safe_task}_{args.assignee}_{stamp}_watchdog.log"
    state_path = WATCHDOG_DIR / f"{safe_task}_{safe_assignee}_{stamp}.json"
    command.extend(["--state-file", str(state_path)])
    dispatch_result = {
        "ok": True,
        "skipped": True,
        "reason": "coordinator_visible_reply_required",
    }
    if args.dispatch_as_user and not args.no_dispatch:
        dispatch_result = send_dispatch_message(args.task_id, args.assignee, args.phase, args.task_text, args.dry_run)
        if not dispatch_result.get("ok"):
            state = {
                "task_id": args.task_id,
                "assignee": args.assignee,
                "phase": args.phase,
                "status": "dispatch_failed",
                "dispatch_result": dispatch_result,
                "started_at": dt.datetime.now().isoformat(timespec="seconds"),
            }
            write_json(state_path, state)
            print(json.dumps({
                "ok": False,
                "task_id": args.task_id,
                "assignee": args.assignee,
                "phase": args.phase,
                "state": str(state_path),
                "dispatch_result": dispatch_result,
            }, ensure_ascii=False))
            return 2
    cancelled = [] if args.keep_existing else cancel_existing(args.task_id)
    log = log_path.open("a", encoding="utf-8")
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
    proc = subprocess.Popen(command, cwd=REPO_ROOT, stdout=log, stderr=log, creationflags=flags)
    state = {
        "task_id": args.task_id,
        "assignee": args.assignee,
        "phase": args.phase,
        "pid": proc.pid,
        "launcher_pid": proc.pid,
        "status": "launched",
        "log": str(log_path),
        "launcher": "python",
        "started_at": dt.datetime.now().isoformat(timespec="seconds"),
        "cancelled_previous": cancelled,
        "dispatch_result": dispatch_result,
    }
    write_json(state_path, state)
    status_msg = json.dumps({
        "ok": True,
        "pid": proc.pid,
        "task_id": args.task_id,
        "state": str(state_path),
    }, ensure_ascii=False)
    print(status_msg, file=sys.stderr)
    log.write(status_msg + "\n")
    log.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
