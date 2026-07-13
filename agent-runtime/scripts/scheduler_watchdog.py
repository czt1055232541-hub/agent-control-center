from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from a2a_workflow_config import default_chat_id as configured_default_chat_id
from a2a_workflow_config import require_role_open_id

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

AGENT_RUNTIME_ROOT = Path(__file__).resolve().parents[1]
STACK_ROOT = AGENT_RUNTIME_ROOT.parent
REPO_ROOT = STACK_ROOT
PUBLIC_STACK_CONFIG = Path(os.environ.get("STACK_SETTINGS_PATH") or STACK_ROOT / "config" / "stack.settings.local.json")
AGENT_HOME = AGENT_RUNTIME_ROOT / ".home"
WATCHDOG_DIR = STACK_ROOT / "runtime" / "watchdogs"
DEFAULT_CHAT_ID_ENV = "MULTIAGENT_DEFAULT_CHAT_ID"
COORDINATOR_OPEN_ID_ENV = "MULTIAGENT_COORDINATOR_OPEN_ID"


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def update_state(path: Path | None, **updates: object) -> None:
    if path is None:
        return
    payload = read_json(path)
    payload.update(updates)
    payload["updated_at"] = dt.datetime.now().isoformat(timespec="seconds")
    write_json(path, payload)


def local_settings() -> dict:
    return {}


def public_settings() -> dict:
    return read_json(PUBLIC_STACK_CONFIG)


def default_chat_id() -> str:
    value = os.environ.get(DEFAULT_CHAT_ID_ENV)
    if value:
        return value
    return configured_default_chat_id()


def coordinator_open_id() -> str:
    value = os.environ.get(COORDINATOR_OPEN_ID_ENV)
    if value:
        return value
    return require_role_open_id("项目调度官")


def lark_cli_path() -> Path:
    configured = public_settings().get("agent", {}).get("larkCliBin")
    if configured:
        return Path(configured)
    return AGENT_RUNTIME_ROOT / ".npm-global" / "node_modules" / "@larksuite" / "cli" / "bin" / "lark-cli.exe"


def lark_env() -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if key.upper() in {"PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC", "TEMP", "TMP"}
    }
    env["USERPROFILE"] = str(AGENT_HOME)
    env["HOME"] = str(AGENT_HOME)
    env["LARK_CLI_HOME"] = str(AGENT_HOME / ".lark-cli")
    env["LARK_CLI_CWD"] = str(REPO_ROOT)
    env["LARK_CLI_OUTPUT_ENCODING"] = "utf-8"
    env.setdefault("PYTHONUTF8", "1")
    return env


def choose_delay_seconds(task_text: str) -> int:
    text = task_text.lower()
    if any(token in text for token in ("lumerical", "fdtd", "仿真", "mmi", "lumapi", "扫描", "优化")):
        return 30 * 60
    if any(token in text for token in ("开发", "实现", "修复", "代码", "测试", "gui", "应用")):
        return 15 * 60
    if any(token in text for token in ("调研", "论文", "方案", "讨论", "审计", "归档")):
        return 10 * 60
    return 8 * 60


def build_prompt(task_id: str, task_text: str, elapsed_seconds: int, assignee: str | None = None, phase: str | None = None) -> str:
    minutes = max(1, round(elapsed_seconds / 60))
    assignee_text = f"当前派发对象：{assignee}。" if assignee else ""
    phase_text = f"当前阶段：{phase}。" if phase else ""
    return (
        f" TASK-ID {task_id} 的看护倒计时已到（约 {minutes} 分钟）。"
        f"{assignee_text}{phase_text}"
        "请立即检查当前任务执行 agent 状态："
        "1. 哪个 agent 正在执行；"
        "2. 是否已回复但缺少有效 @；"
        "3. 是否需要继续同一 TASK-ID 轻推；"
        "4. 是否存在卡死、失效回复或上下文过大；"
        "5. 下一步只调度一个 agent。"
        "如果任务仍在执行且未收到有效最终回报，本 watchdog 会继续周期性提醒；你必须确认仍有 active waiting watchdog。"
        "只有发现没有 active waiting watchdog 时，才立即调用 "
        "`python scripts/stack.py watchdog start --task-id ... --assignee ... --phase ... --task-text ... --no-dispatch` 补开同一 TASK-ID 的 continuation watchdog；不要等待人工提醒。"
        "如果已收到有效最终回报，你必须调用 `python scripts/stack.py watchdog stop --task-id ... --assignee ... --phase ...` 关闭 watchdog。"
        f" 原任务摘要：{compact(task_text, 500)}"
    )


def compact(value: str, max_len: int) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= max_len:
        return normalized
    return normalized[: max_len - 3] + "..."


def iso_after(seconds: int) -> str:
    return (dt.datetime.now() + dt.timedelta(seconds=seconds)).isoformat(timespec="seconds")


