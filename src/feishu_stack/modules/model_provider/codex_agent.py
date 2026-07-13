from __future__ import annotations

import os
import json
import subprocess
import time
from pathlib import Path

from feishu_stack.core.settings import StackConfig, load_config
from feishu_stack.core.models import OperationResult
from feishu_stack.core.process import CREATE_NO_WINDOW, process_info, read_pid, start_process, stop_component, write_pid
from feishu_stack.modules.model_provider import codex_config

AGENT_CONTEXT_ENV_KEYS = (
    "OPENCLAW_HOME",
    "CLAW_HOME",
    "HERMES_HOME",
    "LARK_CHANNEL",
)

BUILD_INPUTS = (
    "src",
    "package.json",
    "package-lock.json",
    "tsconfig.json",
)


def _iter_build_inputs(agent_dir: Path):
    for relative in BUILD_INPUTS:
        path = agent_dir / relative
        if path.is_file():
            yield path
        elif path.is_dir():
            yield from (candidate for candidate in path.rglob("*") if candidate.is_file())


def _needs_build(cfg: StackConfig) -> tuple[bool, str]:
    if not cfg.agent_entry.exists():
        return True, "Codex Agent build output is missing."
    entry_mtime = cfg.agent_entry.stat().st_mtime
    for path in _iter_build_inputs(cfg.agent_dir):
        if path.stat().st_mtime > entry_mtime:
            return True, f"Codex Agent build input changed: {path.relative_to(cfg.agent_dir)}"
    return False, "Codex Agent is already built."


def _build_if_needed(cfg: StackConfig) -> tuple[bool, str]:
    needs_build, message = _needs_build(cfg)
    if not needs_build:
        return True, message
    install = subprocess.run([str(cfg.npm_exe), "install"], cwd=cfg.agent_dir, text=True, capture_output=True, creationflags=CREATE_NO_WINDOW)
    if install.returncode != 0:
        return False, install.stderr or install.stdout
    build = subprocess.run([str(cfg.npm_exe), "run", "build"], cwd=cfg.agent_dir, text=True, capture_output=True, creationflags=CREATE_NO_WINDOW)
    if build.returncode != 0:
        return False, build.stderr or build.stdout
    return cfg.agent_entry.exists(), "Codex Agent build complete."


def _build_agent_env(cfg: StackConfig) -> dict[str, str]:
    lark_cli_home = cfg.lark_cli_home or (cfg.stack_root / ".home")
    env = os.environ.copy()
    for key in AGENT_CONTEXT_ENV_KEYS:
        env.pop(key, None)
    env.update(
        {
            "CODEX_HOME": str(cfg.agent.codex_home),
            "CODEX_CLI_BIN": str(cfg.codex_bin),
            "CODEX_CLI_PATH": str(cfg.codex_bin),
            "CODEX_AGENT_ARGS": cfg.agent.codex_agent_args,
            "ACC_STACK_ROOT": str(cfg.stack_root),
            "AGENT_PROVIDER": cfg.agent.provider,
            "AGENT_NAME": "codex",
            "AGENT_MENTION": "Codex",
            "DRY_RUN": "false",
            "LARK_IDENTITY": "bot",
            "LARK_CLI_OUTPUT_ENCODING": "utf-8",
            "LARK_EVENT_TIMEOUT": "8760h",
            "LARK_CLI_BIN": str(cfg.lark_cli_bin),
            "LARK_CLI_CWD": str(cfg.stack_root),
            "HOME": str(lark_cli_home),
            "USERPROFILE": str(lark_cli_home),
            "APPDATA": str(lark_cli_home / "AppData" / "Roaming"),
            "LOCALAPPDATA": str(lark_cli_home / "AppData" / "Local"),
        }
    )
    if cfg.agent.lark_bot_open_id:
        env["LARK_BOT_OPEN_ID"] = cfg.agent.lark_bot_open_id
    if cfg.agent.a2a_bots:
        env["A2A_BOTS"] = json.dumps(cfg.agent.a2a_bots, ensure_ascii=False)
    a2a_relay = cfg.agent.a2a_relay
    if a2a_relay.enabled or any((a2a_relay.group_chat_id, a2a_relay.peer_name, a2a_relay.peer_open_id, a2a_relay.peer_cli_home)):
        env["A2A_RELAY_ENABLED"] = "true" if a2a_relay.enabled else "false"
        relay_values = {
            "A2A_RELAY_GROUP_CHAT_ID": a2a_relay.group_chat_id,
            "A2A_RELAY_PEER_NAME": a2a_relay.peer_name,
            "A2A_RELAY_PEER_OPEN_ID": a2a_relay.peer_open_id,
            "A2A_RELAY_PEER_CLI_HOME": a2a_relay.peer_cli_home,
        }
        for env_key, value in relay_values.items():
            if value:
                env[env_key] = value
    return env


def start(config: StackConfig | None = None) -> OperationResult:
    cfg = config or load_config()
    started = time.monotonic()
    pid = read_pid(cfg.pid_codex_agent)
    running, _ = process_info(pid)
    if running:
        return OperationResult(True, "codex-agent", "start", "Codex Agent is already running.", pid=pid)
    codex_config._bootstrap_agent_config(cfg)
    built, build_message = _build_if_needed(cfg)
    if not built:
        return OperationResult(False, "codex-agent", "start", build_message)
    env = _build_agent_env(cfg)
    proc = start_process(
        [str(cfg.node_exe), "dist\\src\\index.js"],
        cwd=cfg.agent_dir,
        stdout_log=cfg.codex_agent_stdout_log,
        stderr_log=cfg.codex_agent_stderr_log,
        env=env,
    )
    write_pid(cfg.pid_codex_agent, proc.pid)
    time.sleep(3)
    running, _ = process_info(proc.pid)
    duration = int((time.monotonic() - started) * 1000)
    return OperationResult(
        ok=running,
        component="codex-agent",
        action="start",
        message="Codex Agent started." if running else "Codex Agent exited during startup.",
        pid=proc.pid,
        stdout_log=str(cfg.codex_agent_stdout_log),
        stderr_log=str(cfg.codex_agent_stderr_log),
        duration_ms=duration,
    )


def stop(config: StackConfig | None = None) -> OperationResult:
    cfg = config or load_config()
    return stop_component("codex-agent", cfg.pid_codex_agent, None, expected_process_markers=("feishu-codex-agent", "dist\\src\\index.js", "dist/src/index.js"))


def restart(config: StackConfig | None = None) -> OperationResult:
    cfg = config or load_config()
    stop(cfg)
    result = start(cfg)
    result.action = "restart"
    return result
