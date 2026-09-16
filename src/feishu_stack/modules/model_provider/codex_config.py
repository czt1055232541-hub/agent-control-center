from __future__ import annotations

import shutil
import time
from pathlib import Path

from feishu_stack.core.settings import StackConfig, load_config
from feishu_stack.core.models import OperationResult
from feishu_stack.core.status import read_provider_status

REASONING_EFFORTS = {"minimal", "low", "medium", "high", "xhigh"}


def _read_lines(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"config.toml not found: {path}")
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


def _write_lines(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _first_section_index(lines: list[str]) -> int:
    for index, line in enumerate(lines):
        if line.lstrip().startswith("["):
            return index
    return len(lines)


def _top_level_value(lines: list[str], key: str) -> str | None:
    section_start = _first_section_index(lines)
    prefix = f"{key}"
    for line in lines[:section_start]:
        stripped = line.strip()
        if stripped.startswith(prefix) and "=" in stripped:
            return stripped.split("=", 1)[1].strip().strip('"')
    return None


def _set_top_level_key(lines: list[str], key: str, value: str) -> list[str]:
    result = list(lines)
    section_start = _first_section_index(result)
    for index in range(section_start):
        if result[index].strip().startswith(f"{key}") and "=" in result[index]:
            result[index] = f"{key} = {value}"
            return result
    insert_at = section_start
    while insert_at > 0 and not result[insert_at - 1].strip():
        insert_at -= 1
    result.insert(insert_at, f"{key} = {value}")
    return result


def _remove_top_level_keys(lines: list[str], keys: set[str]) -> list[str]:
    section_start = _first_section_index(lines)
    result: list[str] = []
    for index, line in enumerate(lines):
        if index < section_start:
            stripped = line.strip()
            if any(stripped.startswith(f"{key}") and "=" in stripped for key in keys):
                continue
        result.append(line)
    return result


def _remove_section(lines: list[str], section_name: str) -> list[str]:
    result: list[str] = []
    skipping = False
    target = f"[{section_name}]"
    for line in lines:
        if line.strip() == target:
            skipping = True
            continue
        if skipping and line.lstrip().startswith("["):
            skipping = False
        if not skipping:
            result.append(line)
    return result


def _append_section(lines: list[str], section_lines: list[str]) -> list[str]:
    result = list(lines)
    while result and not result[-1].strip():
        result.pop()
    result.append("")
    result.extend(section_lines)
    return result


def _timestamp() -> str:
    return time.strftime("%Y%m%d-%H%M%S") + f"-{int((time.time() % 1) * 1000):03d}"


def _target_paths(cfg: StackConfig, target: str) -> tuple[Path, Path, str]:
    if target == "app":
        return cfg.codex_home, cfg.codex_config, "app"
    if target == "agent":
        return cfg.agent.codex_home, cfg.agent.codex_config, "agent"
    raise ValueError(f"Unsupported codex provider target: {target}")


def _bootstrap_agent_config(cfg: StackConfig) -> None:
    agent_home = cfg.agent.codex_home
    agent_config = cfg.agent.codex_config
    agent_home.mkdir(parents=True, exist_ok=True)
    if not agent_config.exists():
        if not cfg.codex_config.exists():
            raise FileNotFoundError(f"Cannot bootstrap Agent Codex config because App config is missing: {cfg.codex_config}")
        agent_config.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(cfg.codex_config, agent_config)
    lines = _read_lines(agent_config)
    replacements = {
        "CODEX_HOME": str(agent_home).replace("\\", "\\\\"),
        "CODEX_CLI_PATH": str(cfg.codex_bin).replace("\\", "\\\\"),
    }
    for key, value in replacements.items():
        lines = [f"{key} = '{value}'" if line.strip().startswith(key) and "=" in line else line for line in lines]
    _write_lines(agent_config, lines)
    for name in ("models_catalog.json", "models_catalog.json.bak-switch"):
        source = cfg.codex_home / name
        target = agent_home / name
        if source.exists() and not target.exists():
            shutil.copy2(source, target)


def _cleanup_backups(codex_home: Path, pattern: str, keep: int, keep_path: Path | None = None) -> int:
    files = sorted(codex_home.glob(pattern), key=lambda path: path.stat().st_mtime, reverse=True)
    removed = 0
    kept = 0
    for path in files:
        if keep_path and path.resolve() == keep_path.resolve():
            kept += 1
            continue
        if kept < keep:
            kept += 1
            continue
        path.unlink(missing_ok=True)
        removed += 1
    return removed


def clean_backups(config: StackConfig | None = None, keep: int = 1) -> OperationResult:
    cfg = config or load_config()
    started = time.monotonic()
    removed_switch = _cleanup_backups(cfg.codex_home, "config.toml.bak-switch-*", keep)
    removed_restore = _cleanup_backups(cfg.codex_home, "config.toml.bak-restore-native-*", keep)
    return OperationResult(
        ok=True,
        component="backups",
        action="clean",
        message=f"Removed switch backups: {removed_switch}; removed restore backups: {removed_restore}; goal backups preserved.",
        duration_ms=int((time.monotonic() - started) * 1000),
    )


def _apply_native(lines: list[str], cfg: StackConfig) -> list[str]:
    result = _set_top_level_key(lines, "model", f'"{cfg.native_model}"')
    result = _set_top_level_key(result, "model_reasoning_effort", f'"{cfg.native_reasoning_effort}"')
    result = _remove_top_level_keys(result, {"model_provider", "model_context_window", "model_max_output_tokens", "model_catalog_json"})
    result = _remove_section(result, "model_providers.moonbridge")
    return _remove_section(result, "model_providers.deepseek")


def _normalize_reasoning_effort(value: str | None, fallback: str = "high") -> str:
    effort = str(value or fallback).strip().lower()
    if effort not in REASONING_EFFORTS:
        raise ValueError(f"Unsupported reasoning effort: {value}. Expected one of: {', '.join(sorted(REASONING_EFFORTS))}")
    return effort


def _apply_deepseek(
    lines: list[str],
    cfg: StackConfig,
    model: str | None = None,
    reasoning_effort: str | None = None,
) -> list[str]:
    target_model = model or cfg.deepseek.model
    target_effort = _normalize_reasoning_effort(reasoning_effort, cfg.deepseek.reasoning_effort)
    result = _set_top_level_key(lines, "model", f'"{target_model}"')
    result = _set_top_level_key(result, "model_provider", '"deepseek"')
    result = _set_top_level_key(result, "model_reasoning_effort", f'"{target_effort}"')
    result = _remove_top_level_keys(result, {"model_context_window", "model_max_output_tokens", "model_catalog_json"})
    result = _remove_section(result, "model_providers.moonbridge")
    result = _remove_section(result, "model_providers.deepseek")
    return _append_section(
        result,
        [
            "[model_providers.deepseek]",
            'name = "DeepSeek"',
            f'base_url = "{cfg.deepseek.base_url}"',
            f'env_key = "{cfg.deepseek.env_key}"',
            'wire_api = "responses"',
        ],
    )


def switch_provider(
    mode: str,
    config: StackConfig | None = None,
    deepseek_model: str | None = None,
    reasoning_effort: str | None = None,
    target: str = "app",
) -> OperationResult:
    if mode not in {"native", "deepseek", "toggle"}:
        raise ValueError(f"Unsupported provider mode: {mode}")
    cfg = config or load_config()
    codex_home, codex_config_path, target_label = _target_paths(cfg, target)
    if target_label == "agent":
        _bootstrap_agent_config(cfg)
    started = time.monotonic()
    current = read_provider_status(cfg, codex_config_path)
    target = "native" if mode == "toggle" and current.mode != "native" else "deepseek" if mode == "toggle" else mode
    lines = _read_lines(codex_config_path)
    backup = codex_home / f"config.toml.bak-switch-{target_label}-{_timestamp()}"
    shutil.copy2(codex_config_path, backup)
    if target == "native":
        new_lines = _apply_native(lines, cfg)
    else:
        new_lines = _apply_deepseek(lines, cfg, deepseek_model, reasoning_effort)
    _write_lines(codex_config_path, new_lines)
    verified = read_provider_status(cfg, codex_config_path)
    if target == "native":
        expected_model = cfg.native_model
    else:
        expected_model = deepseek_model or cfg.deepseek.model
    ok = verified.mode == target and verified.model == expected_model
    _cleanup_backups(codex_home, f"config.toml.bak-switch-{target_label}-*", 1, backup)
    return OperationResult(
        ok=ok,
        component=f"codex-provider-{target_label}",
        action=f"switch-{target}",
        message=f"Switched {target_label} provider from {current.mode}/{current.model} to {verified.mode}/{verified.model}. Backup: {backup}",
        duration_ms=int((time.monotonic() - started) * 1000),
    )
