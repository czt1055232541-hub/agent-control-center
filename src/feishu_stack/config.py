from __future__ import annotations

import json
import logging
import os
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator


_log = logging.getLogger(__name__)


class StackConfigValidation(BaseModel):
    """Pydantic validation for stack.settings.json before StackConfig construction."""
    codex_home: str = Field(alias="codexHome")
    codex_bin: str = Field(alias="codexBin")
    codex_config: str = Field(alias="codexConfig")
    codex_switch_script: str = Field(alias="codexSwitchScript")
    python_exe: str = Field(default="E:\\Python\\python.exe", alias="pythonExe")
    codex_native_model: str = Field(alias="codexNativeModel")
    codex_moonbridge_model: str = Field(alias="codexMoonBridgeModel")
    moonbridge_dir: str
    moonbridge_exe: str
    moonbridge_config: str
    moonbridge_port: int
    openclaw_home: str
    openclaw_gateway_cmd: str
    openclaw_port: int
    agent_dir: str
    agent_entry: str
    lark_cli_bin: str
    runtime_dir: str
    log_dir: str
    pid_dir: str

    @model_validator(mode="after")
    def validate_ports(self) -> "StackConfigValidation":
        for name in ("moonbridge_port", "openclaw_port"):
            port = getattr(self, name)
            if not (1 <= port <= 65535):
                raise ValueError(f"{name} must be 1-65535, got {port}")
        return self

    @model_validator(mode="after")
    def validate_paths_exist(self) -> "StackConfigValidation":
        critical_paths = {
            "codex_home": self.codex_home,
            "codex_bin": self.codex_bin,
            "codex_config": self.codex_config,
            "codex_switch_script": self.codex_switch_script,
            "moonbridge_dir": self.moonbridge_dir,
            "moonbridge_exe": self.moonbridge_exe,
            "moonbridge_config": self.moonbridge_config,
            "openclaw_home": self.openclaw_home,
            "openclaw_gateway_cmd": self.openclaw_gateway_cmd,
            "agent_dir": self.agent_dir,
            "lark_cli_bin": self.lark_cli_bin,
        }
        missing = []
        for name, path_str in critical_paths.items():
            p = Path(path_str)
            if not p.exists():
                missing.append(f"{name}={path_str}")
        if missing:
            _log.warning("paths not found: %s", ", ".join(missing))
        return self


def validate_config(raw: dict[str, Any]) -> StackConfigValidation:
    """Validate raw stack.settings.json with Pydantic."""
    moonbridge = raw.get("moonbridge", {})
    openclaw = raw.get("openclaw", {})
    agent = raw.get("agent", {})
    runtime = raw.get("runtime", {})

    return StackConfigValidation(
        codexHome=raw["codexHome"],
        codexBin=raw["codexBin"],
        codexConfig=raw["codexConfig"],
        codexSwitchScript=raw["codexSwitchScript"],
        pythonExe=raw.get("pythonExe", os.environ.get("PYTHON_EXE", "E:\\Python\\python.exe")),
        codexNativeModel=raw["codexNativeModel"],
        codexMoonBridgeModel=raw["codexMoonBridgeModel"],
        moonbridge_dir=moonbridge["dir"],
        moonbridge_exe=moonbridge["exe"],
        moonbridge_config=moonbridge["config"],
        moonbridge_port=int(moonbridge["port"]),
        openclaw_home=openclaw["home"],
        openclaw_gateway_cmd=openclaw["gatewayCmd"],
        openclaw_port=int(openclaw["port"]),
        agent_dir=agent["dir"],
        agent_entry=agent["entry"],
        lark_cli_bin=agent["larkCliBin"],
        runtime_dir=runtime["dir"],
        log_dir=runtime["logs"],
        pid_dir=runtime["pids"],
    )


def find_stack_root(start: Path | None = None) -> Path:
    current = (start or Path(__file__)).resolve()
    for parent in [current, *current.parents]:
        config_dir = parent / "config"
        if (config_dir / "stack.settings.local.json").exists() or (config_dir / "stack.settings.json").exists():
            return parent
    raise FileNotFoundError("Could not find config/stack.settings.json")


