from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config" / "skill-tree-workshop" / "agents"
DEMO_HTML = ROOT / "docs" / "prototypes" / "skill-tree-workshop-demo.html"
OPENCLAW_ROOT = Path(r"E:\openclaw\npm\node_modules\openclaw\skills")
CODEX_ROOTS = [
    ("codex", Path(r"E:\codeX\skills")),
    ("lark", Path(r"C:\Users\admin\.agents\skills")),
    ("codex-bundled", Path(r"E:\codeX\plugins\cache\openai-bundled")),
    ("codex-curated", Path(r"E:\codeX\plugins\cache\openai-curated-remote")),
]
AGENT_FILES = {
    "coordinator": "agent-coordinator.skill-tree.json",
    "ops": "agent-ops.skill-tree.json",
    "audit": "agent-audit.skill-tree.json",
    "archive": "agent-archive.skill-tree.json",
    "codex": "agent-codex.skill-tree.json",
}
ROLE_KEYWORDS = {
    "coordinator": {"clawhub", "coding-agent", "github", "gh-issues", "healthcheck", "diagram-maker", "blogwatcher"},
    "ops": {"healthcheck", "coding-agent", "goplaces", "gog", "eightctl", "gifgrep", "camsnap", "blucli"},
    "audit": {"github", "gh-issues", "healthcheck", "coding-agent", "gifgrep", "diagram-maker"},
    "archive": {"clawhub", "github", "gh-issues", "blogwatcher", "apple-notes", "bear-notes", "canvas", "diagram-maker"},
}
CODEX_PROFESSIONAL = {
    "ai-project-delivery-workflow-version1.5",
    "feishu-openclaw-multiagent-ops",
    "control-in-app-browser",
    "control-chrome",
    "computer-use",
    "github",
    "gh-fix-ci",
    "gh-address-comments",
    "yeet",
}


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", value.lower()).strip("_") or "skill"


