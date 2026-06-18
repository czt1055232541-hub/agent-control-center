# Python-First GUI Control Center Plan

## Goal

Build a local GUI control center for operating the Feishu/Codex stack without opening PowerShell for routine work.

The GUI must support independent start, stop, restart, status, logs, and provider switching for:

- OpenClaw Gateway
- MoonBridge
- Feishu Codex Agent
- Codex provider mode: `native` / `moonbridge`

It must not stop Codex Desktop, rewrite Codex sqlite databases, or mutate historical rollout files.

## Architecture Decision

Use Python as the primary control layer.

PowerShell remains useful, but it should become a compatibility and fallback layer, not the main source of control logic.

### Why Python First

- Python process control is easier to test and maintain than scattered PowerShell scripts.
- FastAPI provides a clean local API for the GUI.
- Python can return typed JSON objects consistently.
- `pytest` makes status, process, and provider switching logic testable.
- The same Python control package can support a web GUI, CLI, future Electron wrapper, or tray app.
- Existing PowerShell scripts can be preserved as wrappers while behavior is migrated gradually.

### Role Split

```text
Python:
  - status model
  - process start/stop/restart
  - PID file handling
  - port checks
  - log tailing
  - provider config edits
  - operation locking
  - FastAPI local server
  - tests

PowerShell:
  - legacy wrappers
  - double-click entry scripts
  - Windows-specific fallback commands
  - compatibility with existing start-all.ps1 / stop-all.ps1
```

## Proposed Structure

```text
F:\1AI\feishu_agent\
  control-center\
    pyproject.toml
    README.md
    src\
      feishu_stack\
        __init__.py
        app.py                 # FastAPI local API
        cli.py                 # Python CLI for scripts/wrappers
        config.py              # stack.settings.json loader
        models.py              # typed status/result models
        process.py             # process start/stop/PID/port helpers
        status.py              # aggregate status
        openclaw.py            # OpenClaw Gateway operations
        moonbridge.py          # MoonBridge operations
        codex_agent.py         # Feishu Codex Agent operations
        codex_provider.py      # native/moonbridge config switching
        logs.py                # log tail helpers
        operations.py          # operation lock and audit log
        security.py            # localhost token and request guard
    tests\
      test_status.py
      test_process.py
      test_codex_provider.py
    web\
      package.json
      src\
        App.tsx
        api.ts
        components\
        pages\
  scripts\
    start-control-center.ps1
    start-all.ps1
    stop-all.ps1
  config\
    stack.settings.json
  docs\
    gui-control-center-plan.md
```

## Configuration

`config\stack.settings.json` should become the canonical machine-readable config.

Python should read this JSON directly. `config\paths.ps1` can remain for legacy scripts, but should not be the primary source for the GUI.

Recommended JSON fields:

```json
{
  "codexHome": "E:\\codeX",
  "codexBin": "E:\\codeX\\bin\\codex.exe",
  "codexConfig": "E:\\codeX\\config.toml",
  "moonbridge": {
    "dir": "E:\\codeX\\moon-bridge",
    "exe": "E:\\codeX\\moon-bridge\\.cache\\moonbridge.exe",
    "config": "E:\\codeX\\moon-bridge\\config.yml",
    "port": 38440
  },
  "openclaw": {
    "home": "E:\\openclaw\\clawclaw",
    "gatewayCmd": "E:\\openclaw\\clawclaw\\.openclaw\\gateway.cmd",
    "port": 18789
  },
  "agent": {
    "dir": "F:\\1AI\\feishu_agent\\agents\\feishu-codex-agent",
    "entry": "dist\\src\\index.js"
  }
}
```

## Product Scope

### MVP

- Show current status:
  - Codex model and provider
  - OpenClaw port and PID status
  - MoonBridge port and PID status
  - Feishu Codex Agent PID status
  - Codex Desktop read-only presence
- Independently operate components:
  - OpenClaw Gateway: start, stop, restart
  - MoonBridge: start, stop, restart
  - Feishu Codex Agent: start, stop, restart
- Switch Codex provider:
  - `native`
  - `moonbridge`
  - show latest backup file
- Run grouped actions:
  - start native stack
  - start moonbridge stack
  - stop stack, excluding Codex Desktop
- Show logs:
  - OpenClaw stdout/stderr
  - MoonBridge stdout/stderr
  - Feishu Codex Agent stdout/stderr
  - recent operation log

### Later Versions

