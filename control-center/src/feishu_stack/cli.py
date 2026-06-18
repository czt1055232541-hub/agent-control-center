from __future__ import annotations

import argparse
import json
import sys
from typing import Callable

from . import backups, codex_agent, codex_desktop, codex_provider, control_center, diagnostics, moonbridge, openclaw, stack_actions
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
        ("start", "codex-desktop"): codex_desktop.start,
        ("stop", "codex-desktop"): codex_desktop.stop,
        ("restart", "codex-desktop"): codex_desktop.restart,
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
        sub.add_argument("component", choices=["openclaw", "moonbridge", "codex-agent", "codex-desktop"])

    switch = subcommands.add_parser("switch-provider", help="Switch Codex provider.")
    switch.add_argument("mode", choices=["native", "moonbridge", "toggle"])

    stack = subcommands.add_parser("stack", help="Run stack actions.")
    stack.add_argument("action", choices=["start-native", "start-moonbridge", "stop"])

    backups_cmd = subcommands.add_parser("backups", help="Backup actions.")
    backups_cmd.add_argument("action", choices=["clean"])

    doctor = subcommands.add_parser("doctor", help="Diagnostics.")
    doctor.add_argument("target", choices=["codex"])

    serve = subcommands.add_parser("serve-control-center", help="Start Control Center API.")
    serve.add_argument("--open", action="store_true", help="Open browser.")
    serve.add_argument("--no-build", action="store_true", help="Do not build the web UI if missing.")

    subcommands.add_parser("stop-control-center", help="Stop Control Center API.")
    subcommands.add_parser("status-control-center", help="Show Control Center status.")
    subcommands.add_parser("install-shortcut", help="Install desktop shortcut command.")
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
        if args.command == "stack":
            table = {
                "start-native": stack_actions.start_native,
                "start-moonbridge": stack_actions.start_moonbridge,
                "stop": stack_actions.stop,
            }
            result = table[args.action]()
            _print(result, args.json)
            return 0 if result.ok else 1
        if args.command == "backups":
            result = backups.clean()
            _print(result, args.json)
            return 0 if result.ok else 1
        if args.command == "doctor":
            _print(diagnostics.codex_doctor(), args.json)
            return 0
        if args.command == "serve-control-center":
            result = control_center.start(open_browser=args.open, build=not args.no_build)
            _print(result, args.json)
            return 0 if result.ok else 1
        if args.command == "stop-control-center":
            result = control_center.stop()
            _print(result, args.json)
            return 0 if result.ok else 1
        if args.command == "status-control-center":
            _print(control_center.status(), args.json)
            return 0
        if args.command == "install-shortcut":
            result = control_center.install_shortcut()
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
