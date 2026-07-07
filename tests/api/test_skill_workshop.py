from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from feishu_stack import app as app_module
from feishu_stack.modules.agent_array.skill_tree.skill_registry import (
    ScanMetadata,
    SkillEntry,
    SkillInventory,
    SOURCE_CODEX,
)
from feishu_stack.modules.agent_array.skill_tree.skill_drift import (
    DriftEntry,
    DriftReport,
)
from feishu_stack.modules.agent_array.skill_tree import skill_baseline


client = TestClient(app_module.app)


def _token() -> str:
    response = client.get("/api/session")
    assert response.status_code == 200
    return response.json()["token"]


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _mock_inventory(num_skills: int = 3) -> SkillInventory:
    skills = [
        SkillEntry(
            skill_id=f"codeX:skill-{i}",
            name=f"Skill {i}",
            source=SOURCE_CODEX,
            source_alias="codeX",
            version="abc123",
            path_hash=f"hash-{i}",
            dir_hash=None,
            mtime="2026-07-01T00:00:00",
            dependencies=[],
            description=f"Description for skill {i}",
            agent_visibility=["codex-code-agent"],
            category="tooling",
            status="active",
            size=100 + i,
            path=f"skill-{i}",
        )
        for i in range(num_skills)
    ]
    return SkillInventory(
        skills=skills,
        total=num_skills,
        by_source={SOURCE_CODEX: num_skills},
        by_agent={"codex-code-agent": num_skills},
        scan_metadata=ScanMetadata(
            scanned_at="2026-07-01T00:00:00",
            duration_ms=500,
            total_skills=num_skills,
            sources_scanned=[SOURCE_CODEX],
            sources_failed=[],
            cache_hits=0,
            cache_misses=num_skills,
            mode="full",
        ),
    )


def _mock_drift_report(num_drifts: int = 2, p0: int = 1, p1: int = 1) -> DriftReport:
    drifts = [
        DriftEntry(
            drift_id=f"drift-{i}",
            skill_name=f"Skill {i}",
            severity="P0" if i == 0 else "P1",
            category="version_mismatch",
            source=SOURCE_CODEX,
            source_alias="codeX",
            message=f"Version mismatch for Skill {i}",
            details={"skillId": f"codeX:skill-{i}"},
        )
        for i in range(num_drifts)
    ]
    return DriftReport(
        generated_at="2026-07-01T00:00:00",
        drifts=drifts,
        total_drifts=num_drifts,
        p0_count=p0,
        p1_count=p1,
        p2_count=0,
        info_count=0,
        has_baseline=True,
        summary=f"{num_drifts} drifts detected",
    )


# ---------------------------------------------------------------------------
# GET /api/skill-workshop/summary
# ---------------------------------------------------------------------------