- `codex doctor --summary` panel
- MoonBridge `/v1/models` panel
- Lark CLI auth status panel
- backup cleanup button
- cross-provider resume/fork validation button
- Electron or tray wrapper
- optional startup shortcut

## Python Control Layer

The Python package is the source of truth for GUI operations.

### Core Models

Use typed dataclasses or Pydantic models:

- `ComponentStatus`
- `StackStatus`
- `OperationResult`
- `ProviderStatus`
- `LogTail`

### Process Rules

- Start child processes hidden.
- Redirect stdout/stderr to `runtime\logs`.
- Write PID files under `runtime\pids`.
- Validate both PID and port because processes can be started outside the GUI.
- Stop by PID first, then controlled fallback by port.
- Never stop Codex Desktop.

### Provider Switching Rules

Python can either:

1. call the existing `codex\Switch-CodexProvider.ps1` initially, then migrate logic later, or
2. directly edit `E:\codeX\config.toml` using a TOML-aware or line-preserving config helper.

Recommended first implementation: call the existing script for safety, then migrate after tests cover the behavior.

## Local API

Use FastAPI under `control-center/src/feishu_stack/app.py`.

Rules:

- Bind only to `127.0.0.1`
- Use a local token for write operations
- Do not expose arbitrary command execution
- Enforce a single operation lock for start/stop/switch actions
- Capture stdout, stderr, exit code, start time, end time, and duration

### API Endpoints

```text
GET  /api/status

POST /api/openclaw/start
POST /api/openclaw/stop
POST /api/openclaw/restart

POST /api/moonbridge/start
POST /api/moonbridge/stop
POST /api/moonbridge/restart

POST /api/codex-agent/start
POST /api/codex-agent/stop
POST /api/codex-agent/restart

POST /api/codex-provider/native
POST /api/codex-provider/moonbridge

POST /api/stack/start-native
POST /api/stack/start-moonbridge
POST /api/stack/stop

GET  /api/logs/openclaw
GET  /api/logs/moonbridge
GET  /api/logs/codex-agent
GET  /api/logs/operations

POST /api/backups/clean
GET  /api/doctor/codex
```

## GUI Design

Build a dense operational dashboard, not a landing page.

First screen:

- Top status strip:
  - Codex provider mode
  - OpenClaw status
  - MoonBridge status
  - Codex Agent status
- Component panels:
  - OpenClaw Gateway: start, stop, restart, log
  - MoonBridge: start, stop, restart, log
  - Feishu Codex Agent: start, stop, restart, log
- Provider panel:
  - segmented control: `Native` / `MoonBridge`
  - switch button
  - latest backup display
- Stack actions:
  - start native stack
  - start moonbridge stack
  - stop stack
- Operation log:
  - last 20 actions
  - status, duration, stdout/stderr link

UX rules:

- Disable action buttons while another operation is running.
- Confirm provider switches and stop actions.
- Never show a "Stop Codex Desktop" action.
- Show exact failing operation and stderr on failure.
- Auto-refresh status every 2 seconds.

## Implementation Phases

### Phase 0: Goal Definition

Before implementation, define the initial goal precisely:

- target GUI type: browser-based local app first
- Python runtime choice
- whether to use FastAPI + React/Vite
- which operations must ship in MVP
- acceptable behavior when a component was started outside the GUI
- whether the current provider should remain unchanged after GUI tests

### Phase 1: Python Control Package

Deliverables:

- `control-center\pyproject.toml`
- `feishu_stack.config`
- `feishu_stack.models`
- `feishu_stack.process`
- `feishu_stack.status`
- component modules for OpenClaw, MoonBridge, and Codex Agent
- Python CLI commands:
  - `status`
  - `start openclaw`
  - `stop openclaw`
  - `start moonbridge`
  - `stop moonbridge`
  - `start codex-agent`
  - `stop codex-agent`
  - `switch-provider native`
  - `switch-provider moonbridge`

Validation:

- `python -m feishu_stack.cli status --json`
- each component can start/stop independently
- logs and PID files are written consistently
- Codex Desktop remains running

### Phase 2: FastAPI Local Server

Deliverables:

- local API server
- operation lock
- structured error responses
- read-only status endpoint
- start/stop/restart endpoints
- provider switch endpoints

Validation:

- API calls work from `127.0.0.1`
- concurrent writes are rejected or queued
- failed operations return actionable errors

### Phase 3: Web GUI MVP

Deliverables:

- React/Vite frontend
- status dashboard
- component action buttons
- provider switch control
- operation log panel

