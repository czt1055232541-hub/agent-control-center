#!/usr/bin/env python3
"""
Launcher: starts typing-indicator.py and keeps it alive as long as
the codex lark-cli bus is running. Single-click to run both.

Usage: python launcher.py
  or:  pythonw launcher.py  (no console window)
"""

import os
import subprocess
import sys
import time
import signal
import psutil

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON = r"E:\Python\python.exe"
TYPING_SCRIPT = os.path.join(SCRIPT_DIR, "typing-indicator.py")
BUS_PROFILE = "cli_aaa600e91939dcd9"

typing_proc = None
shutdown = False


def find_codex_bus_pid() -> int | None:
    """Find the lark-cli _bus process for the codex profile."""
    for proc in psutil.process_iter(["pid", "cmdline"]):
        try:
            cmd = proc.info["cmdline"] or []
            if len(cmd) >= 2:
                # match: lark-cli.exe event _bus --profile cli_aaa600e91939dcd9
                if "event" in cmd and "_bus" in cmd and BUS_PROFILE in cmd:
                    return proc.info["pid"]
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return None


def start_typing():
    global typing_proc
    typing_proc = subprocess.Popen(
        [PYTHON, TYPING_SCRIPT],
        cwd=SCRIPT_DIR,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    print(f"[launcher] typing-indicator started (PID {typing_proc.pid})")


def stop_typing():
    global typing_proc
    if typing_proc and typing_proc.poll() is None:
        print(f"[launcher] stopping typing-indicator (PID {typing_proc.pid})")
        typing_proc.terminate()
        try:
            typing_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            typing_proc.kill()
        print(f"[launcher] typing-indicator stopped")


def on_exit(signum=None, frame=None):
    global shutdown
    shutdown = True
    print("[launcher] shutting down...")


def main():
    global shutdown
    signal.signal(signal.SIGINT, on_exit)
    signal.signal(signal.SIGTERM, on_exit)

    print("[launcher] waiting for codex bus...")
    while not shutdown:
        bus_pid = find_codex_bus_pid()
        if bus_pid:
            print(f"[launcher] codex bus found (PID {bus_pid})")
            break
        time.sleep(2)

    if shutdown:
        return

    restart_count = 0
    start_typing()

    while not shutdown:
        time.sleep(3)

        # Check bus still alive
        bus_pid = find_codex_bus_pid()
        if not bus_pid:
            print("[launcher] codex bus disappeared — stopping")
            stop_typing()
            break

        # Check typing indicator health
        if typing_proc and typing_proc.poll() is not None:
            rc = typing_proc.returncode
            print(f"[launcher] typing-indicator exited (code {rc})")
            if restart_count < 5 and not shutdown:
                restart_count += 1
                print(f"[launcher] restarting ({restart_count}/5)...")
                time.sleep(3)
                start_typing()
            else:
                print("[launcher] restart limit reached — giving up")
                break

    stop_typing()
    print("[launcher] done")


if __name__ == "__main__":
    if find_codex_bus_pid() is None:
        print("[launcher] WARNING: codex bus not found. Will wait for it.")
    main()
