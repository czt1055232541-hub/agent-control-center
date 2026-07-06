from __future__ import annotations

import json
import re
import sqlite3
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from feishu_stack.core.settings import StackConfig, load_config
from feishu_stack.core.models import ThreadListItem, ThreadMigrationResult
from feishu_stack.core.process import CREATE_NO_WINDOW

SUMMARY_TAIL_LINES = 80
DEFAULT_CONTINUATION_PROMPT = "Continue this work from the migrated context."
MAX_TEXT_ITEMS = 6
MAX_PATHS = 8


@dataclass
class RolloutContext:
    session_id: str
    source_title: str
    source_provider: str
    source_model: str
    cwd: str
    first_user_message: str
    recent_user_messages: list[str]
    recent_assistant_messages: list[str]
    important_files: list[str]
    rollout_path: Path
    excerpt_lines: list[str]


@dataclass
class SummaryArtifacts:
    summary_text: str
    summary_path: Path
    excerpt_path: Path
    prompt_path: Path
    summary_dir: Path


def _timestamp() -> str:
    return time.strftime("%Y%m%d-%H%M%S") + f"-{int((time.time() % 1) * 1000):03d}"


def _summary_artifact_path(cfg: StackConfig, name: str) -> Path:
    cfg.migration_summary_dir.mkdir(parents=True, exist_ok=True)
    return cfg.migration_summary_dir / name


def _state_db_paths(cfg: StackConfig) -> list[Path]:
    return [cfg.codex_home / "state_5.sqlite", cfg.codex_home / "sqlite" / "state_5.sqlite"]


def _pick_state_db(cfg: StackConfig) -> Path:
    for path in _state_db_paths(cfg):
        if path.exists():
            return path
    raise FileNotFoundError("Codex state DB not found.")


def _load_thread_title(session_id: str, cfg: StackConfig) -> str | None:
    query = "select title from threads where id = ? limit 1"
    for db_path in _state_db_paths(cfg):
        if not db_path.exists():
            continue
        try:
            with sqlite3.connect(str(db_path)) as conn:
                row = conn.execute(query, (session_id,)).fetchone()
        except sqlite3.Error:
            continue
        if row and row[0]:
            return str(row[0]).strip()
    return None


def _sanitize_filename(value: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "-", value).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = cleaned.rstrip(". ")
    return cleaned[:80] or "untitled-thread"


def _format_updated_at(value: int | None) -> str:
    if not value:
        return ""
    try:
        if value > 10_000_000_000:
            value = value // 1000
        return datetime.fromtimestamp(value).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ""


def find_session_rollout(session_id: str, config: StackConfig | None = None) -> Path:
    cfg = config or load_config()
    for path in cfg.codex_home.joinpath("sessions").rglob("*.jsonl"):
        try:
            with path.open("r", encoding="utf-8", errors="replace") as handle:
                first_line = handle.readline()
            if not first_line.strip():
                continue
            first = json.loads(first_line)
        except Exception:
            continue
        if first.get("type") == "session_meta" and first.get("payload", {}).get("id") == session_id:
            return path
    raise FileNotFoundError(f"Session rollout not found for {session_id}")


def list_recent_threads(limit: int = 20, config: StackConfig | None = None) -> list[ThreadListItem]:
    cfg = config or load_config()
    db_path = _pick_state_db(cfg)
    query = """
    select id, title, model_provider, coalesce(model, ''), coalesce(updated_at_ms, updated_at)
    from threads
    where coalesce(archived, 0) = 0
    order by coalesce(updated_at_ms, updated_at) desc
    limit ?
    """
    items: list[ThreadListItem] = []
    with sqlite3.connect(str(db_path)) as conn:
        rows = conn.execute(query, (int(limit),)).fetchall()
    for session_id, title, provider, model, updated_at in rows:
        items.append(
            ThreadListItem(
                session_id=str(session_id),
                title=str(title or session_id),
                provider=str(provider or "unknown"),
                model=str(model or "unknown"),
                updated_at=_format_updated_at(updated_at if isinstance(updated_at, int) else None),
            )
        )
    return items


def _extract_texts(content: list[dict], role: str) -> list[str]:
    texts: list[str] = []
    text_key = "input_text" if role == "user" else "output_text"
    for item in content:
        if item.get("type") == text_key and item.get("text"):
            texts.append(str(item["text"]).strip())
    return [text for text in texts if text]


