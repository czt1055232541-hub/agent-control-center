from __future__ import annotations

import argparse
import csv
import io
import subprocess
import sys
import time


def tcp_pids_for_port(port: int) -> set[int]:
    output = subprocess.run(
        ["netstat", "-ano", "-p", "tcp"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
    ).stdout
    pids: set[int] = set()
    for line in output.splitlines():
        parts = line.split()
        if len(parts) < 5 or parts[0].upper() != "TCP":
            continue
        local = parts[1]
        pid_text = parts[-1]
        if local.rsplit(":", 1)[-1] != str(port):
            continue
        try:
            pids.add(int(pid_text))
        except ValueError:
            continue
    return pids


def process_names(pids: set[int]) -> dict[int, str]:
    if not pids:
        return {}
    result = subprocess.run(
        ["wmic", "process", "get", "ProcessId,Name", "/format:csv"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
    )
    names: dict[int, str] = {}
    for row in csv.DictReader(io.StringIO(result.stdout)):
        try:
            pid = int(row.get("ProcessId") or 0)
        except ValueError:
            continue
        if pid in pids:
            names[pid] = row.get("Name") or ""
    return names


def terminate(pid: int) -> bool:
    result = subprocess.run(
        ["taskkill", "/PID", str(pid), "/T", "/F"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
    )
    return result.returncode == 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Terminate processes listening on a TCP port.")
    parser.add_argument("port", nargs="?", type=int, default=8888)
    args = parser.parse_args(argv)
    pids = tcp_pids_for_port(args.port)
    if not pids:
        print(f"No process on port {args.port}")
        return 0
    names = process_names(pids)
    failed = []
    for pid in sorted(pids):
        ok = terminate(pid)
        print(f"{'Stopped' if ok else 'Failed to stop'} PID {pid} {names.get(pid, '')} on port {args.port}".strip())
        if not ok:
            failed.append(pid)
    time.sleep(1.0)
    print("Done")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
