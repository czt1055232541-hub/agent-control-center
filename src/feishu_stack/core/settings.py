from __future__ import annotations

import json
import logging
import os
import shlex
import shutil
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator


_log = logging.getLogger(__name__)
REASONING_EFFORTS = {"minimal", "low", "medium", "high", "xhigh"}


class StackConfigValidation(BaseModel):
    """Pydantic validation for stack settings before StackConfig construction."""
    codex_home: str = Field(alias="codexHome")
    codex_bin: str = Field(alias="codexBin")
    codex_config: str = Field(alias="codexConfig")
    codex_switch_script: str = Field(alias="codexSwitchScript")
    python_exe: str = Field(default_factory=lambda: sys.executable, alias="pythonExe")
    node_exe: str | None = Field(default=None, alias="nodeExe")
    npm_exe: str | None = Field(default=None, alias="npmExe")
    codex_native_model: str = Field(alias="codexNativeModel")
    codex_native_reasoning_effort: str = Field(default="high", alias="codexNativeReasoningEffort")
    codex_deepseek_model: str = Field(default="", alias="codexDeepSeekModel")
    codex_deepseek_reasoning_effort: str = Field(default="high", alias="codexDeepSeekReasoningEffort")
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
        for name in ("openclaw_port",):
            port = getattr(self, name)
            if not (1 <= port <= 65535):
                raise ValueError(f"{name} must be 1-65535, got {port}")
        return self

    @model_validator(mode="after")
    def validate_reasoning_effort(self) -> "StackConfigValidation":
        for name in ("codex_native_reasoning_effort", "codex_deepseek_reasoning_effort"):
            effort = getattr(self, name)
            if effort not in REASONING_EFFORTS:
                raise ValueError(f"{name} must be one of {sorted(REASONING_EFFORTS)}, got {effort}")
        return self

    @model_validator(mode="after")
    def validate_paths_exist(self) -> "StackConfigValidation":
        critical_paths = {
            "codex_home": self.codex_home,
            "codex_bin": self.codex_bin,
            "codex_config": self.codex_config,
            "codex_switch_script": self.codex_switch_script,
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
    """Validate raw stack settings with Pydantic."""
    openclaw = raw.get("openclaw", {})
    agent = raw.get("agent", {})
    runtime = raw.get("runtime", {})

    return StackConfigValidation(
        codexHome=raw["codexHome"],
        codexBin=raw["codexBin"],
        codexConfig=raw["codexConfig"],
        codexSwitchScript=raw["codexSwitchScript"],
        pythonExe=raw.get("pythonExe", os.environ.get("PYTHON_EXE", sys.executable)),
        nodeExe=raw.get("nodeExe"),
        npmExe=raw.get("npmExe"),
        codexNativeModel=raw["codexNativeModel"],
        codexNativeReasoningEffort=raw.get("codexNativeReasoningEffort", "high"),
        codexDeepSeekModel=raw.get("codexDeepSeekModel", ""),
        codexDeepSeekReasoningEffort=raw.get("codexDeepSeekReasoningEffort", "high"),
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
        if (
            (config_dir / "stack.settings.local.json").exists()
            or (config_dir / "stack.settings.example.json").exists()
            or (config_dir / "stack.settings.json").exists()
        ):
            return parent
    raise FileNotFoundError("Could not find config/stack.settings.local.json or config/stack.settings.example.json")


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


def resolve_command(configured: str | None, env_key: str, executable_name: str) -> Path | str:
    if configured:
        candidate = Path(configured)
        if candidate.exists():
            return candidate
    env_value = os.environ.get(env_key)
    if env_value:
        candidate = Path(env_value)
        if candidate.exists():
            return candidate
    found = shutil.which(executable_name)
    return Path(found) if found else executable_name


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
    example_path = config_dir / "stack.settings.example.json"
    if example_path.exists():
        return example_path
    return config_dir / "stack.settings.json"


def _resolve_local_tool_path(value: Any, base: Path) -> Path:
    path = Path(str(value))
    return path if path.is_absolute() else base / path


def _read_local_tool_manifest(tool_dir: Path, manifest_value: Any = None) -> dict[str, Any]:
    candidates: list[Path] = []
    if manifest_value:
        manifest_path = Path(str(manifest_value))
        candidates.append(manifest_path if manifest_path.is_absolute() else tool_dir / manifest_path)
    candidates.extend([tool_dir / "acc.local-tool.json", tool_dir / "local-tool.json"])
    for candidate in candidates:
        if not candidate.exists():
            continue
        try:
            data = json.loads(candidate.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as exc:
            _log.warning("failed to read local tool manifest %s: %s", candidate, exc)
            continue
        if isinstance(data, dict):
            return {**data, "_manifest_path": str(candidate)}
    return {}


def _first_tool_value(item: dict[str, Any], manifest: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in item and item[key] not in (None, ""):
            return item[key]
    for key in keys:
        if key in manifest and manifest[key] not in (None, ""):
            return manifest[key]
    return default


def _local_tool_settings(raw: dict[str, Any], stack_root: Path, default_python: Path) -> list["LocalToolSettings"]:
    local_tools = raw.get("localTools", {}) if isinstance(raw.get("localTools", {}), dict) else {}
    tools = local_tools.get("tools", []) if isinstance(local_tools.get("tools", []), list) else []
    parsed: list[LocalToolSettings] = []
    for item in tools:
        if not isinstance(item, dict):
            continue
        provisional_id = str(item.get("id") or "").strip()
        tool_dir = Path(str(item.get("dir") or stack_root / "projects" / provisional_id))
        if not tool_dir.is_absolute():
            tool_dir = stack_root / tool_dir
        manifest = _read_local_tool_manifest(tool_dir, item.get("manifest"))
        tool_id = str(_first_tool_value(item, manifest, "id", default="")).strip()
        if not tool_id:
            continue
        entry = str(_first_tool_value(item, manifest, "entry", default="app.py"))
        runtime = str(_first_tool_value(item, manifest, "runtime", "kind", default="python"))
        command = _first_tool_value(item, manifest, "command")
        if isinstance(command, list) and command:
            command_parts = [str(part) for part in command]
        elif isinstance(command, str) and command.strip():
            command_parts = shlex.split(command, posix=os.name != "nt")
        else:
            python_exe = _first_tool_value(item, manifest, "pythonExe", default=default_python)
            node_exe = _first_tool_value(item, manifest, "nodeExe", default=raw.get("nodeExe") or "node")
            if runtime in {"node", "javascript", "js"}:
                command_parts = [str(node_exe), entry]
            else:
                command_parts = [str(python_exe), entry]
        host = str(_first_tool_value(item, manifest, "host", default="127.0.0.1"))
        port = int(_first_tool_value(item, manifest, "port", default=0) or 0)
        url = str(_first_tool_value(item, manifest, "url", default=f"http://{host}:{port}"))
        env = item.get("env", {}) if isinstance(item.get("env", {}), dict) else {}
        manifest_env = manifest.get("env", {}) if isinstance(manifest.get("env", {}), dict) else {}
        merged_env = {**{str(k): str(v) for k, v in manifest_env.items()}, **{str(k): str(v) for k, v in env.items()}}
        open_path = str(_first_tool_value(item, manifest, "openPath", "open_path", default="/"))
        if not open_path.startswith("/"):
            open_path = f"/{open_path}"
        source = str(_first_tool_value(item, manifest, "source", default="manifest" if manifest else "stack-settings"))
        raw_tags = _first_tool_value(item, manifest, "tags", default=[])
        parsed.append(
            LocalToolSettings(
                id=tool_id,
                name=str(_first_tool_value(item, manifest, "name", default=tool_id)),
                description=str(_first_tool_value(item, manifest, "description", default="")),
                dir=tool_dir,
                entry=_resolve_local_tool_path(entry, tool_dir),
                command=command_parts,
                host=host,
                port=port,
                url=url.rstrip("/"),
                health_path=str(_first_tool_value(item, manifest, "healthPath", "health_path", default="/api/health")),
                open_path=open_path,
                runtime=runtime,
                source=source,
                manifest_path=Path(manifest["_manifest_path"]) if manifest.get("_manifest_path") else None,
                enabled=bool(_first_tool_value(item, manifest, "enabled", default=True)),
                embed=bool(_first_tool_value(item, manifest, "embed", default=True)),
                tags=[str(tag) for tag in raw_tags] if isinstance(raw_tags, list) else [],
                env=merged_env,
            )
        )
    return parsed


@dataclass(frozen=True)
class ToolchainSettings:
    python_exe: Path
    node_exe: Path | str
    npm_exe: Path | str


@dataclass(frozen=True)
class CodexSettings:
    home: Path
    bin: Path
    config: Path
    switch_script: Path
    native_model: str
    native_reasoning_effort: str
    deepseek_model: str
    deepseek_reasoning_effort: str


@dataclass(frozen=True)
class DeepSeekSettings:
    base_url: str
    env_key: str
    model: str
    models: list[str]
    reasoning_effort: str


@dataclass(frozen=True)
class OpenClawSettings:
    home: Path
    gateway_cmd: Path
    port: int
    a2a_bots: list[dict[str, Any]]


@dataclass(frozen=True)
class A2ARelaySettings:
    enabled: bool = False
    group_chat_id: str = ""
    peer_name: str = ""
    peer_open_id: str = ""
    peer_cli_home: str = ""


@dataclass(frozen=True)
class AgentSettings:
    dir: Path
    entry: Path
    provider: str
    codex_home: Path
    codex_config: Path
    codex_agent_args: str
    lark_cli_bin: Path
    lark_cli_home: Path | None
    lark_cli_profile: str
    lark_bot_open_id: str
    a2a_bots: list[dict[str, Any]]
    a2a_relay: A2ARelaySettings


@dataclass(frozen=True)
class RuntimeSettings:
    dir: Path
    logs: Path
    pids: Path
    summaries: Path


@dataclass(frozen=True)
class LocalToolSettings:
    id: str
    name: str
    description: str
    dir: Path
    entry: Path
    command: list[str]
    host: str
    port: int
    url: str
    health_path: str
    open_path: str = "/"
    runtime: str = "python"
    source: str = "stack-settings"
    manifest_path: Path | None = None
    enabled: bool = True
    embed: bool = True
    tags: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)


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
    native_reasoning_effort: str
    openclaw_home: Path
    openclaw_gateway_cmd: Path
    openclaw_port: int
    agent_dir: Path
    agent_entry: Path
    agent_codex_home: Path
    agent_codex_config: Path
    lark_cli_bin: Path
    runtime_dir: Path
    log_dir: Path
    pid_dir: Path
    deepseek_model: str = ""
    deepseek_models: list[str] = field(default_factory=list)
    app_id: str = ""
    app_name: str = ""
    projects_root: Path | None = None
    lark_cli_home: Path | None = None
    summary_dir: Path | None = None
    watchdog_state_dir: Path | None = None
    node_exe: Path | str = "node"
    npm_exe: Path | str = "npm"
    deepseek_reasoning_effort: str = "high"
    local_tools: list[LocalToolSettings] = field(default_factory=list)
    toolchain: ToolchainSettings = field(init=False)
    codex: CodexSettings = field(init=False)
    deepseek: DeepSeekSettings = field(init=False)
    openclaw: OpenClawSettings = field(init=False)
    agent: AgentSettings = field(init=False)
    runtime: RuntimeSettings = field(init=False)

    def __post_init__(self) -> None:
        raw = self.raw if isinstance(self.raw, dict) else {}
        agent_settings = raw.get("agent", {}) if isinstance(raw.get("agent", {}), dict) else {}
        openclaw_settings = raw.get("openclaw", {}) if isinstance(raw.get("openclaw", {}), dict) else {}
        relay = agent_settings.get("a2aRelay", {}) if isinstance(agent_settings.get("a2aRelay", {}), dict) else {}
        summary_dir = self.summary_dir or (self.runtime_dir / "summaries")
        object.__setattr__(self, "toolchain", ToolchainSettings(self.python_exe, self.node_exe, self.npm_exe))
        object.__setattr__(
            self,
            "codex",
            CodexSettings(
                home=self.codex_home,
                bin=self.codex_bin,
                config=self.codex_config,
                switch_script=self.codex_switch_script,
                native_model=self.native_model,
                native_reasoning_effort=self.native_reasoning_effort,
                deepseek_model=self.deepseek_model,
                deepseek_reasoning_effort=self.deepseek_reasoning_effort,
            ),
        )
        deepseek_settings = raw.get("deepseek", {}) if isinstance(raw.get("deepseek", {}), dict) else {}
        deepseek_models = self.deepseek_models or [self.deepseek_model]
        object.__setattr__(
            self,
            "deepseek",
            DeepSeekSettings(
                base_url=str(deepseek_settings.get("baseUrl") or raw.get("deepSeekBaseUrl") or "https://api.deepseek.com"),
                env_key=str(deepseek_settings.get("envKey") or raw.get("deepSeekEnvKey") or "DEEPSEEK_API_KEY"),
                model=self.deepseek_model,
                models=[model for model in deepseek_models if model],
                reasoning_effort=self.deepseek_reasoning_effort,
            ),
        )
        object.__setattr__(
            self,
            "openclaw",
            OpenClawSettings(
                home=self.openclaw_home,
                gateway_cmd=self.openclaw_gateway_cmd,
                port=self.openclaw_port,
                a2a_bots=list(openclaw_settings.get("a2aBots") or []),
            ),
        )
        object.__setattr__(
            self,
            "agent",
            AgentSettings(
                dir=self.agent_dir,
                entry=self.agent_entry,
                provider=str(agent_settings.get("provider") or "codex"),
                codex_home=self.agent_codex_home,
                codex_config=self.agent_codex_config,
                codex_agent_args=str(agent_settings.get("codexAgentArgs") or "exec --skip-git-repo-check"),
                lark_cli_bin=self.lark_cli_bin,
                lark_cli_home=self.lark_cli_home,
                lark_cli_profile=str(agent_settings.get("larkCliProfile") or ""),
                lark_bot_open_id=str(agent_settings.get("larkBotOpenId") or ""),
                a2a_bots=list(agent_settings.get("a2aBots") or []),
                a2a_relay=A2ARelaySettings(
                    enabled=bool(relay.get("enabled", False)),
                    group_chat_id=str(relay.get("groupChatId") or ""),
                    peer_name=str(relay.get("peerName") or ""),
                    peer_open_id=str(relay.get("peerOpenId") or ""),
                    peer_cli_home=str(relay.get("peerCliHome") or ""),
                ),
            ),
        )
        object.__setattr__(self, "runtime", RuntimeSettings(self.runtime_dir, self.log_dir, self.pid_dir, summary_dir))

    @property
    def pid_openclaw(self) -> Path:
        return self.pid_dir / "openclaw-gateway.pid"

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
    def codex_agent_stdout_log(self) -> Path:
        return self.log_dir / "codex-agent-out.log"

    @property
    def codex_agent_stderr_log(self) -> Path:
        return self.log_dir / "codex-agent-err.log"

    @property
    def typing_indicator_dir(self) -> Path:
        return self.stack_root / "agent-runtime" / "typing-indicator"

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

    def local_tool_pid(self, tool_id: str) -> Path:
        return self.pid_dir / f"local-tool-{tool_id}.pid"

    def local_tool_stdout_log(self, tool_id: str) -> Path:
        return self.log_dir / f"local-tool-{tool_id}-out.log"

    def local_tool_stderr_log(self, tool_id: str) -> Path:
        return self.log_dir / f"local-tool-{tool_id}-err.log"


def load_config(path: Path | None = None) -> StackConfig:
    settings_path = resolve_settings_path(path)
    raw = json.loads(settings_path.read_text(encoding="utf-8-sig"))
    validate_config(raw)  # raises on invalid config
    stack_root = Path(raw.get("stackRoot") or settings_path.parents[1]).resolve()
    openclaw = raw["openclaw"]
    agent = raw["agent"]
    runtime = raw["runtime"]
    codex_config = Path(raw["codexConfig"])
    configured_port = int(openclaw["port"])
    openclaw_json_port = _read_openclaw_json_port(Path(openclaw["home"]))
    if openclaw_json_port is not None and configured_port != openclaw_json_port:
        _log.warning(
            "openclaw.port %d differs from openclaw.json gateway.port %d; "
            "stack.settings value is used, update it to match when upstream changes.",
            configured_port,
            openclaw_json_port,
        )
    config = StackConfig(
        raw=raw,
        stack_root=stack_root,
        codex_home=Path(raw["codexHome"]),
        codex_bin=resolve_codex_bin(raw["codexBin"], codex_config),
        codex_config=codex_config,
        codex_switch_script=Path(raw["codexSwitchScript"]),
        python_exe=Path(raw.get("pythonExe") or os.environ.get("PYTHON_EXE") or sys.executable),
        node_exe=resolve_command(raw.get("nodeExe"), "NODE_EXE", "node.exe" if os.name == "nt" else "node"),
        npm_exe=resolve_command(raw.get("npmExe"), "NPM_EXE", "npm.cmd" if os.name == "nt" else "npm"),
        native_model=raw["codexNativeModel"],
        native_reasoning_effort=str(raw.get("codexNativeReasoningEffort") or "high"),
        deepseek_model=str(raw.get("codexDeepSeekModel") or "deepseek-v4-pro"),
        deepseek_models=[str(item) for item in raw.get("codexDeepSeekModels", [])] if isinstance(raw.get("codexDeepSeekModels"), list) else [],
        deepseek_reasoning_effort=str(raw.get("codexDeepSeekReasoningEffort") or "high"),
        openclaw_home=Path(openclaw["home"]),
        openclaw_gateway_cmd=Path(openclaw["gatewayCmd"]),
        openclaw_port=configured_port,
        agent_dir=Path(agent["dir"]),
        agent_entry=Path(agent["dir"]) / agent["entry"],
        agent_codex_home=Path(agent.get("codexHome") or (stack_root / "agent-runtime" / "codex-home")),
        agent_codex_config=Path(agent.get("codexConfig") or (Path(agent.get("codexHome") or (stack_root / "agent-runtime" / "codex-home")) / "config.toml")),
        lark_cli_bin=Path(agent["larkCliBin"]),
        lark_cli_home=Path(agent["larkCliHome"]) if agent.get("larkCliHome") else infer_lark_cli_home(Path(agent["larkCliBin"]), stack_root),
        runtime_dir=Path(runtime["dir"]),
        log_dir=Path(runtime["logs"]),
        pid_dir=Path(runtime["pids"]),
        app_id=str(raw.get("appId") or raw.get("app_id") or ""),
        app_name=str(raw.get("appName") or raw.get("app_name") or ""),
        projects_root=Path(raw["projectsRoot"]) if raw.get("projectsRoot") else None,
        summary_dir=Path(runtime.get("summaries") or Path(runtime["dir"]) / "summaries"),
        watchdog_state_dir=Path(agent.get("watchdogStateDir") or raw["watchdogStateDir"]) if (agent.get("watchdogStateDir") or raw.get("watchdogStateDir")) else None,
        local_tools=_local_tool_settings(raw, stack_root, Path(raw.get("pythonExe") or os.environ.get("PYTHON_EXE") or sys.executable)),
    )
    config.ensure_runtime_dirs()
    return config


def _read_openclaw_json_port(openclaw_home: Path) -> int | None:
    """Read the gateway port from the upstream openclaw.json config.

    Returns None when the config file is missing or unreadable.
    This is the port OpenClaw itself believes it should run on.
    """
    config_path = openclaw_home / ".openclaw" / "openclaw.json"
    if not config_path.exists():
        return None
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    port = data.get("gateway", {}).get("port")
    if isinstance(port, int) and 1 <= port <= 65535:
        return port
    if isinstance(port, str):
        try:
            p = int(port)
            if 1 <= p <= 65535:
                return p
        except ValueError:
            pass
    return None
