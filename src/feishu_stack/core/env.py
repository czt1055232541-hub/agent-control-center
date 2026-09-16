from __future__ import annotations

import os
from collections.abc import Iterable, Mapping


def _windows_registry_env_value(name: str) -> str | None:
    if os.name != "nt":
        return None
    try:
        import winreg
    except ImportError:
        return None

    locations = (
        (winreg.HKEY_CURRENT_USER, r"Environment"),
        (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
    )
    for root, path in locations:
        try:
            with winreg.OpenKey(root, path) as key:
                value, _ = winreg.QueryValueEx(key, name)
        except FileNotFoundError:
            continue
        except PermissionError:
            continue
        if value:
            return str(value)
    return None


def ensure_env_var(name: str) -> tuple[bool, str]:
    if os.environ.get(name):
        return True, "process"
    value = _windows_registry_env_value(name)
    if value:
        os.environ[name] = value
        return True, "windows-registry"
    return False, "missing"


def env_with_registry_fallback(base: Mapping[str, str], keys: Iterable[str]) -> dict[str, str]:
    env = dict(base)
    for key in keys:
        if env.get(key):
            continue
        value = _windows_registry_env_value(key)
        if value:
            env[key] = value
    return env
