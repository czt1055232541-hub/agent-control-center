from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from pathlib import Path

from feishu_stack.core.settings import StackConfig, load_config
from feishu_stack.core.log_manager import open_rotating
from feishu_stack.core.models import OperationResult
from feishu_stack.core.process import CREATE_NO_WINDOW, is_port_listening, process_info, read_pid, run_capture, terminate_pid, write_pid

PORT = 8765
EXCLUDED_PROCESS_MARKERS = (
    "openclaw",
    "codex-agent",
    "codex_desktop",
    "codex desktop",
)


def _web_dist_index(cfg: StackConfig) -> Path:
    return cfg.stack_root / "web" / "dist" / "index.html"


def _control_pid(cfg: StackConfig) -> Path:
    return cfg.pid_dir / "control-center-api.pid"


def _pythonpath_env(cfg: StackConfig) -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    src_path = str(cfg.stack_root / "src")
    env["PYTHONPATH"] = src_path + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    return env


def start(config: StackConfig | None = None, open_browser: bool = False, build: bool = True) -> OperationResult:
    cfg = config or load_config()
    started = time.monotonic()
    if is_port_listening(PORT):
        if open_browser:
            os.startfile(f"http://127.0.0.1:{PORT}")
        return OperationResult(True, "control-center", "start", "Control Center API is already listening.", port=PORT, duration_ms=int((time.monotonic() - started) * 1000))
    control_dir = cfg.stack_root
    web_dir = control_dir / "web"
    if build and not _web_dist_index(cfg).exists():
        install = run_capture([str(cfg.npm_exe), "install"], cwd=web_dir, timeout=180)
        if install.returncode != 0:
            return OperationResult(False, "control-center", "start", install.stderr or install.stdout, duration_ms=int((time.monotonic() - started) * 1000))
        build_result = run_capture([str(cfg.npm_exe), "run", "build"], cwd=web_dir, timeout=180)
        if build_result.returncode != 0:
            return OperationResult(False, "control-center", "start", build_result.stderr or build_result.stdout, duration_ms=int((time.monotonic() - started) * 1000))
    proc = subprocess.Popen(
        [str(cfg.python_exe), "-m", "uvicorn", "src.feishu_stack.api.app:app", "--host", "127.0.0.1", "--port", str(PORT)],
        cwd=str(control_dir),
        env=_pythonpath_env(cfg),
        stdin=subprocess.DEVNULL,
        stdout=open_rotating(cfg.log_dir / "control-center-api-out.log"),
        stderr=open_rotating(cfg.log_dir / "control-center-api-err.log"),
        creationflags=CREATE_NO_WINDOW,
    )
    write_pid(_control_pid(cfg), proc.pid)
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline and not is_port_listening(PORT):
        time.sleep(1)
    if open_browser:
        os.startfile(f"http://127.0.0.1:{PORT}")
    ready = is_port_listening(PORT)
    return OperationResult(
        ok=ready,
        component="control-center",
        action="start",
        message="Control Center API started." if ready else "Control Center API did not become ready.",
        pid=proc.pid,
        port=PORT,
        duration_ms=int((time.monotonic() - started) * 1000),
    )


def stop(config: StackConfig | None = None) -> OperationResult:
    cfg = config or load_config()
    started = time.monotonic()
    pid = read_pid(_control_pid(cfg))
    stopped = False
    if pid:
        running, name = process_info(pid)
        if running and name and "python" in name.lower():
            stopped = terminate_pid(pid)
    if _control_pid(cfg).exists():
        _control_pid(cfg).unlink(missing_ok=True)
    return OperationResult(
        ok=not is_port_listening(PORT),
        component="control-center",
        action="stop",
        message="Control Center API stopped." if stopped else "Control Center API stop requested.",
        pid=pid,
        port=PORT,
        duration_ms=int((time.monotonic() - started) * 1000),
    )


def status(config: StackConfig | None = None) -> dict:
    cfg = config or load_config()
    pid = read_pid(_control_pid(cfg))
    running, process_name = process_info(pid)
    return {
        "url": f"http://127.0.0.1:{PORT}",
        "port": PORT,
        "port_listening": is_port_listening(PORT),
        "pid": pid,
        "pid_running": running,
        "process_name": process_name,
        "gui_build": _web_dist_index(cfg).exists(),
        "stdout_log": str(cfg.log_dir / "control-center-api-out.log"),
        "stderr_log": str(cfg.log_dir / "control-center-api-err.log"),
    }