def send_coordinator_prompt(
    chat_id: str,
    task_id: str,
    task_text: str,
    elapsed_seconds: int,
    dry_run: bool,
    assignee: str | None = None,
    phase: str | None = None,
) -> int:
    coordinator_id = coordinator_open_id()
    content = {
        "zh_cn": {
            "content": [[
                {"tag": "at", "user_id": coordinator_id, "user_name": "项目调度官"},
                {"tag": "text", "text": build_prompt(task_id, task_text, elapsed_seconds, assignee, phase)},
            ]]
        }
    }
    command = [
        str(lark_cli_path()),
        "im",
        "+messages-send",
        "--chat-id",
        chat_id,
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
        sanitized_command = [
            "<lark-cli>" if item == str(lark_cli_path()) else
            "<chat-id>" if item == chat_id else
            item.replace(coordinator_id, "<coordinator-open-id>") if coordinator_id in item else
            item
            for item in command
        ]
        sanitized_content = json.loads(json.dumps(content))
        sanitized_content["zh_cn"]["content"][0][0]["user_id"] = "<coordinator-open-id>"
        print(json.dumps({"command": sanitized_command, "content": sanitized_content}, ensure_ascii=False, indent=2))
        return 0
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        env=lark_env(),
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Send a delayed Feishu coordinator watchdog prompt.")
    parser.add_argument("--chat-id", default=None)
    parser.add_argument("--task-id", default=None)
    parser.add_argument("--task-text", required=True)
    parser.add_argument("--assignee", default=None)
    parser.add_argument("--phase", default=None)
    parser.add_argument("--delay-seconds", type=int, default=None)
    parser.add_argument("--delay-minutes", type=float, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-wait", action="store_true", help="Send immediately after computing the delay; useful for smoke tests.")
    parser.add_argument("--state-file", default=None, help="Runtime state JSON written by the launcher.")
    parser.add_argument(
        "--single-shot",
        action="store_true",
        help="Send one coordinator check and exit. Default is periodic checks until stop_scheduler_watchdog cancels the process.",
    )
    parser.add_argument(
        "--max-sends",
        type=int,
        default=0,
        help="Maximum check prompts before exiting in periodic mode. 0 means unlimited.",
    )
    args = parser.parse_args(argv)

    state_file = Path(args.state_file) if args.state_file else None
    task_id = args.task_id or "TASK-WATCH-" + dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    try:
        chat_id = args.chat_id or default_chat_id()
        delay_seconds = choose_delay_seconds(args.task_text)
        if args.delay_minutes is not None:
            delay_seconds = max(1, int(args.delay_minutes * 60))
        if args.delay_seconds is not None:
            delay_seconds = max(1, args.delay_seconds)
    except Exception as exc:
        update_state(
            state_file,
            task_id=task_id,
            pid=os.getpid(),
            status="config_failed",
            error=repr(exc),
            finished_at=dt.datetime.now().isoformat(timespec="seconds"),
        )
        print(json.dumps({"task_id": task_id, "status": "config_failed", "error": repr(exc)}, ensure_ascii=False), flush=True)
        return 2

    periodic = not args.single_shot and not args.dry_run
    startup = {
        "task_id": task_id,
        "chat_id_source": "argument" if args.chat_id else "local_config_or_env",
        "delay_seconds": delay_seconds,
        "send_as": "user",
        "target": "项目调度官",
        "started_at": dt.datetime.now().isoformat(timespec="seconds"),
        "pid": os.getpid(),
        "status": "waiting" if not args.no_wait and delay_seconds > 0 else "sending",
        "periodic": periodic,
        "max_sends": max(0, args.max_sends),
        "send_count": 0,
    }
    if startup["status"] == "waiting":
        startup["next_check_at"] = iso_after(delay_seconds)
    print(json.dumps(startup, ensure_ascii=False), flush=True)
    update_state(state_file, **startup)
    send_count = 0
    first = True
    while True:
        should_wait = not args.no_wait or not first
        if should_wait and delay_seconds > 0:
            update_state(
                state_file,
                status="waiting",
                send_count=send_count,
                next_check_at=iso_after(delay_seconds),
                updated_at=dt.datetime.now().isoformat(timespec="seconds"),
            )
            time.sleep(delay_seconds)
        update_state(state_file, status="sending", sending_at=dt.datetime.now().isoformat(timespec="seconds"))
        rc = send_coordinator_prompt(chat_id, task_id, args.task_text, delay_seconds, args.dry_run, args.assignee, args.phase)
        send_count += 1
        sent_at = dt.datetime.now().isoformat(timespec="seconds")
        if rc != 0:
            update_state(
                state_file,
                status="send_failed",
                returncode=rc,
                send_count=send_count,
                finished_at=sent_at,
            )
            print(json.dumps({"task_id": task_id, "status": "send_failed", "returncode": rc, "send_count": send_count}, ensure_ascii=False), flush=True)
            return rc
        max_reached = args.max_sends > 0 and send_count >= args.max_sends
        if not periodic or max_reached:
            update_state(
                state_file,
                status="sent",
                returncode=rc,
                send_count=send_count,
                finished_at=sent_at,
            )
            print(json.dumps({"task_id": task_id, "status": "sent", "returncode": rc, "send_count": send_count}, ensure_ascii=False), flush=True)
            return rc
        next_check_at = iso_after(delay_seconds)
        update_state(
            state_file,
            status="waiting",
            returncode=rc,
            send_count=send_count,
            last_sent_at=sent_at,
            next_check_at=next_check_at,
            updated_at=sent_at,
        )
        print(json.dumps({"task_id": task_id, "status": "waiting", "returncode": rc, "send_count": send_count, "next_check_at": next_check_at}, ensure_ascii=False), flush=True)
        first = False


if __name__ == "__main__":
    raise SystemExit(main())
