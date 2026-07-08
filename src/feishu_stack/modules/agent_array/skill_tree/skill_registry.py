from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from feishu_stack.core.settings import StackConfig, load_config

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SOURCE_LARK_CLI = "lark-cli-home"
SOURCE_OPENCLAW_NPM = "openclaw-npm"
SOURCE_CODEX = "codeX"

SOURCE_ALIASES: dict[str, str] = {
    SOURCE_LARK_CLI: "lark-cli-home",
    SOURCE_OPENCLAW_NPM: "openclaw-npm",
    SOURCE_CODEX: "codeX",
}

SOURCE_PRIORITY: list[str] = [SOURCE_LARK_CLI, SOURCE_OPENCLAW_NPM, SOURCE_CODEX]

CACHE_MAX_AGE_S: int = 86400  # 24 hours

AGENT_VISIBILITY_MAP: dict[str, list[str]] = {
    SOURCE_LARK_CLI: ["feishu-codex-agent", "codex-code-agent"],
    SOURCE_OPENCLAW_NPM: [
        "openclaw-coordinator",
        "openclaw-orchestrator",
        "openclaw-main",
        "openclaw-archivist",
    ],
    SOURCE_CODEX: ["codex-code-agent"],
}

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class SkillEntry:
    """A single skill discovered from a source directory."""

    skill_id: str
    name: str
    source: str
    source_alias: str
    version: str
    path_hash: str
    dir_hash: str | None
    mtime: str | None
    dependencies: list[str]
    description: str
    agent_visibility: list[str]
    category: str
    status: str
    size: int
    path: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "skillId": self.skill_id,
            "name": self.name,
            "source": self.source,
            "sourceAlias": self.source_alias,
            "version": self.version,
            "pathHash": self.path_hash,
            "dirHash": self.dir_hash,
            "mtime": self.mtime,
            "dependencies": self.dependencies,
            "description": self.description,
            "agentVisibility": self.agent_visibility,
            "category": self.category,
            "status": self.status,
            "size": self.size,
            "path": self.path,
        }


@dataclass
class ScanMetadata:
    """Metadata about the most recent scan."""

    scanned_at: str
    duration_ms: int
    total_skills: int
    sources_scanned: list[str]
    sources_failed: list[str]
    cache_hits: int
    cache_misses: int
    mode: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "scannedAt": self.scanned_at,
            "durationMs": self.duration_ms,
            "totalSkills": self.total_skills,
            "sourcesScanned": self.sources_scanned,
            "sourcesFailed": self.sources_failed,
            "cacheHits": self.cache_hits,
            "cacheMisses": self.cache_misses,
            "mode": self.mode,
        }


@dataclass
class SkillInventory:
    """Complete skill inventory including scan metadata."""

    skills: list[SkillEntry]
    total: int
    by_source: dict[str, int]
    by_agent: dict[str, int]
    scan_metadata: ScanMetadata | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "skills": [s.to_dict() for s in self.skills],
            "total": self.total,
            "bySource": self.by_source,
            "byAgent": self.by_agent,
            "scanMetadata": self.scan_metadata.to_dict() if self.scan_metadata else None,
        }


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------


def _resolve_source_dirs(config: StackConfig | None = None) -> dict[str, Path | None]:
    """Resolve the three skill source directories.

    Returns a dict with keys SOURCE_LARK_CLI, SOURCE_OPENCLAW_NPM, SOURCE_CODEX.
    A value of None means the source is unavailable.
    """
    cfg = config or load_config()

    lark_cli_home = os.environ.get("LARK_CLI_HOME")
    if not lark_cli_home:
        lark_cli_home = str(Path.home() / ".agents" / "skills")

    openclaw_npm = os.environ.get("OPENCLAW_NPM_DIR")
    if not openclaw_npm:
        openclaw_npm = str(Path(os.environ.get("APPDATA", "")) / "npm" / "node_modules" / "openclaw" / "skills")

    codex_dir = os.environ.get("CODEX_SKILLS_DIR")
    if not codex_dir:
        codex_dir = str(cfg.stack_root / "skills")

    return {
        SOURCE_LARK_CLI: Path(lark_cli_home) if lark_cli_home else None,
        SOURCE_OPENCLAW_NPM: Path(openclaw_npm) if openclaw_npm else None,
        SOURCE_CODEX: Path(codex_dir) if codex_dir else None,
    }


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_sha256(path: Path) -> str:
    """Compute sha256 of a file's content."""
    return _sha256_hex(path.read_bytes())


def _dir_sha256(dir_path: Path) -> str | None:
    """Compute a directory-level sha256 by hashing all file contents in order."""
    if not dir_path.is_dir():
        return None
    hasher = hashlib.sha256()
    files = sorted(dir_path.rglob("*"))
    for fpath in files:
        if fpath.is_file() and not fpath.is_symlink():
            hasher.update(fpath.read_bytes())
    return hasher.hexdigest() if files else _sha256_hex(b"")