def install_shortcut(config: StackConfig | None = None) -> OperationResult:
    cfg = config or load_config()
    started = time.monotonic()
    desktop = Path.home() / "Desktop"
    desktop.mkdir(parents=True, exist_ok=True)
    launcher_path = desktop / "Agent Control Center.pyw"
    script = (cfg.stack_root / "scripts" / "stack.py").resolve()
    python_exe = Path(sys.executable).resolve()
    launcher_log = (cfg.log_dir / "control-center-launcher.log").resolve()
    launcher_path.write_text(
        "\n".join(
            [
                "from __future__ import annotations",
                "",
                "import os",
                "import subprocess",
                "import sys",
                "from pathlib import Path",
                "",
                f"STACK_ROOT = Path({str(cfg.stack_root.resolve())!r})",
                f"PYTHON_EXE = Path({str(python_exe)!r})",
                f"STACK_SCRIPT = Path({str(script)!r})",
                f"LAUNCHER_LOG = Path({str(launcher_log)!r})",
                "",
                "env = os.environ.copy()",
                "env.setdefault('PYTHONUTF8', '1')",
                "env.setdefault('PYTHONIOENCODING', 'utf-8')",
                "src_path = str(STACK_ROOT / 'src')",
                "env['PYTHONPATH'] = src_path + (os.pathsep + env['PYTHONPATH'] if env.get('PYTHONPATH') else '')",
                "LAUNCHER_LOG.parent.mkdir(parents=True, exist_ok=True)",
                "with LAUNCHER_LOG.open('a', encoding='utf-8') as log:",
                "    log.write('Launching Agent Control Center\\n')",
                "    log.flush()",
                "    subprocess.Popen(",
                "        [str(PYTHON_EXE), '-X', 'utf8', str(STACK_SCRIPT), 'serve-control-center', '--open'],",
                "        cwd=str(STACK_ROOT),",
                "        env=env,",
                "        stdin=subprocess.DEVNULL,",
                "        stdout=log,",
                "        stderr=log,",
                "        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),",
                "    )",
                "sys.exit(0)",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return OperationResult(
        True,
        "control-center",
        "install-shortcut",
        f"Created Python launcher: {launcher_path}",
        duration_ms=int((time.monotonic() - started) * 1000),
    )


def _safe_process_table() -> list[dict[str, object]]:
    try:
        import psutil  # type: ignore
    except Exception:
        return []

    rows: list[dict[str, object]] = []
    for proc in psutil.process_iter(["pid", "name", "exe", "cmdline", "ppid"]):
        try:
            rows.append(
                {
                    "pid": proc.pid,
                    "name": proc.info.get("name") or "",
                    "exe": proc.info.get("exe") or "",
                    "cmdline": " ".join(proc.info.get("cmdline") or []),
                    "cwd": proc.cwd(),
                }
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return rows


def _is_control_center_process(row: dict[str, object], cfg: StackConfig) -> bool:
    pid = int(row.get("pid") or 0)
    if pid <= 0:
        return False
    text = " ".join(str(row.get(key) or "") for key in ("name", "exe", "cmdline", "cwd")).lower()
    if any(marker in text for marker in EXCLUDED_PROCESS_MARKERS):
        return False
    if str(cfg.stack_root).lower() not in text:
        return False
    return (
        "serve-control-center" in text
        or "stop-control-center" in text
        or "status-control-center" in text
        or "src.feishu_stack.api.app:app" in text
        or "control-center" in text
        or f"--port {PORT}" in text
    )


def control_center_processes(config: StackConfig | None = None) -> list[dict[str, object]]:
    cfg = config or load_config()
    return [row for row in _safe_process_table() if _is_control_center_process(row, cfg)]


def _terminate_pids(pids: list[int], *, current_pid: int) -> None:
    try:
        import psutil  # type: ignore
    except Exception:
        return

    for pid in pids:
        if pid == current_pid:
            continue
        try:
            psutil.Process(pid).terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    deadline = time.monotonic() + 4
    while time.monotonic() < deadline:
        alive: list[int] = []
        for pid in pids:
            if pid == current_pid:
                continue
            try:
                if psutil.Process(pid).is_running():
                    alive.append(pid)
            except psutil.NoSuchProcess:
                pass
        if not alive:
            break
        time.sleep(0.2)
    for pid in pids:
        if pid == current_pid:
            continue
        try:
            psutil.Process(pid).kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue


def request_shutdown(config: StackConfig | None = None, *, delay_s: float = 0.4) -> OperationResult:
    cfg = config or load_config()
    started = time.monotonic()
    current_pid = os.getpid()
    pids = sorted({int(row["pid"]) for row in control_center_processes(cfg)})
    if current_pid not in pids:
        pids.append(current_pid)

    def _shutdown_later() -> None:
        time.sleep(delay_s)
        _terminate_pids(pids, current_pid=current_pid)
        if _control_pid(cfg).exists():
            _control_pid(cfg).unlink(missing_ok=True)
        os._exit(0)

    threading.Thread(target=_shutdown_later, name="control-center-shutdown", daemon=True).start()
    return OperationResult(
        ok=True,
        component="control-center",
        action="shutdown",
        message=f"Control Center shutdown scheduled for PIDs: {', '.join(str(pid) for pid in pids)}. OpenClaw and Codex processes are excluded.",
        pid=current_pid,
        port=PORT,
        duration_ms=int((time.monotonic() - started) * 1000),
    )