def read_frontmatter(path: Path) -> tuple[str, str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    name = path.parent.name
    description = ""
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            fm = text[3:end]
            for line in fm.splitlines():
                if line.startswith("name:"):
                    name = line.split(":", 1)[1].strip().strip("\"'") or name
                if line.startswith("description:"):
                    description = line.split(":", 1)[1].strip().strip("\"'")
    if not description:
        for line in text.splitlines():
            line = line.strip()
            if line and not line.startswith("---") and not line.startswith("#"):
                description = line[:140]
                break
    return name, description


def human_label(name: str) -> str:
    clean = name.split(":")[-1]
    if clean == "ai-project-delivery-workflow-version1.5":
        return "AI 合作工作流"
    if clean == "feishu-openclaw-multiagent-ops":
        return "飞书群聊调度"
    if clean.startswith("lark-"):
        return "飞书 " + clean[5:].replace("-", " ")
    return clean.replace("-", " ")


def category_for(name: str) -> str:
    n = name.lower()
    if any(k in n for k in ["approval", "permission", "1password"]):
        return "permission"
    if any(k in n for k in ["github", "coding", "browser", "chrome", "computer", "tool", "cli", "ctl", "snap", "grep"]):
        return "tool"
    if any(k in n for k in ["health", "test", "review", "audit", "fix", "ci"]):
        return "quality"
    if any(k in n for k in ["workflow", "calendar", "task", "schedule", "automation"]):
        return "workflow"
    if any(k in n for k in ["docs", "drive", "sheets", "slides", "notes", "mail", "minutes", "wiki", "base"]):
        return "basic"
    return "advanced"


def scan_openclaw() -> list[dict[str, str]]:
    skills: list[dict[str, str]] = []
    for path in sorted(OPENCLAW_ROOT.glob("*/SKILL.md")):
        _, description = read_frontmatter(path)
        name = path.parent.name
        skills.append(
            {
                "name": name,
                "display": human_label(name),
                "runtime": "openclaw",
                "path": str(path),
                "description": description or f"OpenClaw skill: {name}",
            }
        )
    return skills


def scan_codex() -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    skills: list[dict[str, str]] = []
    for runtime, root in CODEX_ROOTS:
        if not root.exists():
            continue
        for path in sorted(root.rglob("SKILL.md")):
            parts = {part.lower() for part in path.parts}
            if "plugin-backup-jtgvgl" in parts or "latest" in parts:
                continue
            name, description = read_frontmatter(path)
            key = (runtime, name if runtime == "codex-bundled" else str(path.parent).lower())
            if key in seen:
                continue
            seen.add(key)
            skills.append(
                {
                    "name": name,
                    "display": human_label(name),
                    "runtime": runtime,
                    "path": str(path),
                    "description": description or f"{runtime} skill: {name}",
                }
            )
    return skills


def position(branch: str, index: int) -> tuple[int, int]:
    xs = [14, 27, 40] if branch == "generic" else [60, 73, 86]
    return xs[index % len(xs)], 28 + (index // len(xs)) * 13


def make_nodes(agent: dict, skills: list[dict[str, str]], professional_names: set[str]) -> tuple[list[dict], list[list[str]]]:
    nodes: list[dict] = [
        {
            "id": "model_base",
            "label": "模型基座",
            "nodeType": "model",
            "model": agent["model"],
            "category": "basic",
            "branch": "base",
            "x": 50,
            "y": 12,
            "description": f"{agent['name']} 的模型原点，不对应 SKILL.md。",
        }
    ]
    generic: list[dict[str, str]] = []
    professional: list[dict[str, str]] = []
    for skill in skills:
        (professional if skill["name"] in professional_names else generic).append(skill)
    if not professional and generic:
        professional.append(generic.pop(0))

    edges: list[list[str]] = []
    for branch, items in [("generic", generic), ("professional", professional)]:
        previous = "model_base"
        for index, skill in enumerate(items):
            x, y = position(branch, index)
            node_id = f"{branch}_{slug(skill['runtime'])}_{slug(skill['name'])}"
            nodes.append(
                {
                    "id": node_id,
                    "label": skill["display"],
                    "nodeType": "skill",
                    "skillName": skill["name"],
                    "skillRuntime": skill["runtime"],
                    "skillPath": skill["path"],
                    "category": category_for(skill["name"]),
                    "branch": branch,
                    "x": x,
                    "y": y,
                    "gear": [],
                    "description": skill["description"],
                }
            )
            edges.append([previous, node_id])
            previous = node_id
    return nodes, edges


def load_agent(agent_id: str) -> dict:
    cfg = json.loads((CONFIG_DIR / AGENT_FILES[agent_id]).read_text(encoding="utf-8"))
    return cfg["agent"]


def write_agent_config(agent_id: str, agent: dict, skills: list[dict[str, str]], professional_names: set[str]) -> None:
    nodes, edges = make_nodes(agent, skills, professional_names)
    cfg = {
        "version": 3,
        "agent": agent,
        "nodes": nodes,
        "edges": edges,
        "futureAnchors": [
            {"id": next((n["id"] for n in nodes if n.get("branch") == "generic"), "model_base"), "label": "通用技能未来规划"},
            {"id": next((n["id"] for n in nodes if n.get("branch") == "professional"), "model_base"), "label": "专业技能未来规划"},
        ],
    }
    (CONFIG_DIR / AGENT_FILES[agent_id]).write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def sync_html_fallback() -> None:
    agents: list[dict] = []
    for agent_id in ["coordinator", "ops", "audit", "archive", "codex"]:
        cfg = json.loads((CONFIG_DIR / AGENT_FILES[agent_id]).read_text(encoding="utf-8"))
        agent = dict(cfg["agent"])
        agent.update({"nodes": cfg["nodes"], "edges": cfg["edges"], "futureAnchors": cfg.get("futureAnchors", [])})
        agents.append(agent)
    fallback = {"version": 3, "agents": agents}
    html_path = DEMO_HTML
    text = html_path.read_text(encoding="utf-8")
    start = text.index("    const fallbackConfig = ")
    end = text.index("\n\n    function node(", start)
    replacement = "    const fallbackConfig = " + json.dumps(fallback, ensure_ascii=False, indent=6) + ";"
    html_path.write_text(text[:start] + replacement + text[end:], encoding="utf-8")


def main() -> None:
    openclaw_skills = scan_openclaw()
    codex_skills = scan_codex()
    for agent_id in ["coordinator", "ops", "audit", "archive"]:
        write_agent_config(agent_id, load_agent(agent_id), openclaw_skills, ROLE_KEYWORDS[agent_id])
    write_agent_config("codex", load_agent("codex"), codex_skills, CODEX_PROFESSIONAL)
    sync_html_fallback()
    print({"openclaw_skills": len(openclaw_skills), "codex_skills": len(codex_skills)})
    for agent_id in ["coordinator", "ops", "audit", "archive", "codex"]:
        cfg = json.loads((CONFIG_DIR / AGENT_FILES[agent_id]).read_text(encoding="utf-8"))
        print(agent_id, len(cfg["nodes"]) - 1, "skills", len(cfg["edges"]), "edges")


if __name__ == "__main__":
    main()
