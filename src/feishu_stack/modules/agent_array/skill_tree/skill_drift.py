from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from feishu_stack.modules.agent_array.skill_tree.skill_registry import (
    SkillEntry,
    SkillInventory,
    get_inventory,
)


@dataclass
class DriftEntry:
    """A single drift finding."""

    drift_id: str
    skill_name: str
    severity: str  # P0 / P1 / P2 / info
    category: str  # version_mismatch / priority_missing / residue / no_baseline
    source: str
    source_alias: str
    message: str
    details: dict[str, Any]
    resolved: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "driftId": self.drift_id,
            "skillName": self.skill_name,
            "severity": self.severity,
            "category": self.category,
            "source": self.source,
            "sourceAlias": self.source_alias,
            "message": self.message,
            "details": self.details,
            "resolved": self.resolved,
        }


@dataclass
class DriftReport:
    """Complete drift analysis report."""

    generated_at: str
    drifts: list[DriftEntry]
    total_drifts: int
    p0_count: int
    p1_count: int
    p2_count: int
    info_count: int
    has_baseline: bool
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "generatedAt": self.generated_at,
            "drifts": [d.to_dict() for d in self.drifts],
            "totalDrifts": self.total_drifts,
            "p0Count": self.p0_count,
            "p1Count": self.p1_count,
            "p2Count": self.p2_count,
            "infoCount": self.info_count,
            "hasBaseline": self.has_baseline,
            "summary": self.summary,
        }


def _same_name_skills(inventory: SkillInventory) -> dict[str, list[SkillEntry]]:
    """Group skills by normalized name across sources."""
    groups: dict[str, list[SkillEntry]] = {}
    for skill in inventory.skills:
        key = skill.name.lower()
        groups.setdefault(key, []).append(skill)
    return {k: v for k, v in groups.items() if len(v) > 1}


