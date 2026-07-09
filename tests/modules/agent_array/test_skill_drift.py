from __future__ import annotations

from feishu_stack.modules.agent_array.skill_tree.skill_drift import detect_drift
from feishu_stack.modules.agent_array.skill_tree.skill_registry import SkillEntry, SkillInventory


def _skill(source: str, version: str) -> SkillEntry:
    return SkillEntry(
        skill_id=f"{source}:shared-skill",
        name="Shared Skill",
        source=source,
        source_alias=source,
        version=version,
        path_hash=f"path-{source}",
        dir_hash=f"dir-{version}",
        mtime="2026-07-07T00:00:00+00:00",
        dependencies=[],
        description="shared",
        agent_visibility=["codex-code-agent"],
        category="tooling",
        status="active",
        size=100,
        path="shared-skill",
    )


def test_cross_runtime_hash_mismatch_is_p0() -> None:
    inventory = SkillInventory(
        skills=[
            _skill("lark-cli-home", "hash-a"),
            _skill("openclaw-npm", "hash-b"),
        ],
        total=2,
        by_source={"lark-cli-home": 1, "openclaw-npm": 1},
        by_agent={"codex-code-agent": 2},
        scan_metadata=None,
    )

    report = detect_drift(inventory, baseline={"skills": [skill.to_dict() for skill in inventory.skills]})

    cross_runtime = [item for item in report.drifts if item.category == "cross_runtime_mismatch"]
    assert len(cross_runtime) == 2
    assert {item.severity for item in cross_runtime} == {"P0"}
    assert report.p0_count == 2
