from __future__ import annotations

from fastapi import APIRouter
from feishu_stack.plugin_sdk import AccPlugin, PluginCard
from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel
from feishu_stack.modules.agent_array.skill_tree import agent_config_editor, agent_dashboard, skill_baseline, skill_registry, skill_drift, tree_config
from feishu_stack.core.models import to_dict
from feishu_stack.api.security import require_control_token

DASHBOARD_TAG = "Dashboard"
SKILL_WORKSHOP_TAG = "Skill Workshop"
router = APIRouter()

class AgentEditableConfigUpdateRequest(BaseModel):
    values: dict


class SkillBaselineConfirmRequest(BaseModel):
    confirmText: str
    confirmedBy: str = "manual"


class SkillSnapshotRequest(BaseModel):
    confirmText: str
    createdBy: str = "manual"


class SkillRollbackRequest(BaseModel):
    confirmText: str
    confirmedBy: str = "manual"


@router.get(
    "/api/agents",
    summary="Agent inventory",
    description="Return the v1 read-only agent inventory used by the command dashboard.",
    tags=[DASHBOARD_TAG],
)
def agents() -> dict:
    return {"agents": to_dict(agent_dashboard.list_agents())}


@router.get(
    "/api/agents/{agent_id}",
    summary="Agent detail",
    description="Return a single read-only agent configuration summary.",
    tags=[DASHBOARD_TAG],
)
def agent_detail(agent_id: str) -> dict:
    agent = agent_dashboard.get_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Unknown agent: {agent_id}")
    return to_dict(agent)


