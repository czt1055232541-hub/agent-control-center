from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

REPO_ROOT = Path(__file__).resolve().parents[1]
LARK_CLI = REPO_ROOT / ".npm-global" / "node_modules" / "@larksuite" / "cli" / "bin" / "lark-cli.exe"
AGENT_HOME = REPO_ROOT / ".home"
CONTROL_CENTER_LOCAL_CONFIG = Path(r"F:\1AI\Agent control center\config\stack.settings.local.json")
DEFAULT_CHAT_ID_ENV = "MULTIAGENT_DEFAULT_CHAT_ID"
COORDINATOR_OPEN_ID_ENV = "MULTIAGENT_COORDINATOR_OPEN_ID"


def _local_stack_settings() -> dict:
    if not CONTROL_CENTER_LOCAL_CONFIG.exists():
        return {}
    try:
        return json.loads(CONTROL_CENTER_LOCAL_CONFIG.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}


def default_chat_id() -> str:
    value = os.environ.get(DEFAULT_CHAT_ID_ENV)
    if value:
        return value
    settings = _local_stack_settings()
    value = settings.get("agent", {}).get("a2aRelay", {}).get("groupChatId")
    if value:
        return str(value)
    raise RuntimeError(f"missing group chat id; set {DEFAULT_CHAT_ID_ENV}")


def coordinator_open_id() -> str:
    value = os.environ.get(COORDINATOR_OPEN_ID_ENV)
    if value:
        return value
    settings = _local_stack_settings()
    for bot in settings.get("agent", {}).get("a2aBots", []):
        if bot.get("name") == "项目调度官" and bot.get("openId"):
            return str(bot["openId"])
    for bot in settings.get("openclaw", {}).get("a2aBots", []):
        if bot.get("name") == "项目调度官" and bot.get("openId"):
            return str(bot["openId"])
    raise RuntimeError(f"missing coordinator open id; set {COORDINATOR_OPEN_ID_ENV}")


def lark_env() -> dict[str, str]:
    env = os.environ.copy()
    home = str(AGENT_HOME)
    env["USERPROFILE"] = home
    env["HOME"] = home
    env["LARK_CLI_HOME"] = str(AGENT_HOME / ".lark-cli")
    env["LARK_CLI_CWD"] = str(REPO_ROOT)
    env["LARK_CLI_OUTPUT_ENCODING"] = "utf-8"
    for name in ("OPENCLAW_HOME", "CLAW_HOME", "HERMES_HOME", "LARK_CHANNEL"):
        env.pop(name, None)
    return env


def run_lark(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(LARK_CLI), *args],
        cwd=REPO_ROOT,
        env=lark_env(),
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )


def print_result(result: subprocess.CompletedProcess[str]) -> int:
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode


def send_calc_test(chat_id: str) -> int:
    task_id = "TASK-CALC-" + dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    body = (
        f" Multi-agent workflow test #{task_id}. "
        "Please coordinate the team to build a temporary local UI calculator app. "
        "Requirements: 1. support add, subtract, multiply, divide, clear, backspace, decimal point; "
        "2. simple polished UI; "
        "3. Code Executor implements it in a temporary local folder and reports path/self-test; "
        "4. Ops Validator checks run method and basic operability; "
        "5. Quality Auditor checks feature completeness, UI usability, invalid input and requests rework if needed; "
        "6. Project Archivist records artifact, validation result, and audit conclusion; "
        "7. Project Coordinator sends final summary. "
        "All agents should use Feishu post rich-text mentions to hand work to the next agent. "
        "Do not create Feishu Apps, Spark/Miaoda apps, task lists, or cloud resources."
    )
    content = {
        "zh_cn": {
            "content": [[
                {"tag": "at", "user_id": coordinator_open_id(), "user_name": "Project Coordinator"},
                {"tag": "text", "text": body},
            ]]
        }
    }
    result = run_lark([
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
    ])
    print(f"TASK_ID={task_id}")
    return print_result(result)


def send_final_nudge(chat_id: str, task_id: str) -> int:
    body = (
        f" #{task_id}: Project Archivist has posted the archive card, but the coordinator was not mentioned. "
        "Please send the final workflow summary now, including development, ops validation, quality audit, archive result, "
        "artifact path, and any issues found during this test."
    )
    content = {
        "zh_cn": {
            "content": [[
                {"tag": "at", "user_id": coordinator_open_id(), "user_name": "Project Coordinator"},
                {"tag": "text", "text": body},
            ]]
        }
    }
    result = run_lark([
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
    ])
    return print_result(result)


def send_nudge(chat_id: str, text: str) -> int:
    content = {
        "zh_cn": {
            "content": [[
                {"tag": "at", "user_id": coordinator_open_id(), "user_name": "Project Coordinator"},
                {"tag": "text", "text": " " + text},
            ]]
        }
    }
    result = run_lark([
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
    ])
    return print_result(result)


def list_messages(chat_id: str, page_size: int) -> int:
    result = run_lark([
        "im",
        "+chat-messages-list",
        "--chat-id",
        chat_id,
        "--page-size",
        str(page_size),
        "--order",
        "desc",
        "--as",
        "user",
        "--format",
        "json",
    ])
    return print_result(result)


def iter_message_tree(payload: dict) -> list[dict]:
    messages = payload.get("data", {}).get("messages", [])
    flattened: list[dict] = []
    for message in messages:
        flattened.append(message)
        flattened.extend(message.get("thread_replies", []))
    return flattened


