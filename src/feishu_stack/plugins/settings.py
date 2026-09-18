"""Framework-owned plugin preferences; changes take effect on the next start."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import tempfile
from threading import RLock

from feishu_stack.core.settings import resolve_settings_path
from feishu_stack.plugin_runtime import PluginRegistry

_lock = RLock()


def settings_path() -> Path:
    return resolve_settings_path().parent / "plugin-settings.local.json"


def configured_disabled() -> tuple[str, ...]:
    path = settings_path()
    if not path.exists():
        return ()
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError("Invalid plugin settings version")
    disabled = data.get("disabled")
    if not isinstance(disabled, list) or any(not isinstance(p, str) or not p or p != p.strip() for p in disabled):
        raise ValueError("Plugin settings disabled must be a list of plugin IDs")
    return tuple(sorted(set(disabled)))


def effective_disabled() -> tuple[str, ...]:
    # Presence, even an empty value, explicitly overrides the saved preference.
    if "ACC_DISABLED_PLUGINS" in os.environ:
        return tuple(sorted({p.strip() for p in os.environ["ACC_DISABLED_PLUGINS"].split(",") if p.strip()}))
    return configured_disabled()


def snapshot(registry: PluginRegistry) -> dict:
    configured = set(configured_disabled())
    effective = set(effective_disabled())
    running = {p.id for p in registry.resolve()}
    return {
        "plugins": [{"id": p.id, "name": p.name, "description": p.description,
                     "kind": p.kind, "requires": list(p.requires),
                     "configured_enabled": p.id not in configured,
                     "next_start_enabled": p.id not in effective,
                     "running_enabled": p.id in running} for p in registry.installed],
        "disabled": sorted(configured),
        "environment_override": "ACC_DISABLED_PLUGINS" in os.environ,
        "restart_required": running != {p.id for p in registry.installed if p.id not in effective},
    }


def save_disabled(registry: PluginRegistry, disabled: list[str]) -> dict:
    with _lock:
        if "ACC_DISABLED_PLUGINS" in os.environ:
            raise RuntimeError("ACC_DISABLED_PLUGINS overrides saved settings; remove it and restart ACC before editing.")
        PluginRegistry(registry.installed, disabled=disabled).resolve()
        path = settings_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, prefix=".plugin-settings-", suffix=".tmp", delete=False) as output:
                temporary = Path(output.name)
                json.dump({"version": 1, "disabled": sorted(set(disabled))}, output, ensure_ascii=False, indent=2)
                output.write("\n")
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return snapshot(registry)
