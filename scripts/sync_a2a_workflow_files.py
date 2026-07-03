from __future__ import annotations

import json
from pathlib import Path

from a2a_workflow_config import REPO_ROOT, collaboration_block, sanitized_inventory, team_table_markdown

OPENCLAW_ROOT = Path(r"E:\openclaw\clawclaw\.openclaw")

PROMPT_FILES = [
    REPO_ROOT / "agents" / "auditor" / "AGENT.md",
    REPO_ROOT / "agents" / "auditor" / "SKILL.md",
    REPO_ROOT / "agents" / "coordinator" / "AGENTS.md",
    REPO_ROOT / "agents" / "executor-dev" / "AGENT.md",
    REPO_ROOT / "agents" / "executor-dev" / "SKILL.md",
    REPO_ROOT / "agents" / "executor-ops" / "AGENT.md",
    REPO_ROOT / "agents" / "executor-ops" / "AGENTS.md",
    REPO_ROOT / "agents" / "executor-ops" / "IDENTITY.md",
    REPO_ROOT / "agents" / "executor-ops" / "SKILL.md",
    REPO_ROOT / "agents" / "executor-ops" / "SOUL.md",
    REPO_ROOT / "agents" / "feishu-codex-agent" / "AGENTS.md",
    REPO_ROOT / "agents" / "feishu-codex-agent" / "SKILL.md",
    REPO_ROOT / "agents" / "knowledge" / "AGENT.md",
    REPO_ROOT / "agents" / "knowledge" / "AGENTS.md",
    REPO_ROOT / "agents" / "knowledge" / "IDENTITY.md",
    REPO_ROOT / "agents" / "knowledge" / "SKILL.md",
    REPO_ROOT / "agents" / "knowledge" / "SOUL.md",
    REPO_ROOT / "agents" / "orchestrator" / "AGENT.md",
    REPO_ROOT / "agents" / "orchestrator" / "AGENTS.md",
    REPO_ROOT / "agents" / "orchestrator" / "SKILL.md",
    OPENCLAW_ROOT / "workspace-coordinator" / "AGENTS.md",
    OPENCLAW_ROOT / "workspace-coordinator" / "SKILL.md",
    OPENCLAW_ROOT / "skills" / "feishu-team-workflow" / "SKILL.md",
]

PROTOCOL_FILE = REPO_ROOT / "docs" / "protocols" / "A2A_MENTION_PROTOCOL.md"
INVENTORY_FILE = REPO_ROOT / "docs" / "protocols" / "A2A_WORKFLOW_LINKAGE.md"


def replace_collaboration_block(text: str) -> tuple[str, bool]:
    lines = text.splitlines()
    if lines and lines[0].strip() == "## 团队协作强制规则":
        end = 1
        while end < len(lines):
            if lines[end].startswith("## ") and lines[end].strip() != "## 团队协作强制规则":
                break
            if lines[end].strip() == "---":
                break
            end += 1
        lines = lines[end:]
    frontmatter_end = 0
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                frontmatter_end = i + 1
                break
    start = next((i for i, line in enumerate(lines) if line.strip() == "## 团队协作强制规则"), None)
    if start is None:
        insert_at = frontmatter_end
        if insert_at < len(lines) and lines[insert_at].startswith("# "):
            insert_at += 1
        return "\n".join([*lines[:insert_at], collaboration_block(), *lines[insert_at:]]).rstrip() + "\n", True
    end = start + 1
    while end < len(lines):
        if lines[end].startswith("## ") and lines[end].strip() != "## 团队协作强制规则":
            break
        end += 1
    new_lines = [*lines[:start], *collaboration_block().splitlines(), *lines[end:]]
    return "\n".join(new_lines).rstrip() + "\n", True


def write_if_changed(path: Path, text: str) -> bool:
    old = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
    if old == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def sync_prompt_files() -> list[str]:
    changed = []
    for path in PROMPT_FILES:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        new_text, _ = replace_collaboration_block(text)
        if write_if_changed(path, new_text):
            changed.append(str(path))
    return changed