def task_summary(chat_id: str, task_id: str, page_size: int) -> int:
    result = run_lark([
        "im",
        "+chat-messages-list",
        "--chat-id",
        chat_id,
        "--page-size",
        str(page_size),
        "--order",
        "desc",
        "--as",
        "user",
        "--format",
        "json",
    ])
    if result.returncode != 0:
        return print_result(result)
    payload = json.loads(result.stdout)
    rows = []
    for message in iter_message_tree(payload):
        content = str(message.get("content", ""))
        if task_id not in content:
            continue
        mentions = ", ".join(
            f"{item.get('name') or item.get('id')}" for item in message.get("mentions", [])
        )
        sender = message.get("sender", {})
        preview = " ".join(content.split())
        if len(preview) > 500:
            preview = preview[:497] + "..."
        rows.append({
            "time": message.get("create_time"),
            "position": message.get("message_position"),
            "thread_position": message.get("thread_message_position"),
            "type": message.get("msg_type"),
            "sender": sender.get("id"),
            "mentions": mentions,
            "content": preview,
        })
    rows.sort(key=lambda item: str(item.get("time") or ""))
    print(json.dumps({"task_id": task_id, "matches": rows}, ensure_ascii=False, indent=2))
    return 0


def recent_summary(chat_id: str, min_position: int, page_size: int) -> int:
    result = run_lark([
        "im",
        "+chat-messages-list",
        "--chat-id",
        chat_id,
        "--page-size",
        str(page_size),
        "--order",
        "desc",
        "--as",
        "user",
        "--format",
        "json",
    ])
    if result.returncode != 0:
        return print_result(result)
    payload = json.loads(result.stdout)
    rows = []
    for message in iter_message_tree(payload):
        position_raw = str(message.get("message_position") or "")
        try:
            position = int(position_raw)
        except ValueError:
            position = -1
        parent_position_raw = str(message.get("thread_message_position") or "")
        if position >= 0 and position < min_position:
            continue
        content = str(message.get("content", ""))
        mentions = ", ".join(
            f"{item.get('name') or item.get('id')}" for item in message.get("mentions", [])
        )
        sender = message.get("sender", {})
        preview = " ".join(content.split())
        if len(preview) > 700:
            preview = preview[:697] + "..."
        rows.append({
            "time": message.get("create_time"),
            "position": position_raw,
            "thread_position": parent_position_raw or None,
            "type": message.get("msg_type"),
            "sender": sender.get("id"),
            "mentions": mentions,
            "content": preview,
        })
    rows.sort(key=lambda item: (str(item.get("time") or ""), str(item.get("position") or "")))
    print(json.dumps({"min_position": min_position, "messages": rows}, ensure_ascii=False, indent=2))
    return 0


def update_miaoda_prompts(session_id: str) -> int:
    del session_id
    print("deprecated: all five agents are local now; Miaoda prompt updates are disabled.")
    return 2


def update_miaoda_runtime_context(session_id: str) -> int:
    del session_id
    print("deprecated: all five agents are local now; Miaoda runtime prompt context updates are disabled.")
    return 2


def reload_miaoda_agents(session_id: str) -> int:
    del session_id
    print("deprecated: all five agents are local now; Miaoda agent reload is disabled.")
    return 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chat-id", default=None)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("send-calc-test")
    nudge_parser = subparsers.add_parser("send-final-nudge")
    nudge_parser.add_argument("task_id")
    send_nudge_parser = subparsers.add_parser("send-nudge")
    send_nudge_parser.add_argument("text")
    list_parser = subparsers.add_parser("list-messages")
    list_parser.add_argument("--page-size", type=int, default=20)
    task_parser = subparsers.add_parser("task-summary")
    task_parser.add_argument("task_id")
    task_parser.add_argument("--page-size", type=int, default=50)
    recent_parser = subparsers.add_parser("recent-summary")
    recent_parser.add_argument("--min-position", type=int, default=404)
    recent_parser.add_argument("--page-size", type=int, default=50)
    miaoda_parser = subparsers.add_parser("update-miaoda-prompts")
    miaoda_parser.add_argument("session_id")
    miaoda_runtime_parser = subparsers.add_parser("update-miaoda-runtime-context")
    miaoda_runtime_parser.add_argument("session_id")
    miaoda_reload_parser = subparsers.add_parser("reload-miaoda-agents")
    miaoda_reload_parser.add_argument("session_id")
    args = parser.parse_args()

    if args.command == "update-miaoda-prompts":
        return update_miaoda_prompts(args.session_id)
    if args.command == "update-miaoda-runtime-context":
        return update_miaoda_runtime_context(args.session_id)
    if args.command == "reload-miaoda-agents":
        return reload_miaoda_agents(args.session_id)

    chat_id = args.chat_id or default_chat_id()

    if args.command == "send-calc-test":
        return send_calc_test(chat_id)
    if args.command == "send-final-nudge":
        return send_final_nudge(chat_id, args.task_id)
    if args.command == "send-nudge":
        return send_nudge(chat_id, args.text)
    if args.command == "list-messages":
        return list_messages(chat_id, args.page_size)
    if args.command == "task-summary":
        return task_summary(chat_id, args.task_id, args.page_size)
    if args.command == "recent-summary":
        return recent_summary(chat_id, args.min_position, args.page_size)
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
