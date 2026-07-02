from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
LOCAL_SETTINGS_PATH = Path(r"F:\1AI\Agent control center\config\stack.settings.local.json")

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
            f"- 角色、别名、open_id 与群 chat_id 的唯一来源：`{LOCAL_SETTINGS_PATH}`。",
            "- 仓库和 OpenClaw prompt 不保存真实 open_id；需要修改角色映射时只改上述本地配置，然后运行 `python scripts/sync_a2a_workflow_files.py`。",
            "- 飞书群内向指定对象交接或提醒时，正文必须写规范角色名：" + mention_names_text() + "。",
            "- 每次交接最多 @ 一个 agent；不要一次 @ 多人，不要绕过项目调度官。",
            "- 真实发送必须由 Feishu sender 转成 `msg_type=post` 富文本 `at` 标签；不得把 `<at user_id=\"...\">名称</at>` 当作交接格式。",
            "- 如果 Feishu 已发送消息的 `mentions` 为空，该次交接视为失败，必须修复映射/发送层后补发。",
            "- 项目调度官每次派发后必须启动 watchdog；收到下游有效回报后必须关闭对应 watchdog。",
            "- 不在配置、文档、回复中暴露真实 open_id、chat_id、app_id、app_secret、token 或会话数据。",
            "",
            "<!-- A2A_WORKFLOW_GENERATED:END -->",
        ]
    )


def sanitized_inventory() -> dict[str, Any]:
    return {
        "source_of_truth": str(LOCAL_SETTINGS_PATH),
        "roles": [{"name": name, "description": ROLE_DESCRIPTIONS.get(name, "")} for name in role_names()],
        "runtime_env": "OPENCLAW_FEISHU_A2A_BOTS is generated from source_of_truth at gateway startup",
        "watchdog": {
            "start": str(REPO_ROOT / "scripts" / "start_scheduler_watchdog.py"),
            "stop": str(REPO_ROOT / "scripts" / "stop_scheduler_watchdog.py"),
        },
    }


def main() -> int:
    print(json.dumps(sanitized_inventory(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
