# Python Maintenance Refactor Plan

Last updated: 2026-06-18

## Current State

The Feishu/Codex stack now has a Python-first control package under `control-center`, a FastAPI local API, and a React/Tailwind GUI. The stack can operate OpenClaw, MoonBridge, Feishu Codex Agent, Codex provider mode, diagnostics, logs, and backup cleanup from Python.

Several PowerShell files still exist for compatibility and double-click usage, but they should no longer own core business logic. Their long-term role is to locate the repository, call `E:\Python\python.exe -m feishu_stack.cli ...`, and exit with the Python command status.

Current boundaries:

- `E:\codeX` remains the real `CODEX_HOME`.
- `F:\1AI\feishu_agent` remains the unified management repository.
- Runtime files under `runtime\`, frontend build output, `node_modules`, tokens, logs, PID files, sqlite files, and caches stay ignored by git.
- Codex DB and historical rollout files are not modified.

## Target Architecture

Python is the source of truth for all maintainable behavior:

- Provider switching edits `E:\codeX\config.toml` directly with line-preserving helpers.
- Backup cleanup is implemented in Python and preserves `config.toml.bak-goal-*`.
- Stack start/stop/restart and diagnostics run through Python modules and CLI commands.
- FastAPI calls Python modules directly, not PowerShell scripts.
- React GUI consumes FastAPI only.
- PowerShell remains as compatibility wrappers for old paths and desktop double-click entry.

Primary Python commands:

```powershell
cd F:\1AI\feishu_agent\control-center
E:\Python\python.exe -m feishu_stack.cli status --json
E:\Python\python.exe -m feishu_stack.cli start openclaw
E:\Python\python.exe -m feishu_stack.cli start moonbridge
E:\Python\python.exe -m feishu_stack.cli start codex-agent
E:\Python\python.exe -m feishu_stack.cli start codex-desktop
E:\Python\python.exe -m feishu_stack.cli restart codex-desktop
E:\Python\python.exe -m feishu_stack.cli stack start-moonbridge
E:\Python\python.exe -m feishu_stack.cli stack stop
E:\Python\python.exe -m feishu_stack.cli switch-provider native
E:\Python\python.exe -m feishu_stack.cli switch-provider moonbridge
E:\Python\python.exe -m feishu_stack.cli backups clean
E:\Python\python.exe -m feishu_stack.cli doctor codex
E:\Python\python.exe -m feishu_stack.cli serve-control-center --open
E:\Python\python.exe -m feishu_stack.cli install-shortcut
```

## Migration Phases

### Phase A: Replace the Plan Document

Replace the old phase log with this Python maintenance plan. The old Phase 0-5 notes are superseded because they mixed historical progress with future work and no longer reflected the actual architecture.

### Phase B: Move Provider and Backup Logic to Python

Provider switching is owned by Python:

- `native` sets `model = "gpt-5.5"`.
- `moonbridge` sets `model = "moonbridge"`, `model_provider = "moonbridge"`, context window, model catalog, and `[model_providers.moonbridge]`.
- Each switch creates `config.toml.bak-switch-*`.
- Only the latest switch backup is retained.
- `switch-provider native` replaces the old restore-native behavior.

Backup cleanup is owned by Python:

- Keep latest `config.toml.bak-switch-*`.
- Keep latest `config.toml.bak-restore-native-*`.
- Preserve all `config.toml.bak-goal-*`.

### Phase C: Move Stack and Control Center Entrypoints to Python

Python CLI owns:

- stack start native
- stack start moonbridge
- stack stop
- control center start/stop/status
- shortcut installation

PowerShell wrappers remain only for compatibility:

- `scripts\start-all.ps1`
- `scripts\stop-all.ps1`
- `scripts\status-all.ps1`
- `scripts\start-control-center.ps1`
- `scripts\stop-control-center.ps1`
- `scripts\status-control-center.ps1`
- `scripts\install-control-center-shortcut.ps1`
- `codex\Switch-CodexProvider.ps1`
- `codex\Restore-CodexNative.ps1`
- `codex\Clean-CodexBackups.ps1`
- `codex\Get-CodexProviderStatus.ps1`

### Phase D: Improve the GUI Runtime Model

The GUI exposes one combined `Codex Runtime` panel:

- Codex Desktop status
- Codex Desktop Start / Stop / Restart / Logs
- Codex provider mode
- Native / MoonBridge switch buttons

Stop and Restart for Codex Desktop remain dangerous actions and require second confirmation. Automated tests do not execute real Codex Desktop stop/restart.

## Compatibility Rules

- Existing PowerShell entry paths remain callable.
- PowerShell wrappers must not duplicate provider switching, backup cleanup, stack orchestration, or diagnostics logic.
- The GUI must not call PowerShell directly.
- The FastAPI server must bind to `127.0.0.1`.
- Write APIs require `X-Control-Token`.
- `stack stop` stops OpenClaw, MoonBridge, and Feishu Codex Agent only; it does not stop Codex Desktop.
- Codex Desktop stop/restart is explicit and isolated.

## Test Plan

Python tests:

```powershell
cd F:\1AI\feishu_agent\control-center
E:\Python\python.exe -m pytest -q
```

Frontend build:

```powershell
cd F:\1AI\feishu_agent\control-center\web
npm run build
```

PowerShell wrapper syntax:

```powershell
cd F:\1AI\feishu_agent
[scriptblock]::Create((Get-Content scripts\start-all.ps1 -Raw))
[scriptblock]::Create((Get-Content codex\Switch-CodexProvider.ps1 -Raw))
```

Integration checks:

- Switch provider `native -> moonbridge`, then leave final mode as `moonbridge`.
- Run backup cleanup and verify switch/restore backup counts are each at most 1.
- Verify goal backups still exist.
- Verify Control Center is reachable at `http://127.0.0.1:8765`.
- Verify Codex Desktop remains running.
- Verify OpenClaw, MoonBridge, and Feishu Codex Agent match expected final state.

## Operational Usage

Start the GUI:

```powershell
F:\1AI\feishu_agent\scripts\start-control-center.ps1
```

Open:

```text
http://127.0.0.1:8765
```

Use Python directly for maintainable operations:

```powershell
cd F:\1AI\feishu_agent\control-center
E:\Python\python.exe -m feishu_stack.cli status --json
E:\Python\python.exe -m feishu_stack.cli stack start-moonbridge
E:\Python\python.exe -m feishu_stack.cli backups clean
```

Push changes:

```powershell
cd F:\1AI\feishu_agent
git status
git add -A
git commit -m "Describe the change"
git push
```