# ---------------------------------------------------------------------------
# SKILL.md parsing
# ---------------------------------------------------------------------------


def _parse_skill_md(skill_dir: Path) -> dict[str, Any]:
    """Parse a SKILL.md file to extract metadata.

    Returns a dict with keys: name, description, dependencies, category.
    Falls back to directory name if SKILL.md is missing or unparseable.
    """
    skill_md = skill_dir / "SKILL.md"
    result: dict[str, Any] = {
        "name": skill_dir.name,
        "description": "",
        "dependencies": [],
        "category": "uncategorized",
    }
    if not skill_md.is_file():
        return result

    try:
        content = skill_md.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return result

    # Extract name from first # heading
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# ") and not stripped.startswith("## "):
            result["name"] = stripped[2:].strip()
            break

    # Look for YAML frontmatter or description markers
    lines = content.splitlines()
    in_frontmatter = False
    frontmatter_lines: list[str] = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "---":
            if not in_frontmatter:
                in_frontmatter = True
                continue
            elif in_frontmatter:
                in_frontmatter = False
                break
        if in_frontmatter:
            frontmatter_lines.append(stripped)

    for line in frontmatter_lines:
        if line.lower().startswith("description:"):
            result["description"] = line.split(":", 1)[1].strip().strip('"').strip("'")
        elif line.lower().startswith("dependencies:"):
            deps = line.split(":", 1)[1].strip()
            result["dependencies"] = [d.strip() for d in deps.split(",") if d.strip()]
        elif line.lower().startswith("category:"):
            result["category"] = line.split(":", 1)[1].strip().strip('"').strip("'")

    # Fallback: search body for explicit patterns
    if not result["description"]:
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("> "):
                result["description"] = stripped[2:].strip()
                break
            if stripped and not stripped.startswith("#"):
                if len(stripped) > 20:
                    result["description"] = stripped[:200]
                    break

    return result

def _collect_skills_in_dir(
    source_dir: Path,
    source_key: str,
) -> list[SkillEntry]:
    """Scan a source directory for skills and return SkillEntry list.

    Does NOT follow symlinks. Each subdirectory containing a SKILL.md
    is treated as one skill.
    """
    skills: list[SkillEntry] = []
    if not source_dir.is_dir():
        return skills

    source_alias = SOURCE_ALIASES.get(source_key, source_key)
    visibility = AGENT_VISIBILITY_MAP.get(source_key, [])

    for entry in sorted(source_dir.iterdir()):
        if entry.is_symlink():
            continue
        if not entry.is_dir():
            continue

        skill_md = entry / "SKILL.md"
        if not skill_md.is_file():
            continue

        try:
            version = _file_sha256(skill_md)
            dir_hash = _dir_sha256(entry)
            stat = skill_md.stat()
            mtime = datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()
            size = stat.st_size
        except OSError:
            continue

        metadata = _parse_skill_md(entry)
        skill_id = f"{source_key}:{entry.name}"

        skills.append(
            SkillEntry(
                skill_id=skill_id,
                name=metadata["name"],
                source=source_key,
                source_alias=source_alias,
                version=version,
                path_hash=_sha256_hex(str(entry.relative_to(source_dir)).encode()),
                dir_hash=dir_hash,
                mtime=mtime,
                dependencies=metadata["dependencies"],
                description=metadata["description"],
                agent_visibility=visibility,
                category=metadata["category"],
                status="active",
                size=size,
                path=str(entry.relative_to(source_dir)),
            )
        )

    return skills


# ---------------------------------------------------------------------------
# Caching
# ---------------------------------------------------------------------------


def _cache_path(config: StackConfig | None = None) -> Path:
    cfg = config or load_config()
    cache_dir = cfg.runtime_dir / "skill-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / "skill-inventory.json"


def _load_cache(config: StackConfig | None = None) -> dict[str, Any] | None:
    path = _cache_path(config)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    return data


