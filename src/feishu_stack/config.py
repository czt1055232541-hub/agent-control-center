from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def find_stack_root(start: Path | None = None) -> Path:
    current = (start or Path(__file__)).resolve()
    for parent in [current, *current.parents]:
        if (parent / "config" / "stack.settings.json").exists():
            return parent
    raise FileNotFoundError("Could not find config/stack.settings.json")


@dataclass(frozen=True)
class StackConfig:
    raw: dict[str, Any]
    stack_root: Path
    codex_home: Path
    codex_bin: Path
    codex_config: Path
    codex_switch_script: Path
    native_model: str
    moonbridge_model: str
    moonbridge_dir: Path
    moonbridge_exe: Path
    moonbridge_config: Path
    moonbridge_port: int
    openclaw_home: Path
    openclaw_gateway_cmd: Path
    openclaw_port: int
    agent_dir: Path
    agent_entry: Path
    lark_cli_bin: Path
    runtime_dir: Path
    log_dir: Path
    pid_dir: Path

    @property
    def pid_openclaw(self) -> Path:
        return self.pid_dir / "openclaw-gateway.pid"

    @property
    def pid_moonbridge(self) -> Path:
        return self.pid_dir / "moonbridge.pid"

    @property
    def pid_codex_agent(self) -> Path:
        return self.pid_dir / "codex-agent.pid"

    @property
    def openclaw_stdout_log(self) -> Path:
        return self.log_dir / "openclaw-gateway-out.log"

    @property
    def openclaw_stderr_log(self) -> Path:
        return self.log_dir / "openclaw-gateway-err.log"

    @property
    def moonbridge_stdout_log(self) -> Path:
        return self.log_dir / "moonbridge-out.log"

    @property
    def moonbridge_stderr_log(self) -> Path:
        return self.log_dir / "moonbridge-err.log"

    @property
    def codex_agent_stdout_log(self) -> Path:
        return self.log_dir / "codex-agent-out.log"

    @property
    def codex_agent_stderr_log(self) -> Path:
        return self.log_dir / "codex-agent-err.log"

    def ensure_runtime_dirs(self) -> None:
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.pid_dir.mkdir(parents=True, exist_ok=True)


def load_config(path: Path | None = None) -> StackConfig:
    settings_path = path or (find_stack_root() / "config" / "stack.settings.json")
    raw = json.loads(settings_path.read_text(encoding="utf-8"))
    stack_root = Path(raw.get("stackRoot") or settings_path.parents[1]).resolve()
    moonbridge = raw["moonbridge"]
    openclaw = raw["openclaw"]
    agent = raw["agent"]
    runtime = raw["runtime"]
    config = StackConfig(
        raw=raw,
        stack_root=stack_root,
        codex_home=Path(raw["codexHome"]),
        codex_bin=Path(raw["codexBin"]),
        codex_config=Path(raw["codexConfig"]),
        codex_switch_script=Path(raw["codexSwitchScript"]),
        native_model=raw["codexNativeModel"],
        moonbridge_model=raw["codexMoonBridgeModel"],
        moonbridge_dir=Path(moonbridge["dir"]),
        moonbridge_exe=Path(moonbridge["exe"]),
        moonbridge_config=Path(moonbridge["config"]),
        moonbridge_port=int(moonbridge["port"]),
        openclaw_home=Path(openclaw["home"]),
        openclaw_gateway_cmd=Path(openclaw["gatewayCmd"]),
        openclaw_port=int(openclaw["port"]),
        agent_dir=Path(agent["dir"]),
        agent_entry=Path(agent["dir"]) / agent["entry"],
        lark_cli_bin=Path(agent["larkCliBin"]),
        runtime_dir=Path(runtime["dir"]),
        log_dir=Path(runtime["logs"]),
        pid_dir=Path(runtime["pids"]),
    )
    config.ensure_runtime_dirs()
    return config

