from __future__ import annotations

import shutil
import time
import urllib.request
from pathlib import Path

from .config import StackConfig, load_config
from .models import OperationResult
from .status import read_provider_status


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


def _moonbridge_ready(cfg: StackConfig, timeout: int = 3) -> bool:
    url = str(cfg.raw.get("moonBridgeBaseUrl") or f"http://127.0.0.1:{cfg.moonbridge_port}/v1").rstrip("/") + "/models"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return 200 <= response.status < 500
    except Exception:
        return False


def _apply_native(lines: list[str], cfg: StackConfig) -> list[str]:
    result = _set_top_level_key(lines, "model", f'"{cfg.native_model}"')
    result = _remove_top_level_keys(result, {"model_provider", "model_context_window", "model_max_output_tokens", "model_catalog_json"})
    return _remove_section(result, "model_providers.moonbridge")


def _apply_moonbridge(lines: list[str], cfg: StackConfig, allow_unavailable: bool = False) -> list[str]:
    if not allow_unavailable and not _moonbridge_ready(cfg):
        raise RuntimeError(f"MoonBridge is not reachable at 127.0.0.1:{cfg.moonbridge_port}.")
    catalog = cfg.codex_home / "models_catalog.json"
    catalog_source = cfg.codex_home / "models_catalog.json.bak-switch"
    if not catalog.exists() and catalog_source.exists():
        shutil.copy2(catalog_source, catalog)
    if not catalog.exists():
        raise FileNotFoundError(f"MoonBridge model catalog not found: {catalog}")
    catalog_toml = str(catalog).replace("\\", "\\\\")
    base_url = str(cfg.raw.get("moonBridgeBaseUrl") or f"http://127.0.0.1:{cfg.moonbridge_port}/v1")
    result = _set_top_level_key(lines, "model", f'"{cfg.moonbridge_model}"')
    result = _set_top_level_key(result, "model_provider", '"moonbridge"')
    result = _set_top_level_key(result, "model_context_window", "1000000")
    result = _set_top_level_key(result, "model_catalog_json", f'"{catalog_toml}"')
    result = _remove_section(result, "model_providers.moonbridge")
    return _append_section(
        result,
        [
            "[model_providers.moonbridge]",
            'name = "Moon Bridge"',
            f'base_url = "{base_url}"',
            'wire_api = "responses"',
        ],
    )


def switch_provider(mode: str, config: StackConfig | None = None, allow_unavailable_moonbridge: bool = False) -> OperationResult:
    if mode not in {"native", "moonbridge", "toggle"}:
        raise ValueError(f"Unsupported provider mode: {mode}")
    cfg = config or load_config()
    started = time.monotonic()
    current = read_provider_status(cfg)
    target = "native" if mode == "toggle" and current.mode == "moonbridge" else "moonbridge" if mode == "toggle" else mode
    lines = _read_lines(cfg.codex_config)
    backup = cfg.codex_home / f"config.toml.bak-switch-{_timestamp()}"
    shutil.copy2(cfg.codex_config, backup)
    new_lines = _apply_native(lines, cfg) if target == "native" else _apply_moonbridge(lines, cfg, allow_unavailable_moonbridge)
    _write_lines(cfg.codex_config, new_lines)
    verified = read_provider_status(cfg)
    ok = verified.mode == target and ((target == "native" and verified.model == cfg.native_model) or (target == "moonbridge" and verified.model == cfg.moonbridge_model))
    _cleanup_backups(cfg.codex_home, "config.toml.bak-switch-*", 1, backup)
    return OperationResult(
        ok=ok,
        component="codex-provider",
        action=f"switch-{target}",
        message=f"Switched provider from {current.mode}/{current.model} to {verified.mode}/{verified.model}. Backup: {backup}",
        duration_ms=int((time.monotonic() - started) * 1000),
    )
