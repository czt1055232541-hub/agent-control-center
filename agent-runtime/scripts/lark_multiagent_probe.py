from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

from a2a_workflow_config import default_chat_id as configured_default_chat_id
from a2a_workflow_config import require_role_open_id

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

REPO_ROOT = Path(__file__).resolve().parents[1]
LARK_CLI = REPO_ROOT / ".npm-global" / "node_modules" / "@larksuite" / "cli" / "bin" / "lark-cli.exe"
AGENT_HOME = REPO_ROOT / ".home"
DEFAULT_CHAT_ID_ENV = "MULTIAGENT_DEFAULT_CHAT_ID"
COORDINATOR_OPEN_ID_ENV = "MULTIAGENT_COORDINATOR_OPEN_ID"


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


def send_mmi_3d_optimization_task(chat_id: str) -> int:
    task_id = "TASK-MMI-3D-OPT-" + dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    body = f"""
【{task_id}｜MMI 设计优化进入三维 FDTD 闭环】
请以项目调度官身份组织群内 agents 继续推进 MMI 设计优化任务。上轮 2D 基线已归档，但 <0.5 dB 工程目标未达成，本轮不要直接开跑参数扫；必须先完成文献和方案闭环，再进入 2D/3D 仿真。

硬性流程：
1. 先派发给代码执行官与质量审计官做经典论文/文献调研：覆盖自成像 MMI 理论、低损耗 1x2 MMI splitter、SOI 220nm 平台、taper/多段锥形/形状优化、3D FDTD 验证做法。要求输出可追溯论文清单、关键公式/设计初值、可仿真参数范围。
2. 组织集体讨论制定 Lumerical 方案：明确 2D 快速优化变量、目标函数、清理策略、停止条件、3D FDTD 边界/mesh/monitor/source/端口归一化设置，以及由 2D 过渡到 3D 的验收门槛。
3. 再派发代码执行官实现自动化优化脚本。仿真扫描过程中必须像 FDTD optimize 一样及时清理中间仿真文件，只保留 manifest、核心目标参数、趋势图、最佳 fsp 和必要报告。
4. 运维验证官负责验证脚本可运行、Lumerical GUI 可见、单实例串行、文件清理和结果 JSON 可解析。
5. 质量审计官必须审计论文依据、优化方案、2D 收敛、3D 设置和最终指标；未达目标要给出下一轮返工项，而不是形式通过。
6. 项目档案官最后归档论文调研、讨论纪要、优化脚本、2D/3D 结果、最佳 fsp、趋势图、审计结论。

协作要求：
- 每次向下游 agent 派发时，必须使用富文本 mention，并由项目调度官在派发动作中同步启动 scheduler watchdog；收到有效回复后关闭对应 watchdog。
- 不要泄露任何 open_id/chat_id/app_secret。群内只按角色名汇报。
- 本轮最终目标是得到三维 FDTD 仿真结果；如果物理目标 <0.5 dB 仍未达成，也必须给出有证据的原因和下一轮设计方向。
""".strip()
    content = {
        "zh_cn": {
            "content": [[
                {"tag": "at", "user_id": coordinator_open_id(), "user_name": "项目调度官"},
                {"tag": "text", "text": " " + body},
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


def send_mmi_3d_dispatch_nudge(chat_id: str, task_id: str) -> int:
    body = f"""
【监督纠偏｜{task_id}】
我已看到你启动了代码执行官的文献调研 watchdog，但最近群消息中还没有出现真正 `@代码执行官` 的富文本派发消息；watchdog 不能替代任务派发。

请立即发送一条 `post` 富文本消息真实 @代码执行官，派发“经典论文/文献调研”阶段：
- 调研自成像 MMI 理论、低损耗 1x2 MMI splitter、SOI 220nm 平台、taper/多段锥形/形状优化、3D FDTD 验证做法；
- 输出可追溯论文清单、关键公式/设计初值、可仿真参数范围；
- 不开跑仿真，不创建云资源；
- 回报后由你关闭当前 watchdog，再交给质量审计官复审文献。

请保持同一个 TASK-ID，不要新开任务。
""".strip()
    content = {
        "zh_cn": {
            "content": [[
                {"tag": "at", "user_id": coordinator_open_id(), "user_name": "项目调度官"},
                {"tag": "text", "text": " " + body},
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
    subparsers.add_parser("send-mmi-3d-optimization-task")
    dispatch_nudge_parser = subparsers.add_parser("send-mmi-3d-dispatch-nudge")
    dispatch_nudge_parser.add_argument("task_id")
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
    if args.command == "send-mmi-3d-optimization-task":
        return send_mmi_3d_optimization_task(chat_id)
    if args.command == "send-mmi-3d-dispatch-nudge":
        return send_mmi_3d_dispatch_nudge(chat_id, args.task_id)
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