@router.get(
    "/api/agents/{agent_id}/editable-config",
    summary="Editable agent config",
    description="Return safe, editable configuration fields for a real agent.",
    tags=[DASHBOARD_TAG],
)
def agent_editable_config(agent_id: str) -> dict:
    try:
        return agent_config_editor.get_editable_config(agent_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/api/agents/{agent_id}/config-preview",
    summary="Agent config preview",
    description="Return current safe config values and editing notes.",
    tags=[DASHBOARD_TAG],
)
def agent_config_preview(agent_id: str) -> dict:
    try:
        return agent_config_editor.preview_config(agent_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put(
    "/api/agents/{agent_id}/editable-config",
    summary="Update editable agent config",
    description="Update whitelisted low-risk config fields. Requires control token.",
    tags=[DASHBOARD_TAG],
    dependencies=[Depends(require_control_token)],
)
def update_agent_editable_config(agent_id: str, request: AgentEditableConfigUpdateRequest) -> dict:
    try:
        return agent_config_editor.update_editable_config(agent_id, request.values)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/api/agents/{agent_id}/config-backup",
    summary="Backup agent config",
    description="Create a backup for the editable config file. Requires control token.",
    tags=[DASHBOARD_TAG],
    dependencies=[Depends(require_control_token)],
)
def backup_agent_config(agent_id: str) -> dict:
    try:
        return agent_config_editor.backup_config(agent_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/api/agents/{agent_id}/config-rollback-latest",
    summary="Rollback latest agent config backup",
    description="Restore the latest backup for the editable config file. Requires control token.",
    tags=[DASHBOARD_TAG],
    dependencies=[Depends(require_control_token)],
)
def rollback_agent_config(agent_id: str) -> dict:
    try:
        return agent_config_editor.rollback_latest(agent_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _to_workshop_skill(entry: skill_registry.SkillEntry, report: skill_drift.DriftReport | None = None) -> dict:
    """Transform a SkillEntry into the frontend SkillWorkshopSkill shape."""
    drift_status: str = "ok"
    drift_severity: str = "normal"
    drift_reasons: list[str] = []
    baseline_sha: str | None = None
    baseline_dir_sha: str | None = None
    baseline_version: str | None = None
    confirmed_at: str | None = None
    confirmed_by: str | None = None

    if report is not None:
        for d in report.drifts:
            raw = d.to_dict()
            if raw.get("details", {}).get("skillId") == entry.skill_id:
                drift_status = "drift" if d.severity in ("P0", "P1", "P2") else "no_baseline"
                drift_severity = {"P0": "critical", "P1": "warning", "P2": "warning", "info": "info"}.get(d.severity, "normal")
                drift_reasons.append(d.message)

    baseline_entry = _baseline_for_skill(entry.skill_id)
    if baseline_entry:
        baseline_info = baseline_entry.get("baseline", {})
        baseline_sha = baseline_info.get("skillMdSha256") or baseline_entry.get("version")
        baseline_dir_sha = baseline_info.get("directorySha256") or baseline_entry.get("dirHash")
        baseline_version = baseline_info.get("version") or baseline_entry.get("version")
        confirmed_at = baseline_info.get("confirmedAt")
        confirmed_by = baseline_info.get("confirmedBy")

    return {
        "skillId": entry.skill_id,
        "displayName": entry.name,
        "sourceAlias": entry.source_alias,
        "runtime": entry.source,
        "agentIds": entry.agent_visibility,
        "relativePath": entry.path,
        "loadPriority": 0,
        "updateMechanism": "manual",
        "actual": {
            "skillMdSha256": entry.version,
            "directorySha256": entry.dir_hash or "",
            "mtime": entry.mtime or "",
            "version": entry.version,
        },
        "baseline": {
            "skillMdSha256": baseline_sha or "",
            "directorySha256": baseline_dir_sha or "",
            "version": baseline_version or "",
            "confirmedAt": confirmed_at,
            "confirmedBy": confirmed_by,
        },
        "drift": {
            "status": drift_status,
            "severity": drift_severity,
            "reasons": drift_reasons,
        },
    }


def _baseline_for_skill(skill_id: str) -> dict | None:
    baseline = skill_baseline.load_baseline()
    if not baseline:
        return None
    for entry in baseline.get("skills", []):
        if isinstance(entry, dict) and entry.get("skillId") == skill_id:
            return entry
    return None


def _to_drift_report_dict(report: skill_drift.DriftReport, inventory: skill_registry.SkillInventory) -> dict:
    """Transform a DriftReport into the frontend SkillDriftReport shape."""
    items: list[dict] = []
    for d in report.drifts:
        raw = d.to_dict()
        sev = d.severity
        drift_status = "drift" if sev in ("P0", "P1", "P2") else "no_baseline"
        drift_severity = {"P0": "critical", "P1": "warning", "P2": "warning", "info": "info"}.get(sev, "normal")
        details = raw.get("details", {})
        actual_hash = details.get("actualVersion", details.get("version", ""))
        baseline_hash = details.get("baselineVersion")
        suggestion = details.get("recommendation", d.message)
        items.append({
            "skillId": raw.get("skillId", details.get("skillId", "")),
            "displayName": d.skill_name,
            "sourceAlias": d.source_alias,
            "runtime": d.source,
            "drift": {
                "status": drift_status,
                "severity": drift_severity,
                "reasons": [d.message],
            },
            "actualHash": actual_hash,
            "baselineHash": baseline_hash,
            "suggestion": suggestion,
        })
    return {
        "generatedAt": report.generated_at,
        "summary": {
            "totalSkills": inventory.total,
            "driftCount": report.total_drifts,
            "noBaselineCount": report.info_count,
            "p0Count": report.p0_count,
            "p1Count": report.p1_count,
            "p2Count": report.p2_count,
        },
        "items": items,
    }


@router.get(
    "/api/skill-workshop/summary",
    summary="Skill workshop summary",
    description="Return skill counts, drift counts, P0/P1/P2, and last scan time.",
    tags=[SKILL_WORKSHOP_TAG],
)
def skill_workshop_summary() -> dict:
    inventory = skill_registry.get_inventory()
    report = skill_drift.detect_drift(inventory, baseline=skill_baseline.load_baseline())
    affected_agents = sorted(inventory.by_agent.keys()) if inventory.by_agent else []
    affected_runtimes = sorted(inventory.by_source.keys()) if inventory.by_source else []
    return {
        "totalSkills": inventory.total,
        "driftCount": report.total_drifts,
        "p0Count": report.p0_count,
        "p1Count": report.p1_count,
        "p2Count": report.p2_count,
        "lastScanTime": inventory.scan_metadata.scanned_at if inventory.scan_metadata else None,
        "affectedAgents": len(affected_agents),
        "affectedRuntimes": affected_runtimes,
    }


@router.get(
    "/api/skill-workshop/skills",
    summary="Skill inventory",
    description="Return the full skill inventory. Supports filtering by "
    "?agent_id=, ?runtime=, ?source=, ?status=.",
    tags=[SKILL_WORKSHOP_TAG],
)
def skill_workshop_skills(
    agent_id: str | None = None,
    runtime: str | None = None,
    source: str | None = None,
    status: str | None = None,
) -> dict:
    inventory = skill_registry.get_inventory()
    report = skill_drift.detect_drift(inventory, baseline=skill_baseline.load_baseline())
    skills = inventory.skills

    if agent_id:
        skills = [s for s in skills if agent_id in s.agent_visibility]
    if runtime:
        skills = [s for s in skills if s.source == runtime]
    if source:
        skills = [s for s in skills if s.source == source]
    if status:
        skills = [s for s in skills if s.status == status]

    return {
        "skills": [_to_workshop_skill(s, report) for s in skills],
        "total": len(skills),
        "totalInventory": inventory.total,
        "scanMetadata": inventory.scan_metadata.to_dict() if inventory.scan_metadata else None,
    }


@router.get(
    "/api/skill-workshop/tree-config",
    summary="Configured skill tree",
    description="Return the configured per-agent skill tree graph used by the integrated workshop page.",
    tags=[SKILL_WORKSHOP_TAG],
)
def skill_workshop_tree_config() -> dict:
    return tree_config.load_all_tree_configs()


@router.get(
    "/api/skill-workshop/tree-config/{agent_id}",
    summary="Configured agent skill tree",
    description="Return one configured agent skill tree graph.",
    tags=[SKILL_WORKSHOP_TAG],
)
def skill_workshop_agent_tree_config(agent_id: str) -> dict:
    try:
        return tree_config.load_agent_tree(agent_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown skill tree agent: {agent_id}") from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/api/skill-workshop/skills/{skill_id}",
    summary="Skill detail",
    description="Return a single skill's details.",
    tags=[SKILL_WORKSHOP_TAG],
)
def skill_workshop_skill_detail(skill_id: str) -> dict:
    skill = skill_registry.get_skill_by_id(skill_id)
    if skill is None:
        raise HTTPException(status_code=404, detail=f"Unknown skill: {skill_id}")
    report = skill_drift.detect_drift(baseline=skill_baseline.load_baseline())
    return _to_workshop_skill(skill, report)


@router.get(
    "/api/skill-workshop/agents/{agent_id}/skills",
    summary="Agent skills",
    description="Return skills visible to a specific agent.",
    tags=[SKILL_WORKSHOP_TAG],
)
def skill_workshop_agent_skills(agent_id: str) -> dict:
    skills = skill_registry.get_agent_skills(agent_id)
    report = skill_drift.detect_drift(baseline=skill_baseline.load_baseline())
    return {"agentId": agent_id, "skills": [_to_workshop_skill(s, report) for s in skills], "total": len(skills)}


@router.get(
    "/api/skill-workshop/drift-report",
    summary="Drift report",
    description="Return the current skill drift report.",
    tags=[SKILL_WORKSHOP_TAG],
)
def skill_workshop_drift_report() -> dict:
    inventory = skill_registry.get_inventory()
    report = skill_drift.detect_drift(inventory, baseline=skill_baseline.load_baseline())
    return _to_drift_report_dict(report, inventory)


@router.get(
    "/api/skill-workshop/baseline/preview",
    summary="Baseline diff preview",
    description="Preview the changes that confirming the current scan as baseline would make.",
    tags=[SKILL_WORKSHOP_TAG],
)
def skill_workshop_baseline_preview() -> dict:
    return skill_baseline.preview_baseline_diff()


@router.post(
    "/api/skill-workshop/baseline/confirm",
    summary="Confirm skill baseline",
    description="Persist the current skill inventory as the manual baseline. Requires control token and confirmText.",
    tags=[SKILL_WORKSHOP_TAG],
    dependencies=[Depends(require_control_token)],
)
def skill_workshop_baseline_confirm(request: SkillBaselineConfirmRequest) -> dict:
    try:
        return skill_baseline.confirm_baseline(
            confirm_text=request.confirmText,
            confirmed_by=request.confirmedBy,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/api/skill-workshop/snapshot",
    summary="Create skill snapshot",
    description="Create a skill inventory snapshot without changing baseline. Requires control token and confirmText.",
    tags=[SKILL_WORKSHOP_TAG],
    dependencies=[Depends(require_control_token)],
)
def skill_workshop_snapshot(request: SkillSnapshotRequest) -> dict:
    try:
        return skill_baseline.create_snapshot(
            confirm_text=request.confirmText,
            created_by=request.createdBy,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/api/skill-workshop/history",
    summary="Skill workshop version history",
    description="List baseline changes and skill inventory snapshots.",
    tags=[SKILL_WORKSHOP_TAG],
)
def skill_workshop_history() -> dict:
    return skill_baseline.list_history()


@router.get(
    "/api/skill-workshop/history/{version_id}",
    summary="Skill workshop version detail",
    description="Return the stored skill state for a baseline or snapshot version.",
    tags=[SKILL_WORKSHOP_TAG],
)
def skill_workshop_history_detail(version_id: str) -> dict:
    try:
        return skill_baseline.get_version(version_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/api/skill-workshop/compare",
    summary="Skill workshop version diff",
    description="Compare two stored skill workshop versions.",
    tags=[SKILL_WORKSHOP_TAG],
)
def skill_workshop_compare(from_: str = Query(default="", alias="from"), to: str = "") -> dict:
    if not from_:
        raise HTTPException(status_code=400, detail="Query parameter 'from' is required.")
    if not to:
        raise HTTPException(status_code=400, detail="Query parameter 'to' is required.")
    try:
        return skill_baseline.compare_versions(from_, to)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/api/skill-workshop/rollback/{version_id}",
    summary="Rollback skill workshop baseline",
    description="Rollback workshop baseline state to a stored version. Requires control token and confirmText.",
    tags=[SKILL_WORKSHOP_TAG],
    dependencies=[Depends(require_control_token)],
)
def skill_workshop_rollback(version_id: str, request: SkillRollbackRequest) -> dict:
    try:
        return skill_baseline.rollback_to_version(
            version_id,
            confirm_text=request.confirmText,
            confirmed_by=request.confirmedBy,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/api/skill-workshop/comparison",
    summary="Cross-runtime comparison",
    description="Compare a skill's versions across different runtimes.",
    tags=[SKILL_WORKSHOP_TAG],
)
def skill_workshop_comparison(skillId: str = "") -> dict:
    if not skillId:
        raise HTTPException(status_code=400, detail="Query parameter 'skillId' is required.")
    return skill_drift.build_comparison(skillId)


@router.post(
    "/api/skill-workshop/scan",
    summary="Trigger skill scan",
    description="Trigger a read-only skill scan. Requires control token.",
    tags=[SKILL_WORKSHOP_TAG],
    dependencies=[Depends(require_control_token)],
)
def skill_workshop_scan() -> dict:
    inventory = skill_registry.scan_skills(force_full=True)
    return {
        "ok": True,
        "totalSkills": inventory.total,
        "scanMetadata": inventory.scan_metadata.to_dict() if inventory.scan_metadata else None,
    }

def create_plugin() -> AccPlugin:
    return AccPlugin(id='acc.agent-array', name='Agent 阵列', version='1.0.0', description='Agent 阵列', requires=('acc.framework',), capabilities=('agents.read', 'skills.manage'), cards=(PluginCard('acc.agent-array.overview', 'Agent 阵列', 'Agent 阵列', 'agents', icon='swords', order=20),), router_factory=lambda: router)
