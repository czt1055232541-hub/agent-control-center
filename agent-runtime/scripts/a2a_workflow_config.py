from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
STACK_ROOT = REPO_ROOT.parent
LOCAL_SETTINGS_PATH = Path(os.environ.get("STACK_SETTINGS_PATH") or STACK_ROOT / "config" / "stack.settings.local.json")
PUBLIC_SETTINGS_LABEL = "{ACC_ROOT}/config/stack.settings.local.json"

ROLE_DESCRIPTIONS = {
    "项目调度官": "任务拆解、调度、进度管理",
    "代码执行官": "代码实现、修复和本地测试",
    "运维验证官": "运行、环境、部署和验证",
    "质量审计官": "质量审计、返工意见",
    "项目档案官": "项目记录、文档归档",
}

DEFAULT_ROLE_ORDER = ["项目调度官", "代码执行官", "运维验证官", "质量审计官", "项目档案官"]


def read_json(path: Path = LOCAL_SETTINGS_PATH) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def local_settings() -> dict[str, Any]:
    return read_json(LOCAL_SETTINGS_PATH)


def default_chat_id() -> str:
    settings = local_settings()
    for section in ("agent", "openclaw"):
        section_data = settings.get(section, {})
        if not isinstance(section_data, dict):
            continue
        value = section_data.get("a2aRelay", {}).get("groupChatId") if isinstance(section_data.get("a2aRelay"), dict) else None
        if value:
            return str(value)
    raise RuntimeError("missing group chat id in Agent Control Center local settings")


def configured_bots() -> list[dict[str, Any]]:
    settings = local_settings()
    by_open_id: dict[str, dict[str, Any]] = {}
    for section in ("agent", "openclaw"):
        section_data = settings.get(section, {})
        if not isinstance(section_data, dict):
            continue
        bots = section_data.get("a2aBots", [])
        if not isinstance(bots, list):
            continue
        for bot in bots:
            if not isinstance(bot, dict):
                continue
            name = str(bot.get("name") or "").strip()
            open_id = str(bot.get("openId") or "").strip()
            description = str(bot.get("description") or ROLE_DESCRIPTIONS.get(name, "")).strip()
            if not name or not open_id:
                continue
            entry = by_open_id.setdefault(open_id, {"name": name, "openId": open_id, "aliases": [], "description": description})
            aliases = set(entry.get("aliases") or [])
            aliases.add(name)
            entry["aliases"] = sorted(aliases)
            if description and not entry.get("description"):
                entry["description"] = description
    bots = list(by_open_id.values())
    order = {name: i for i, name in enumerate(DEFAULT_ROLE_ORDER)}
    bots.sort(key=lambda item: order.get(str(item.get("name")), 999))
    return bots


def role_names() -> list[str]:
    return [str(bot["name"]) for bot in configured_bots()]


def require_role_open_id(role_name: str) -> str:
    for bot in configured_bots():
        if role_name == bot.get("name") or role_name in bot.get("aliases", []):
            return str(bot["openId"])
    raise RuntimeError(f"missing A2A role mapping: {role_name}")


def feishu_a2a_bots_env() -> str:
    payload = [
        {
            "name": bot["name"],
            "openId": bot["openId"],
            "aliases": bot.get("aliases", [bot["name"]]),
        }
        for bot in configured_bots()
    ]
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def mention_names_text() -> str:
    return "、".join(f"`@{name}`" for name in role_names())


def team_table_markdown(id_source: str = "本地 A2A 配置") -> str:
    lines = ["| 名称 | ID 来源 | 角色 |", "|---|---|---|"]
    for name in role_names():
        lines.append(f"| {name} | {id_source} | {ROLE_DESCRIPTIONS.get(name, '')} |")
    return "\n".join(lines)


def collaboration_block() -> str:
    return "\n".join(
        [
            "## 团队协作强制规则",
            "",
            "<!-- A2A_WORKFLOW_GENERATED:BEGIN -->",
            "",
            f"- 角色、别名、open_id 与群 chat_id 的唯一来源：`{PUBLIC_SETTINGS_LABEL}`。",
            "- 仓库和 OpenClaw prompt 不保存真实 open_id；需要修改角色映射时只改上述本地配置，然后运行 `python scripts/stack.py a2a sync`。",
            "- 飞书群内向指定对象交接或提醒时，正文必须写规范角色名：" + mention_names_text() + "。",
            "- 项目调度官可同时 @ 多个 agent 进行并行派发；其他 agent 每次交接最多 @ 一个 agent。不要绕过项目调度官。",
            "- 派发或催促下游 agent 时，只能真实 @ 当前 assignee；如需说明回报对象，写“完成后回报项目调度官”，不要在同一条派发消息里再写 `@项目调度官`。",
            "- 下游 agent 完成任务、验证、审计或归档时，最终报告第一行必须以 `@项目调度官` 开头；不要只在“建议下一步”里写项目调度官。",
            "- 真实发送必须由 Feishu sender 转成 `msg_type=post` 富文本 `at` 标签；不得把 `<at user_id=\"...\">名称</at>` 当作交接格式。",
            "- 如果 Feishu 已发送消息的 `mentions` 为空，该次交接视为失败，必须修复映射/发送层后补发。",
            "- 下游 agent 收到任务中明确的项目路径或产物路径后，必须只围绕该路径执行和回报；不得把旁观者、系统修补或仓库中无关改动当成本任务产物。",
            "- 项目调度官每次派发必须先调用 `python scripts/stack.py watchdog start --task-id ... --assignee ... --phase ... --task-text ...` 启动 watchdog；脚本默认不得代发群消息。",
            "- 启动 watchdog 后，项目调度官的最终可见回复必须包含完整派发正文并真实 @ 当前 assignee；不得让脚本以用户身份发送额外派发消息，除非人工明确要求 `--dispatch-as-user` 恢复。",
            "- watchdog 默认周期性看护直到 stop；项目调度官收到 watchdog 检查提示后必须当轮处理：若任务仍在执行，确认仍有 active waiting watchdog；若没有，则立刻为同一 TASK-ID 补开 continuation watchdog，不得等待用户或旁观者再次提醒。",
            "- 收到下游有效回报后必须调用 `python scripts/stack.py watchdog stop --task-id ... --assignee ... --phase ...` 关闭对应 watchdog。",
            "- 不在配置、文档、回复中暴露真实 open_id、chat_id、app_id、app_secret、token 或会话数据。",
            "",
            "<!-- A2A_WORKFLOW_GENERATED:END -->",
        ]
    )


def sanitized_inventory() -> dict[str, Any]:
    return {
        "source_of_truth": PUBLIC_SETTINGS_LABEL,
        "roles": [{"name": name, "description": ROLE_DESCRIPTIONS.get(name, "")} for name in role_names()],
        "runtime_env": "OPENCLAW_FEISHU_A2A_BOTS is generated from source_of_truth at gateway startup",
        "watchdog": {
            "start": "python scripts/stack.py watchdog start",
            "stop": "python scripts/stack.py watchdog stop",
        },
    }


def main() -> int:
    print(json.dumps(sanitized_inventory(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