def _collect_messages(lines: list[str]) -> tuple[list[str], list[str]]:
    users: list[str] = []
    assistants: list[str] = []
    for line in lines:
        try:
            payload = json.loads(line)
        except Exception:
            continue
        if payload.get("type") != "response_item":
            continue
        item = payload.get("payload", {})
        if item.get("type") != "message":
            continue
        role = item.get("role")
        content = item.get("content", [])
        if not isinstance(content, list):
            continue
        texts = _extract_texts(content, role)
        if role == "user":
            users.extend(texts)
        elif role == "assistant":
            assistants.extend(texts)
    return users, assistants


def _extract_paths(texts: list[str]) -> list[str]:
    pattern = re.compile(r"[A-Za-z]:\\[^\r\n\t\"'<>|?*]+")
    paths: list[str] = []
    seen: set[str] = set()
    for text in texts:
        for match in pattern.findall(text):
            cleaned = match.rstrip(".,);]")
            if cleaned not in seen:
                seen.add(cleaned)
                paths.append(cleaned)
            if len(paths) >= MAX_PATHS:
                return paths
    return paths


def load_rollout_context(session_id: str, config: StackConfig | None = None) -> RolloutContext:
    cfg = config or load_config()
    rollout_path = find_session_rollout(session_id, cfg)
    lines = rollout_path.read_text(encoding="utf-8", errors="replace").splitlines()
    if not lines:
        raise RuntimeError(f"Session rollout is empty: {rollout_path}")
    try:
        first = json.loads(lines[0])
    except Exception as exc:
        raise RuntimeError(f"Session rollout meta could not be parsed: {rollout_path}") from exc
    payload = first.get("payload", {})
    users, assistants = _collect_messages(lines)
    excerpt_lines = lines[-SUMMARY_TAIL_LINES:]
    texts = users[-MAX_TEXT_ITEMS:] + assistants[-MAX_TEXT_ITEMS:]
    first_user_message = str(payload.get("first_user_message") or (users[0] if users else ""))
    source_title = _load_thread_title(session_id, cfg) or first_user_message or session_id
    return RolloutContext(
        session_id=session_id,
        source_title=source_title,
        source_provider=str(payload.get("model_provider") or "unknown"),
        source_model=str(payload.get("model") or "unknown"),
        cwd=str(payload.get("cwd") or cfg.stack_root),
        first_user_message=first_user_message,
        recent_user_messages=users[-MAX_TEXT_ITEMS:],
        recent_assistant_messages=assistants[-MAX_TEXT_ITEMS:],
        important_files=_extract_paths(texts),
        rollout_path=rollout_path,
        excerpt_lines=excerpt_lines,
    )


def _choose_current_goal(context: RolloutContext, user_prompt: str) -> str:
    if user_prompt.strip():
        return user_prompt.strip()
    if context.recent_user_messages:
        return context.recent_user_messages[-1]
    if context.first_user_message:
        return context.first_user_message
    return "Continue the prior work from the migrated context."


def _choose_completed_work(context: RolloutContext) -> str:
    if context.recent_assistant_messages:
        return context.recent_assistant_messages[-1]
    return "No assistant completion summary could be inferred from the rollout tail."


def _choose_pending_work(context: RolloutContext, user_prompt: str) -> str:
    if user_prompt.strip():
        return user_prompt.strip()
    if context.recent_user_messages:
        return context.recent_user_messages[-1]
    return "Continue from the most recent known thread state."


def _choose_constraints(context: RolloutContext) -> str:
    return (
        f"Source provider was {context.source_provider}/{context.source_model}. "
        f"Do not assume the original thread id or provider binding can be reused. "
        f"Preserve the existing workspace and continue from the summarized state."
    )


def _choose_files(context: RolloutContext) -> str:
    if context.important_files:
        return "\n".join(f"- {path}" for path in context.important_files)
    return "- No important file paths were inferred from the recent rollout text."


def _choose_next_step(context: RolloutContext, target_provider: str, user_prompt: str) -> str:
    pending = _choose_pending_work(context, user_prompt)
    return f"Continue the pending work under provider {target_provider}. Start with: {pending}"


