from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

REPO_ROOT = Path(__file__).resolve().parents[1]
LARK_CLI = REPO_ROOT / ".npm-global" / "node_modules" / "@larksuite" / "cli" / "bin" / "lark-cli.exe"
AGENT_HOME = REPO_ROOT / ".home"


def lark_env() -> dict[str, str]:
    env = os.environ.copy()
    home = str(AGENT_HOME)
    env["USERPROFILE"] = home
    env["HOME"] = home
    env["LARK_CLI_HOME"] = str(AGENT_HOME / ".lark-cli")
    env["LARK_CLI_CWD"] = str(REPO_ROOT)
    env["LARK_CLI_OUTPUT_ENCODING"] = "utf-8"
    env.pop("OPENCLAW_HOME", None)
    return env


def run_lark(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(LARK_CLI), *args],
        cwd=REPO_ROOT,
        env=lark_env(),
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )


def list_apps(keywords: list[str]) -> int:
    results = []
    for keyword in keywords:
        result = run_lark(["apps", "+list", "--keyword", keyword, "--as", "user", "--format", "json"])
        item = {
            "keyword": keyword,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
        try:
            item["json"] = json.loads(result.stdout)
            item.pop("stdout", None)
        except json.JSONDecodeError:
            pass
        results.append(item)
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if all(item["returncode"] == 0 for item in results) else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("keywords", nargs="+")
    args = parser.parse_args()

    if args.command == "list":
        return list_apps(args.keywords)
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
