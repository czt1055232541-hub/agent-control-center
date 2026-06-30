from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


STACK_ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    return subprocess.call(
        [sys.executable, "-X", "utf8", "-m", "feishu_stack.cli", *args],
        cwd=STACK_ROOT,
        env=env,
    )


if __name__ == "__main__":
    raise SystemExit(main())