Validation:

- GUI operates OpenClaw, MoonBridge, and Codex Agent independently
- GUI switches `native` / `moonbridge`
- GUI reflects status changes after operations

### Phase 4: Logs and Diagnostics

Deliverables:

- log tail API
- log viewer UI
- Codex doctor panel
- MoonBridge models check
- Lark CLI auth status check
- backup cleanup action

Validation:

- common startup failures can be diagnosed from GUI
- runtime logs remain ignored by git

### Phase 5: Desktop Convenience

Deliverables:

- `scripts\start-control-center.ps1`
- browser auto-open
- optional Electron wrapper or tray app

Validation:

- double-click script opens the GUI
- GUI works after reboot with no manual terminal setup

## Testing Plan

- Python tests:
  - config loading
  - PID handling
  - port detection
  - provider parsing
  - operation locking
- API tests:
  - `GET /api/status`
  - start/stop/restart endpoint smoke tests
  - provider switch endpoint smoke tests
- UI tests:
  - dashboard renders
  - buttons disable during operations
  - logs render
  - status auto-refresh updates after a state change
- Integration:
  - start native stack
  - start moonbridge stack
  - stop stack without stopping Codex Desktop

## Risks

- Components can be started outside the GUI, so status must validate both PID files and ports.
- OpenClaw stop behavior may require both gateway command and port fallback.
- Codex provider switch changes `E:\codeX\config.toml`; active Codex Desktop threads may not immediately reflect the change.
- Hidden non-interactive `codex fork` is not suitable for automated GUI validation because it requires a terminal.
- Direct TOML editing should remain conservative until tests cover the exact config transformations.

## First Implementation Target

Start with Phase 0 and Phase 1.

The first build should not include Electron. A local Python API plus CLI gives a stable foundation, and the GUI can sit on top once process control is proven.

## Current Progress

Last updated: 2026-06-18

### Implemented

Phase 1 is implemented as a Python control package plus CLI under `control-center`.

Implemented files:

