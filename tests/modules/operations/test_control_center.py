from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from feishu_stack.modules.operations import control_center


def _cfg() -> SimpleNamespace:
    return SimpleNamespace(stack_root=Path(r"F:\1AI\Agent control center"))


def test_control_center_process_match_excludes_agent_stack_processes() -> None:
    cfg = _cfg()
    assert control_center._is_control_center_process(
        {
            "pid": 100,
            "name": "python.exe",
            "exe": r"E:\Python\python.exe",
            "cmdline": r"E:\Python\python.exe -m uvicorn feishu_stack.app:app --host 127.0.0.1 --port 8765",
            "cwd": str(cfg.stack_root),
        },
        cfg,
    )
    for marker in ("openclaw gateway", "codex-agent"):
        assert not control_center._is_control_center_process(
            {
                "pid": 101,
                "name": "python.exe",
                "exe": r"E:\Python\python.exe",
                "cmdline": marker,
                "cwd": str(cfg.stack_root),
            },
            cfg,
        )
