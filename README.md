# Agent Control Center

Local desktop control center for the machine's agent stack.

This project owns the Python control package, FastAPI API, React/Tailwind GUI, local diagnostics, logs, PID files, and desktop-friendly wrappers. It can operate OpenClaw Gateway, MoonBridge, Feishu Codex Agent, Codex provider mode, and Codex Desktop explicit actions from one local console.

The Feishu agent source and OpenClaw/Feishu connection configuration remain in `F:\1AI\feishu_agent`.

## Common Commands

```powershell
cd "F:\1AI\Agent control center"
E:\Python\python.exe -m feishu_stack.cli status --json
E:\Python\python.exe -m feishu_stack.cli stack start-moonbridge
E:\Python\python.exe -m feishu_stack.cli switch-provider moonbridge
E:\Python\python.exe -m feishu_stack.cli backups clean
```

## GUI

Start the local API and production GUI:

```powershell
F:\1AI\Agent control center\scripts\start-control-center.ps1
```

Open:

```text
http://127.0.0.1:8765
```

Install or refresh the desktop shortcut:

```powershell
F:\1AI\Agent control center\scripts\install-control-center-shortcut.ps1
```

## Development

Install Python dependencies:

```powershell
cd "F:\1AI\Agent control center"
E:\Python\python.exe -m pip install -e .[dev]
```

Run tests:

```powershell
E:\Python\python.exe -m pytest -q
```

Build the GUI:

```powershell
cd "F:\1AI\Agent control center\web"
npm install
npm run build
```

## Repository Boundaries

- `src/`: Python control package and FastAPI app
- `web/`: React/Tailwind GUI
- `scripts/`: desktop-friendly wrappers
- `config/`: local stack settings pointing at the real agent/runtime dependencies
- `docs/`: control center plans and operating notes
- `runtime/`: ignored local logs, PID files, and control token
- `tests/`: Python tests

Generated files, logs, PID files, tokens, SQLite files, `node_modules`, and frontend build output are not committed.
