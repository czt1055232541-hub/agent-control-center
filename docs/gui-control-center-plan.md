# GUI Control Center Implementation Plan

## Goal

Build a local GUI for operating the Feishu/Codex stack without opening PowerShell for routine work.

The GUI must support independent start, stop, restart, status, logs, and provider switching for:

- OpenClaw Gateway
- MoonBridge
- Feishu Codex Agent
- Codex provider mode: `native` / `moonbridge`

It must not stop Codex Desktop, rewrite Codex sqlite databases, or mutate historical rollout files.

## Product Scope

### MVP

- Show current stack status:
  - Codex model and provider
  - OpenClaw port and PID status
  - MoonBridge port and PID status
  - Feishu Codex Agent PID status
  - Codex Desktop read-only presence
- Operate each component independently:
  - Start OpenClaw Gateway
  - Stop OpenClaw Gateway
  - Restart OpenClaw Gateway
  - Start MoonBridge
  - Stop MoonBridge
  - Restart MoonBridge
  - Start Feishu Codex Agent
  - Stop Feishu Codex Agent
  - Restart Feishu Codex Agent
- Switch Codex provider:
  - Switch to `native`
  - Switch to `moonbridge`
  - Show latest provider backup file
- Run bundled operations:
  - Start native stack
  - Start moonbridge stack
  - Stop stack, excluding Codex Desktop
- Show logs:
  - OpenClaw stdout/stderr
  - MoonBridge stdout/stderr
  - Feishu Codex Agent stdout/stderr
  - Recent operation log

### Later Versions

- `codex doctor --summary` panel
- MoonBridge `/v1/models` panel
- Lark CLI auth status panel
- Backup cleanup button
- Cross-provider resume/fork validation button
- Electron tray app
- Optional startup shortcut

## Architecture

Use a local web control center first, then optionally wrap it with Electron.

```text
F:\1AI\feishu_agent\
  scripts\
    lib\
      Stack.Control.psm1
    start-openclaw.ps1
    stop-openclaw.ps1
    start-moonbridge.ps1
    stop-moonbridge.ps1
    start-codex-agent.ps1
    stop-codex-agent.ps1
  control-center\
    package.json
    server\
      src\
        index.ts
        powershell.ts
        operations.ts
        status.ts
    web\
      src\
        App.tsx
        components\
        pages\
  docs\
    gui-control-center-plan.md
```

## Control Layer

The GUI must not parse human-oriented PowerShell text. First, create a stable PowerShell control layer with JSON output.

### New Shared Module

`scripts\lib\Stack.Control.psm1`

Responsibilities:

- Load `config\paths.ps1`
- Test TCP ports
- Read and validate PID files
- Start hidden processes
- Stop by PID file
- Stop by port fallback
- Read Codex provider mode
- Switch Codex provider mode
- Return structured objects suitable for `ConvertTo-Json`

### New Component Scripts

Each script should support `-Json` and `-NoPause`.

```powershell
.\scripts\start-openclaw.ps1 -Json
.\scripts\stop-openclaw.ps1 -Json
.\scripts\start-moonbridge.ps1 -Json
.\scripts\stop-moonbridge.ps1 -Json
.\scripts\start-codex-agent.ps1 -Json
.\scripts\stop-codex-agent.ps1 -Json
.\scripts\status-all.ps1 -Json
```

Existing `start-all.ps1` and `stop-all.ps1` stay as compatibility wrappers.

## Local API

Build a Node/TypeScript server under `control-center/server`.

Rules:

- Bind only to `127.0.0.1`
- Use a local token for write operations
- Only execute allowlisted scripts
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
  - Segmented control: `Native` / `MoonBridge`
  - Switch button
  - Latest backup display
- Stack actions:
  - Start native stack
  - Start moonbridge stack
  - Stop stack
- Operation log:
  - Last 20 actions
  - Status, duration, stdout/stderr link

UX rules:

- Disable action buttons while another operation is running
- Confirm provider switches and stop actions
- Never show a "Stop Codex Desktop" action
- Show exact failing script and stderr on failure
- Auto-refresh status every 2 seconds

## Implementation Phases

### Phase 1: PowerShell Control API

Deliverables:

- `scripts\lib\Stack.Control.psm1`
- Component start/stop scripts
- `status-all.ps1 -Json`
- Existing wrapper compatibility preserved

Validation:

- PowerShell parse checks pass
- Each component can start/stop independently
- JSON output is stable and machine-readable
- Codex Desktop remains running

### Phase 2: Node Local Server

Deliverables:

- `control-center/server`
- Allowlisted PowerShell runner
- Operation lock
- Status endpoint
- Component start/stop/restart endpoints
- Provider switch endpoints

Validation:

- API calls work from localhost
- Concurrent write operations are rejected or queued
- Failed PowerShell scripts return structured errors

### Phase 3: Web GUI MVP

Deliverables:

- `control-center/web`
- Status dashboard
- Component action buttons
- Provider switch control
- Operation log panel

Validation:

- GUI can operate OpenClaw, MoonBridge, and Codex Agent independently
- GUI can switch `native` / `moonbridge`
- GUI reflects current state after operations

### Phase 4: Logs and Diagnostics

Deliverables:

- Log tail API
- Log viewer UI
- Codex doctor panel
- MoonBridge models check
- Lark CLI auth status check
- Backup cleanup action

Validation:

- Common startup failures can be diagnosed from GUI
- Runtime logs remain ignored by git

### Phase 5: Desktop Convenience

Deliverables:

- `scripts\start-control-center.ps1`
- Browser auto-open
- Optional Electron wrapper

Validation:

- Double-click script opens the GUI
- GUI works after reboot with no manual terminal setup

## Testing Plan

- PowerShell syntax:
  - All `scripts\*.ps1`
  - All `codex\*.ps1`
  - `scripts\lib\Stack.Control.psm1`
- API tests:
  - `GET /api/status`
  - Start/stop/restart endpoint smoke tests
  - Provider switch endpoint smoke tests
- UI tests:
  - Dashboard renders
  - Buttons disable during operations
  - Logs render
  - Status auto-refresh updates after a state change
- Integration:
  - Start native stack
  - Start moonbridge stack
  - Stop stack without stopping Codex Desktop

## Risks

- PowerShell process control can become inconsistent if a component is started outside the GUI.
- OpenClaw stop behavior depends on the gateway process and port fallback.
- Codex provider switch changes `E:\codeX\config.toml`; active Codex Desktop threads may not immediately reflect the change.
- Hidden non-interactive `codex fork` is not suitable for automated GUI validation because it requires a terminal.

## First Implementation Target

Start with Phase 1 and Phase 2 only.

Do not build Electron first. A local web GUI is enough to validate the control model and avoid locking the project into the wrong desktop packaging approach.
