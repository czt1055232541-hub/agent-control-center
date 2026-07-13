from __future__ import annotations

import json
import time
from pathlib import Path

import yaml

from feishu_stack.core.settings import StackConfig, load_config, resolve_settings_path
from feishu_stack.core.models import OperationResult
from feishu_stack.core.process import is_port_listening, start_process, stop_component, wait_for_port, write_pid

SETTINGS_PATH: Path | None = None
REASONING_EFFORTS = {"minimal", "low", "medium", "high", "xhigh"}


def _get_settings_path(cfg: StackConfig) -> Path:
    global SETTINGS_PATH
    if SETTINGS_PATH is not None:
        return SETTINGS_PATH
    SETTINGS_PATH = resolve_settings_path()
    return SETTINGS_PATH


def _read_moonbridge_yaml(cfg: StackConfig) -> dict:
    """Read moonbridge config YAML as a dict."""
    with open(cfg.moonbridge_config, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _write_moonbridge_yaml(cfg: StackConfig, data: dict) -> None:
    """Write moonbridge config YAML, preserving basic structure."""
    with open(cfg.moonbridge_config, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def get_available_models(config: StackConfig | None = None) -> list[str]:
    """Return available model names from moonbridge config."""
    cfg = config or load_config()
    data = _read_moonbridge_yaml(cfg)
    models = data.get("models", {})
    return list(models.keys())


def _normalize_reasoning_effort(value: str | None, fallback: str = "high") -> str:
    effort = str(value or fallback).strip().lower()
    if effort not in REASONING_EFFORTS:
        raise ValueError(f"Unsupported reasoning effort: {value}. Expected one of: {', '.join(sorted(REASONING_EFFORTS))}")
    return effort


def _update_stack_settings(settings_path: Path, model: str, reasoning_effort: str) -> None:
    if not settings_path.exists():
        return
    settings = json.loads(settings_path.read_text(encoding="utf-8-sig"))
    settings["codexMoonBridgeModel"] = model
    settings["codexMoonBridgeReasoningEffort"] = reasoning_effort
    settings_path.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def switch_model(model: str, config: StackConfig | None = None, reasoning_effort: str | None = None) -> OperationResult:
    """Switch the active moonbridge model and restart.

    1. Validate model exists in moonbridge config YAML
    2. Update routes.moonbridge.model in moonbridge config YAML
    3. Update codexMoonBridgeModel in the active stack settings file
    4. Update codex TOML model field if currently in moonbridge mode
    5. Restart moonbridge
    """
    cfg = config or load_config()
    started = time.monotonic()
    target_effort = _normalize_reasoning_effort(reasoning_effort, getattr(cfg, "moonbridge_reasoning_effort", "high"))

    data = _read_moonbridge_yaml(cfg)
    available = list(data.get("models", {}).keys())
    if model not in available:
        return OperationResult(
            False, "moonbridge", "switch-model",
            f"Unknown model '{model}'. Available: {', '.join(available)}",
            port=cfg.moonbridge_port,
        )

    current_model = data.get("routes", {}).get("moonbridge", {}).get("model", "unknown")
    current_effort = getattr(cfg, "moonbridge_reasoning_effort", "high")
    if current_model == model and current_effort == target_effort:
        return OperationResult(
            True, "moonbridge", "switch-model",
            f"Model is already '{model}' with reasoning effort '{target_effort}'. No change needed.",
            port=cfg.moonbridge_port,
        )

    data.setdefault("routes", {}).setdefault("moonbridge", {})["model"] = model
    _write_moonbridge_yaml(cfg, data)

    settings_path = _get_settings_path(cfg)
    _update_stack_settings(settings_path, model, target_effort)

    from feishu_stack.core.status import read_provider_status
    prov_status = read_provider_status(cfg)
    if prov_status.mode == "moonbridge":
        from feishu_stack.modules.model_provider.codex_config import switch_provider
        try:
            switch_provider(
                "moonbridge",
                cfg,
                allow_unavailable_moonbridge=True,
                moonbridge_model=model,
                reasoning_effort=target_effort,
            )
        except Exception as exc:
            return OperationResult(
                False,
                "moonbridge",
                "switch-model",
                f"MoonBridge model changed, but Codex config sync failed: {exc}",
                port=cfg.moonbridge_port,
                duration_ms=int((time.monotonic() - started) * 1000),
            )

    result = restart(cfg)
    result.action = "switch-model"
    result.message = f"Switched model '{current_model}' -> '{model}' with reasoning effort '{target_effort}'. MoonBridge restarted."
    result.duration_ms = int((time.monotonic() - started) * 1000)
    return result


def start(config: StackConfig | None = None) -> OperationResult:
    cfg = config or load_config()
    started = time.monotonic()
    if is_port_listening(cfg.moonbridge_port):
        return OperationResult(True, "moonbridge", "start", "MoonBridge is already listening.", port=cfg.moonbridge_port)
    proc = start_process(
        [str(cfg.moonbridge_exe), "-config", str(cfg.moonbridge_config)],
        cwd=cfg.moonbridge_dir,
        stdout_log=cfg.moonbridge_stdout_log,
        stderr_log=cfg.moonbridge_stderr_log,
    )
    write_pid(cfg.pid_moonbridge, proc.pid)
    ready = wait_for_port(cfg.moonbridge_port, True)
    duration = int((time.monotonic() - started) * 1000)
    return OperationResult(
        ok=ready,
        component="moonbridge",
        action="start",
        message="MoonBridge started." if ready else "MoonBridge did not become ready.",
        pid=proc.pid,
        port=cfg.moonbridge_port,
        stdout_log=str(cfg.moonbridge_stdout_log),
        stderr_log=str(cfg.moonbridge_stderr_log),
        duration_ms=duration,
    )


def stop(config: StackConfig | None = None) -> OperationResult:
    cfg = config or load_config()
    return stop_component("moonbridge", cfg.pid_moonbridge, cfg.moonbridge_port, expected_process_markers=("moonbridge",))


def restart(config: StackConfig | None = None) -> OperationResult:
    cfg = config or load_config()
    stop(cfg)
    result = start(cfg)
    result.action = "restart"
    return result
