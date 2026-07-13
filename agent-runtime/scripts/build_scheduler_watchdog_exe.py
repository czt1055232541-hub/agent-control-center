from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
STACK_ROOT = REPO_ROOT.parent
ENTRY = REPO_ROOT / "scripts" / "scheduler_watchdog.py"
DIST = STACK_ROOT / "runtime" / "tools"
BUILD = STACK_ROOT / "runtime" / "build" / "scheduler-watchdog"


def main() -> int:
    DIST.mkdir(parents=True, exist_ok=True)
    BUILD.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--clean",
        "--name",
        "scheduler-watchdog-current",
        "--distpath",
        str(DIST),
        "--workpath",
        str(BUILD),
        str(ENTRY),
    ]
    result = subprocess.run(command, cwd=REPO_ROOT, text=True)
    if result.returncode == 0:
        print(DIST / "scheduler-watchdog-current.exe")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
