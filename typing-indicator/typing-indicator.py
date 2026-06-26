#!/usr/bin/env python3
"""
B2 typing indicator — Python rewrite.
POST typing reaction on im.message.receive_v1, DELETE after 60s.
Run this as a child process of Codex Desktop App; kill it when the app exits.
"""

import json
import os
import signal
import subprocess
import sys
import threading
from datetime import datetime, timezone

# Fix Windows console encoding for emoji
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ─── Config ───────────────────────────────────────────────────────────────
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
LARK_CLI    = r"F:\1AI\feishu_agent\.npm-global\node_modules\@larksuite\cli\bin\lark-cli.exe"
PROFILE     = "cli_aaa600e91939dcd9"
CLEANUP_SEC = 60
MAX_AGE_MS  = 120_000  # skip messages older than 2 min
EXIT_FLAG   = threading.Event()

# Inline reaction payload — no external data.json needed
REACTION_BODY = json.dumps({"reaction_type": {"emoji_type": "Typing"}})
TMP_BODY      = os.path.join(SCRIPT_DIR, "tmp-typing-body.json")


# ─── Env helpers ──────────────────────────────────────────────────────────
def clean_env() -> dict:
    """os.environ minus OPENCLAW_* and CODEX_HOME."""
    env = os.environ.copy()
    for k in list(env):
        if k.startswith("OPENCLAW_") or k == "CODEX_HOME":
            del env[k]
    return env


# ─── Logging ──────────────────────────────────────────────────────────────
def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


# ─── lark-cli API wrapper ─────────────────────────────────────────────────
def lark_api(method: str, path: str, data: str | None = None) -> dict:
    """Run `lark-cli api <method> <path>` with profile, return {ok, stdout, stderr}."""
    cmd = [LARK_CLI, "api", method, path, "--profile", PROFILE]
    if data:
        # Write temporary body file so lark-cli --data @<file> works
        with open(TMP_BODY, "w", encoding="utf-8") as f:
            f.write(data)
        cmd += ["--data", f"@{TMP_BODY}"]

    try:
        r = subprocess.run(cmd, cwd=SCRIPT_DIR, env=clean_env(),
                           capture_output=True, text=True, timeout=15)
        return {"ok": r.returncode == 0, "stdout": r.stdout.strip(), "stderr": r.stderr.strip()}
    except Exception as e:
        return {"ok": False, "stdout": "", "stderr": str(e)}
    finally:
        # Clean up temp body file after every call
        try:
            if os.path.exists(TMP_BODY):
                os.remove(TMP_BODY)
        except OSError:
            pass


def api_add_typing(msg_id: str) -> str | None:
    """POST typing reaction → reaction_id or None."""
    r = lark_api("POST", f"/open-apis/im/v1/messages/{msg_id}/reactions", REACTION_BODY)
    if not r["ok"]:
        log(f"✗ POST failed: {r['stderr'][:200]}")
        return None
    try:
        j = json.loads(r["stdout"])
        if j.get("code") == 0 and j.get("data", {}).get("reaction_id"):
            return j["data"]["reaction_id"]
    except json.JSONDecodeError:
        pass
    log(f"✗ POST unexpected: {r['stdout'][:200]}")
    return None


def api_delete_typing(msg_id: str, reaction_id: str):
    """DELETE typing reaction."""
    r = lark_api("DELETE", f"/open-apis/im/v1/messages/{msg_id}/reactions/{reaction_id}")
    status = "OK" if r["ok"] else f"ERR"
    log(f"🗑️ Typing OFF  msg={msg_id}  {status}")


# ─── Cleanup scheduler ────────────────────────────────────────────────────
def schedule_cleanup(msg_id: str, reaction_id: str) -> threading.Timer:
    """Fire-and-forget DELETE after CLEANUP_SEC."""
    timer = threading.Timer(CLEANUP_SEC, api_delete_typing, args=[msg_id, reaction_id])
    timer.daemon = True
    timer.start()
    return timer


# ─── Signal handling (graceful exit) ──────────────────────────────────────
def on_shutdown(signum, frame):
    log(f"Received signal {signum}, shutting down...")
    EXIT_FLAG.set()


# ─── Main loop ────────────────────────────────────────────────────────────
def main():
    signal.signal(signal.SIGINT, on_shutdown)
    signal.signal(signal.SIGTERM, on_shutdown)

    log(f"🚀 Typing Indicator (B2 Python, {CLEANUP_SEC}s timeout)")
    log(f"   Profile: {PROFILE}")
    log(f"   lark-cli: {LARK_CLI}")

    # Clean up stale tmp files from previous runs
    if os.path.exists(TMP_BODY):
        try:
            os.remove(TMP_BODY)
        except OSError:
            pass

    cmd = [LARK_CLI, "event", "consume", "im.message.receive_v1",
           "--as", "bot", "--max-events", "0", "--timeout", "8760h",
           "--profile", PROFILE]
    log("   Connecting to bus...")
    proc = subprocess.Popen(cmd, cwd=SCRIPT_DIR, env=clean_env(),
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True)

    active: dict[str, dict] = {}  # msg_id → {reaction_id, timer}

    for line in proc.stdout:
        if EXIT_FLAG.is_set():
            proc.terminate()
            break

        line = line.strip()
        if not line:
            continue

        # Parse event
        try:
            evt = json.loads(line)
            msg_id = evt.get("event", {}).get("message", {}).get("message_id")
            if not msg_id or msg_id in active:
                continue

            ct = evt.get("event", {}).get("message", {}).get("create_time", "0")
            now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            if now_ms - int(ct) > MAX_AGE_MS:
                continue
        except (json.JSONDecodeError, ValueError, KeyError):
            continue

        # POST typing reaction
        rid = api_add_typing(msg_id)
        if rid:
            log(f"✔ Typing ON  msg={msg_id}")
            timer = schedule_cleanup(msg_id, rid)
            active[msg_id] = {"reaction_id": rid, "timer": timer}
        else:
            log(f"✗ FAILED  msg={msg_id}")

    # Drain stderr on exit
    if proc.stderr:
        for line in proc.stderr:
            line = line.strip()
            if line:
                log(f"⚠ stderr: {line[:300]}")

    # ── Flush all pending timers before exit ─────────────────────
    log(f"Flushing {len(active)} pending cleanup(s)...")
    for msg_id, entry in active.items():
        entry["timer"].cancel()
        log(f"🗑️ Force cleanup: {msg_id}")
        api_delete_typing(msg_id, entry["reaction_id"])
    active.clear()

    log(f"Consumer exited. Shutdown complete.")


if __name__ == "__main__":
    main()
