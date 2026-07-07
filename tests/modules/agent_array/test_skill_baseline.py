from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from feishu_stack.modules.agent_array.skill_tree import skill_baseline
from tests.api.test_skill_workshop import _mock_inventory


def _cfg(tmp_path):
    return SimpleNamespace(runtime_dir=tmp_path)


def test_confirm_baseline_requires_confirm_text(tmp_path) -> None:
    with pytest.raises(ValueError):
        skill_baseline.confirm_baseline(
            confirm_text="wrong",
            inventory=_mock_inventory(1),
            config=_cfg(tmp_path),
        )


def test_confirm_baseline_writes_schema_and_skills(tmp_path) -> None:
    result = skill_baseline.confirm_baseline(
        confirm_text=skill_baseline.CONFIRM_BASELINE_TEXT,
        confirmed_by="tester",
        inventory=_mock_inventory(2),
        config=_cfg(tmp_path),
    )

    assert result["ok"] is True
    assert result["skillCount"] == 2
    path = skill_baseline.baseline_path(_cfg(tmp_path))
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["schemaVersion"] == 1
    assert data["confirmedBy"] == "tester"
    assert len(data["skills"]) == 2
    assert data["skills"][0]["baseline"]["confirmedBy"] == "tester"


def test_confirm_baseline_backs_up_existing_baseline(tmp_path) -> None:
    cfg = _cfg(tmp_path)
    skill_baseline.confirm_baseline(
        confirm_text=skill_baseline.CONFIRM_BASELINE_TEXT,
        inventory=_mock_inventory(1),
        config=cfg,
    )
    result = skill_baseline.confirm_baseline(
        confirm_text=skill_baseline.CONFIRM_BASELINE_TEXT,
        inventory=_mock_inventory(2),
        config=cfg,
    )

    assert result["previousBaselineSnapshot"] is not None
    assert (skill_baseline.snapshots_dir(cfg) / result["previousBaselineSnapshot"]).is_file()


def test_preview_baseline_diff_reports_added_removed_changed(tmp_path) -> None:
    cfg = _cfg(tmp_path)
    base_inv = _mock_inventory(1)
    skill_baseline.confirm_baseline(
        confirm_text=skill_baseline.CONFIRM_BASELINE_TEXT,
        inventory=base_inv,
        config=cfg,
    )
    next_inv = _mock_inventory(2)
    next_inv.skills[0].version = "changed"

    preview = skill_baseline.preview_baseline_diff(next_inv, config=cfg)

    assert preview["hasBaseline"] is True
    assert preview["baselineSkillCount"] == 1
    assert preview["actualSkillCount"] == 2
    assert preview["addedSkillIds"] == ["codeX:skill-1"]
    assert preview["changed"][0]["skillId"] == "codeX:skill-0"


def test_create_snapshot_writes_inventory_without_changing_baseline(tmp_path) -> None:
    cfg = _cfg(tmp_path)
    result = skill_baseline.create_snapshot(
        confirm_text=skill_baseline.CONFIRM_SNAPSHOT_TEXT,
        created_by="tester",
        inventory=_mock_inventory(2),
        config=cfg,
    )

    assert result["ok"] is True
    assert result["skillCount"] == 2
    assert (skill_baseline.snapshots_dir(cfg) / result["snapshotFile"]).is_file()
    assert skill_baseline.load_baseline(cfg) is None


def test_history_lists_current_baseline_and_snapshots(tmp_path) -> None:
    cfg = _cfg(tmp_path)
    skill_baseline.confirm_baseline(
        confirm_text=skill_baseline.CONFIRM_BASELINE_TEXT,
        inventory=_mock_inventory(1),
        config=cfg,
    )
    skill_baseline.create_snapshot(
        confirm_text=skill_baseline.CONFIRM_SNAPSHOT_TEXT,
        inventory=_mock_inventory(2),
        config=cfg,
    )

    history = skill_baseline.list_history(cfg)

    assert history["total"] == 2
    assert {item["type"] for item in history["versions"]} == {"baseline-current", "snapshot"}


def test_compare_versions_reports_added_and_changed(tmp_path) -> None:
    cfg = _cfg(tmp_path)
    base_inv = _mock_inventory(1)
    skill_baseline.confirm_baseline(
        confirm_text=skill_baseline.CONFIRM_BASELINE_TEXT,
        inventory=base_inv,
        config=cfg,
    )
    next_inv = _mock_inventory(2)
    next_inv.skills[0].version = "changed"
    snapshot = skill_baseline.create_snapshot(
        confirm_text=skill_baseline.CONFIRM_SNAPSHOT_TEXT,
        inventory=next_inv,
        config=cfg,
    )
    snapshot_id = snapshot["snapshotFile"].removesuffix(".json")

    diff = skill_baseline.compare_versions("baseline-current", snapshot_id, cfg)

    assert diff["summary"] == {"added": 1, "removed": 0, "changed": 1}
    assert diff["addedSkillIds"] == ["codeX:skill-1"]
    assert diff["changed"][0]["skillId"] == "codeX:skill-0"


def test_rollback_to_snapshot_requires_confirm_text(tmp_path) -> None:
    cfg = _cfg(tmp_path)
    snapshot = skill_baseline.create_snapshot(
        confirm_text=skill_baseline.CONFIRM_SNAPSHOT_TEXT,
        inventory=_mock_inventory(1),
        config=cfg,
    )

    with pytest.raises(ValueError):
        skill_baseline.rollback_to_version(
            snapshot["snapshotFile"].removesuffix(".json"),
            confirm_text="wrong",
            config=cfg,
        )


def test_rollback_to_snapshot_writes_baseline_and_backs_up_current(tmp_path) -> None:
    cfg = _cfg(tmp_path)
    skill_baseline.confirm_baseline(
        confirm_text=skill_baseline.CONFIRM_BASELINE_TEXT,
        inventory=_mock_inventory(1),
        config=cfg,
    )
    next_inv = _mock_inventory(2)
    snapshot = skill_baseline.create_snapshot(
        confirm_text=skill_baseline.CONFIRM_SNAPSHOT_TEXT,
        inventory=next_inv,
        config=cfg,
    )

    result = skill_baseline.rollback_to_version(
        snapshot["snapshotFile"].removesuffix(".json"),
        confirm_text=skill_baseline.CONFIRM_ROLLBACK_TEXT,
        confirmed_by="tester",
        config=cfg,
    )

    assert result["ok"] is True
    assert result["previousBaselineSnapshot"] is not None
    baseline = skill_baseline.load_baseline(cfg)
    assert baseline is not None
    assert baseline["skillCount"] == 2
    assert baseline["confirmedBy"] == "tester"