def build_migration_summary(
    session_id: str,
    target_provider: str,
    target_model: str,
    user_prompt: str,
    config: StackConfig | None = None,
) -> SummaryArtifacts:
    cfg = config or load_config()
    context = load_rollout_context(session_id, cfg)
    stamp = _timestamp()
    title_slug = _sanitize_filename(context.source_title)
    summary_path = _summary_artifact_path(cfg, f"{title_slug} -- summary to {target_provider} -- {stamp}.txt")
    excerpt_path = _summary_artifact_path(cfg, f"{title_slug} -- excerpt -- {stamp}.jsonl")
    prompt_path = _summary_artifact_path(cfg, f"{title_slug} -- import prompt -- {stamp}.txt")

    summary_text = (
        "Migrated Codex thread context\n"
        f"- Source thread title: {context.source_title}\n"
        f"- Source session id: {context.session_id}\n"
        f"- Source provider/model: {context.source_provider}/{context.source_model}\n"
        f"- Target provider/model: {target_provider}/{target_model}\n"
        f"- Working directory: {context.cwd}\n"
        f"- Current user goal: {_choose_current_goal(context, user_prompt)}\n"
        f"- Completed work: {_choose_completed_work(context)}\n"
        f"- Pending work: {_choose_pending_work(context, user_prompt)}\n"
        f"- Constraints: {_choose_constraints(context)}\n"
        "- Important files:\n"
        f"{_choose_files(context)}\n"
        f"- Recommended next step: {_choose_next_step(context, target_provider, user_prompt)}\n"
        f"- User continuation prompt: {user_prompt.strip() or DEFAULT_CONTINUATION_PROMPT}\n"
    )
    prompt_text = (
        f"{summary_text}\n\n"
        "Manual import instruction:\n"
        f"Open the same-named thread on the {target_provider} side and paste this summary as the first context block.\n"
    )

    summary_path.write_text(summary_text, encoding="utf-8")
    excerpt_path.write_text("\n".join(context.excerpt_lines) + "\n", encoding="utf-8")
    prompt_path.write_text(prompt_text, encoding="utf-8")
    return SummaryArtifacts(
        summary_text=summary_text,
        summary_path=summary_path,
        excerpt_path=excerpt_path,
        prompt_path=prompt_path,
        summary_dir=summary_path.parent,
    )


def _provider_args(target_provider: str, cfg: StackConfig) -> tuple[str, list[str]]:
    if target_provider == "moonbridge":
        return cfg.moonbridge_model, []
    return cfg.native_model, []


def start_migrated_session(
    session_id: str,
    target_provider: str,
    user_prompt: str,
    config: StackConfig | None = None,
) -> ThreadMigrationResult:
    cfg = config or load_config()
    started = time.monotonic()
    context = load_rollout_context(session_id, cfg)
    target_model, provider_cli_args = _provider_args(target_provider, cfg)
    artifacts = build_migration_summary(session_id, target_provider, target_model, user_prompt or DEFAULT_CONTINUATION_PROMPT, cfg)
    message = (
        f"Migration summary created for '{context.source_title}' to {target_provider}/{target_model}. "
        "Open the same-named thread on the target side and import the summary manually."
    )
    return ThreadMigrationResult(
        ok=True,
        component="thread-migration",
        action="migrate",
        message=message,
        duration_ms=int((time.monotonic() - started) * 1000),
        source_session_id=session_id,
        source_title=context.source_title,
        target_provider=target_provider,
        target_model=target_model,
        summary_path=str(artifacts.summary_path),
        summary_dir=str(artifacts.summary_dir),
        launched_command=" ".join(provider_cli_args) if provider_cli_args else None,
        launch_mode="summary-only-manual",
    )


def open_summary_folder(summary_path: str) -> ThreadMigrationResult:
    started = time.monotonic()
    target = Path(summary_path).resolve()
    if not target.exists():
        raise FileNotFoundError(f"Summary file not found: {target}")
    directory = target.parent
    subprocess.Popen(["explorer.exe", str(directory)], creationflags=CREATE_NO_WINDOW)
    return ThreadMigrationResult(
        ok=True,
        component="thread-migration",
        action="open-summary-folder",
        message=f"Opened summary folder: {directory}",
        duration_ms=int((time.monotonic() - started) * 1000),
        summary_path=str(target),
        summary_dir=str(directory),
    )


def migrate_thread(
    session_id: str,
    target_provider: str,
    prompt: str = DEFAULT_CONTINUATION_PROMPT,
    config: StackConfig | None = None,
) -> ThreadMigrationResult:
    if target_provider not in {"native", "moonbridge"}:
        raise ValueError(f"Unsupported target provider: {target_provider}")
    return start_migrated_session(session_id, target_provider, prompt, config or load_config())
