from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from feishu_stack.modules.agent_array.skill_tree.skill_registry import (
    AGENT_VISIBILITY_MAP,
    CACHE_MAX_AGE_S,
    SOURCE_CODEX,
    SOURCE_LARK_CLI,
    SOURCE_OPENCLAW_NPM,
    SOURCE_PRIORITY,
    SkillEntry,
    SkillInventory,
    _collect_skills_in_dir,
    _deduplicate,
    _dir_sha256,
    _file_sha256,
    _parse_skill_md,
    _resolve_source_dirs,
    _save_cache,
    _sha256_hex,
    get_agent_skills,
    get_inventory,
    get_skill_by_id,
    scan_skills,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_skill_dir(parent: Path, name: str, description: str = "", dependencies: list[str] | None = None) -> Path:
    """Create a fake skill directory with a SKILL.md file."""
    skill_dir = parent / name
    skill_dir.mkdir(parents=True)
    deps_str = ""
    if dependencies:
        deps_str = f"dependencies: {', '.join(dependencies)}\n"

    content = f"# {name.replace('-', ' ').title()}\n\n---\ndescription: \"{description or f'Skill for {name}'}\"\n{deps_str}category: tooling\n---\n\nThis is the {name} skill.\n"
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
    return skill_dir


def _make_skill_dir_with_subfile(parent: Path, name: str) -> Path:
    """Create a fake skill directory with SKILL.md and additional files."""
    skill_dir = parent / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(f"# {name}\n\nA skill.\n", encoding="utf-8")
    (skill_dir / "helpers.py").write_text("def helper(): pass\n", encoding="utf-8")
    (skill_dir / "config.json").write_text('{"version": 1}', encoding="utf-8")
    return skill_dir


def _mock_config(tmp_path: Path):
    """Create a minimal mock StackConfig for testing."""
    from types import SimpleNamespace

    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(parents=True)

    return SimpleNamespace(
        stack_root=tmp_path,
        runtime_dir=runtime_dir,
    )


# ---------------------------------------------------------------------------
# Hash tests
# ---------------------------------------------------------------------------


def test_sha256_hex_produces_64_char_hex() -> None:
    result = _sha256_hex(b"hello")
    assert len(result) == 64
    assert all(c in "0123456789abcdef" for c in result)


def test_file_sha256_consistent(tmp_path: Path) -> None:
    f = tmp_path / "test.txt"
    f.write_text("consistent content", encoding="utf-8")
    h1 = _file_sha256(f)
    h2 = _file_sha256(f)
    assert h1 == h2
    assert len(h1) == 64


def test_file_sha256_detects_change(tmp_path: Path) -> None:
    f = tmp_path / "test.txt"
    f.write_text("original", encoding="utf-8")
    h1 = _file_sha256(f)
    f.write_text("changed", encoding="utf-8")
    h2 = _file_sha256(f)
    assert h1 != h2


def test_dir_sha256_returns_none_for_file(tmp_path: Path) -> None:
    f = tmp_path / "not_a_dir.txt"
    f.write_text("data", encoding="utf-8")
    assert _dir_sha256(f) is None


def test_dir_sha256_empty_dir(tmp_path: Path) -> None:
    d = tmp_path / "empty"
    d.mkdir()
    result = _dir_sha256(d)
    assert result is not None
    assert len(result) == 64


def test_dir_sha256_detects_file_change(tmp_path: Path) -> None:
    d = tmp_path / "skills"
    d.mkdir()
    (d / "a.txt").write_text("data1", encoding="utf-8")
    h1 = _dir_sha256(d)
    (d / "a.txt").write_text("data2", encoding="utf-8")
    h2 = _dir_sha256(d)
    assert h1 != h2


# ---------------------------------------------------------------------------
# SKILL.md parsing
# ---------------------------------------------------------------------------


def test_parse_skill_md_extracts_name(tmp_path: Path) -> None:
    skill_dir = _make_skill_dir(tmp_path, "test-skill", description="A test skill")
    result = _parse_skill_md(skill_dir)
    assert result["name"] == "Test Skill"


def test_parse_skill_md_extracts_description(tmp_path: Path) -> None:
    skill_dir = _make_skill_dir(tmp_path, "test-skill", description="A test skill")
    result = _parse_skill_md(skill_dir)
    assert result["description"] == "A test skill"


def test_parse_skill_md_extracts_dependencies(tmp_path: Path) -> None:
    skill_dir = _make_skill_dir(tmp_path, "test-skill", dependencies=["skill-a", "skill-b"])
    result = _parse_skill_md(skill_dir)
    assert result["dependencies"] == ["skill-a", "skill-b"]


def test_parse_skill_md_extracts_category(tmp_path: Path) -> None:
    skill_dir = _make_skill_dir(tmp_path, "test-skill")
    result = _parse_skill_md(skill_dir)
    assert result["category"] == "tooling"


def test_parse_skill_md_missing_file(tmp_path: Path) -> None:
    d = tmp_path / "empty"
    d.mkdir()
    result = _parse_skill_md(d)
    assert result["name"] == "empty"
    assert result["description"] == ""


# ---------------------------------------------------------------------------
# Skill collection
# ---------------------------------------------------------------------------


def test_collect_skills_in_dir_finds_skills(tmp_path: Path) -> None:
    _make_skill_dir(tmp_path, "skill-a")
    _make_skill_dir(tmp_path, "skill-b")

    skills = _collect_skills_in_dir(tmp_path, SOURCE_CODEX)

    assert len(skills) == 2
    names = {s.name for s in skills}
    assert "Skill A" in names
    assert "Skill B" in names


def test_collect_skills_ignores_dirs_without_skill_md(tmp_path: Path) -> None:
    (tmp_path / "not-a-skill").mkdir()
    _make_skill_dir(tmp_path, "real-skill")

    skills = _collect_skills_in_dir(tmp_path, SOURCE_CODEX)

    assert len(skills) == 1
    assert skills[0].path == "real-skill"


def test_collect_skills_returns_empty_for_nonexistent_dir() -> None:
    skills = _collect_skills_in_dir(Path("Z:/nonexistent/path"), SOURCE_CODEX)
    assert skills == []


def test_collect_skills_skips_symlinks(tmp_path: Path) -> None:
    _make_skill_dir(tmp_path, "real-skill")
    # We cannot reliably create symlinks in tests without admin,
    # but the code path checks is_symlink() which returns False for regular dirs
    skills = _collect_skills_in_dir(tmp_path, SOURCE_CODEX)
    assert len(skills) == 1
    assert skills[0].path == "real-skill"


def test_collect_skills_sets_source_alias(tmp_path: Path) -> None:
    _make_skill_dir(tmp_path, "test-skill")

    skills = _collect_skills_in_dir(tmp_path, SOURCE_CODEX)
    assert skills[0].source_alias == "codeX"

    skills = _collect_skills_in_dir(tmp_path, SOURCE_LARK_CLI)
    assert skills[0].source_alias == "lark-cli-home"


def test_collect_skills_sets_agent_visibility(tmp_path: Path) -> None:
    _make_skill_dir(tmp_path, "test-skill")

    skills = _collect_skills_in_dir(tmp_path, SOURCE_CODEX)
    assert "codex-code-agent" in skills[0].agent_visibility

    skills = _collect_skills_in_dir(tmp_path, SOURCE_OPENCLAW_NPM)
    assert "openclaw-coordinator" in skills[0].agent_visibility


def test_collect_skills_includes_hash_and_mtime(tmp_path: Path) -> None:
    _make_skill_dir(tmp_path, "test-skill")

    skills = _collect_skills_in_dir(tmp_path, SOURCE_CODEX)
    assert len(skills[0].version) == 64
    assert skills[0].mtime is not None
    assert skills[0].dir_hash is not None
    assert skills[0].size > 0


def test_collect_skills_unique_skill_ids(tmp_path: Path) -> None:
    _make_skill_dir(tmp_path, "my-skill")

    skills = _collect_skills_in_dir(tmp_path, SOURCE_CODEX)
    assert skills[0].skill_id == "codeX:my-skill"


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


def test_deduplicate_keeps_higher_priority_source() -> None:
    s1 = SkillEntry(
        skill_id="lark-cli-home:test-skill",
        name="test-skill",
        source=SOURCE_LARK_CLI,
        source_alias="lark-cli-home",
        version="abc123",
        path_hash="hash1",
        dir_hash=None,
        mtime=None,
        dependencies=[],
        description="from lark-cli",
        agent_visibility=[],
        category="mock",
        status="active",
        size=100,
        path="test-skill",
    )
    s2 = SkillEntry(
        skill_id="codeX:test-skill",
        name="test-skill",
        source=SOURCE_CODEX,
        source_alias="codeX",
        version="def456",
        path_hash="hash2",
        dir_hash=None,
        mtime=None,
        dependencies=[],
        description="from codex",
        agent_visibility=[],
        category="mock",
        status="active",
        size=200,
        path="test-skill",
    )

    result = _deduplicate([s2, s1])  # intentionally reverse order
    assert len(result) == 1
    assert result[0].source == SOURCE_LARK_CLI
    assert result[0].version == "abc123"


def test_deduplicate_keeps_unique_names() -> None:
    s1 = SkillEntry(
        skill_id="a:skill-a", name="skill-a", source=SOURCE_CODEX, source_alias="codeX",
        version="v1", path_hash="h1", dir_hash=None, mtime=None, dependencies=[],
        description="a", agent_visibility=[], category="m", status="active", size=1, path="a",
    )
    s2 = SkillEntry(
        skill_id="b:skill-b", name="skill-b", source=SOURCE_CODEX, source_alias="codeX",
        version="v1", path_hash="h2", dir_hash=None, mtime=None, dependencies=[],
        description="b", agent_visibility=[], category="m", status="active", size=1, path="b",
    )

    result = _deduplicate([s1, s2])
    assert len(result) == 2


def test_deduplicate_case_insensitive() -> None:
    s1 = SkillEntry(
        skill_id="a:My-Skill", name="My-Skill", source=SOURCE_LARK_CLI, source_alias="lark-cli-home",
        version="v1", path_hash="h1", dir_hash=None, mtime=None, dependencies=[],
        description="upper", agent_visibility=[], category="m", status="active", size=1, path="a",
    )
    s2 = SkillEntry(
        skill_id="b:my-skill", name="my-skill", source=SOURCE_CODEX, source_alias="codeX",
        version="v2", path_hash="h2", dir_hash=None, mtime=None, dependencies=[],
        description="lower", agent_visibility=[], category="m", status="active", size=1, path="b",
    )

    result = _deduplicate([s2, s1])
    assert len(result) == 1
    assert result[0].source == SOURCE_LARK_CLI


# ---------------------------------------------------------------------------
# Source resolution
# ---------------------------------------------------------------------------


def test_resolve_source_dirs_returns_three_sources(tmp_path: Path) -> None:
    cfg = _mock_config(tmp_path)
    dirs = _resolve_source_dirs(cfg)
    assert set(dirs.keys()) == {SOURCE_LARK_CLI, SOURCE_OPENCLAW_NPM, SOURCE_CODEX}


def test_resolve_source_dirs_codex_uses_stack_root(tmp_path: Path) -> None:
    cfg = _mock_config(tmp_path)
    dirs = _resolve_source_dirs(cfg)
    assert dirs[SOURCE_CODEX] == tmp_path / "skills"


def test_resolve_source_dirs_codex_env_override(tmp_path: Path, monkeypatch) -> None:
    custom = tmp_path / "custom-skills"
    custom.mkdir()
    monkeypatch.setenv("CODEX_SKILLS_DIR", str(custom))
    cfg = _mock_config(tmp_path)
    dirs = _resolve_source_dirs(cfg)
    assert dirs[SOURCE_CODEX] == custom


def test_resolve_source_dirs_lark_cli_home_env_override(tmp_path: Path, monkeypatch) -> None:
    custom = tmp_path / "lark-home"
    custom.mkdir()
    monkeypatch.setenv("LARK_CLI_HOME", str(custom))
    cfg = _mock_config(tmp_path)
    dirs = _resolve_source_dirs(cfg)
    assert dirs[SOURCE_LARK_CLI] == custom


def test_resolve_source_dirs_openclaw_npm_env_override(tmp_path: Path, monkeypatch) -> None:
    custom = tmp_path / "openclaw-skills"
    custom.mkdir()
    monkeypatch.setenv("OPENCLAW_NPM_DIR", str(custom))
    cfg = _mock_config(tmp_path)
    dirs = _resolve_source_dirs(cfg)
    assert dirs[SOURCE_OPENCLAW_NPM] == custom


def test_resolve_source_dirs_missing_source_not_none(tmp_path: Path) -> None:
    """Missing env vars should still return a Path (may not exist)."""
    cfg = _mock_config(tmp_path)
    dirs = _resolve_source_dirs(cfg)
    for source in SOURCE_PRIORITY:
        assert dirs[source] is not None


# ---------------------------------------------------------------------------
# Scan

# tests
# ---------------------------------------------------------------------------


def test_scan_skills_returns_inventory(tmp_path: Path, monkeypatch) -> None:
    cfg = _mock_config(tmp_path)

    # Create a codex skills dir
    codex_skills = tmp_path / "skills"
    _make_skill_dir(codex_skills, "skill-a")
    _make_skill_dir(codex_skills, "skill-b")

    # Mock source resolution to only use codex
    def fake_dirs(config=None):
        return {
            SOURCE_LARK_CLI: tmp_path / "nonexistent-lark",
            SOURCE_OPENCLAW_NPM: tmp_path / "nonexistent-npm",
            SOURCE_CODEX: codex_skills,
        }

    monkeypatch.setattr(
        "feishu_stack.modules.agent_array.skill_tree.skill_registry._resolve_source_dirs",
        fake_dirs,
    )
    monkeypatch.setattr(
        "feishu_stack.modules.agent_array.skill_tree.skill_registry._cache_path",
        lambda config=None: tmp_path / "runtime" / "skill-cache" / "skill-inventory.json",
    )

    inventory = scan_skills(cfg, force_full=True)
    assert inventory.total == 2
    assert inventory.by_source.get(SOURCE_CODEX, 0) == 2
    assert inventory.scan_metadata is not None
    assert inventory.scan_metadata.mode == "full"
    assert inventory.scan_metadata.total_skills == 2


def test_scan_skills_empty_sources_returns_empty_inventory(tmp_path: Path, monkeypatch) -> None:
    cfg = _mock_config(tmp_path)

    def fake_dirs(config=None):
        return {
            SOURCE_LARK_CLI: tmp_path / "nonexistent-lark",
            SOURCE_OPENCLAW_NPM: tmp_path / "nonexistent-npm",
            SOURCE_CODEX: tmp_path / "nonexistent-codex",
        }

    monkeypatch.setattr(
        "feishu_stack.modules.agent_array.skill_tree.skill_registry._resolve_source_dirs",
        fake_dirs,
    )

    inventory = scan_skills(cfg, force_full=True)
    assert inventory.total == 0
    assert inventory.skills == []


def test_scan_skills_preserves_same_named_sources(tmp_path: Path, monkeypatch) -> None:
    """The registry inventory keeps all source instances for drift comparison."""
    lark_dir = tmp_path / "lark-skills"
    npm_dir = tmp_path / "npm-skills"
    codex_dir = tmp_path / "codex-skills"
    cfg = _mock_config(tmp_path)

    _make_skill_dir(lark_dir, "shared-skill", description="from lark")
    _make_skill_dir(npm_dir, "shared-skill", description="from npm")
    _make_skill_dir(codex_dir, "shared-skill", description="from codex")

    # Force lark version to be different
    lark_md = lark_dir / "shared-skill" / "SKILL.md"
    lark_md.write_text("# Shared Skill\n\n---\ndescription: \"from lark (custom)\"\n---\n\nLark version.\n")

    def fake_dirs(config=None):
        return {
            SOURCE_LARK_CLI: lark_dir,
            SOURCE_OPENCLAW_NPM: npm_dir,
            SOURCE_CODEX: codex_dir,
        }

    monkeypatch.setattr(
        "feishu_stack.modules.agent_array.skill_tree.skill_registry._resolve_source_dirs",
        fake_dirs,
    )

    inventory = scan_skills(cfg, force_full=True)

    assert inventory.total == 3
    assert {skill.source for skill in inventory.skills} == {SOURCE_LARK_CLI, SOURCE_OPENCLAW_NPM, SOURCE_CODEX}


def test_deduplicate_prefers_highest_priority_source(tmp_path: Path) -> None:
    """When a loaded view needs one winner, higher priority still wins."""
    lark_dir = tmp_path / "lark-skills"
    npm_dir = tmp_path / "npm-skills"
    codex_dir = tmp_path / "codex-skills"

    _make_skill_dir(lark_dir, "shared-skill", description="from lark")
    _make_skill_dir(npm_dir, "shared-skill", description="from npm")
    _make_skill_dir(codex_dir, "shared-skill", description="from codex")

    lark_md = lark_dir / "shared-skill" / "SKILL.md"
    lark_md.write_text("# Shared Skill\n\n---\ndescription: \"from lark (custom)\"\n---\n\nLark version.\n")

    lark_skills = _collect_skills_in_dir(lark_dir, SOURCE_LARK_CLI)
    npm_skills = _collect_skills_in_dir(npm_dir, SOURCE_OPENCLAW_NPM)
    codex_skills = _collect_skills_in_dir(codex_dir, SOURCE_CODEX)

    all_skills = lark_skills + npm_skills + codex_skills
    result = _deduplicate(all_skills)

    assert len(result) == 1
    assert result[0].source == SOURCE_LARK_CLI
    assert "lark" in result[0].description.lower()


@pytest.mark.slow
def test_scan_skills_cache_hit_on_second_scan(tmp_path: Path, monkeypatch) -> None:
    cfg = _mock_config(tmp_path)
    skill_dir = tmp_path / "skills"
    _make_skill_dir(skill_dir, "skill-x")

    def fake_dirs(config=None):
        return {
            SOURCE_LARK_CLI: tmp_path / "nonexistent-lark",
            SOURCE_OPENCLAW_NPM: tmp_path / "nonexistent-npm",
            SOURCE_CODEX: skill_dir,
        }

    monkeypatch.setattr(
        "feishu_stack.modules.agent_array.skill_tree.skill_registry._resolve_source_dirs",
        fake_dirs,
    )

    # First scan (full)
    inv1 = scan_skills(cfg, force_full=True)
    assert inv1.scan_metadata.mode == "full"
    assert inv1.total == 1

    # Second scan (should be incremental and use cache)
    inv2 = scan_skills(cfg, force_full=False)
    assert inv2.total == 1
    assert inv2.scan_metadata.mode == "incremental"
    assert inv2.scan_metadata.cache_hits >= 1


def test_get_inventory_returns_skill_inventory(tmp_path: Path, monkeypatch) -> None:
    cfg = _mock_config(tmp_path)
    skill_dir = tmp_path / "skills"
    _make_skill_dir(skill_dir, "test-skill")

    def fake_dirs(config=None):
        return {
            SOURCE_LARK_CLI: tmp_path / "nonexistent",
            SOURCE_OPENCLAW_NPM: tmp_path / "nonexistent",
            SOURCE_CODEX: skill_dir,
        }

    monkeypatch.setattr(
        "feishu_stack.modules.agent_array.skill_tree.skill_registry._resolve_source_dirs",
        fake_dirs,
    )

    inv = get_inventory(cfg)
    assert inv.total >= 1
    found = any(s.name == "Test Skill" for s in inv.skills)
    assert found is True


def test_get_skill_by_id_found(tmp_path: Path, monkeypatch) -> None:
    cfg = _mock_config(tmp_path)
    skill_dir = tmp_path / "skills"
    _make_skill_dir(skill_dir, "unique-skill")

    def fake_dirs(config=None):
        return {
            SOURCE_LARK_CLI: tmp_path / "nonexistent",
            SOURCE_OPENCLAW_NPM: tmp_path / "nonexistent",
            SOURCE_CODEX: skill_dir,
        }

    monkeypatch.setattr(
        "feishu_stack.modules.agent_array.skill_tree.skill_registry._resolve_source_dirs",
        fake_dirs,
    )

    skill = get_skill_by_id("codeX:unique-skill", cfg)
    assert skill is not None
    assert skill.name == "Unique Skill"


def test_get_skill_by_id_not_found(tmp_path: Path, monkeypatch) -> None:
    cfg = _mock_config(tmp_path)
    skill_dir = tmp_path / "skills"
    _make_skill_dir(skill_dir, "real-skill")

    def fake_dirs(config=None):
        return {
            SOURCE_LARK_CLI: tmp_path / "nonexistent",
            SOURCE_OPENCLAW_NPM: tmp_path / "nonexistent",
            SOURCE_CODEX: skill_dir,
        }

    monkeypatch.setattr(
        "feishu_stack.modules.agent_array.skill_tree.skill_registry._resolve_source_dirs",
        fake_dirs,
    )

    skill = get_skill_by_id("codeX:nonexistent", cfg)
    assert skill is None


def test_get_agent_skills_filters_by_agent(tmp_path: Path, monkeypatch) -> None:
    cfg = _mock_config(tmp_path)

    # Two source dirs
    codex_dir = tmp_path / "codex-skills"
    codex_dir.mkdir()
    npm_dir = tmp_path / "npm-skills"
    npm_dir.mkdir()

    _make_skill_dir(codex_dir, "codex-only")
    _make_skill_dir(npm_dir, "npm-only")

    def fake_dirs(config=None):
        return {
            SOURCE_LARK_CLI: tmp_path / "nonexistent",
            SOURCE_OPENCLAW_NPM: npm_dir,
            SOURCE_CODEX: codex_dir,
        }

    monkeypatch.setattr(
        "feishu_stack.modules.agent_array.skill_tree.skill_registry._resolve_source_dirs",
        fake_dirs,
    )

    codex_skills = get_agent_skills("codex-code-agent", cfg)
    npm_skills = get_agent_skills("openclaw-coordinator", cfg)

    assert any(s.name == "Codex Only" for s in codex_skills)
    assert any(s.name == "Npm Only" for s in npm_skills)
    assert not any(s.name == "Npm Only" for s in codex_skills)


def test_skill_entry_to_dict_includes_all_keys(tmp_path: Path) -> None:
    _make_skill_dir(tmp_path, "test")
    skills = _collect_skills_in_dir(tmp_path, SOURCE_CODEX)
    d = skills[0].to_dict()

    expected_keys = {
        "skillId", "name", "source", "sourceAlias", "version",
        "pathHash", "dirHash", "mtime", "dependencies", "description",
        "agentVisibility", "category", "status", "size", "path",
    }
    assert set(d.keys()) == expected_keys
    assert d["sourceAlias"] == "codeX"
    assert d["path"] == "test"


def test_scan_skills_dir_hash_detects_sub_file_changes(tmp_path: Path) -> None:
    skill_dir = _make_skill_dir_with_subfile(tmp_path, "my-skill")
    h1 = _dir_sha256(skill_dir)

    # Change the sub-file
    (skill_dir / "helpers.py").write_text("def helper(): return 42\n")
    h2 = _dir_sha256(skill_dir)

    assert h1 != h2


def test_scan_skills_respects_force_full(tmp_path: Path, monkeypatch) -> None:
    cfg = _mock_config(tmp_path)
    skill_dir = tmp_path / "skills"
    _make_skill_dir(skill_dir, "s1")

    def fake_dirs(config=None):
        return {
            SOURCE_LARK_CLI: tmp_path / "nonexistent",
            SOURCE_OPENCLAW_NPM: tmp_path / "nonexistent",
            SOURCE_CODEX: skill_dir,
        }

    monkeypatch.setattr(
        "feishu_stack.modules.agent_array.skill_tree.skill_registry._resolve_source_dirs",
        fake_dirs,
    )

    inv = scan_skills(cfg, force_full=True)
    assert inv.scan_metadata.mode == "full"


# ---------------------------------------------------------------------------
# Cache save/load
# ---------------------------------------------------------------------------


def test_save_and_load_cache(tmp_path: Path, monkeypatch) -> None:
    cfg = _mock_config(tmp_path)
    (tmp_path / "runtime" / "skill-cache").mkdir(parents=True)
    cache_path = tmp_path / "runtime" / "skill-cache" / "skill-inventory.json"

    monkeypatch.setattr(
        "feishu_stack.modules.agent_array.skill_tree.skill_registry._cache_path",
        lambda config=None: cache_path,
    )

    from feishu_stack.modules.agent_array.skill_tree.skill_registry import (
        ScanMetadata,
        SkillInventory,
        _load_cache,
        _save_cache,
    )

    skills = [
        SkillEntry(
            skill_id="test:skill",
            name="test",
            source=SOURCE_CODEX,
            source_alias="codeX",
            version="abc",
            path_hash="h1",
            dir_hash=None,
            mtime="2026-01-01",
            dependencies=[],
            description="test skill",
            agent_visibility=[],
            category="test",
            status="active",
            size=100,
            path="test",
        )
    ]
    metadata = ScanMetadata(
        scanned_at="2026-01-01T00:00:00",
        duration_ms=100,
        total_skills=1,
        sources_scanned=[SOURCE_CODEX],
        sources_failed=[],
        cache_hits=0,
        cache_misses=1,
        mode="full",
    )
    inventory = SkillInventory(
        skills=skills,
        total=1,
        by_source={SOURCE_CODEX: 1},
        by_agent={"codex-code-agent": 1},
        scan_metadata=metadata,
    )

    _save_cache(inventory, cfg)
    assert cache_path.is_file()

    loaded = _load_cache(cfg)
    assert loaded is not None
    assert loaded.get("scanned_at") == "2026-01-01T00:00:00"
    assert len(loaded.get("skills", [])) == 1


def test_load_cache_returns_none_for_missing_file(tmp_path: Path, monkeypatch) -> None:
    from feishu_stack.modules.agent_array.skill_tree.skill_registry import _load_cache

    cfg = _mock_config(tmp_path)
    monkeypatch.setattr(
        "feishu_stack.modules.agent_array.skill_tree.skill_registry._cache_path",
        lambda config=None: tmp_path / "nonexistent" / "cache.json",
    )

    assert _load_cache(cfg) is None
