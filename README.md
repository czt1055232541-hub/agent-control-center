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

## Codex App And MoonBridge Mode

The control center keeps Codex provider switching in the user-level `E:\codeX\config.toml`.
When the official Codex app writes an app-managed CLI path under `CODEX_CLI_PATH`, the
control center uses that path for Feishu Codex Agent startup and falls back to the
configured `codexBin` only when the app-managed path is unavailable. This keeps the
agent aligned with Codex app updates whose CLI lives under versioned app runtime folders.

MoonBridge mode expects MoonBridge to be listening at the configured base URL, currently:

```text
http://127.0.0.1:38440/v1
```

Use these checks after switching provider or updating the Codex app:

```powershell
E:\Python\python.exe -m feishu_stack.cli start moonbridge
E:\Python\python.exe -m feishu_stack.cli switch-provider moonbridge
curl http://127.0.0.1:38440/v1/models
E:\Python\python.exe -m feishu_stack.cli start codex-agent
```

`codex-agent` startup intentionally sanitizes only its child-process environment for
agent-source auto-detection variables such as `OPENCLAW_HOME`, `CLAW_HOME`,
`HERMES_HOME`, and `LARK_CHANNEL`. This prevents lark-cli from accidentally entering an
OpenClaw binding flow while preserving the real OpenClaw gateway and Feishu multi-agent
environment outside that child process. Do not run `lark-cli config bind` as part of
normal `codex-agent` startup; binding changes identity policy and should remain an
explicit operational action.

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