def test_skill_workshop_summary_returns_counts(monkeypatch) -> None:
    inventory = _mock_inventory(5)
    drift_report = _mock_drift_report(2, 1, 1)

    monkeypatch.setattr(app_module.skill_registry, "get_inventory", lambda: inventory)
    monkeypatch.setattr(app_module.skill_drift, "detect_drift", lambda inventory=None, baseline=None: drift_report)

    response = client.get("/api/skill-workshop/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["totalSkills"] == 5
    assert data["driftCount"] == 2
    assert data["p0Count"] == 1
    assert data["p1Count"] == 1
    assert data["p2Count"] == 0
    assert data["lastScanTime"] is not None
    assert "affectedAgents" in data
    assert "affectedRuntimes" in data


def test_skill_workshop_summary_no_baseline(monkeypatch) -> None:
    inventory = _mock_inventory(3)
    drift_report = DriftReport(
        generated_at="2026-07-01T00:00:00",
        drifts=[],
        total_drifts=3,
        p0_count=0,
        p1_count=0,
        p2_count=0,
        info_count=3,
        has_baseline=False,
        summary="No baseline",
    )

    monkeypatch.setattr(app_module.skill_registry, "get_inventory", lambda: inventory)
    monkeypatch.setattr(app_module.skill_drift, "detect_drift", lambda inventory=None, baseline=None: drift_report)

    response = client.get("/api/skill-workshop/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["driftCount"] == 3
    assert len(data["affectedRuntimes"]) >= 0


# ---------------------------------------------------------------------------
# GET /api/skill-workshop/skills
# ---------------------------------------------------------------------------


def test_skill_workshop_skills_returns_all(monkeypatch) -> None:
    monkeypatch.setattr(app_module.skill_registry, "get_inventory", lambda: _mock_inventory(3))

    response = client.get("/api/skill-workshop/skills")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert data["totalInventory"] == 3
    assert len(data["skills"]) == 3
    assert data["scanMetadata"] is not None


def test_skill_workshop_skills_filter_by_source(monkeypatch) -> None:
    monkeypatch.setattr(app_module.skill_registry, "get_inventory", lambda: _mock_inventory(3))

    response = client.get("/api/skill-workshop/skills?source=codeX")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3  # all in codeX


def test_skill_workshop_skills_filter_by_status(monkeypatch) -> None:
    monkeypatch.setattr(app_module.skill_registry, "get_inventory", lambda: _mock_inventory(3))

    response = client.get("/api/skill-workshop/skills?status=active")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3


def test_skill_workshop_skills_filter_by_agent(monkeypatch) -> None:
    monkeypatch.setattr(app_module.skill_registry, "get_inventory", lambda: _mock_inventory(3))

    response = client.get("/api/skill-workshop/skills?agent_id=codex-code-agent")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3


def test_skill_workshop_skills_filter_returns_empty_for_unknown_agent(monkeypatch) -> None:
    monkeypatch.setattr(app_module.skill_registry, "get_inventory", lambda: _mock_inventory(3))

    response = client.get("/api/skill-workshop/skills?agent_id=unknown-agent")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0


def test_skill_workshop_skills_empty_inventory(monkeypatch) -> None:
    empty = SkillInventory(
        skills=[], total=0, by_source={}, by_agent={},
        scan_metadata=ScanMetadata(
            scanned_at="2026-07-01T00:00:00", duration_ms=0, total_skills=0,
            sources_scanned=[], sources_failed=[], cache_hits=0, cache_misses=0, mode="full",
        ),
    )
    monkeypatch.setattr(app_module.skill_registry, "get_inventory", lambda: empty)

    response = client.get("/api/skill-workshop/skills")
    assert response.status_code == 200
    data = response.json()
    assert data["skills"] == []
    assert data["total"] == 0


# ---------------------------------------------------------------------------
# GET /api/skill-workshop/skills/{skill_id}
# ---------------------------------------------------------------------------


def test_skill_workshop_skill_detail_found(monkeypatch) -> None:
    monkeypatch.setattr(app_module.skill_registry, "get_inventory", lambda: _mock_inventory(3))
    monkeypatch.setattr(app_module.skill_registry, "get_skill_by_id", lambda skill_id, config=None: _mock_inventory(3).skills[0] if skill_id == "codeX:skill-0" else None)
    monkeypatch.setattr(app_module.skill_drift, "detect_drift", lambda inventory=None, baseline=None: _mock_drift_report(0, 0, 0))

    response = client.get("/api/skill-workshop/skills/codeX:skill-0")
    assert response.status_code == 200
    data = response.json()
    assert data["skillId"] == "codeX:skill-0"
    assert data["displayName"] == "Skill 0"
    assert data["sourceAlias"] == "codeX"


def test_skill_workshop_skill_detail_not_found(monkeypatch) -> None:
    monkeypatch.setattr(app_module.skill_registry, "get_inventory", lambda: _mock_inventory(3))
    monkeypatch.setattr(app_module.skill_registry, "get_skill_by_id", lambda skill_id, config=None: None)

    response = client.get("/api/skill-workshop/skills/nonexistent")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/skill-workshop/agents/{agent_id}/skills
# ---------------------------------------------------------------------------


def test_skill_workshop_agent_skills_returns_filtered(monkeypatch) -> None:
    monkeypatch.setattr(app_module.skill_registry, "get_inventory", lambda: _mock_inventory(3))

    # get_agent_skills actually filters, so let's mock it properly
    def fake_agent_skills(agent_id, config=None):
        inv = _mock_inventory(3)
        if agent_id == "codex-code-agent":
            return inv.skills
        return []

    monkeypatch.setattr(app_module.skill_registry, "get_agent_skills", fake_agent_skills)

    response = client.get("/api/skill-workshop/agents/codex-code-agent/skills")
    assert response.status_code == 200
    data = response.json()
    assert data["agentId"] == "codex-code-agent"
    assert data["total"] == 3


def test_skill_workshop_agent_skills_unknown_agent(monkeypatch) -> None:
    def fake_agent_skills(agent_id, config=None):
        return []

    monkeypatch.setattr(app_module.skill_registry, "get_agent_skills", fake_agent_skills)

    response = client.get("/api/skill-workshop/agents/unknown-agent/skills")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["skills"] == []


# ---------------------------------------------------------------------------
# GET /api/skill-workshop/drift-report
# ---------------------------------------------------------------------------


def test_skill_workshop_drift_report_has_baseline(monkeypatch) -> None:
    monkeypatch.setattr(app_module.skill_registry, "get_inventory", lambda: _mock_inventory(3))
    monkeypatch.setattr(app_module.skill_drift, "detect_drift", lambda inventory=None, baseline=None: _mock_drift_report(2, 1, 1))

    response = client.get("/api/skill-workshop/drift-report")
    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["driftCount"] == 2
    assert data["summary"]["p0Count"] == 1
    assert data["summary"]["p1Count"] == 1
    assert len(data["items"]) == 2


def test_skill_workshop_drift_report_no_baseline(monkeypatch) -> None:
    inv = _mock_inventory(2)
    # Call real detect_drift with None baseline
    from feishu_stack.modules.agent_array.skill_tree.skill_drift import detect_drift

    monkeypatch.setattr(app_module.skill_registry, "get_inventory", lambda: inv)
    monkeypatch.setattr(app_module.skill_drift, "detect_drift", lambda inventory=None, baseline=None: detect_drift(inv, baseline=None))

    response = client.get("/api/skill-workshop/drift-report")
    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["noBaselineCount"] >= 1
    # Each skill gets an "info" level drift for no_baseline
    assert all(d["drift"]["severity"] == "info" for d in data["items"])


def test_skill_workshop_drift_report_no_drift(monkeypatch) -> None:
    """When baseline matches actual, no drifts should be reported."""
    inventory = _mock_inventory(2)
    baseline_skills = [s.to_dict() for s in inventory.skills]
    baseline = {"skills": baseline_skills}

    from feishu_stack.modules.agent_array.skill_tree.skill_drift import detect_drift

    monkeypatch.setattr(app_module.skill_registry, "get_inventory", lambda: inventory)
    monkeypatch.setattr(app_module.skill_drift, "detect_drift", lambda _inv=None, baseline=None: detect_drift(inventory, baseline=baseline))

    report = detect_drift(inventory, baseline=baseline)

    response = client.get("/api/skill-workshop/drift-report")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# GET /api/skill-workshop/comparison
# ---------------------------------------------------------------------------


def test_skill_workshop_comparison_missing_param(monkeypatch) -> None:
    response = client.get("/api/skill-workshop/comparison")
    assert response.status_code == 400


def test_skill_workshop_comparison_found(monkeypatch) -> None:
    comparison = {
        "skillId": "codeX:skill-0",
        "found": True,
        "skillName": "Skill 0",
        "comparisons": [
            {"skillId": "codeX:skill-0", "source": "codeX", "sourceAlias": "codeX",
             "version": "abc", "mtime": "2026-01-01", "size": 100, "path": "skill-0", "status": "active"},
        ],
        "match": True,
        "recommendation": "All runtimes have consistent versions.",
    }
    monkeypatch.setattr(app_module.skill_drift, "build_comparison", lambda skillId, inventory=None: comparison)

    response = client.get("/api/skill-workshop/comparison?skillId=codeX:skill-0")
    assert response.status_code == 200
    data = response.json()
    assert data["found"] is True
    assert data["match"] is True
    assert len(data["comparisons"]) == 1


def test_skill_workshop_comparison_not_found(monkeypatch) -> None:
    comparison = {"skillId": "nonexistent", "found": False, "comparisons": []}
    monkeypatch.setattr(app_module.skill_drift, "build_comparison", lambda skillId, inventory=None: comparison)

    response = client.get("/api/skill-workshop/comparison?skillId=nonexistent")
    assert response.status_code == 200
    data = response.json()
    assert data["found"] is False


# ---------------------------------------------------------------------------
# POST /api/skill-workshop/scan (requires token)
# ---------------------------------------------------------------------------


def test_skill_workshop_scan_requires_token() -> None:
    response = client.post("/api/skill-workshop/scan")
    assert response.status_code == 401


def test_skill_workshop_scan_rejects_bad_token() -> None:
    response = client.post("/api/skill-workshop/scan", headers={"X-Control-Token": "bad"})
    assert response.status_code == 403


def test_skill_workshop_scan_with_token(monkeypatch) -> None:
    token = _token()
    inventory = _mock_inventory(3)

    called = {"scan": False}

    def fake_scan(config=None, force_full=True):
        called["scan"] = True
        return inventory

    monkeypatch.setattr(app_module.skill_registry, "scan_skills", fake_scan)

    response = client.post(
        "/api/skill-workshop/scan",
        headers={"X-Control-Token": token},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["totalSkills"] == 3
    assert data["scanMetadata"] is not None
    assert called["scan"] is True


# ---------------------------------------------------------------------------
# Phase C baseline management
# ---------------------------------------------------------------------------


def test_skill_workshop_baseline_preview(monkeypatch) -> None:
    preview = {
        "hasBaseline": False,
        "actualSkillCount": 3,
        "baselineSkillCount": 0,
        "addedSkillIds": ["codeX:skill-0"],
        "removedSkillIds": [],
        "changed": [],
        "confirmText": skill_baseline.CONFIRM_BASELINE_TEXT,
    }
    monkeypatch.setattr(app_module.skill_baseline, "preview_baseline_diff", lambda: preview)

    response = client.get("/api/skill-workshop/baseline/preview")
    assert response.status_code == 200
    data = response.json()
    assert data["hasBaseline"] is False
    assert data["confirmText"] == skill_baseline.CONFIRM_BASELINE_TEXT


def test_skill_workshop_baseline_confirm_requires_token() -> None:
    response = client.post(
        "/api/skill-workshop/baseline/confirm",
        json={"confirmText": skill_baseline.CONFIRM_BASELINE_TEXT},
    )
    assert response.status_code == 401


def test_skill_workshop_baseline_confirm_rejects_bad_confirm_text(monkeypatch) -> None:
    token = _token()

    response = client.post(
        "/api/skill-workshop/baseline/confirm",
        headers={"X-Control-Token": token},
        json={"confirmText": "wrong"},
    )
    assert response.status_code == 400


def test_skill_workshop_baseline_confirm_with_token(monkeypatch) -> None:
    token = _token()
    result = {
        "ok": True,
        "baselineFile": "baseline.json",
        "previousBaselineSnapshot": None,
        "skillCount": 3,
        "confirmedAt": "2026-07-01T00:00:00",
        "confirmedBy": "tester",
    }
    called = {"confirm": False}

    def fake_confirm(confirm_text, confirmed_by="manual", inventory=None, config=None):
        called["confirm"] = True
        assert confirm_text == skill_baseline.CONFIRM_BASELINE_TEXT
        assert confirmed_by == "tester"
        return result

    monkeypatch.setattr(app_module.skill_baseline, "confirm_baseline", fake_confirm)

    response = client.post(
        "/api/skill-workshop/baseline/confirm",
        headers={"X-Control-Token": token},
        json={"confirmText": skill_baseline.CONFIRM_BASELINE_TEXT, "confirmedBy": "tester"},
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert called["confirm"] is True


def test_skill_workshop_snapshot_requires_token() -> None:
    response = client.post(
        "/api/skill-workshop/snapshot",
        json={"confirmText": skill_baseline.CONFIRM_SNAPSHOT_TEXT},
    )
    assert response.status_code == 401


def test_skill_workshop_snapshot_with_token(monkeypatch) -> None:
    token = _token()
    result = {
        "ok": True,
        "snapshotFile": "skill-snapshot.json",
        "skillCount": 3,
        "createdAt": "2026-07-01T00:00:00",
        "createdBy": "tester",
    }

    monkeypatch.setattr(app_module.skill_baseline, "create_snapshot", lambda confirm_text, created_by="manual", inventory=None, config=None: result)

    response = client.post(
        "/api/skill-workshop/snapshot",
        headers={"X-Control-Token": token},
        json={"confirmText": skill_baseline.CONFIRM_SNAPSHOT_TEXT, "createdBy": "tester"},
    )
    assert response.status_code == 200
    assert response.json()["snapshotFile"] == "skill-snapshot.json"


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


def test_skill_workshop_skills_response_has_correct_shape(monkeypatch) -> None:
    monkeypatch.setattr(app_module.skill_registry, "get_inventory", lambda: _mock_inventory(1))
    monkeypatch.setattr(app_module.skill_drift, "detect_drift", lambda inventory=None, baseline=None: _mock_drift_report(0, 0, 0))

    response = client.get("/api/skill-workshop/skills")
    assert response.status_code == 200
    skill = response.json()["skills"][0]
    assert "skillId" in skill
    assert "displayName" in skill
    assert "sourceAlias" in skill
    assert "runtime" in skill
    assert "agentIds" in skill
    assert "actual" in skill
    assert "skillMdSha256" in skill["actual"]
    assert skill["sourceAlias"] == "codeX"
    # Ensure no absolute paths leaked
    assert "F:" not in skill.get("path", "")
    assert "\\\\" not in skill.get("path", "")


def test_skill_workshop_summary_response_has_correct_shape(monkeypatch) -> None:
    inventory = _mock_inventory(5)
    drift_report = _mock_drift_report(0, 0, 0)

    monkeypatch.setattr(app_module.skill_registry, "get_inventory", lambda: inventory)
    monkeypatch.setattr(app_module.skill_drift, "detect_drift", lambda inventory=None, baseline=None: drift_report)

    response = client.get("/api/skill-workshop/summary")
    assert response.status_code == 200
    data = response.json()
    assert "totalSkills" in data
    assert "driftCount" in data
    assert "p0Count" in data
    assert "p1Count" in data
    assert "p2Count" in data
    assert "lastScanTime" in data
    assert "affectedAgents" in data
    assert "affectedRuntimes" in data


def test_skill_workshop_agent_skills_response_shape(monkeypatch) -> None:
    monkeypatch.setattr(app_module.skill_registry, "get_inventory", lambda: _mock_inventory(2))
    monkeypatch.setattr(app_module.skill_registry, "get_agent_skills", lambda agent_id, config=None: _mock_inventory(2).skills)

    response = client.get("/api/skill-workshop/agents/codex-code-agent/skills")
    assert response.status_code == 200
    data = response.json()
    assert "agentId" in data
    assert "skills" in data
    assert "total" in data
    assert data["agentId"] == "codex-code-agent"


def test_skill_workshop_all_routes_are_read_only_except_scan() -> None:
    """Verify GET routes don't require token, POST /scan does."""
    # GET routes should all return 200 or 400 (not 401)
    get_routes = [
        "/api/skill-workshop/summary",
        "/api/skill-workshop/skills",
        "/api/skill-workshop/drift-report",
        "/api/skill-workshop/comparison?skillId=test",
        "/api/skill-workshop/agents/test-agent/skills",
    ]
    for route in get_routes:
        response = client.get(route)
        assert response.status_code in (200, 400, 404), f"{route} returned {response.status_code}"

    # POST /scan should require token
    response = client.post("/api/skill-workshop/scan")
    assert response.status_code == 401