def detect_drift(
    inventory: SkillInventory | None = None,
    *,
    baseline: dict[str, Any] | None = None,
) -> DriftReport:
    """Detect skill drift between actual state and baseline.

    Args:
        inventory: Current skill inventory (auto-scanned if None).
        baseline: Baseline snapshot dict from a previous confirmed state.
                   When None, all findings are severity="info" with
                   category="no_baseline".

    Returns:
        DriftReport with categorized drift findings.
    """
    inv = inventory or get_inventory()
    drifts: list[DriftEntry] = []
    now = datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------
    # No baseline case
    # ------------------------------------------------------------------
    if baseline is None:
        for skill in inv.skills:
            drifts.append(
                DriftEntry(
                    drift_id=f"no-baseline-{skill.skill_id}",
                    skill_name=skill.name,
                    severity="info",
                    category="no_baseline",
                    source=skill.source,
                    source_alias=skill.source_alias,
                    message=f"No baseline set for {skill.name} ({skill.source})",
                    details={
                        "skillId": skill.skill_id,
                        "version": skill.version,
                        "recommendation": "Run a full scan and confirm a baseline to enable drift detection.",
                    },
                )
            )
        return DriftReport(
            generated_at=now,
            drifts=drifts,
            total_drifts=len(drifts),
            p0_count=0,
            p1_count=0,
            p2_count=0,
            info_count=len(drifts),
            has_baseline=False,
            summary=f"No baseline set. {len(drifts)} skills need baseline confirmation.",
        )

    # ------------------------------------------------------------------
    # Baseline exists — compare
    # ------------------------------------------------------------------
    baseline_skills: dict[str, dict[str, Any]] = {}
    for entry in baseline.get("skills", []):
        if isinstance(entry, dict) and entry.get("skillId"):
            baseline_skills[entry["skillId"]] = entry

    actual_ids: set[str] = set()
    for skill in inv.skills:
        actual_ids.add(skill.skill_id)
        bs = baseline_skills.get(skill.skill_id)

        if bs is None:
            # Skill in actual but not in baseline — new/unbaselined
            continue

        # P0: version mismatch (content has changed)
        if bs.get("version") != skill.version:
            drifts.append(
                DriftEntry(
                    drift_id=f"version-mismatch-{skill.skill_id}",
                    skill_name=skill.name,
                    severity="P0",
                    category="version_mismatch",
                    source=skill.source,
                    source_alias=skill.source_alias,
                    message=f"Skill {skill.name} version changed since baseline",
                    details={
                        "skillId": skill.skill_id,
                        "baselineVersion": bs.get("version"),
                        "actualVersion": skill.version,
                        "baselineMtime": bs.get("mtime"),
                        "actualMtime": skill.mtime,
                        "recommendation": "Review changes and confirm or rollback.",
                    },
                )
            )

    # P1: loading priority — check if higher-priority source duplicates exist
    same_name_groups = _same_name_skills(inv)
    for name, group in same_name_groups.items():
        # If skills with same name exist in multiple sources, only one wins
        # The dedup already happened, so group should be size 1
        # But we can still flag that lower-priority versions were suppressed
        pass

    # P2: old version residue — skills in baseline but not in actual
    baseline_ids = set(baseline_skills.keys())
    residue_ids = baseline_ids - actual_ids
    for resid_id in residue_ids:
        bs = baseline_skills[resid_id]
        drifts.append(
            DriftEntry(
                drift_id=f"residue-{resid_id}",
                skill_name=bs.get("name", resid_id),
                severity="P2",
                category="residue",
                source=bs.get("source", "unknown"),
                source_alias=bs.get("sourceAlias", ""),
                message=f"Skill {bs.get('name', resid_id)} present in baseline but missing from actual scan",
                details={
                    "skillId": resid_id,
                    "baselineVersion": bs.get("version"),
                    "recommendation": "Skill may have been removed. Update baseline or restore the skill.",
                },
            )
        )

    # P0: cross-runtime content diff for same-named skills
    for name, skills in _same_name_skills(inv).items():
        versions = set(s.version for s in skills)
        if len(versions) > 1:
            for skill in skills:
                drifts.append(
                    DriftEntry(
                        drift_id=f"cross-runtime-{skill.skill_id}",
                        skill_name=skill.name,
                        severity="P0",
                        category="cross_runtime_mismatch",
                        source=skill.source,
                        source_alias=skill.source_alias,
                        message=f"Skill {skill.name} has different versions across runtimes",
                        details={
                            "skillId": skill.skill_id,
                            "version": skill.version,
                            "allVersions": sorted(versions),
                            "recommendation": "Ensure consistent skill versions across runtimes.",
                        },
                    )
                )

    # ------------------------------------------------------------------
    # Build report
    # ------------------------------------------------------------------
    severity_counts = {"P0": 0, "P1": 0, "P2": 0, "info": 0}
    for d in drifts:
        sev = d.severity
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    if drifts:
        summary_parts: list[str] = []
        if severity_counts["P0"]:
            summary_parts.append(f"{severity_counts['P0']} P0 (critical)")
        if severity_counts["P1"]:
            summary_parts.append(f"{severity_counts['P1']} P1 (warning)")
        if severity_counts["P2"]:
            summary_parts.append(f"{severity_counts['P2']} P2 (info)")
        summary_text = "Drift detected: " + ", ".join(summary_parts)
    else:
        summary_text = "No drift detected. All skills match baseline."

    return DriftReport(
        generated_at=now,
        drifts=drifts,
        total_drifts=len(drifts),
        p0_count=severity_counts["P0"],
        p1_count=severity_counts["P1"],
        p2_count=severity_counts["P2"],
        info_count=severity_counts["info"],
        has_baseline=True,
        summary=summary_text,
    )


def build_comparison(
    skill_id: str,
    inventory: SkillInventory | None = None,
) -> dict[str, Any]:
    """Build a cross-runtime comparison for a specific skill.

    Shows the skill's state across all runtimes where it appears,
    highlighting version differences.
    """
    inv = inventory or get_inventory()
    target_skill = None
    for skill in inv.skills:
        if skill.skill_id == skill_id:
            target_skill = skill
            break

    if target_skill is None:
        return {"skillId": skill_id, "found": False, "comparisons": []}

    # Find all skills with same name across runtimes
    comparisons: list[dict[str, Any]] = []
    for skill in inv.skills:
        if skill.name.lower() == target_skill.name.lower():
            comparisons.append(
                {
                    "skillId": skill.skill_id,
                    "source": skill.source,
                    "sourceAlias": skill.source_alias,
                    "version": skill.version,
                    "mtime": skill.mtime,
                    "size": skill.size,
                    "path": skill.path,
                    "status": skill.status,
                }
            )

    match = len(set(c["version"] for c in comparisons)) <= 1

    return {
        "skillId": skill_id,
        "found": True,
        "skillName": target_skill.name,
        "comparisons": comparisons,
        "match": match,
        "recommendation": (
            "All runtimes have consistent versions."
            if match
            else "Versions differ across runtimes. Review and synchronize."
        ),
    }