def _save_cache(inventory: SkillInventory, config: StackConfig | None = None) -> None:
    path = _cache_path(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "skills": [s.to_dict() for s in inventory.skills],
        "scanned_at": inventory.scan_metadata.scanned_at if inventory.scan_metadata else "",
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _has_skill_changed(skill: SkillEntry, cache_map: dict[str, dict[str, Any]]) -> bool:
    """Check if a skill has changed compared to cache using mtime+size."""
    cached = cache_map.get(skill.skill_id)
    if not cached:
        return True
    return (
        cached.get("mtime") != skill.mtime
        or cached.get("size") != skill.size
        or cached.get("version") != skill.version
    )


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


def _deduplicate(skills: list[SkillEntry]) -> list[SkillEntry]:
    """Deduplicate skills by name across sources.

    Priority: lark-cli-home > openclaw-npm > codeX.
    Skills with the same name from lower-priority sources are removed.
    """
    seen: dict[str, SkillEntry] = {}
    priority_rank = {s: i for i, s in enumerate(SOURCE_PRIORITY)}

    for skill in skills:
        name = skill.name.lower()
        existing = seen.get(name)
        if existing is None:
            seen[name] = skill
        else:
            current_rank = priority_rank.get(skill.source, 99)
            existing_rank = priority_rank.get(existing.source, 99)
            if current_rank < existing_rank:
                seen[name] = skill

    return sorted(seen.values(), key=lambda s: s.name.lower())


# ---------------------------------------------------------------------------
# Main scan function
# ---------------------------------------------------------------------------


def scan_skills(
    config: StackConfig | None = None,
    *,
    force_full: bool = False,
) -> SkillInventory:
    """Scan all skill sources and return a SkillInventory.

    By default uses incremental scanning (mtime+size cache) with
    a 24h full-rescan fallback. Pass force_full=True to skip cache.

    Performance targets: first scan <30s, incremental <5s.
    """
    cfg = config or load_config()
    start_time = time.monotonic()

    # Determine scan mode
    cache_data = None if force_full else _load_cache(cfg)
    cache_map: dict[str, dict[str, Any]] = {}
    cache_age = 0.0

    if cache_data and not force_full:
        cached_skills = cache_data.get("skills", [])
        for cs in cached_skills:
            if isinstance(cs, dict) and cs.get("skillId"):
                cache_map[cs["skillId"]] = cs
        scanned_at_str = cache_data.get("scanned_at", "")
        if scanned_at_str:
            try:
                scanned_at = datetime.fromisoformat(scanned_at_str)
                cache_age = (datetime.now(timezone.utc) - scanned_at).total_seconds()
            except ValueError:
                cache_age = CACHE_MAX_AGE_S + 1

    if cache_age >= CACHE_MAX_AGE_S:
        cache_map.clear()
        cache_data = None

    mode = "full" if not cache_map else "incremental"

    # Resolve sources
    source_dirs = _resolve_source_dirs(cfg)
    sources_scanned: list[str] = []
    sources_failed: list[str] = []
    all_skills: list[SkillEntry] = []
    cache_hits = 0
    cache_misses = 0

    for source_key in SOURCE_PRIORITY:
        src_dir = source_dirs.get(source_key)
        if src_dir is None:
            sources_failed.append(source_key)
            continue
        if not src_dir.is_dir():
            sources_scanned.append(source_key)
            continue

        sources_scanned.append(source_key)
        try:
            discovered = _collect_skills_in_dir(src_dir, source_key)
        except Exception:
            sources_failed.append(source_key)
            continue

        for skill in discovered:
            if cache_map and not _has_skill_changed(skill, cache_map):
                # Use cached version
                cached = cache_map[skill.skill_id]
                cache_hits += 1
                cached_entry = SkillEntry(
                    skill_id=skill.skill_id,
                    name=cached.get("name", skill.name),
                    source=skill.source,
                    source_alias=skill.source_alias,
                    version=skill.version,
                    path_hash=skill.path_hash,
                    dir_hash=skill.dir_hash,
                    mtime=skill.mtime,
                    dependencies=cached.get("dependencies", skill.dependencies),
                    description=cached.get("description", skill.description),
                    agent_visibility=skill.agent_visibility,
                    category=cached.get("category", skill.category),
                    status=cached.get("status", "active"),
                    size=skill.size,
                    path=skill.path,
                )
                all_skills.append(cached_entry)
            else:
                cache_misses += 1
                all_skills.append(skill)

    # Compute aggregates
    by_source: dict[str, int] = {}
    by_agent: dict[str, int] = {}
    for skill in all_skills:
        by_source[skill.source] = by_source.get(skill.source, 0) + 1
        for agent_id in skill.agent_visibility:
            by_agent[agent_id] = by_agent.get(agent_id, 0) + 1

    duration_ms = int((time.monotonic() - start_time) * 1000)
    metadata = ScanMetadata(
        scanned_at=datetime.now(timezone.utc).isoformat(),
        duration_ms=duration_ms,
        total_skills=len(all_skills),
        sources_scanned=sources_scanned,
        sources_failed=sources_failed,
        cache_hits=cache_hits,
        cache_misses=cache_misses,
        mode=mode,
    )

    inventory = SkillInventory(
        skills=all_skills,
        total=len(all_skills),
        by_source=by_source,
        by_agent=by_agent,
        scan_metadata=metadata,
    )

    _save_cache(inventory, cfg)
    return inventory


def get_inventory(
    config: StackConfig | None = None,
) -> SkillInventory:
    """Return the current skill inventory (from cache or fresh scan)."""
    return scan_skills(config)


def get_skill_by_id(
    skill_id: str,
    config: StackConfig | None = None,
) -> SkillEntry | None:
    """Get a single skill by its skill_id."""
    inventory = get_inventory(config)
    for skill in inventory.skills:
        if skill.skill_id == skill_id:
            return skill
    return None


def get_agent_skills(
    agent_id: str,
    config: StackConfig | None = None,
) -> list[SkillEntry]:
    """Return skills visible to a specific agent."""
    inventory = get_inventory(config)
    return [s for s in inventory.skills if agent_id in s.agent_visibility]
