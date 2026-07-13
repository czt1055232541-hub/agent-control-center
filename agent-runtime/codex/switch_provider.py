from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
STACK_WRAPPER = REPO_ROOT / "scripts" / "stack.py"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Switch Codex provider through the Python control-center CLI.")
    parser.add_argument("mode", nargs="?", choices=["toggle", "native", "moonbridge"], default="toggle")
    parser.add_argument("--allow-unavailable-moonbridge", action="store_true", help="Accepted for compatibility; the control center enforces availability checks.")
    args = parser.parse_args(argv)
    command = [sys.executable, "-X", "utf8", str(STACK_WRAPPER), "switch-provider", args.mode]
    return subprocess.call(command, cwd=REPO_ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