- `control-center\pyproject.toml`
- `control-center\README.md`
- `control-center\src\feishu_stack\config.py`
- `control-center\src\feishu_stack\models.py`
- `control-center\src\feishu_stack\process.py`
- `control-center\src\feishu_stack\status.py`
- `control-center\src\feishu_stack\openclaw.py`
- `control-center\src\feishu_stack\moonbridge.py`
- `control-center\src\feishu_stack\codex_agent.py`
- `control-center\src\feishu_stack\codex_provider.py`
- `control-center\src\feishu_stack\logs.py`
- `control-center\src\feishu_stack\cli.py`
- `control-center\tests\`

Implemented capabilities:

- Load machine-readable stack config from `config\stack.settings.json`.
- Report unified stack status as human-readable text or stable JSON.
- Detect current Codex provider and model from `E:\codeX\config.toml`.
- Detect Codex Desktop in read-only mode; the control package never stops it.
- Start, stop, and restart OpenClaw Gateway.
- Start, stop, and restart MoonBridge.
- Start, stop, and restart Feishu Codex Agent.
- Build Feishu Codex Agent automatically when `dist\src\index.js` is missing.
- Switch Codex provider to `native` or `moonbridge` by calling the existing PowerShell switching script.
- Start child processes hidden and redirect stdout/stderr to `runtime\logs`.
- Store process IDs in `runtime\pids`.
- Determine status by combining PID files and port checks.
- Stop by PID first, then use port-based fallback where applicable.
- Tail runtime logs through the Python logs module.
- Run unit tests with `pytest`.

Validated commands:

```powershell
cd F:\1AI\feishu_agent\control-center
E:\Python\python.exe -m pip install -e .[dev]
E:\Python\python.exe -m compileall src tests
E:\Python\python.exe -m pytest -q
E:\Python\python.exe -m feishu_stack.cli status --json
E:\Python\python.exe -m feishu_stack.cli stop codex-agent --json
E:\Python\python.exe -m feishu_stack.cli start codex-agent --json
E:\Python\python.exe -m feishu_stack.cli restart codex-agent --json
E:\Python\python.exe -m feishu_stack.cli stop moonbridge --json
E:\Python\python.exe -m feishu_stack.cli start moonbridge --json
E:\Python\python.exe -m feishu_stack.cli restart moonbridge --json
E:\Python\python.exe -m feishu_stack.cli stop openclaw --json
E:\Python\python.exe -m feishu_stack.cli start openclaw --json
E:\Python\python.exe -m feishu_stack.cli restart openclaw --json
E:\Python\python.exe -m feishu_stack.cli switch-provider native --json
E:\Python\python.exe -m feishu_stack.cli switch-provider moonbridge --json
```

Current validation result:

- Python syntax check passed.
- `pytest` passed.
- OpenClaw, MoonBridge, and Feishu Codex Agent independent start/stop/restart were validated.
- Provider switching via the existing PowerShell script was validated for `native` and `moonbridge`.
- Codex Desktop remained running during validation.
- Final tested provider state after integration validation was `moonbridge`.

### Manual Usage

Install or refresh the editable Python package:

```powershell
cd F:\1AI\feishu_agent\control-center
E:\Python\python.exe -m pip install -e .[dev]
```

Check full stack status:

```powershell
E:\Python\python.exe -m feishu_stack.cli status
E:\Python\python.exe -m feishu_stack.cli status --json
```

Operate OpenClaw Gateway:

```powershell
E:\Python\python.exe -m feishu_stack.cli start openclaw
E:\Python\python.exe -m feishu_stack.cli stop openclaw
E:\Python\python.exe -m feishu_stack.cli restart openclaw
```

Operate MoonBridge:

```powershell
E:\Python\python.exe -m feishu_stack.cli start moonbridge
E:\Python\python.exe -m feishu_stack.cli stop moonbridge
E:\Python\python.exe -m feishu_stack.cli restart moonbridge
```

Operate Feishu Codex Agent:

```powershell
E:\Python\python.exe -m feishu_stack.cli start codex-agent
E:\Python\python.exe -m feishu_stack.cli stop codex-agent
E:\Python\python.exe -m feishu_stack.cli restart codex-agent
```

Switch Codex provider:

```powershell
E:\Python\python.exe -m feishu_stack.cli switch-provider native
E:\Python\python.exe -m feishu_stack.cli switch-provider moonbridge
```

Use `--json` after any command when another tool or GUI needs a stable machine-readable response:

```powershell
E:\Python\python.exe -m feishu_stack.cli restart moonbridge --json
```

Runtime files:

- Logs: `F:\1AI\feishu_agent\runtime\logs`
- PID files: `F:\1AI\feishu_agent\runtime\pids`
- Runtime files are ignored by git.

### Manual Verification Checklist

1. Run tests:

```powershell
cd F:\1AI\feishu_agent\control-center
E:\Python\python.exe -m pytest -q
```

Expected result: all tests pass.

2. Check status:

```powershell
E:\Python\python.exe -m feishu_stack.cli status --json
```

Expected result:

- `codex.provider` reflects the current provider.
- `openclaw`, `moonbridge`, and `codex_agent` show PID and/or port information when running.
- `codex_desktop_running` is reported, but no command stops Codex Desktop.

3. Restart one component at a time:

```powershell
E:\Python\python.exe -m feishu_stack.cli restart openclaw --json
E:\Python\python.exe -m feishu_stack.cli restart moonbridge --json
E:\Python\python.exe -m feishu_stack.cli restart codex-agent --json
```

Expected result: each command returns `ok: true`, writes logs, and updates the related PID file.

4. Switch provider:

```powershell
E:\Python\python.exe -m feishu_stack.cli switch-provider native --json
E:\Python\python.exe -m feishu_stack.cli status --json
E:\Python\python.exe -m feishu_stack.cli switch-provider moonbridge --json
E:\Python\python.exe -m feishu_stack.cli status --json
```

Expected result: provider status changes between `native` and `moonbridge`. Active Codex Desktop sessions may need a manual refresh or new session to reflect provider changes.

5. Confirm git hygiene:

```powershell
cd F:\1AI\feishu_agent
git status --short
```

Expected result: no runtime logs, PID files, sqlite files, `node_modules`, Python caches, or editable-install metadata should appear as tracked changes.

### Remaining Work

Phase 2 is not started:

- FastAPI local server.
- Local write-operation token.
- Single operation lock for concurrent start/stop/switch requests.
- API-level structured error responses.

Phase 3 is not started:

- React/Vite GUI.
- Dashboard status panels.
- Component action buttons.
- Provider segmented control.
- Operation log panel.

Phase 4 is not started:

- Browser log viewer.
- Codex doctor panel.
- MoonBridge models check panel.
- Lark CLI auth status panel.
- Backup cleanup action in GUI.

Phase 5 is not started:

- `scripts\start-control-center.ps1`.
- Auto-open browser.
- Optional desktop wrapper or tray app.

### Known Limitations

- Provider switching still delegates to `codex\Switch-CodexProvider.ps1`; Python does not directly rewrite TOML yet.
- Phase 2/3 now provide FastAPI and a React GUI; Phase 4 diagnostics and Phase 5 desktop convenience are still pending.
- Active Codex Desktop conversations may not immediately adopt a changed provider until Codex refreshes or a new session is opened.
- Cross-provider conversation inheritance remains a Codex behavior limitation; the earlier verification path still favors resume/fork testing or summary migration rather than database edits.

## Phase 2/3 Progress

Last updated: 2026-06-18

Phase 2 and Phase 3 are implemented as a local FastAPI server plus a React/Vite/Tailwind GUI.

Implemented capabilities:

- `GET /api/status` exposes stack status without a token.
- `GET /api/session` returns the local control token for the same-origin GUI.
- Write APIs require `X-Control-Token`.
- Operation locking rejects concurrent write operations with a busy response.
- Operation results are recorded in memory and appended to `runtime\logs\operations.jsonl`.
- The API can start, stop, and restart OpenClaw, MoonBridge, and Feishu Codex Agent.
- The API can switch Codex provider to `native` or `moonbridge`.
- The API includes `POST /api/codex-desktop/stop` as an explicit dangerous action.
- `POST /api/stack/stop` does not stop Codex Desktop.
- The GUI shows status panels, component controls, provider controls, stack actions, logs, and operation history.
- The GUI includes a dangerous `Stop Codex Desktop` button with a second confirmation step.

Run the local API and production GUI:

```powershell
cd F:\1AI\feishu_agent\control-center
E:\Python\python.exe -m uvicorn feishu_stack.app:app --host 127.0.0.1 --port 8765
```

Open:

```text
http://127.0.0.1:8765
```

Build or rebuild the GUI:

```powershell
cd F:\1AI\feishu_agent\control-center\web
npm install
npm run build
```

Development server:

```powershell
cd F:\1AI\feishu_agent\control-center\web
npm run dev
```

Validation completed:

- `E:\Python\python.exe -m pytest -q` passed with 12 tests.
- `npm run build` passed.
- FastAPI started on `127.0.0.1:8765`.
- Real API integration verified:
  - restart OpenClaw
  - restart MoonBridge
  - restart Feishu Codex Agent
  - switch provider to `native`
  - switch provider back to `moonbridge`
- Final status after validation:
  - Codex provider: `moonbridge`
  - OpenClaw listening on port `18789`
  - MoonBridge listening on port `38440`
  - Feishu Codex Agent running
  - Codex Desktop still running

Codex Desktop stop validation:

- The route and GUI button were implemented.
- Unit tests validate token/route behavior through a mock.
- The real `POST /api/codex-desktop/stop` action was not executed.

Remaining work:

- Phase 4 diagnostics panels are not implemented yet.
- Phase 5 desktop convenience script/tray/Electron work is not implemented yet.
- Production GUI requires `web\dist`; this build output is intentionally ignored by git.

## Phase 4/5 Progress

Last updated: 2026-06-18

Phase 4 and the script-based part of Phase 5 are implemented.

Implemented diagnostics:

- `GET /api/doctor/codex`
- `GET /api/moonbridge/models`
- `GET /api/lark/auth-status`
- `GET /api/diagnostics`
- `POST /api/backups/clean`
- GUI Diagnostics panel for Codex doctor, MoonBridge models, Lark auth status, and backup cleanup.
- Log viewer supports OpenClaw, MoonBridge, Codex Agent, Control Center API, and Operations logs.

Implemented desktop convenience:

- `scripts\start-control-center.ps1`
- `scripts\stop-control-center.ps1`
- `scripts\status-control-center.ps1`
- `scripts\install-control-center-shortcut.ps1`
- Desktop shortcut: `Feishu Codex Control Center.lnk`

Run:

```powershell
cd F:\1AI\feishu_agent
.\scripts\start-control-center.ps1
.\scripts\status-control-center.ps1
.\scripts\install-control-center-shortcut.ps1
```

Open:

```text
http://127.0.0.1:8765
```

Notes:

- Backup cleanup keeps the latest `config.toml.bak-switch-*` and latest `config.toml.bak-restore-native-*`; `config.toml.bak-goal-*` is preserved.
- `scripts\stop-control-center.ps1` stops only the Control Center API.
- Electron/tray wrapper remains unimplemented by design.
