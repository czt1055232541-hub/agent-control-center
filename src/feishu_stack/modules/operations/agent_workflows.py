from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from feishu_stack.core.settings import StackConfig, load_config, resolve_settings_path


WATCHDOG_SCRIPTS = {"start": "start_scheduler_watchdog.py", "stop": "stop_scheduler_watchdog.py"}
A2A_SCRIPTS = {"sync": "sync_a2a_workflow_files.py", "probe": "lark_multiagent_probe.py"}


def scripts_dir(config: StackConfig | None = None) -> Path:
    cfg = config or load_config()
    return cfg.stack_root / "agent-runtime" / "scripts"


def run_script(script_name: str, arguments: list[str], config: StackConfig | None = None) -> subprocess.CompletedProcess[str]:
    cfg = config or load_config()
    script = scripts_dir(cfg) / script_name
    if not script.exists():
        raise FileNotFoundError(f"Agent workflow script not found: {script}")
    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env["STACK_SETTINGS_PATH"] = str(resolve_settings_path())
    return subprocess.run(
        [str(cfg.python_exe), "-X", "utf8", str(script), *arguments],
        cwd=cfg.stack_root,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=180,
    )


def watchdog_status(config: StackConfig | None = None) -> dict[str, Any]:
    cfg = config or load_config()
    state_dir = cfg.runtime_dir / "watchdogs"
    states: list[dict[str, Any]] = []
    if state_dir.exists():
        for path in sorted(state_dir.glob("*.json")):
            try:
                value = json.loads(path.read_text(encoding="utf-8-sig"))
            except (OSError, json.JSONDecodeError):
                states.append({"state_file": str(path), "status": "invalid"})
                continue
            if isinstance(value, dict):
                value = dict(value)
                value["state_file"] = str(path)
                states.append(value)
    return {"watchdogs": states, "count": len(states), "state_dir": str(state_dir)}