def sync_protocol() -> bool:
    text = "\n".join(
        [
            "# A2A Mention Protocol",
            "",
            "<!-- A2A_WORKFLOW_GENERATED:BEGIN -->",
            "",
            "## Source Of Truth",
            "",
            "- Role names, aliases, Feishu open IDs, and the default group chat ID are read from the local Agent Control Center settings.",
            "- Repository files must not contain real open IDs or chat IDs.",
            "- Runtime Feishu delivery uses `OPENCLAW_FEISHU_A2A_BOTS`, generated from the same local settings at gateway startup.",
            "",
            "## Mention Rules",
            "",
            "- Agent replies write normalized role names such as `@项目调度官` or `@代码执行官`.",
            "- Downstream agents must start final completion, validation, audit, or archival reports with `@项目调度官`.",
            "- The Feishu sender converts normalized role names to `msg_type=post` rich-text `at` elements.",
            "- Do not output literal `<at user_id=\"...\">名称</at>` as the handoff format.",
            "- Mention at most one agent in a handoff reply.",
            "- Assignment or downstream reminder messages may only truly mention the current assignee; write the coordinator name without `@` when explaining where the assignee should report back.",
            "- If a delivered Feishu message has an empty `mentions` list after a supposed handoff, the handoff failed and must be retried after fixing the mapping or sender layer.",
            "- The coordinator must publish every assignment in its own current reply with a real rich-text mention of the assignee.",
            "- `start_scheduler_watchdog.py` only starts delayed coordinator-check reminders by default; it must not be treated as the assignment sender.",
            "- Watchdog prompts are also sent as Feishu `post` messages with a real `at` element for 项目调度官.",
            "",
            "## Team Map",
            "",
            team_table_markdown(),
            "",
            "<!-- A2A_WORKFLOW_GENERATED:END -->",
            "",
        ]
    )
    return write_if_changed(PROTOCOL_FILE, text)


def sync_inventory() -> bool:
    inventory = sanitized_inventory()
    active_files = {
        "source_config": inventory["source_of_truth"],
        "runtime_readers": [
            str(REPO_ROOT / "scripts" / "a2a_workflow_config.py"),
            str(REPO_ROOT / "scripts" / "print_a2a_bots_env.py"),
            str(REPO_ROOT / "scripts" / "scheduler_watchdog.py"),
            str(REPO_ROOT / "scripts" / "lark_multiagent_probe.py"),
        ],
        "sync_tool": str(REPO_ROOT / "scripts" / "sync_a2a_workflow_files.py"),
        "watchdog_tools": [
            str(REPO_ROOT / "scripts" / "start_scheduler_watchdog.py"),
            str(REPO_ROOT / "scripts" / "stop_scheduler_watchdog.py"),
        ],
        "gateway_entry": str(OPENCLAW_ROOT / "gateway.cmd"),
        "feishu_sender": str(OPENCLAW_ROOT / "npm" / "projects" / "openclaw-feishu-dc69f44688" / "node_modules" / "@openclaw" / "feishu" / "dist" / "send-B3kteMF8.js"),
        "bot_chat_plugin": str(OPENCLAW_ROOT / "npm" / "projects" / "feishu-bot-chat" / "node_modules" / "feishu-bot-chat" / "index.js"),
        "generated_prompt_files": [str(path) for path in PROMPT_FILES if path.exists()],
        "protocol": str(PROTOCOL_FILE),
        "operator_readme": str(REPO_ROOT / "README.md"),
        "this_inventory": str(INVENTORY_FILE),
    }
    text = [
        "# A2A Workflow Linkage",
        "",
        "This file is generated by `python scripts/sync_a2a_workflow_files.py`.",
        "",
        "## Single Source",
        "",
        f"- Local config: `{active_files['source_config']}`",
        "- This local config owns role names, aliases, Feishu open IDs, and the default group chat ID.",
        "- Repository files and shared prompts only reference role names and never store raw IDs.",
        "",
        "## Active Linkage",
        "",
        "```json",
        json.dumps(active_files, ensure_ascii=False, indent=2),
        "```",
        "",
        "## Change Procedure",
        "",
        "1. Update the local Agent Control Center settings.",
        "2. Run `python scripts/sync_a2a_workflow_files.py`.",
        "3. Restart the OpenClaw gateway so `OPENCLAW_FEISHU_A2A_BOTS` is regenerated.",
        "4. Verify with a Feishu post whose delivered `mentions` contains the target role.",
        "",
    ]
    return write_if_changed(INVENTORY_FILE, "\n".join(text))


def main() -> int:
    changed = sync_prompt_files()
    protocol_changed = sync_protocol()
    inventory_changed = sync_inventory()
    print(json.dumps({
        "changed_prompt_files": changed,
        "protocol_changed": protocol_changed,
        "inventory_changed": inventory_changed,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
