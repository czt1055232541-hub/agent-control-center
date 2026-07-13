from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from feishu_stack.modules.operations import agent_workflows


def test_watchdog_status_reads_root_runtime(tmp_path: Path) -> None:
    state_dir = tmp_path / "runtime" / "watchdogs"
    state_dir.mkdir(parents=True)
    (state_dir / "task.json").write_text(json.dumps({"task_id": "TASK-1", "status": "waiting"}), encoding="utf-8")
    config = SimpleNamespace(runtime_dir=tmp_path / "runtime")
    result = agent_workflows.watchdog_status(config)
    assert result["count"] == 1
    assert result["watchdogs"][0]["task_id"] == "TASK-1"


def test_scripts_dir_uses_merged_agent_runtime(tmp_path: Path) -> None:
    config = SimpleNamespace(stack_root=tmp_path)
    assert agent_workflows.scripts_dir(config) == tmp_path / "agent-runtime" / "scripts"