def infer_lark_cli_home(lark_cli_bin: Path, stack_root: Path) -> Path:
    for parent in [lark_cli_bin, *lark_cli_bin.parents]:
        if parent.name == ".npm-global":
            return parent.parent / ".home"
    return stack_root / ".home"


def resolve_codex_bin(configured_bin: str, codex_config: Path) -> Path:
    """Prefer the Codex app-managed CLI path when the app writes one."""
    configured = Path(configured_bin)
    if not codex_config.exists():
        return configured
    try:
        data = tomllib.loads(codex_config.read_text(encoding="utf-8", errors="replace"))
    except tomllib.TOMLDecodeError:
        return configured
    env = (
        data.get("mcp_servers", {})
        .get("node_repl", {})
        .get("env", {})
    )
    codex_cli_path = env.get("CODEX_CLI_PATH") if isinstance(env, dict) else None
    if not codex_cli_path:
        return configured
    candidate = Path(str(codex_cli_path))
    return candidate if candidate.exists() else configured


def resolve_settings_path(path: Path | None = None) -> Path:
    if path is not None:
        return path
    env_path = os.environ.get("STACK_SETTINGS_PATH")
    if env_path:
        return Path(env_path)
    config_dir = find_stack_root() / "config"
    local_path = config_dir / "stack.settings.local.json"
    if local_path.exists():
        return local_path
    return config_dir / "stack.settings.json"


@dataclass(frozen=True)
class StackConfig:
    raw: dict[str, Any]
    stack_root: Path
    codex_home: Path
    codex_bin: Path
    codex_config: Path
    codex_switch_script: Path
    python_exe: Path
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
    lark_cli_home: Path | None = None
    summary_dir: Path | None = None

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

    @property
    def typing_indicator_dir(self) -> Path:
        return self.stack_root / "typing-indicator"

    @property
    def typing_indicator_launcher(self) -> Path:
        return self.typing_indicator_dir / "launcher.py"

    @property
    def pid_typing_indicator(self) -> Path:
        return self.pid_dir / "typing-indicator.pid"

    @property
    def typing_indicator_stdout_log(self) -> Path:
        return self.log_dir / "typing-indicator-out.log"

    @property
    def typing_indicator_stderr_log(self) -> Path:
        return self.log_dir / "typing-indicator-err.log"

    @property
    def migration_summary_dir(self) -> Path:
        return self.summary_dir or (self.runtime_dir / "summaries")

    def ensure_runtime_dirs(self) -> None:
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.pid_dir.mkdir(parents=True, exist_ok=True)
        self.migration_summary_dir.mkdir(parents=True, exist_ok=True)


def load_config(path: Path | None = None) -> StackConfig:
    settings_path = resolve_settings_path(path)
    raw = json.loads(settings_path.read_text(encoding="utf-8"))
    validate_config(raw)  # raises on invalid config
    stack_root = Path(raw.get("stackRoot") or settings_path.parents[1]).resolve()
    moonbridge = raw["moonbridge"]
    openclaw = raw["openclaw"]
    agent = raw["agent"]
    runtime = raw["runtime"]
    codex_config = Path(raw["codexConfig"])
    config = StackConfig(
        raw=raw,
        stack_root=stack_root,
        codex_home=Path(raw["codexHome"]),
        codex_bin=resolve_codex_bin(raw["codexBin"], codex_config),
        codex_config=codex_config,
        codex_switch_script=Path(raw["codexSwitchScript"]),
        python_exe=Path(raw.get("pythonExe") or os.environ.get("PYTHON_EXE") or "E:\\Python\\python.exe"),
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
        lark_cli_home=Path(agent["larkCliHome"]) if agent.get("larkCliHome") else infer_lark_cli_home(Path(agent["larkCliBin"]), stack_root),
        runtime_dir=Path(runtime["dir"]),
        log_dir=Path(runtime["logs"]),
        pid_dir=Path(runtime["pids"]),
        summary_dir=Path(runtime.get("summaries") or Path(runtime["dir"]) / "summaries"),
    )
    config.ensure_runtime_dirs()
    return config
