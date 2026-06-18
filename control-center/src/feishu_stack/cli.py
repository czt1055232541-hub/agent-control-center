from __future__ import annotations

import argparse
import json
import sys
from typing import Callable

from . import codex_agent, codex_provider, moonbridge, openclaw
from .config import load_config
from .models import OperationResult, to_dict
from .status import get_status


ComponentFn = Callable[[], OperationResult]


def _print(value: object, json_output: bool) -> None:
    if json_output:
        print(json.dumps(to_dict(value), ensure_ascii=False, indent=2))
        return
    if isinstance(value, OperationResult):
        print(f"{value.component} {value.action}: {'ok' if value.ok else 'failed'}")
        print(value.message)
        if value.pid is not None:
            print(f"pid: {value.pid}")
        if value.port is not None:
            print(f"port: {value.port}")
        if value.stdout_log:
            print(f"stdout: {value.stdout_log}")
        if value.stderr_log:
            print(f"stderr: {value.stderr_log}")
        print(f"duration_ms: {value.duration_ms}")
        return
    print(json.dumps(to_dict(value), ensure_ascii=False, indent=2))


def _component_action(action: str, component: str) -> OperationResult:
    table: dict[tuple[str, str], ComponentFn] = {
        ("start", "openclaw"): openclaw.start,
        ("stop", "openclaw"): openclaw.stop,
        ("restart", "openclaw"): openclaw.restart,
        ("start", "moonbridge"): moonbridge.start,
        ("stop", "moonbridge"): moonbridge.stop,
        ("restart", "moonbridge"): moonbridge.restart,
        ("start", "codex-agent"): codex_agent.start,
        ("stop", "codex-agent"): codex_agent.stop,
        ("restart", "codex-agent"): codex_agent.restart,
    }
    try:
        return table[(action, component)]()
    except KeyError as exc:
        raise SystemExit(f"Unsupported component/action: {action} {component}") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="feishu-stack")
    parser.add_argument("--json", action="store_true", help="Print stable JSON output.")
    subcommands = parser.add_subparsers(dest="command", required=True)

    subcommands.add_parser("status", help="Show stack status.")

    for action in ("start", "stop", "restart"):
        sub = subcommands.add_parser(action, help=f"{action.title()} a component.")
        sub.add_argument("component", choices=["openclaw", "moonbridge", "codex-agent"])

    switch = subcommands.add_parser("switch-provider", help="Switch Codex provider.")
    switch.add_argument("mode", choices=["native", "moonbridge"])
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    json_output = False
    if "--json" in argv:
        json_output = True
        argv = [item for item in argv if item != "--json"]
    parser = build_parser()
    args = parser.parse_args(argv)
    args.json = args.json or json_output
    try:
        load_config()
        if args.command == "status":
            _print(get_status(), args.json)
            return 0
        if args.command in {"start", "stop", "restart"}:
            result = _component_action(args.command, args.component)
            _print(result, args.json)
            return 0 if result.ok else 1
        if args.command == "switch-provider":
            result = codex_provider.switch_provider(args.mode)
            _print(result, args.json)
            return 0 if result.ok else 1
    except Exception as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"error: {exc}", file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
