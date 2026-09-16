from __future__ import annotations

import importlib
from pathlib import Path


def test_legacy_module_wrappers_resolve() -> None:
    legacy_modules = [
        "feishu_stack.app",
        "feishu_stack.cli",
        "feishu_stack.config",
        "feishu_stack.openclaw",
        "feishu_stack.codex_agent",
        "feishu_stack.codex_config",
        "feishu_stack.codex_desktop",
        "feishu_stack.codex_provider",
        "feishu_stack.stack_actions",
        "feishu_stack.thread_migration",
    ]

    for module_name in legacy_modules:
        assert importlib.import_module(module_name)


def test_source_uses_modules_layout() -> None:
    package_root = Path(__file__).resolve().parents[2] / "src" / "feishu_stack"
    forbidden = [
        "feishu_stack." + "features",
        "feishu_stack." + "services",
        "feishu_stack." + "integrations",
    ]

    for path in package_root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for needle in forbidden:
            assert needle not in text, f"{needle} remains in {path}"
