from __future__ import annotations

import os
import json
import subprocess
import time

from .config import StackConfig, load_config
from .models import OperationResult
from .process import CREATE_NO_WINDOW, process_info, read_pid, start_process, stop_component, write_pid

AGENT_CONTEXT_ENV_KEYS = (
    "OPENCLAW_HOME",
    "CLAW_HOME",
    "HERMES_HOME",
    "LARK_CHANNEL",
)


def _build_if_needed(cfg: StackConfig) -> tuple[bool, str]:
    if cfg.agent_entry.exists():
        return True, "Codex Agent is already built."
    install = subprocess.run(["npm", "install"], cwd=cfg.agent_dir, text=True, capture_output=True, creationflags=CREATE_NO_WINDOW)
    if install.returncode != 0:
        return False, install.stderr or install.stdout
    build = subprocess.run(["npm", "run", "build"], cwd=cfg.agent_dir, text=True, capture_output=True, creationflags=CREATE_NO_WINDOW)
    if build.returncode != 0:
        return False, build.stderr or build.stdout
    return cfg.agent_entry.exists(), "Codex Agent build complete."


def _build_agent_env(cfg: StackConfig) -> dict[str, str]:
    lark_cli_home = cfg.lark_cli_home or (cfg.stack_root / ".home")
    agent_settings = cfg.raw.get("agent", {})
    env = os.environ.copy()
    for key in AGENT_CONTEXT_ENV_KEYS:
        env.pop(key, None)
    env.update(
        {
            "CODEX_HOME": str(cfg.codex_home),
            "CODEX_CLI_BIN": str(cfg.codex_bin),
            "CODEX_AGENT_ARGS": str(agent_settings.get("codexAgentArgs") or "exec --skip-git-repo-check"),
            "AGENT_PROVIDER": str(agent_settings.get("provider") or "local"),
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
    if agent_settings.get("larkBotOpenId"):
        env["LARK_BOT_OPEN_ID"] = str(agent_settings["larkBotOpenId"])
    if agent_settings.get("a2aBots"):
        env["A2A_BOTS"] = json.dumps(agent_settings["a2aBots"], ensure_ascii=False)
    a2a_relay = agent_settings.get("a2aRelay") or {}
    if a2a_relay:
        env["A2A_RELAY_ENABLED"] = "true" if a2a_relay.get("enabled") else "false"
        relay_env_map = {
            "groupChatId": "A2A_RELAY_GROUP_CHAT_ID",
            "peerName": "A2A_RELAY_PEER_NAME",
            "peerOpenId": "A2A_RELAY_PEER_OPEN_ID",
            "peerCliHome": "A2A_RELAY_PEER_CLI_HOME",
        }
        for key, env_key in relay_env_map.items():
            if a2a_relay.get(key):
                env[env_key] = str(a2a_relay[key])
    return env


def start(config: StackConfig | None = None) -> OperationResult:
    cfg = config or load_config()
    started = time.monotonic()
    pid = read_pid(cfg.pid_codex_agent)
    running, _ = process_info(pid)
    if running:
        return OperationResult(True, "codex-agent", "start", "Codex Agent is already running.", pid=pid)
    built, build_message = _build_if_needed(cfg)
    if not built:
        return OperationResult(False, "codex-agent", "start", build_message)
    env = _build_agent_env(cfg)
    proc = start_process(
        ["node.exe", "dist\\src\\index.js"],
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
    return stop_component("codex-agent", cfg.pid_codex_agent, None)


def restart(config: StackConfig | None = None) -> OperationResult:
    cfg = config or load_config()
    stop(cfg)
    result = start(cfg)
    result.action = "restart"
    return result
