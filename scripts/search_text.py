from __future__ import annotations

import argparse
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

TEXT_SUFFIXES = {".ts", ".js", ".md", ".json", ".env", ".py", ".txt", ".ps1", ".cmd"}


def read_text(path: Path) -> str | None:
    for encoding in ("utf-8", "gb18030"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
        except OSError:
            return None
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("patterns", nargs="+")
    parser.add_argument("--root", action="append")
    parser.add_argument("--max-hits", type=int, default=50)
    args = parser.parse_args()

    total = 0
    roots = args.root or ["agents", "scripts"]
    for root_text in roots:
        root = Path(root_text)
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            text = read_text(path)
            if text is None:
                continue
            hits = []
            for line_number, line in enumerate(text.splitlines(), 1):
                if any(pattern in line for pattern in args.patterns):
                    hits.append((line_number, line[:240]))
            if not hits:
                continue
            total += len(hits)
            print(path)
            for line_number, line in hits[: args.max_hits]:
                print(f"  {line_number}: {line}")
    return 0 if total else 1


if __name__ == "__main__":
    raise SystemExit(main())
