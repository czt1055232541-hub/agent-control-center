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
