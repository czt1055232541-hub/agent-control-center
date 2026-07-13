from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
STACK_WRAPPER = REPO_ROOT / "scripts" / "stack.py"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Show Codex provider status through the Python control-center CLI.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    command = [sys.executable, "-X", "utf8", str(STACK_WRAPPER), "status"]
    if args.json:
        command.append("--json")
    return subprocess.call(command, cwd=REPO_ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
